"""SAP B1 IncomingPayments / VendorPayments.

STATUS: Faz 2 — placeholder
Plan: docs/modules/09-payments.md

TODO Faz 2:
  - POST /IncomingPayments (tahsilat)
  - POST /VendorPayments (tediye)
  - Banka ekstresi (MT940/CSV) parse + auto-match
"""
from __future__ import annotations

from app.sap.client import SAPServiceLayerClient


class PaymentsModule:
    INCOMING = "/IncomingPayments"
    VENDOR = "/VendorPayments"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # TODO: implement in Faz 2
