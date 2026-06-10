"""SAP B1 A/R Invoices (Müşteri Faturası).

Plan: docs/modules/03-invoices.md
Endpoint: /Invoices, /CreditNotes
BaseType referansları:
  Delivery Note (ODLN) → 15
  Sales Order (ORDR)   → 17
  Invoice (OINV)       → 13  (CreditNote için)
"""
from __future__ import annotations

from typing import Any

from app.sap.client import SAPServiceLayerClient
from app.sap.odata import ODataQuery

DELIVERY_NOTE_BASE_TYPE = 15
SALES_ORDER_BASE_TYPE = 17
INVOICE_BASE_TYPE = 13


class InvoicesModule:
    PATH = "/Invoices"
    CREDIT_NOTE_PATH = "/CreditNotes"
    DELIVERY_NOTE_BASE_TYPE = DELIVERY_NOTE_BASE_TYPE
    SALES_ORDER_BASE_TYPE = SALES_ORDER_BASE_TYPE

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    async def create_from_delivery(
        self,
        delivery_doc_entry: int,
        *,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Delivery Note referansı ile fatura oluşturur (BaseType=15)."""
        dn = await self.client.get(f"/DeliveryNotes({delivery_doc_entry})")
        lines = dn.get("DocumentLines", []) or []

        payload: dict[str, Any] = {
            "CardCode": dn["CardCode"],
            "DocDate": dn.get("DocDate"),
            "DocDueDate": dn.get("DocDueDate"),
            "DocCurrency": dn.get("DocCurrency"),
            "NumAtCard": dn.get("NumAtCard"),
            "Comments": dn.get("Comments"),
            "DocumentLines": [
                {
                    "BaseType": DELIVERY_NOTE_BASE_TYPE,
                    "BaseEntry": delivery_doc_entry,
                    "BaseLine": line.get("LineNum", idx),
                    "Quantity": line["Quantity"],
                }
                for idx, line in enumerate(lines)
            ],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        if overrides:
            payload.update(overrides)
        return await self.client.post(self.PATH, payload)

    async def create_from_order(
        self,
        order_doc_entry: int,
        *,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sales Order referansı ile direkt fatura oluşturur (BaseType=17).

        İrsaliye atlanır — küçük işletmelerde yaygın akış.
        """
        order = await self.client.get(f"/Orders({order_doc_entry})")
        lines = order.get("DocumentLines", []) or []

        payload: dict[str, Any] = {
            "CardCode": order["CardCode"],
            "DocDate": order.get("DocDate"),
            "DocDueDate": order.get("DocDueDate"),
            "DocCurrency": order.get("DocCurrency"),
            "NumAtCard": order.get("NumAtCard"),
            "Comments": order.get("Comments"),
            "DocumentLines": [
                {
                    "BaseType": SALES_ORDER_BASE_TYPE,
                    "BaseEntry": order_doc_entry,
                    "BaseLine": line.get("LineNum", idx),
                    "Quantity": line["Quantity"],
                }
                for idx, line in enumerate(lines)
            ],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        if overrides:
            payload.update(overrides)
        return await self.client.post(self.PATH, payload)

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /Invoices — serbest form payload."""
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

    async def credit_note(
        self,
        invoice_doc_entry: int,
        *,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fatura referansı ile iade (Credit Note) oluşturur (BaseType=13)."""
        inv = await self.client.get(f"{self.PATH}({invoice_doc_entry})")
        lines = inv.get("DocumentLines", []) or []

        payload: dict[str, Any] = {
            "CardCode": inv["CardCode"],
            "DocDate": inv.get("DocDate"),
            "DocCurrency": inv.get("DocCurrency"),
            "DocumentLines": [
                {
                    "BaseType": INVOICE_BASE_TYPE,
                    "BaseEntry": invoice_doc_entry,
                    "BaseLine": line.get("LineNum", idx),
                    "Quantity": line["Quantity"],
                }
                for idx, line in enumerate(lines)
            ],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        if overrides:
            payload.update(overrides)
        return await self.client.post(self.CREDIT_NOTE_PATH, payload)
