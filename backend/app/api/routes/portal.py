"""Müşteri Portalı — magic link tabanlı, JWT-free erişim.

Token formatı: base64url(f"{document_id}:{expiry_ts}") + "." + HMAC-SHA256 imzası
TTL: 72 saat. Token sunucu tarafında Redis'te saklanmaz — HMAC ile doğrulanır.

Müşteri akışı:
  1. Operatör → POST /api/portal/generate/{document_id} → magic link
  2. Müşteri linki açar → GET /api/portal/{token} → teklif özeti
  3. Müşteri → POST /api/portal/{token}/accept | /reject
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.db.base import utcnow
from app.db.models import Document, DocumentEvent, DocumentStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["portal"])

PORTAL_TOKEN_TTL = 72 * 3600  # 72 saat


# ------------------------------------------------------------------ #
# Token üretimi + doğrulama                                            #
# ------------------------------------------------------------------ #

def _make_token(document_id: str) -> str:
    expiry = int(time.time()) + PORTAL_TOKEN_TTL
    payload = f"{document_id}:{expiry}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(
        settings.app_secret_key.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{sig}"


def _verify_token(token: str) -> str:
    """Token'ı doğrular, document_id döner. Geçersizse HTTPException."""
    parts = token.split(".", 1)
    if len(parts) != 2:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Geçersiz portal token")

    payload_b64, sig = parts
    expected = hmac.new(
        settings.app_secret_key.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Geçersiz portal token imzası")

    try:
        payload = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        document_id, expiry_str = payload.rsplit(":", 1)
        expiry = int(expiry_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Geçersiz portal token formatı"
        ) from exc

    if time.time() > expiry:
        raise HTTPException(status.HTTP_410_GONE, "Portal linki süresi dolmuş (72 saat)")

    return document_id


# ------------------------------------------------------------------ #
# Endpoint'ler                                                          #
# ------------------------------------------------------------------ #

class MagicLinkOut(BaseModel):
    token: str
    url: str
    expires_in_hours: int = 72


@router.post("/generate/{document_id}", response_model=MagicLinkOut)
async def generate_magic_link(
    document_id: str,
    user: CurrentUser,
    db: DbSession,
) -> MagicLinkOut:
    """Belge için 72 saatlik magic link üretir.

    Sadece READY/PDF_GENERATED durumundaki belgeler için üretilebilir.
    """
    doc = await _get_doc_or_404(db, document_id)
    if doc.status not in {DocumentStatus.READY, DocumentStatus.PDF_GENERATED}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Belge henüz hazır değil (durum: {doc.status.value}). "
            "Teklif PDF'i oluşturulduktan sonra link gönderilebilir.",
        )

    token = _make_token(document_id)
    url = f"{settings.app_base_url}/portal/{token}"

    db.add(DocumentEvent(
        document_id=document_id,
        actor_id=user.id,
        event_type="portal_link_generated",
        payload={"url": url},
        created_at=utcnow(),
    ))
    await db.flush()

    logger.info("[portal] Magic link üretildi: doc=%s user=%s", document_id, user.id)
    return MagicLinkOut(token=token, url=url)


@router.get("/{token}")
async def view_document(token: str, db: DbSession) -> dict[str, Any]:
    """Teklif özetini müşteriye gösterir (authentication gerekmez)."""
    document_id = _verify_token(token)
    doc = await _get_doc_or_404(db, document_id)

    payload: dict[str, Any] = {}
    if doc.extracted and doc.extracted.payload:
        p = doc.extracted.payload
        payload = {
            "kind": p.get("kind"),
            "doc_date": p.get("doc_date"),
            "due_date": p.get("due_date"),
            "currency": p.get("currency"),
            "reference_no": p.get("reference_no"),
            "notes": p.get("notes"),
            "customer": {
                "name": (p.get("customer") or {}).get("name"),
            },
            "lines": [
                {
                    "line_no": ln.get("line_no"),
                    "description": ln.get("description"),
                    "quantity": ln.get("quantity"),
                    "unit": ln.get("unit"),
                    "unit_price": ln.get("unit_price"),
                    "discount_pct": ln.get("discount_pct"),
                    "total": ln.get("total"),
                }
                for ln in (p.get("lines") or [])
            ],
        }

    return {
        "document_id": document_id,
        "status": doc.status.value,
        "filename": doc.original_filename,
        "data": payload,
    }


class CustomerDecision(BaseModel):
    comments: str | None = None


@router.post("/{token}/accept", status_code=status.HTTP_200_OK)
async def customer_accept(token: str, body: CustomerDecision, db: DbSession) -> dict:
    """Müşteri teklifi kabul eder → CUSTOMER_ACCEPTED durumuna geçer."""
    document_id = _verify_token(token)
    doc = await _get_doc_or_404(db, document_id)

    if doc.status not in {DocumentStatus.READY, DocumentStatus.PDF_GENERATED}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Bu işlem {doc.status.value} durumunda yapılamaz.",
        )

    doc.status = DocumentStatus.CUSTOMER_ACCEPTED
    db.add(DocumentEvent(
        document_id=document_id,
        actor_id=None,
        event_type="customer_accepted",
        payload={"comments": body.comments},
        created_at=utcnow(),
    ))
    await db.flush()
    logger.info("[portal] Müşteri kabul etti: doc=%s", document_id)
    return {"status": "accepted", "document_id": document_id}


@router.post("/{token}/reject", status_code=status.HTTP_200_OK)
async def customer_reject(token: str, body: CustomerDecision, db: DbSession) -> dict:
    """Müşteri teklifi reddeder → CUSTOMER_REJECTED durumuna geçer."""
    document_id = _verify_token(token)
    doc = await _get_doc_or_404(db, document_id)

    if doc.status not in {DocumentStatus.READY, DocumentStatus.PDF_GENERATED}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Bu işlem {doc.status.value} durumunda yapılamaz.",
        )

    doc.status = DocumentStatus.CUSTOMER_REJECTED
    db.add(DocumentEvent(
        document_id=document_id,
        actor_id=None,
        event_type="customer_rejected",
        payload={"comments": body.comments},
        created_at=utcnow(),
    ))
    await db.flush()
    logger.info("[portal] Müşteri reddetti: doc=%s", document_id)
    return {"status": "rejected", "document_id": document_id}


async def _get_doc_or_404(db: DbSession, document_id: str) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Belge bulunamadı")
    return doc
