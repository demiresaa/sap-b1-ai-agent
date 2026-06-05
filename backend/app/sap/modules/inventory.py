"""SAP B1 Inventory operations (transfers, counting, gen entries/exits).

STATUS: Faz 3 — placeholder
Plan: docs/modules/05-inventory.md

TODO Faz 3:
  - POST /StockTransfers (depolar arası)
  - POST /InventoryGenEntries (mal giriş, fire)
  - POST /InventoryGenExits (sarf, mal çıkış)
  - InventoryCountings (sayım)
  - BatchNumberDetails, SerialNumberDetails
"""
from __future__ import annotations

from app.sap.client import SAPServiceLayerClient


class InventoryModule:
    TRANSFERS = "/StockTransfers"
    ENTRIES = "/InventoryGenEntries"
    EXITS = "/InventoryGenExits"
    COUNTINGS = "/InventoryCountings"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # TODO: implement in Faz 3
