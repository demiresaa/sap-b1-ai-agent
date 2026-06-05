"""BusinessPartners modülü testleri."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from app.sap.client import SAPServiceLayerClient
from app.sap.modules import BusinessPartnersModule

BASE_URL = "https://sap.test:50000/b1s/v1"


@respx.mock
@pytest.mark.asyncio
async def test_list_customers_filters_card_type() -> None:
    respx.post(f"{BASE_URL}/Login").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))
    route = respx.get(f"{BASE_URL}/BusinessPartners").mock(
        return_value=httpx.Response(200, json={"value": [{"CardCode": "C001"}]})
    )

    async with SAPServiceLayerClient() as client:
        module = BusinessPartnersModule(client)
        await module.list_customers(top=25, search="Acme")

    sent_url = urlparse(str(route.calls.last.request.url))
    params = parse_qs(sent_url.query)
    assert params["$top"] == ["25"]
    filter_value = params["$filter"][0]
    assert "CardType eq 'cCustomer'" in filter_value
    assert "contains(CardName,'Acme')" in filter_value


@respx.mock
@pytest.mark.asyncio
async def test_search_quote_in_name_is_escaped() -> None:
    """Tek tırnaklı isimler OData literal'ında çift tırnak olmalı."""
    respx.post(f"{BASE_URL}/Login").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))
    route = respx.get(f"{BASE_URL}/BusinessPartners").mock(
        return_value=httpx.Response(200, json={"value": []})
    )

    async with SAPServiceLayerClient() as client:
        module = BusinessPartnersModule(client)
        await module.list_customers(search="O'Brien")

    filter_value = parse_qs(urlparse(str(route.calls.last.request.url)).query)["$filter"][0]
    assert "O''Brien" in filter_value
