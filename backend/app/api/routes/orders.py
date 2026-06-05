"""Sipariş aday listesi — müşteri kabul etmiş teklifler + SAP Order'a dönüştürülmüşler."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.db.models import Document, DocumentKind, DocumentStatus, SAPSubmission
from app.schemas.document import OrderCandidateOut

router = APIRouter(tags=["orders"])

_CANDIDATE_STATUSES = {DocumentStatus.CUSTOMER_ACCEPTED, DocumentStatus.CONVERTING_TO_ORDER}
_CONVERTED_STATUSES = {DocumentStatus.ORDER_SUBMITTED}
_ALL_ORDER_STATUSES = _CANDIDATE_STATUSES | _CONVERTED_STATUSES


@router.get("", response_model=list[OrderCandidateOut])
async def list_orders(
    user: CurrentUser,
    db: DbSession,
    filter: Literal["candidates", "converted", "all"] = Query(default="all"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
) -> list[OrderCandidateOut]:
    """
    candidates → Müşteri kabul etti, henüz sipariş oluşturulmadı.
    converted  → SAP Order oluşturulmuş.
    all        → İkisi birden.
    """
    if filter == "candidates":
        statuses = list(_CANDIDATE_STATUSES)
    elif filter == "converted":
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
