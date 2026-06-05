"""API testleri için ortak fixture'lar — SQLite test DB + auth bypass."""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.middleware import reset_rate_limiters
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import User, UserRole, UserRoleAssignment
from app.db.session import get_db
from app.main import app


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Her API testi öncesi rate-limit bucket'larını temizle — testler arası leak yok."""
    reset_rate_limiters()
    yield
    reset_rate_limiters()


@pytest_asyncio.fixture
async def test_db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        tables = [t for t in Base.metadata.sorted_tables if t.name != "item_embeddings"]
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with session_factory() as setup:
        user = User(
            id="user-test",
            email="test@example.com",
            full_name="Test Kullanıcı",
            hashed_password=hash_password("password123"),
        )
        user.role_assignments = [
            UserRoleAssignment(user_id="user-test", role=UserRole.OPERATOR),
            UserRoleAssignment(user_id="user-test", role=UserRole.MANAGER),
        ]
        setup.add(user)
        await setup.commit()
    async with session_factory() as session:
        yield session
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db: AsyncSession) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    resp = await client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
