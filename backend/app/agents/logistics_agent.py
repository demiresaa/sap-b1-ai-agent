"""LogisticsAgent — Delivery Note oluşturma ve sevkiyat tarihi önerisi.

Akış:
  1. SAP Sales Order'ı okur, açık satır miktar/stok kontrol eder.
  2. Tüm satırlar stokta varsa → Delivery Note oluşturur (dry-run modunda simüle eder).
  3. Stok yetersizse → needs_human=True, kısmi teslimat önerisi sunar.

LLM kullanmaz — deterministik lojistik kurallar.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.config import settings
from app.sap import SAPError, pool
from app.sap.modules import DeliveryNotesModule, ItemsModule

logger = logging.getLogger(__name__)

LEAD_TIME_DAYS = 3  # Varsayılan teslim süresi — SAP item'da yoksa


class LogisticsAgent(BaseAgent):
    name = "logistics"
    model = "n/a"

    async def _run(
        self,
        ctx: AgentContext,
        order_doc_entry: int | None = None,
        ship_date: str | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if order_doc_entry is None:
            raise ValueError("order_doc_entry zorunlu")

        async with pool.acquire() as client:
            dn_module = DeliveryNotesModule(client)
            items_module = ItemsModule(client)

            order = await client.get(f"/Orders({order_doc_entry})")
            lines = order.get("DocumentLines", []) or []

            # Satır bazında stok kontrol
            shortages: list[dict[str, Any]] = []
            for line in lines:
                item_code = line.get("ItemCode")
                requested_qty = float(line.get("Quantity", 0))
                if not item_code or requested_qty <= 0:
                    continue
                available = await _get_available(items_module, item_code)
                if available is not None and available < requested_qty:
                    shortages.append({
                        "item_code": item_code,
                        "requested": requested_qty,
                        "available": available,
                    })

            # Sevkiyat tarihi önerisi
            suggested_date = ship_date or _suggest_ship_date(bool(shortages))

            if shortages and not ship_date:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    confidence=0.5,
                    data={
                        "order_doc_entry": order_doc_entry,
                        "shortages": shortages,
                        "suggested_ship_date": suggested_date,
                        "delivery_created": False,
                    },
                    needs_human=True,
                    human_reason=(
                        f"{len(shortages)} satırda stok yetersiz — "
                        "kısmi teslimat veya erteleme gerekli"
                    ),
                )

            # Stok tamam (veya tarih açıkça verilmiş) → Delivery Note oluştur
            if settings.sap_dry_run:
                logger.info(
                    "[logistics] dry-run: Order %d için İrsaliye simüle edildi",
                    order_doc_entry,
                )
                dn_result: dict[str, Any] = {
                    "DocEntry": None,
                    "DocNum": None,
                    "dry_run": True,
                }
            else:
                dn_result = await dn_module.create_from_order(
                    order_doc_entry, ship_date=suggested_date
                )
                logger.info(
                    "[logistics] İrsaliye oluşturuldu: DocEntry=%s DocNum=%s",
                    dn_result.get("DocEntry"),
                    dn_result.get("DocNum"),
                )

            return AgentResult(
                agent_name=self.name,
                success=True,
                confidence=1.0,
                data={
                    "order_doc_entry": order_doc_entry,
                    "shortages": shortages,
                    "suggested_ship_date": suggested_date,
                    "delivery_created": not settings.sap_dry_run,
                    "delivery_doc_entry": dn_result.get("DocEntry"),
                    "delivery_doc_num": dn_result.get("DocNum"),
                    "dry_run": settings.sap_dry_run,
                },
                needs_human=False,
            )


async def _get_available(items_module: ItemsModule, item_code: str) -> float | None:
    try:
        resp = await items_module.availability(item_code)
        val = resp.get("Available") or resp.get("InStock")
        return float(val) if val is not None else None
    except SAPError:
        return None


def _suggest_ship_date(has_shortages: bool) -> str:
    extra_days = LEAD_TIME_DAYS * 2 if has_shortages else LEAD_TIME_DAYS
    return (datetime.now(UTC) + timedelta(days=extra_days)).strftime("%Y-%m-%d")
