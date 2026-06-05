"""Tenant resolver middleware + login tenant claim testleri."""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import decode_token, hash_password
from app.db.base import Base
from app.db.models import Tenant, User, UserRole, UserRoleAssignment
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def tenant_db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        tables = [t for t in Base.metadata.sorted_tables if t.name != "item_embeddings"]
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as setup:
        tenant = Tenant(
            id="t-elekon",
            slug="elekon",
            name="Elekon",
            schema_name="tenant_elekon",
            sl_base_url="https://sap.test:50000/b1s/v1",
            company_db="2026_Test",
            vault_secret_path="tenants/elekon/sap",
            sap_dry_run=True,
        )
        setup.add(tenant)
        user = User(
            id="user-elekon",
            email="op@elekon.com",
            full_name="Elekon Op",
            hashed_password=hash_password("password123"),
            tenant_id="t-elekon",
        )
        user.role_assignments = [
            UserRoleAssignment(user_id="user-elekon", role=UserRole.OPERATOR),
        ]
        setup.add(user)
        await setup.commit()

    async with session_factory() as s:
        yield s

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest_asyncio.fixture
async def tenant_client(tenant_db: AsyncSession) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_login_returns_tenant_slug(tenant_client: AsyncClient) -> None:
    resp = await tenant_client.post(
        "/api/auth/login",
        json={"email": "op@elekon.com", "password": "password123"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tenant_slug"] == "elekon"

    payload = decode_token(body["access_token"], expected_type="access")
    assert payload["tenant"] == "elekon"


@pytest.mark.asyncio
async def test_me_returns_tenant_slug(tenant_client: AsyncClient) -> None:
    login = await tenant_client.post(
        "/api/auth/login",
        json={"email": "op@elekon.com", "password": "password123"},
    )
    token = login.json()["access_token"]

    me = await tenant_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200, me.text
    assert me.json()["tenant_slug"] == "elekon"


@pytest.mark.asyncio
async def test_middleware_extracts_tenant_from_jwt(tenant_client: AsyncClient) -> None:
    """Middleware'in slug'ı JWT'den okuduğunu doğrula — `/api/auth/me` endpoint'i
    me dönüyorsa middleware doğru çalışmıştır."""
    login = await tenant_client.post(
        "/api/auth/login",
        json={"email": "op@elekon.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    me = await tenant_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_does_not_require_tenant(tenant_client: AsyncClient) -> None:
    resp = await tenant_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
