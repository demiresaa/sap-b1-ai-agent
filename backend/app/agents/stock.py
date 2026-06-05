"""Stock — ItemsService_GetItemAvailability sorgular.

Sales Order için zorunlu, Quotation için opsiyonel (yine uyarı çıkar).
Deterministik (LLM kullanmaz).
"""
from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.schemas import ExtractedLine, ProductMatch, StockCheck
from app.sap import SAPError, pool
from app.sap.modules import ItemsModule


class StockAgent(BaseAgent):
    name = "stock"
    model = "n/a"

    async def _run(
        self,
        ctx: AgentContext,
        lines: list[ExtractedLine | dict[str, Any]] | None = None,
        matches: list[ProductMatch | dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if not lines or not matches:
            raise ValueError("lines ve matches zorunlu")

        parsed_lines = [
            line if isinstance(line, ExtractedLine) else ExtractedLine.model_validate(line)
            for line in lines
        ]
        match_by_line = {
            (m.line_no if isinstance(m, ProductMatch) else m["line_no"]): (
                m if isinstance(m, ProductMatch) else ProductMatch.model_validate(m)
            )
            for m in matches
        }

        checks: list[StockCheck] = []
        async with pool.acquire() as client:
            items_module = ItemsModule(client)
            for line in parsed_lines:
                match = match_by_line.get(line.line_no)
                if not match or not match.item_code:
                    continue
                available = await _availability(items_module, match.item_code)
                in_stock = available is not None and available >= line.quantity
                note = (
                    None
                    if in_stock or available is None
                    else f"Yetersiz stok: talep {line.quantity}, mevcut {available}"
                )
                checks.append(
                    StockCheck(
                        line_no=line.line_no,
                        item_code=match.item_code,
                        requested_qty=line.quantity,
                        available_qty=available,
                        in_stock=in_stock,
                        note=note,
                    )
                )

        shortages = [c for c in checks if not c.in_stock]
        needs_human = bool(shortages)
        reason = f"{len(shortages)} satırda stok yetersiz" if shortages else None
        confidence = 1.0 if not shortages else 0.6

        return AgentResult(
            agent_name=self.name,
            success=True,
            confidence=confidence,
            data={"checks": [c.model_dump() for c in checks]},
            needs_human=needs_human,
            human_reason=reason,
        )


async def _availability(items_module: ItemsModule, item_code: str) -> float | None:
    try:
        resp = await items_module.availability(item_code)
    except SAPError:
        return None
    val = resp.get("Available")
    if val is None:
        val = resp.get("InStock")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None
