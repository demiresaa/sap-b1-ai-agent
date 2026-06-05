"""SAP proxy endpoint'leri — BP/Item arama, stok availability, cache yönetimi.

Cache-first stratejisi:
  1. bp_cache / item_cache (Postgres) — her zaman önce buraya bak.
  2. Cache boşsa ve SAP erişilebiliyorsa → live SAP sorgusu.
  3. Dry-run veya SAP erişim yoksa → cache sonucu (boş olabilir).

Cache doldurma:
  - `POST /sap/bp-cache/import` → JSON array ile toplu import (admin).
  - `onboard_tenant.py` scripti → SAP'tan tüm BP/Item'ı çekip upsert eder.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.db.models.sap_cache import BusinessPartnerCache, ItemCache
from app.sap import SAPError, pool
from app.sap.modules import BusinessPartnersModule, ItemsModule

router = APIRouter(tags=["sap"])


# --- cache query helpers ---

async def _search_bp_cache(
    db: DbSession, search: str | None, top: int
) -> list[dict[str, Any]]:
    stmt = select(BusinessPartnerCache).limit(top)
    if search:
        q = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                BusinessPartnerCache.card_name_lower.like(q),
                BusinessPartnerCache.card_code.ilike(q),
                BusinessPartnerCache.federal_tax_id.ilike(q),
            )
        )
    else:
        stmt = stmt.order_by(BusinessPartnerCache.card_name)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_bp_cache_to_dict(r) for r in rows]


async def _search_item_cache(
    db: DbSession, search: str | None, top: int
) -> list[dict[str, Any]]:
    stmt = select(ItemCache).limit(top)
    if search:
        q = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                ItemCache.item_name_lower.like(q),
                ItemCache.item_code.ilike(q),
                ItemCache.bar_code.ilike(q),
            )
        )
    else:
        stmt = stmt.order_by(ItemCache.item_name)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_item_cache_to_dict(r) for r in rows]


def _bp_cache_to_dict(r: BusinessPartnerCache) -> dict[str, Any]:
    # raw JSONB varsa tüm SAP alanlarını döndür; yoksa temel alanları derle.
    if r.raw:
        return r.raw
    return {
        "CardCode": r.card_code,
        "CardName": r.card_name,
        "FederalTaxID": r.federal_tax_id,
        "EmailAddress": r.email_address,
        "Phone1": r.phone1,
        "Currency": r.currency,
        "PriceListNum": r.price_list_num,
        "PaymentTermsGroupCode": r.payment_terms_group_code,
    }


def _item_cache_to_dict(r: ItemCache) -> dict[str, Any]:
    return {
        "ItemCode": r.item_code,
        "ItemName": r.item_name,
        "ForeignName": r.foreign_name,
        "BarCode": r.bar_code,
        "SalesUnit": r.sales_unit,
    }


def _sap_bp_to_cache_row(bp: dict[str, Any]) -> dict[str, Any]:
    name = bp.get("CardName", "")
    return {
        "card_code": bp["CardCode"],
        "card_name": name,
        "card_name_lower": name.lower(),
        "card_type": bp.get("CardType", "cCustomer"),
        "federal_tax_id": bp.get("FederalTaxID"),
        "email_address": bp.get("EmailAddress"),
        "phone1": bp.get("Phone1"),
        "currency": bp.get("Currency"),
        "price_list_num": bp.get("PriceListNum"),
        "payment_terms_group_code": bp.get("PaymentTermsGroupCode"),
        "raw": bp,
        "last_synced_at": datetime.now(timezone.utc),
    }


# --- endpoints ---

@router.get("/business-partners")
async def list_business_partners(
    user: CurrentUser,
    db: DbSession,
    search: str | None = Query(default=None, min_length=2, max_length=100),
    top: int = Query(default=50, le=200),
    skip: int = 0,
) -> list[dict[str, Any]]:
    # 1. Önce local cache
    cached = await _search_bp_cache(db, search, top)
    if cached:
        return cached

    # 2. Cache boş + dry-run → örnek veriler
    if settings.sap_dry_run:
        return _dry_run_bp_response(search)

    # 3. Cache boş + SAP erişilebilir → live sorgu
    try:
        async with pool.acquire() as client:
            module = BusinessPartnersModule(client)
            results = await module.list_customers(top=top, skip=skip, search=search)
        # Getirilen kayıtları cache'e yaz (upsert)
        if results:
            await _upsert_bps(db, results)
        return results
    except SAPError as err:
        raise HTTPException(err.status_code or status.HTTP_502_BAD_GATEWAY, err.message_tr)


@router.post("/bp-cache/import", status_code=status.HTTP_200_OK)
async def import_bp_cache(
    user: CurrentUser,
    db: DbSession,
    bps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Müşteri listesini JSON array olarak içe aktar — cache'e yazar.

    Her kayıt en az `CardCode` ve `CardName` içermeli.
    Örnek: [{"CardCode":"C001","CardName":"Acme Ltd.","Currency":"TRY"}, ...]
    """
    if not bps:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Boş liste gönderildi.")
    await _upsert_bps(db, bps)
    return {"imported": len(bps), "message": f"{len(bps)} müşteri cache'e yazıldı."}


