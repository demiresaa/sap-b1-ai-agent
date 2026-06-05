"""Admin tenants endpoint — list / get / patch + RBAC."""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Tenant, User, UserRole, UserRoleAssignment
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def admin_db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        tables = [t for t in Base.metadata.sorted_tables if t.name != "item_embeddings"]
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async def od():
        async with sf() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = od

    async with sf() as setup:
        for slug, name in [("elekon", "Elekon"), ("demo2", "Demo Müşteri 2")]:
            setup.add(
                Tenant(
                    id=f"t-{slug}",
                    slug=slug,
                    name=name,
                    schema_name=f"tenant_{slug}",
                    sl_base_url=f"https://{slug}.sap.test:50000/b1s/v1",
                    company_db=f"{slug.upper()}_DB",
                    vault_secret_path=f"tenants/{slug}/sap",
                )
            )
        admin = User(
            id="u-admin",
            email="admin@elekon.com",
            full_name="Admin",
            hashed_password=hash_password("password123"),
            tenant_id="t-elekon",
        )
        admin.role_assignments = [
            UserRoleAssignment(user_id="u-admin", role=UserRole.ADMIN),
        ]
        op_user = User(
            id="u-op",
            email="op@elekon.com",
            full_name="Op",
            hashed_password=hash_password("password123"),
            tenant_id="t-elekon",
        )
        op_user.role_assignments = [
            UserRoleAssignment(user_id="u-op", role=UserRole.OPERATOR),
        ]
        setup.add(admin)
        setup.add(op_user)
        await setup.commit()

    async with sf() as s:
        yield s

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(admin_db: AsyncSession) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _login(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        "/api/auth/login", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_can_list_tenants(client: AsyncClient) -> None:
    token = await _login(client, "admin@elekon.com")
    resp = await client.get(
        "/api/admin/tenants", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    slugs = {t["slug"] for t in body}
    assert {"elekon", "demo2"} <= slugs


@pytest.mark.asyncio
async def test_operator_cannot_list_tenants(client: AsyncClient) -> None:
    token = await _login(client, "op@elekon.com")
    resp = await client.get(
        "/api/admin/tenants", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_toggle_dry_run(client: AsyncClient) -> None:
    token = await _login(client, "admin@elekon.com")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.patch(
        "/api/admin/tenants/elekon",
        json={"sap_dry_run": False, "default_warehouse": "01"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sap_dry_run"] is False
    assert body["default_warehouse"] == "01"


@pytest.mark.asyncio
async def test_get_unknown_tenant_404(client: AsyncClient) -> None:
    token = await _login(client, "admin@elekon.com")
    resp = await client.get(
        "/api/admin/tenants/unknown", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404
