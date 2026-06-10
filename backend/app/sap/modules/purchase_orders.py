"""SAP B1 Purchase Orders / Quotations / Requests.

Plan: docs/modules/04-purchasing.md
Akış: PurchaseRequest → PurchaseOrder → PurchaseDelivery → PurchaseInvoice
BaseType referansları:
  PurchaseRequest (OPRQ)  → 1470000113
  PurchaseOrder (OPOR)    → 22
  PurchaseDelivery (OPDN) → 20
"""
from __future__ import annotations

from typing import Any

from app.sap.client import SAPServiceLayerClient
from app.sap.odata import ODataQuery

PURCHASE_REQUEST_BASE_TYPE = 1470000113
PURCHASE_ORDER_BASE_TYPE = 22
PURCHASE_DELIVERY_BASE_TYPE = 20

DEFAULT_WAREHOUSE = "01"


class PurchaseOrdersModule:
    REQUESTS = "/PurchaseRequests"
    QUOTATIONS = "/PurchaseQuotations"
    ORDERS = "/PurchaseOrders"
    DELIVERY = "/PurchaseDeliveryNotes"
    INVOICE = "/PurchaseInvoices"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # ------------------------------------------------------------------ #
    # Purchase Orders                                                       #
    # ------------------------------------------------------------------ #

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /PurchaseOrders — serbest form payload."""
        return await self.client.post(self.ORDERS, payload)

    async def create_from_request(
        self,
        request_doc_entry: int,
        vendor_card_code: str,
        *,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Purchase Request'ten satınalma siparişi oluşturur (BaseType=1470000113)."""
        req = await self.client.get(f"{self.REQUESTS}({request_doc_entry})")
        lines = req.get("DocumentLines", []) or []

        payload: dict[str, Any] = {
            "CardCode": vendor_card_code,
            "DocDate": req.get("DocDate"),
            "DocDueDate": req.get("DocDueDate"),
            "Comments": req.get("Comments"),
            "DocumentLines": [
                {
                    "BaseType": PURCHASE_REQUEST_BASE_TYPE,
                    "BaseEntry": request_doc_entry,
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
        return await self.create(payload)

    async def get(self, doc_entry: int) -> dict[str, Any]:
        return await self.client.get(f"{self.ORDERS}({doc_entry})")

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
        resp = await self.client.get(self.ORDERS, **query.build())
        return resp.get("value", [])

    async def cancel(self, doc_entry: int) -> None:
        await self.client.post(f"{self.ORDERS}({doc_entry})/Cancel", {})

    async def close(self, doc_entry: int) -> None:
        await self.client.post(f"{self.ORDERS}({doc_entry})/Close", {})

    # ------------------------------------------------------------------ #
    # Purchase Requests                                                     #
    # ------------------------------------------------------------------ #

    async def create_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /PurchaseRequests."""
        return await self.client.post(self.REQUESTS, payload)

    async def get_request(self, doc_entry: int) -> dict[str, Any]:
        return await self.client.get(f"{self.REQUESTS}({doc_entry})")

    async def list_requests(
        self,
        *,
        top: int = 50,
        skip: int = 0,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        query = ODataQuery().top(top).skip(skip).orderby("DocEntry", "desc")
        if filter_expr:
            query.filter(filter_expr)
        resp = await self.client.get(self.REQUESTS, **query.build())
        return resp.get("value", [])

    # ------------------------------------------------------------------ #
    # Purchase Delivery Notes                                               #
    # ------------------------------------------------------------------ #

    async def create_delivery(
        self,
        order_doc_entry: int,
        *,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Satınalma irsaliyesi oluşturur (PurchaseOrder referansı, BaseType=22)."""
        order = await self.client.get(f"{self.ORDERS}({order_doc_entry})")
        lines = order.get("DocumentLines", []) or []

        payload: dict[str, Any] = {
            "CardCode": order["CardCode"],
            "DocDate": order.get("DocDate"),
            "DocumentLines": [
                {
                    "BaseType": PURCHASE_ORDER_BASE_TYPE,
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
        return await self.client.post(self.DELIVERY, payload)

    # ------------------------------------------------------------------ #
    # Purchase Invoices                                                     #
    # ------------------------------------------------------------------ #

    async def create_invoice(
        self,
        delivery_doc_entry: int,
        *,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Satınalma faturası — Delivery Note referansı (BaseType=20)."""
        dn = await self.client.get(f"{self.DELIVERY}({delivery_doc_entry})")
        lines = dn.get("DocumentLines", []) or []

        payload: dict[str, Any] = {
            "CardCode": dn["CardCode"],
            "DocDate": dn.get("DocDate"),
            "DocumentLines": [
                {
                    "BaseType": PURCHASE_DELIVERY_BASE_TYPE,
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
        return await self.client.post(self.INVOICE, payload)
