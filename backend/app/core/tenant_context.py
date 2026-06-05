"""Tenant context — request başına aktif tenant.

Akış:
  - Kullanıcı login olunca JWT'sine `tenant_slug` claim'i konur.
  - Auth dependency JWT'yi decode eder → `tenant_slug`'ı request.state'e koyar.
  - `get_current_tenant()` Depends'i bu state'ten Tenant satırını DB'den çeker.
  - DB session açılırken `schema_translate_map` ile `tenant_<slug>` schema'sına yönlendirilir.

Faz 1 not: Tüm tablolar şu an public schema'sında — `schema_translate_map` etkisiz.
B2 retrofit'inden sonra tenant-scoped tablolar `tenant_<slug>` schema'sına taşınınca aktif olur.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tenant import Tenant
from app.db.session import get_db


@dataclass(slots=True, frozen=True)
class TenantContext:
    """Request boyunca aktif tenant."""

    id: str
    slug: str
    schema_name: str
    sap_dry_run: bool
    sl_base_url: str
    company_db: str
    vault_secret_path: str
    default_warehouse: str | None
    default_sales_person_id: int | None
    default_currency: str | None
    default_pdf_template: str


_current_tenant: ContextVar[TenantContext | None] = ContextVar("current_tenant", default=None)


def set_current_tenant(tenant: TenantContext | None) -> None:
    _current_tenant.set(tenant)


def current_tenant() -> TenantContext | None:
    return _current_tenant.get()


def _from_orm(row: Tenant) -> TenantContext:
    return TenantContext(
        id=row.id,
        slug=row.slug,
        schema_name=row.schema_name,
        sap_dry_run=row.sap_dry_run,
        sl_base_url=row.sl_base_url,
        company_db=row.company_db,
        vault_secret_path=row.vault_secret_path,
        default_warehouse=row.default_warehouse,
        default_sales_person_id=row.default_sales_person_id,
        default_currency=row.default_currency,
        default_pdf_template=row.default_pdf_template,
    )


async def resolve_tenant_by_slug(db: AsyncSession, slug: str) -> TenantContext:
    """Slug'a göre tenant getir veya 404."""
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.is_active.is_(True))
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant bulunamadı: {slug}",
        )
    return _from_orm(row)


async def get_current_tenant(
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """FastAPI dependency — context var'dan tenant'ı çekip context'e set eder.

    Auth middleware (faz: api.middleware.tenant) JWT'den slug okuyup
    `set_current_tenant`'a TenantContext bırakır; bu dependency onu döndürür.
    Eğer set edilmemişse 401.
    """
    tenant = _current_tenant.get()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context eksik — giriş yapın",
        )
    # Slug ile tazele (sap_dry_run vb. değişkenlik gösterir)
    return await resolve_tenant_by_slug(db, tenant.slug)
