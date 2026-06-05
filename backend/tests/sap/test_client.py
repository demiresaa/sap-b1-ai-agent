"""Service Layer HTTP client testleri (respx ile mock)."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.sap.client import SAPServiceLayerClient
from app.sap.errors import SAPError

BASE_URL = "https://sap.test:50000/b1s/v1"


@pytest.fixture
def login_payload() -> dict[str, str]:
    return {"SessionId": "abc123"}


@respx.mock
@pytest.mark.asyncio
async def test_login_sets_session_cookie(login_payload: dict[str, str]) -> None:
    respx.post(f"{BASE_URL}/Login").mock(
        return_value=httpx.Response(
            200,
            json=login_payload,
            headers={"set-cookie": "B1SESSION=abc123; Path=/; Secure"},
        )
    )
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))

    async with SAPServiceLayerClient() as client:
        assert client.is_authenticated
        assert client._session_id == "abc123"


@respx.mock
@pytest.mark.asyncio
async def test_get_returns_json() -> None:
    respx.post(f"{BASE_URL}/Login").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))
    respx.get(f"{BASE_URL}/BusinessPartners").mock(
        return_value=httpx.Response(200, json={"value": [{"CardCode": "C001"}]})
    )

    async with SAPServiceLayerClient() as client:
        result = await client.get("/BusinessPartners")
        assert result["value"][0]["CardCode"] == "C001"


@respx.mock
@pytest.mark.asyncio
async def test_401_triggers_relogin_and_retry() -> None:
    login_route = respx.post(f"{BASE_URL}/Login").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))
    # İlk istek 401, ikincisi 200
    items_route = respx.get(f"{BASE_URL}/Items").mock(
        side_effect=[
            httpx.Response(401),
            httpx.Response(200, json={"value": []}),
        ]
    )

    async with SAPServiceLayerClient() as client:
        await client.get("/Items")

    assert login_route.call_count == 2  # ilk açılış + 401 sonrası re-login
    assert items_route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_400_raises_sap_error_with_turkish_message() -> None:
    respx.post(f"{BASE_URL}/Login").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))
    respx.post(f"{BASE_URL}/Orders").mock(
        return_value=httpx.Response(
            400,
            json={"error": {"code": "-10", "message": {"value": "missing CardCode"}}},
        )
    )

    async with SAPServiceLayerClient() as client:
        with pytest.raises(SAPError) as excinfo:
            await client.post("/Orders", {"DocDate": "2026-05-14"})

    assert excinfo.value.code == "-10"
    assert excinfo.value.status_code == 400
    assert "Geçersiz veri" in excinfo.value.message_tr


@respx.mock
@pytest.mark.asyncio
async def test_transient_503_is_retried() -> None:
    respx.post(f"{BASE_URL}/Login").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{BASE_URL}/Logout").mock(return_value=httpx.Response(204))
    route = respx.get(f"{BASE_URL}/Items").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"value": [{"ItemCode": "I001"}]}),
        ]
    )

    async with SAPServiceLayerClient() as client:
        result = await client.get("/Items")

    assert route.call_count == 2
    assert result["value"][0]["ItemCode"] == "I001"
