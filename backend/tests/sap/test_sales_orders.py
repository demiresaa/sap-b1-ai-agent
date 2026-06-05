"""Sales Order modülü testleri."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.sap.client import SAPServiceLayerClient
from app.sap.modules import SalesOrdersModule

BASE_URL = "https://sap.test:50000/b1s/v1"


@respx.mock
@pytest.mark.asyncio
async def test_create_sales_order_posts_payload() -> None:
    respx.post(f"{BASE_URL}/Login").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))
    create_route = respx.post(f"{BASE_URL}/Orders").mock(
        return_value=httpx.Response(201, json={"DocEntry": 42, "DocNum": 1001})
    )

    payload = {
        "CardCode": "C001",
        "DocDate": "2026-05-14",
        "DocDueDate": "2026-06-14",
        "DocCurrency": "TRY",
        "DocumentLines": [{"ItemCode": "A001", "Quantity": 2, "UnitPrice": 100.0}],
    }

    async with SAPServiceLayerClient() as client:
        module = SalesOrdersModule(client)
        result = await module.create(payload)

    assert result == {"DocEntry": 42, "DocNum": 1001}
    assert create_route.called
    sent = create_route.calls.last.request.read()
    assert b"C001" in sent
    assert b"A001" in sent


@respx.mock
@pytest.mark.asyncio
async def test_create_from_quotation_copies_lines_with_base_ref() -> None:
    respx.post(f"{BASE_URL}/Login").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))
    respx.get(f"{BASE_URL}/Quotations(7)").mock(
        return_value=httpx.Response(
            200,
            json={
                "CardCode": "C002",
                "DocDate": "2026-05-14",
                "DocDueDate": "2026-06-14",
                "DocCurrency": "EUR",
                "DocumentLines": [
                    {"LineNum": 0, "ItemCode": "A001", "Quantity": 5},
                    {"LineNum": 1, "ItemCode": "A002", "Quantity": 3},
                ],
            },
        )
    )
    create_route = respx.post(f"{BASE_URL}/Orders").mock(
        return_value=httpx.Response(201, json={"DocEntry": 99, "DocNum": 2002})
    )

    async with SAPServiceLayerClient() as client:
        module = SalesOrdersModule(client)
        result = await module.create_from_quotation(7)

    assert result["DocEntry"] == 99
    sent = create_route.calls.last.request.read().decode("utf-8")
    assert '"BaseType": 23' in sent or '"BaseType":23' in sent
    assert '"BaseEntry": 7' in sent or '"BaseEntry":7' in sent
