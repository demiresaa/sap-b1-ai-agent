"""SAP B1 Purchase Orders / Quotations / Requests.

STATUS: Faz 2 — placeholder
Plan: docs/modules/04-purchasing.md

TODO Faz 2:
  - POST /PurchaseRequests (düşük stok auto-trigger)
  - POST /PurchaseQuotations (tedarikçi teklif)
  - POST /PurchaseOrders (onaylı satınalma)
  - PR → PQ → PO dönüşüm akışı
  - Vendor Matcher Agent (BP CardType='S')
"""
from __future__ import annotations

from app.sap.client import SAPServiceLayerClient


class PurchaseOrdersModule:
    REQUESTS = "/PurchaseRequests"
    QUOTATIONS = "/PurchaseQuotations"
    ORDERS = "/PurchaseOrders"
    DELIVERY = "/PurchaseDeliveryNotes"
    INVOICE = "/PurchaseInvoices"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # TODO: implement in Faz 2
