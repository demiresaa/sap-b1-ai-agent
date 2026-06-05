"""SAP B1 Items — stok kartları."""
from __future__ import annotations

from typing import Any

from app.sap.client import SAPServiceLayerClient
from app.sap.odata import ODataQuery, contains, eq, escape_literal, or_

ITEM_SELECT_FIELDS = (
    "ItemCode",
    "ItemName",
    "ForeignName",
    "BarCode",
    "ItemsGroupCode",
    "SalesUnit",
    "InventoryUOM",
    "SalesItem",
    "InventoryItem",
)


class ItemsModule:
    PATH = "/Items"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    async def list(
        self, *, top: int = 100, skip: int = 0, search: str | None = None
    ) -> list[dict[str, Any]]:
        query = (
            ODataQuery()
            .select(*ITEM_SELECT_FIELDS)
            .filter(eq("SalesItem", "tYES"))
            .top(top)
            .skip(skip)
            .orderby("ItemName")
        )
        if search:
            query.filter(
                or_(
                    contains("ItemCode", search),
                    contains("ItemName", search),
                    eq("BarCode", search),
                )
            )
        resp = await self.client.get(self.PATH, **query.build())
        return resp.get("value", [])

    async def get(self, item_code: str) -> dict[str, Any]:
        return await self.client.get(f"{self.PATH}('{escape_literal(item_code)}')")

    async def search_by_barcode(self, barcode: str) -> list[dict[str, Any]]:
        query = (
            ODataQuery()
            .select(*ITEM_SELECT_FIELDS)
            .filter(eq("BarCode", barcode))
            .top(5)
        )
        resp = await self.client.get(self.PATH, **query.build())
        return resp.get("value", [])

    async def availability(self, item_code: str) -> dict[str, Any]:
        """ItemsService_GetItemAvailability function import wrapper.

        Yanıt formu: `{"InStock": ..., "Committed": ..., "Ordered": ..., "Available": ...}`
        """
        return await self.client.post(
            "/ItemsService_GetItemAvailability",
            {"ItemCode": item_code},
        )
