"""SAP B1 Delivery Notes (İrsaliye).

Plan: docs/modules/02-delivery-notes.md
Endpoint: /DeliveryNotes
BaseType referansı:
  Sales Order (ORDR) → 17
"""
from __future__ import annotations

from typing import Any

from app.sap.client import SAPServiceLayerClient
from app.sap.odata import ODataQuery

DEFAULT_WAREHOUSE = "01"


class DeliveryNotesModule:
    PATH = "/DeliveryNotes"
    SALES_ORDER_BASE_TYPE = 17

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    async def create_from_order(
        self,
        order_doc_entry: int,
        *,
        ship_date: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sales Order referansı ile Delivery Note oluşturur (BaseType=17).

        SAP line bazında BaseType/BaseEntry/BaseLine ile referansı çözer;
        sipariş miktar ve fiyatı otomatik kopyalanır. Kısmi teslimat için
        overrides["DocumentLines"] içinde Quantity alanını override et.
        """
        order = await self.client.get(f"/Orders({order_doc_entry})")
        lines = order.get("DocumentLines", []) or []

        payload: dict[str, Any] = {
            "CardCode": order["CardCode"],
            "DocDate": ship_date or order.get("DocDate"),
            "DocDueDate": ship_date or order.get("DocDueDate"),
            "DocCurrency": order.get("DocCurrency"),
            "NumAtCard": order.get("NumAtCard"),
            "Comments": order.get("Comments"),
            "DocumentLines": [
                {
                    "BaseType": self.SALES_ORDER_BASE_TYPE,
                    "BaseEntry": order_doc_entry,
                    "BaseLine": line.get("LineNum", idx),
                    "Quantity": line["Quantity"],
                    "WarehouseCode": line.get("WarehouseCode", DEFAULT_WAREHOUSE),
                }
                for idx, line in enumerate(lines)
            ],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        if overrides:
            payload.update(overrides)
        return await self.client.post(self.PATH, payload)

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /DeliveryNotes — serbest form payload."""
        return await self.client.post(self.PATH, payload)

    async def get(self, doc_entry: int) -> dict[str, Any]:
        return await self.client.get(f"{self.PATH}({doc_entry})")

    async def list(
        self,
        *,
        top: int = 50,
        skip: int = 0,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        query = ODataQuery().top(top).skip(skip).orderby("DocEntry", "desc")
        if filter_expr:
            query.filter(filter_expr)
        resp = await self.client.get(self.PATH, **query.build())
        return resp.get("value", [])

    async def cancel(self, doc_entry: int) -> None:
        await self.client.post(f"{self.PATH}({doc_entry})/Cancel", {})

    async def close(self, doc_entry: int) -> None:
        await self.client.post(f"{self.PATH}({doc_entry})/Close", {})
