"""Pricing — PDF fiyatı ile SAP fiyat listesini karşılaştırır.

MVP davranışı:
  - Her satır için extracted unit_price ile cache'teki son fiyatı karşılaştırır.
  - Fiyat farkı %5'ten fazla ya da iskonto %15'i geçtiyse `breaches_threshold=True`.
  - Toplam tutar config eşiğini aştıysa flag basılır.

NOT: SAP B1'de PriceList → SpecialPrices zinciri karmaşık. Bu MVP, ItemCache'teki
son satış fiyatını referans alır; Faz 2'de `/PriceLists` + `/SpecialPrices` GET
eklenir.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.schemas import ExtractedLine, PricingCheck, ProductMatch
from app.db.models import ItemCache

PRICE_DELTA_THRESHOLD_PCT = 5.0
DISCOUNT_THRESHOLD_PCT = 15.0


class PricingAgent(BaseAgent):
    name = "pricing"

    async def _run(
        self,
        ctx: AgentContext,
        lines: list[ExtractedLine | dict[str, Any]] | None = None,
        matches: list[ProductMatch | dict[str, Any]] | None = None,
        db: AsyncSession | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if db is None:
            raise ValueError("db session zorunlu")
        if not lines or not matches:
            raise ValueError("lines ve matches zorunlu")

        parsed_lines = [
            line if isinstance(line, ExtractedLine) else ExtractedLine.model_validate(line)
            for line in lines
        ]
        parsed_matches = {
            m.line_no if isinstance(m, ProductMatch) else m["line_no"]: (
                m if isinstance(m, ProductMatch) else ProductMatch.model_validate(m)
            )
            for m in matches
        }

        checks: list[PricingCheck] = []
        for line in parsed_lines:
            match = parsed_matches.get(line.line_no)
            sap_price = await _sap_list_price(db, match.item_code) if match and match.item_code else None
            check = _compare(line, sap_price)
            checks.append(check)

        breaches = [c for c in checks if c.breaches_threshold]
        needs_human = bool(breaches)
        reason = None
        if needs_human:
            reason = f"{len(breaches)} satırda fiyat/iskonto eşik aşıldı"
        avg_conf = 1.0 if not breaches else 0.7

        return AgentResult(
            agent_name=self.name,
            success=True,
            confidence=avg_conf,
            data={"checks": [c.model_dump() for c in checks]},
            needs_human=needs_human,
            human_reason=reason,
        )


def _compare(line: ExtractedLine, sap_price: float | None) -> PricingCheck:
    delta_pct: float | None = None
    breaches = False
    note: str | None = None

    if line.unit_price is not None and sap_price is not None and sap_price > 0:
        delta_pct = ((line.unit_price - sap_price) / sap_price) * 100
        if abs(delta_pct) > PRICE_DELTA_THRESHOLD_PCT:
            breaches = True
            note = f"Fiyat sapması %{delta_pct:.1f} (eşik %{PRICE_DELTA_THRESHOLD_PCT:.0f})"
    elif line.unit_price is None:
        note = "PDF'te fiyat bulunamadı"

    if line.discount_pct is not None and line.discount_pct > DISCOUNT_THRESHOLD_PCT:
        breaches = True
        note = (note + "; " if note else "") + (
            f"İskonto %{line.discount_pct:.1f} > eşik %{DISCOUNT_THRESHOLD_PCT:.0f}"
        )

    return PricingCheck(
        line_no=line.line_no,
        extracted_price=line.unit_price,
        sap_list_price=sap_price,
        delta_pct=delta_pct,
        discount_pct=line.discount_pct,
        breaches_threshold=breaches,
        note=note,
    )


async def _sap_list_price(db: AsyncSession, item_code: str) -> float | None:
    """MVP: ItemCache.raw içinden son satış fiyatı (varsa). Faz 2'de gerçek price list."""
    result = await db.execute(select(ItemCache).where(ItemCache.item_code == item_code))
    item = result.scalars().first()
    if not item or not item.raw:
        return None
    raw = item.raw
    price = raw.get("LastPurchasePrice") or raw.get("AvgStdPrice")
    try:
        return float(price) if price is not None else None
    except (TypeError, ValueError):
        return None
