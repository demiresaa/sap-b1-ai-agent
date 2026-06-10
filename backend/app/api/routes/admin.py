"""Admin endpoint'leri — tenant yönetimi (sadece admin rolü)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import DbSession, require_roles
from app.db.models import Tenant, UserRole
from app.workers.sync_tasks import sync_bp_full, sync_items_full, sync_items_incremental

router = APIRouter(tags=["admin"], dependencies=[Depends(require_roles(UserRole.ADMIN))])


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    schema_name: str
    sl_base_url: str
    company_db: str
    vault_secret_path: str
    sap_dry_run: bool
    is_active: bool
    default_warehouse: str | None
    default_sales_person_id: int | None
    default_currency: str | None
    default_pdf_template: str
    settings: dict[str, Any]


class TenantPatch(BaseModel):
    name: str | None = None
    sap_dry_run: bool | None = None
    is_active: bool | None = None
    default_warehouse: str | None = None
    default_sales_person_id: int | None = None
    default_currency: str | None = None
    default_pdf_template: str | None = None
    settings: dict[str, Any] | None = None


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(db: DbSession) -> list[TenantOut]:
    result = await db.execute(select(Tenant).order_by(Tenant.created_at))
    return [TenantOut.model_validate(t) for t in result.scalars()]


@router.get("/tenants/{slug}", response_model=TenantOut)
async def get_tenant(slug: str, db: DbSession) -> TenantOut:
    t = await _fetch_or_404(db, slug)
    return TenantOut.model_validate(t)


@router.patch("/tenants/{slug}", response_model=TenantOut)
async def patch_tenant(slug: str, patch: TenantPatch, db: DbSession) -> TenantOut:
    t = await _fetch_or_404(db, slug)
    data = patch.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(t, field, value)
    await db.flush()
    return TenantOut.model_validate(t)


@router.post("/sync/items", summary="Tam item sync'i tetikle")
async def trigger_sync_items() -> dict[str, str]:
    """SAP'taki tüm aktif Items'ı item_cache'e senkronize eder (Celery kuyruğuna atar)."""
    sync_items_full.delay()
    return {"status": "queued", "task": "sync.items.full"}


@router.post("/sync/items/incremental", summary="Incremental item sync'i tetikle")
async def trigger_sync_items_incremental() -> dict[str, str]:
    """Dün güncellenen Items'ı item_cache'e senkronize eder."""
    sync_items_incremental.delay()
    return {"status": "queued", "task": "sync.items.incremental"}


@router.post("/sync/bp", summary="Tam BP sync'i tetikle")
async def trigger_sync_bp() -> dict[str, str]:
    """SAP'taki tüm aktif müşterileri bp_cache'e senkronize eder."""
    sync_bp_full.delay()
    return {"status": "queued", "task": "sync.bp.full"}


async def _fetch_or_404(db, slug: str) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Tenant bulunamadı: {slug}")
    return t
