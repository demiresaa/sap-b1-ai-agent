"""SAP B1 A/R Invoices.

STATUS: Faz 2 — placeholder
Plan: docs/modules/03-invoices.md

TODO Faz 2:
  - POST /Invoices (DN referanslı, BaseType=15)
  - CreditNote (iade)
  - e-Fatura UBL 2.1 üretimi (TR GİB entegratör)
"""
from __future__ import annotations

from app.sap.client import SAPServiceLayerClient


class InvoicesModule:
    PATH = "/Invoices"
    DELIVERY_NOTE_BASE_TYPE = 15

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # TODO: implement in Faz 2
