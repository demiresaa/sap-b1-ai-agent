"""SAP B1 Production Orders + BOM (ProductTrees).

STATUS: Faz 3 — placeholder
Plan: docs/modules/06-production.md

TODO Faz 3:
  - POST /ProductionOrders
  - GET /ProductTrees (BoM oku)
  - IssueForProduction (InventoryGenExit, hammadde sarf)
  - ReceiptFromProduction (InventoryGenEntry, mamul giriş)
  - Production Agent (Opus 4.7) — BoM analizi
"""
from __future__ import annotations

from app.sap.client import SAPServiceLayerClient


class ProductionOrdersModule:
    PATH = "/ProductionOrders"
    BOM = "/ProductTrees"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # TODO: implement in Faz 3
