"""SAP master data sync task'ları — item_cache + bp_cache periyodik senkronizasyon.

Tam sync: her gece 02:00 (beat_schedule, celery_app.py).
Incremental: her saat :30 — sadece UpdateDate >= dünden değişenleri çeker.
Manuel tetikleme: POST /api/admin/sync/items veya /sync/bp.

Sayfalama: $top=500 + $skip loop (SAP B1 max page size ≈ 500).
Fiyat: $expand=ItemPrices ile item response'una fiyat listesi gömülür.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models import BusinessPartnerCache, ItemCache
from app.db.session import SessionFactory
from app.sap.odata import ODataQuery, eq
from app.sap.session import pool
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

PAGE_SIZE = 500


# ---------------------------------------------------------------------------
# Celery task'ları (sync → async bridge, tasks.py pattern'ini izler)
# ---------------------------------------------------------------------------


@celery_app.task(name="sync.items.full")
def sync_items_full() -> dict[str, int]:
    """Tüm aktif Items → item_cache upsert."""
    return asyncio.run(_sync_items_async(incremental=False))


@celery_app.task(name="sync.items.incremental")
def sync_items_incremental() -> dict[str, int]:
    """Dün güncellenmiş Items → item_cache upsert."""
    return asyncio.run(_sync_items_async(incremental=True))


@celery_app.task(name="sync.bp.full")
def sync_bp_full() -> dict[str, int]:
    """Tüm aktif BusinessPartners → bp_cache upsert."""
    return asyncio.run(_sync_bp_async())


# ---------------------------------------------------------------------------
# Async implementation
# ---------------------------------------------------------------------------


async def _sync_items_async(*, incremental: bool) -> dict[str, int]:
    """SAP Items'ı çek, item_cache'e upsert et."""
    logger.info("[sync_items] başladı incremental=%s", incremental)
    today = datetime.now(tz=UTC).date()
    since = (today - timedelta(days=1)) if incremental else None

    total = 0
    async with SessionFactory() as db, pool.acquire() as client:
        skip = 0
        while True:
            batch = await _fetch_items_page(client, skip=skip, since=since)
            if not batch:
                break
            await _upsert_items(db, batch)
            await db.commit()
            total += len(batch)
            logger.info("[sync_items] %d item işlendi (skip=%d)", total, skip)
            if len(batch) < PAGE_SIZE:
                break
            skip += PAGE_SIZE

    logger.info("[sync_items] tamamlandı toplam=%d", total)
    return {"synced": total}


async def _sync_bp_async() -> dict[str, int]:
    """SAP BusinessPartners'ı çek, bp_cache'e upsert et."""
    logger.info("[sync_bp] başladı")
    total = 0
    async with SessionFactory() as db, pool.acquire() as client:
        skip = 0
        while True:
            batch = await _fetch_bp_page(client, skip=skip)
            if not batch:
                break
            await _upsert_bp(db, batch)
            await db.commit()
            total += len(batch)
            logger.info("[sync_bp] %d BP işlendi (skip=%d)", total, skip)
            if len(batch) < PAGE_SIZE:
                break
            skip += PAGE_SIZE

    logger.info("[sync_bp] tamamlandı toplam=%d", total)
    return {"synced": total}


# ---------------------------------------------------------------------------
# SAP API çağrıları
# ---------------------------------------------------------------------------


async def _fetch_items_page(
    client: Any, *, skip: int, since: date | None
) -> list[dict[str, Any]]:
    """SAP /Items sayfası — ItemPrices expand ile."""
    query = (
        ODataQuery()
        .select(
            "ItemCode",
            "ItemName",
            "ForeignName",
            "BarCode",
            "ItemsGroupCode",
            "SalesUnit",
            "InventoryUOM",
            "SalesItem",
            "InventoryItem",
            "UpdateDate",
        )
        .expand("ItemPrices")
        .filter(eq("SalesItem", "tYES"))
        .filter(eq("Valid", "tYES"))
        .top(PAGE_SIZE)
        .skip(skip)
        .orderby("ItemCode")
    )
    if since:
        # OData date literal: yyyy-MM-dd (no quotes for date type)
        query.filter(f"UpdateDate ge '{since.isoformat()}'")
    resp = await client.get("/Items", **query.build())
    return resp.get("value", [])


async def _fetch_bp_page(client: Any, *, skip: int) -> list[dict[str, Any]]:
    """SAP /BusinessPartners müşteri sayfası."""
    query = (
        ODataQuery()
        .select(
            "CardCode",
            "CardName",
            "CardType",
            "FederalTaxID",
            "EmailAddress",
            "Phone1",
            "Currency",
            "PriceListNum",
            "PaymentTermsGroupCode",
            "UpdateDate",
        )
        .filter(eq("CardType", "cCustomer"))
        .filter(eq("Valid", "tYES"))
        .top(PAGE_SIZE)
        .skip(skip)
        .orderby("CardCode")
    )
    resp = await client.get("/BusinessPartners", **query.build())
    return resp.get("value", [])


# ---------------------------------------------------------------------------
# DB upsert'ler (PostgreSQL ON CONFLICT DO UPDATE)
# ---------------------------------------------------------------------------


async def _upsert_items(db: AsyncSession, items: list[dict[str, Any]]) -> None:
    if not items:
        return
    now = utcnow()
    rows = []
    for it in items:
        name = it.get("ItemName") or ""
        rows.append(
            {
                "item_code": it["ItemCode"],
                "item_name": name,
                "item_name_lower": _normalize(name),
                "foreign_name": it.get("ForeignName"),
                "bar_code": it.get("BarCode"),
                "items_group_code": it.get("ItemsGroupCode"),
                "sales_unit": it.get("SalesUnit"),
                "inventory_uom": it.get("InventoryUOM"),
                "sales_item": it.get("SalesItem") == "tYES",
                "inventory_item": it.get("InventoryItem") == "tYES",
                "raw": it,  # ItemPrices listesi burada gömülü
                "last_synced_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )

    stmt = pg_insert(ItemCache).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["item_code"],
        set_={
            "item_name": stmt.excluded.item_name,
            "item_name_lower": stmt.excluded.item_name_lower,
            "foreign_name": stmt.excluded.foreign_name,
            "bar_code": stmt.excluded.bar_code,
            "items_group_code": stmt.excluded.items_group_code,
            "sales_unit": stmt.excluded.sales_unit,
            "inventory_uom": stmt.excluded.inventory_uom,
            "sales_item": stmt.excluded.sales_item,
            "inventory_item": stmt.excluded.inventory_item,
            "raw": stmt.excluded.raw,
            "last_synced_at": stmt.excluded.last_synced_at,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await db.execute(stmt)


async def _upsert_bp(db: AsyncSession, bps: list[dict[str, Any]]) -> None:
    if not bps:
        return
    now = utcnow()
    rows = []
    for bp in bps:
        name = bp.get("CardName") or ""
        rows.append(
            {
                "card_code": bp["CardCode"],
                "card_name": name,
                "card_name_lower": _normalize(name),
                "card_type": bp.get("CardType", "cCustomer"),
                "federal_tax_id": bp.get("FederalTaxID"),
                "email_address": bp.get("EmailAddress"),
                "phone1": bp.get("Phone1"),
                "currency": bp.get("Currency"),
                "price_list_num": bp.get("PriceListNum"),
                "payment_terms_group_code": bp.get("PaymentTermsGroupCode"),
                "raw": bp,
                "last_synced_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )

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
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await db.execute(stmt)


def _normalize(text: str) -> str:
    """Türkçe karakterler dahil lowercase — unaccent migration sonrası DB'de de uygulanır."""
    return text.lower().strip()
