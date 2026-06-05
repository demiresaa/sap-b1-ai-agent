"""Auth flow integration testleri — FastAPI TestClient + SQLite."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_returns_tokens(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert "hatalı" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_me_endpoint_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_returns_user(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "operator" in data["roles"]


@pytest.mark.asyncio
async def test_documents_list_empty(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/documents")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_unknown_document_returns_404(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/documents/does-not-exist")
    assert resp.status_code == 404