async def _upsert_bps(db: DbSession, bps: list[dict[str, Any]]) -> None:
    rows = [_sap_bp_to_cache_row(bp) for bp in bps if bp.get("CardCode")]
    if not rows:
        return
    stmt = pg_insert(BusinessPartnerCache).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["card_code"],
        set_={
            "card_name": stmt.excluded.card_name,
            "card_name_lower": stmt.excluded.card_name_lower,
            "federal_tax_id": stmt.excluded.federal_tax_id,
            "email_address": stmt.excluded.email_address,
            "phone1": stmt.excluded.phone1,
            "currency": stmt.excluded.currency,
            "price_list_num": stmt.excluded.price_list_num,
            "payment_terms_group_code": stmt.excluded.payment_terms_group_code,
            "raw": stmt.excluded.raw,
            "last_synced_at": stmt.excluded.last_synced_at,
        },
    )
    await db.execute(stmt)
    await db.commit()


@router.get("/items")
async def list_items(
    user: CurrentUser,
    db: DbSession,
    search: str | None = Query(default=None, min_length=2, max_length=100),
    top: int = Query(default=50, le=200),
    skip: int = 0,
) -> list[dict[str, Any]]:
    # 1. Önce local cache
    cached = await _search_item_cache(db, search, top)
    if cached:
        return cached

    # 2. Cache boş + dry-run → boş
    if settings.sap_dry_run:
        return []

    # 3. Live SAP
    try:
        async with pool.acquire() as client:
            module = ItemsModule(client)
            return await module.list(top=top, skip=skip, search=search)
    except SAPError as err:
        raise HTTPException(err.status_code or status.HTTP_502_BAD_GATEWAY, err.message_tr)


@router.get("/items/{item_code}/availability")
async def item_availability(item_code: str, user: CurrentUser) -> dict[str, Any]:
    if settings.sap_dry_run:
        return {"Available": None, "InStock": None, "dry_run": True}
    try:
        async with pool.acquire() as client:
            module = ItemsModule(client)
            return await module.availability(item_code)
    except SAPError as err:
        raise HTTPException(err.status_code or status.HTTP_502_BAD_GATEWAY, err.message_tr)


def _dry_run_bp_response(search: str | None) -> list[dict[str, Any]]:
    """Cache boş + dry-run → örnek müşteriler (danışman test edebilsin)."""
    samples = [
        {
            "CardCode": "C10001",
            "CardName": "Aybern Elektrik Enerji Mühendislik",
            "FederalTaxID": "1234567890",
            "EmailAddress": "satis@aybern.com",
            "Phone1": "+90 212 555 0101",
            "Currency": "EUR",
            "PriceListNum": 1,
            "PaymentTermsGroupCode": 5,
        },
        {
            "CardCode": "C10002",
            "CardName": "Tekno Sistem Otomasyon A.Ş.",
            "FederalTaxID": "9876543210",
            "EmailAddress": "info@teknosistem.com",
            "Phone1": "+90 216 555 0202",
            "Currency": "TRY",
            "PriceListNum": 2,
            "PaymentTermsGroupCode": 3,
        },
        {
            "CardCode": "C10003",
            "CardName": "Delta Endüstri Makina Ltd.",
            "FederalTaxID": "5555555555",
            "EmailAddress": "satin.alma@deltaendus.com",
            "Phone1": "+90 232 555 0303",
            "Currency": "USD",
            "PriceListNum": 1,
            "PaymentTermsGroupCode": 7,
        },
    ]
    if search:
        q = search.lower()
        return [s for s in samples if q in s["CardName"].lower() or q in s["CardCode"].lower()]
    return samples
