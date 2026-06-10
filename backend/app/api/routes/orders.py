"""Sipariş listesi + lojistik işlemler (İrsaliye, Fatura)."""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.db.models import Document, DocumentKind, DocumentStatus
from app.schemas.document import OrderCandidateOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["orders"])

_CANDIDATE_STATUSES = {DocumentStatus.CUSTOMER_ACCEPTED, DocumentStatus.CONVERTING_TO_ORDER}
_CONVERTED_STATUSES = {DocumentStatus.ORDER_SUBMITTED}
_ALL_ORDER_STATUSES = _CANDIDATE_STATUSES | _CONVERTED_STATUSES


@router.get("", response_model=list[OrderCandidateOut])
async def list_orders(
    user: CurrentUser,
    db: DbSession,
    view: Literal["candidates", "converted", "all"] = Query(default="all"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
) -> list[OrderCandidateOut]:
    """
    candidates → Müşteri kabul etti, henüz sipariş oluşturulmadı.
    converted  → SAP Order oluşturulmuş.
    all        → İkisi birden.
    """
    if view == "candidates":
        statuses = list(_CANDIDATE_STATUSES)
    elif view == "converted":
        statuses = list(_CONVERTED_STATUSES)
    else:
        statuses = list(_ALL_ORDER_STATUSES)

    stmt = (
        select(Document)
        .options(selectinload(Document.extracted), selectinload(Document.submissions))
        .where(Document.kind == DocumentKind.QUOTATION)
        .where(Document.status.in_(statuses))
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    rows: list[OrderCandidateOut] = []
    for doc in docs:
        # Extracted payload'dan müşteri/para bilgisi
        card_code: str | None = None
        card_name: str | None = None
        doc_currency: str | None = None
        doc_total: float | None = None
        if doc.extracted and doc.extracted.payload:
            p = doc.extracted.payload
            customer = p.get("customer") or {}
            card_code = customer.get("card_code")
            card_name = customer.get("card_name") or customer.get("name")
            doc_currency = p.get("currency")
            lines = p.get("lines") or []
            if lines:
                try:
                    doc_total = sum(
                        (ln.get("total") or (ln.get("quantity", 0) * (ln.get("unit_price") or 0)))
                        for ln in lines
                    )
                except (TypeError, ValueError):
                    doc_total = None

        # SAP submission bilgileri
        quotation_entry: int | None = None
        quotation_num: int | None = None
        order_entry: int | None = None
        order_num: int | None = None
        converted_at = None
        for sub in (doc.submissions or []):
            if sub.target_endpoint == "/Quotations" and sub.sap_doc_entry:
                quotation_entry = sub.sap_doc_entry
                quotation_num = sub.sap_doc_num
            elif sub.target_endpoint == "/Orders" and sub.sap_doc_entry:
                order_entry = sub.sap_doc_entry
                order_num = sub.sap_doc_num
                converted_at = sub.created_at

        status_label = (
            "converted" if doc.status in _CONVERTED_STATUSES else "candidate"
        )

        rows.append(
            OrderCandidateOut(
                document_id=doc.id,
                status=status_label,
                card_code=card_code,
                card_name=card_name,
                doc_currency=doc_currency,
                doc_total=doc_total,
                original_filename=doc.original_filename,
                quotation_doc_entry=quotation_entry,
                quotation_doc_num=quotation_num,
                order_doc_entry=order_entry,
                order_doc_num=order_num,
                created_at=doc.created_at,
                converted_at=converted_at,
            )
        )

    return rows


# ------------------------------------------------------------------ #
# C1: İrsaliye (Delivery Note) — Sales Order'dan                       #
# ------------------------------------------------------------------ #

class DeliverRequest(BaseModel):
    ship_date: str | None = None  # YYYY-MM-DD; None → agent önerir


@router.post("/{order_doc_entry}/deliver", status_code=status.HTTP_201_CREATED)
async def create_delivery(
    order_doc_entry: int,
    body: DeliverRequest,
    user: CurrentUser,
) -> dict:
    """Sales Order'dan İrsaliye oluşturur.

    Stok yetersizse 409 döner, human-in-the-loop bilgisi body'de gelir.
    dry_run=true ise SAP'a yazılmaz, sadece payload simüle edilir.
    """
    from app.agents.base import AgentContext
    from app.agents.logistics_agent import LogisticsAgent

    ctx = AgentContext(document_id=str(order_doc_entry), user_id=user.id)
    result = await LogisticsAgent().run(
        ctx,
        order_doc_entry=order_doc_entry,
        ship_date=body.ship_date,
    )

    if not result.success:
        raise HTTPException(status_code=502, detail=result.error or "Lojistik agent hatası")

    if result.needs_human:
        raise HTTPException(
            status_code=409,
            detail={
                "message": result.human_reason,
                "shortages": result.data.get("shortages", []),
                "suggested_ship_date": result.data.get("suggested_ship_date"),
            },
        )

    return result.data


# ------------------------------------------------------------------ #
# C2: Fatura (Invoice) — Delivery veya Order'dan                       #
# ------------------------------------------------------------------ #

class InvoiceRequest(BaseModel):
    source: Literal["delivery", "order"] = "order"
    source_doc_entry: int


@router.post("/{order_doc_entry}/invoice", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    order_doc_entry: int,
    body: InvoiceRequest,
    user: CurrentUser,
) -> dict:
    """Sales Order veya Delivery Note'tan A/R Invoice oluşturur.

    source="delivery" → Delivery Note referansı (BaseType=15).
    source="order"    → Sales Order referansı (BaseType=17).
    e-fatura gönderimi einvoice_enabled=true ise otomatik tetiklenir.
    """
    from app.sap import pool
    from app.sap.modules import InvoicesModule
    from app.services.einvoice import EInvoiceError, send_invoice

    async with pool.acquire() as client:
        inv_module = InvoicesModule(client)
        if body.source == "delivery":
            sap_result = await inv_module.create_from_delivery(body.source_doc_entry)
        else:
            sap_result = await inv_module.create_from_order(body.source_doc_entry)

    logger.info(
        "[orders] Fatura oluşturuldu: DocEntry=%s DocNum=%s",
        sap_result.get("DocEntry"),
        sap_result.get("DocNum"),
    )

    einvoice_uuid: str | None = None
    try:
        einvoice_uuid = await send_invoice(sap_result)
    except EInvoiceError as exc:
        logger.warning("[orders] e-Fatura gönderilemedi: %s", exc)

    return {
        "doc_entry": sap_result.get("DocEntry"),
        "doc_num": sap_result.get("DocNum"),
        "einvoice_uuid": einvoice_uuid,
    }
