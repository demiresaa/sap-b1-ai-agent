"""Async SQLAlchemy engine ve session factory."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — request başına bir session açar."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_tenant_db() -> AsyncIterator[AsyncSession]:
    """Tenant-scoped session — schema_name için search_path'i ayarlar.

    Tenant bağlamı varsa `SET search_path TO tenant_<slug>, public` çalıştırır.
    Bu sayede tenant tabloları kendi schema'sında aranır; ortak tablolar public'te kalır.
    Tenant yoksa normal `get_db` gibi davranır.
    """
    from app.core.tenant_context import current_tenant  # döngüsel import'tan kaçın

    async with SessionFactory() as session:
        try:
            tenant = current_tenant()
            if tenant and tenant.schema_name:
                safe_schema = tenant.schema_name.replace('"', "")
                await session.execute(
                    text(f'SET search_path TO "{safe_schema}", public')
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
