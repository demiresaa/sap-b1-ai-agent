"""SAP B1 Sales Opportunities + Activities.

STATUS: Faz 3 — placeholder
Plan: docs/modules/07-crm.md
"""
from __future__ import annotations

from app.sap.client import SAPServiceLayerClient


class OpportunitiesModule:
    OPPORTUNITIES = "/SalesOpportunities"
    ACTIVITIES = "/Activities"
    CONTACTS = "/ContactEmployees"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    # TODO: implement in Faz 3
