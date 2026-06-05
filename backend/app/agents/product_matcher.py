"""ProductMatcher — PDF satırını SAP Item ile eşler.

Stratejiler (sırayla, ilki bulduğunda durur):
  1. Barkod exact
  2. ItemCode exact (PDF'ten gelen kod ile)
  3. Müşteri-özel ürün alias
  4. Fuzzy ad (rapidfuzz token_set_ratio) > 85
  5. pgvector semantic search (description embedding) — Faz 2'de aktif

Skor < 0.85 → human-in-the-loop. Her satır için ayrı eşleme + en yakın 5 aday döner.
"""
from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.schemas import ExtractedLine, ProductMatch
from app.db.models import CustomerAlias, ItemCache

FUZZY_THRESHOLD = 85
HIGH_CONFIDENCE = 0.85
MAX_CANDIDATES = 5
NAME_TOKEN_LIMIT = 300


class ProductMatcherAgent(BaseAgent):
    name = "product_matcher"

    async def _run(
        self,
        ctx: AgentContext,
        lines: list[ExtractedLine | dict[str, Any]] | None = None,
        customer_card_code: str | None = None,
        db: AsyncSession | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if db is None:
            raise ValueError("db session zorunlu")
        if not lines:
            raise ValueError("lines boş olamaz")

        parsed = [
            line if isinstance(line, ExtractedLine) else ExtractedLine.model_validate(line)
            for line in lines
        ]

        matches: list[ProductMatch] = []
        for line in parsed:
            matches.append(await self._match_line(db, line, customer_card_code))

        scores = [m.score for m in matches]
        avg = sum(scores) / len(scores) if scores else 0.0
        unmatched = [m for m in matches if not m.item_code]
        low_confidence = [m for m in matches if m.score < HIGH_CONFIDENCE]
        needs_human = bool(unmatched or low_confidence)
        reason: str | None = None
        if needs_human:
            if unmatched:
                reason = f"{len(unmatched)} ürün eşleşmedi"
            else:
                reason = f"{len(low_confidence)} satırda düşük güven"

        return AgentResult(
            agent_name=self.name,
            success=True,
            confidence=avg,
            data={"matches": [m.model_dump() for m in matches]},
            needs_human=needs_human,
            human_reason=reason,
        )

    async def _match_line(
        self,
        db: AsyncSession,
        line: ExtractedLine,
        customer_card_code: str | None,
    ) -> ProductMatch:
        if line.barcode:
            item = await _by_barcode(db, line.barcode)
            if item:
                return _exact(line.line_no, item, "barcode")

        if line.item_code_raw:
            item = await _by_code(db, line.item_code_raw)
            if item:
                return _exact(line.line_no, item, "code")

        if customer_card_code and line.description:
            aliased = await _by_alias(db, customer_card_code, line.description)
            if aliased:
                return aliased.model_copy(update={"line_no": line.line_no})

        if line.description:
            return await _fuzzy(db, line.line_no, line.description)

        return ProductMatch(line_no=line.line_no)


async def _by_barcode(db: AsyncSession, barcode: str) -> ItemCache | None:
    result = await db.execute(select(ItemCache).where(ItemCache.bar_code == barcode))
    return result.scalars().first()


async def _by_code(db: AsyncSession, code: str) -> ItemCache | None:
    result = await db.execute(select(ItemCache).where(ItemCache.item_code == code))
    return result.scalars().first()


async def _by_alias(
    db: AsyncSession, card_code: str, description: str
) -> ProductMatch | None:
    lower = description.lower()
    result = await db.execute(
        select(CustomerAlias, ItemCache)
        .join(ItemCache, ItemCache.item_code == CustomerAlias.target_code)
        .where(CustomerAlias.card_code == card_code)
        .where(CustomerAlias.alias_lower == lower)
        .where(CustomerAlias.target_kind == "item")
        .limit(1)
    )
    row = result.first()
    if not row:
        return None
    alias, item = row
    return ProductMatch(
        line_no=0,
        item_code=item.item_code,
        item_name=item.item_name,
        score=float(alias.confidence),
        strategy="alias",
    )


async def _fuzzy(db: AsyncSession, line_no: int, description: str) -> ProductMatch:
    token = description.split()[0].lower() if description else ""
    stmt = (
        select(ItemCache)
        .where(ItemCache.item_name_lower.like(f"%{token}%"))
        .limit(NAME_TOKEN_LIMIT)
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().all())
    if not candidates:
        return ProductMatch(line_no=line_no)
    names = [c.item_name for c in candidates]
    best = process.extractOne(description, names, scorer=fuzz.token_set_ratio)
    if not best:
        return ProductMatch(line_no=line_no)
    _, score, index = best
    summary = lambda it: {  # noqa: E731
        "item_code": it.item_code,
        "item_name": it.item_name,
        "bar_code": it.bar_code,
    }
    if score < FUZZY_THRESHOLD:
        return ProductMatch(
            line_no=line_no,
            candidates=[summary(c) for c in candidates[:MAX_CANDIDATES]],
        )
    item = candidates[index]
    others = [summary(c) for c in candidates[:MAX_CANDIDATES] if c.item_code != item.item_code]
    return ProductMatch(
        line_no=line_no,
        item_code=item.item_code,
        item_name=item.item_name,
        score=score / 100,
        strategy="fuzzy_name",
        candidates=others,
    )


def _exact(line_no: int, item: ItemCache, strategy: str) -> ProductMatch:
    return ProductMatch(
        line_no=line_no,
        item_code=item.item_code,
        item_name=item.item_name,
        score=1.0,
        strategy=strategy,
    )
