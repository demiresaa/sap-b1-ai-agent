"""SAP B1 Delivery Notes (İrsaliye).

STATUS: Faz 2 — placeholder
Plan: docs/modules/02-delivery-notes.md

TODO Faz 2:
  - POST /DeliveryNotes (yeni irsaliye)
  - BaseType=17 (Sales Order) ile referanslı kopya
  - Partial delivery (satır bazında miktar)
  - e-İrsaliye XML üretimi (TR mevzuat)
"""
from __future__ import annotations

from app.sap.client import SAPServiceLayerClient


class DeliveryNotesModule:
    PATH = "/DeliveryNotes"
    SALES_ORDER_BASE_TYPE = 17

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # TODO: implement in Faz 2
