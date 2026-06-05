"""SAP B1 Service Calls + Equipment.

STATUS: Faz 3 — placeholder
Plan: docs/modules/08-service.md
"""
from __future__ import annotations

from app.sap.client import SAPServiceLayerClient


class ServiceCallsModule:
    CALLS = "/ServiceCalls"
    CONTRACTS = "/Contracts"
    EQUIPMENT = "/CustomerEquipmentCards"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # TODO: implement in Faz 3
