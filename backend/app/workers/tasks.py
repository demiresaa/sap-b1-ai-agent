"""Belge işleme task'ları — orchestrator çağrısı, SAP submit.

Şu an Celery worker'ı async SQLAlchemy + Anthropic SDK ile birlikte çalıştırır
(asyncio runtime). Production'da `task_pool=solo` veya `gevent` ile çalıştırılır
(plan: Sprint 5 observability).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.orchestrator import OrchestratorAgent
from app.agents.sap_writer import SAPWriterAgent
from app.db.base import new_uuid, utcnow
from app.db.models import (
    Document,
    DocumentEvent,
    DocumentKind,
    DocumentStatus,
    ExtractedData,
    SAPSubmission,
)
from app.db.session import SessionFactory
from app.sap.idempotency import IdempotencyStore
from app.workers.celery_app import celery_app
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


# --- Public helpers (FastAPI background task'larından çağrılır) ---


async def enqueue_process_document(document_id: str) -> None:
    """AI processing'i tetikler.

    - `celery_enabled=True` ise Redis kuyruğuna atar (worker process alır).
    - `celery_enabled=False` (dev default) ise FastAPI BackgroundTasks içinde
      doğrudan async çalıştırır — ekstra worker process gerekmez.
    """
    if settings.app_env == "test":
        return
    if settings.celery_enabled:
        process_document.delay(document_id)
        return
    try:
        await _process_document_async(document_id)
    except Exception:
        logger.exception("process_document inline run hatası (doc=%s)", document_id)


async def enqueue_submit_document(
    db: AsyncSession, document: Document, actor_id: str | None
) -> str:
    """Submission satırı oluştur, task'ı tetikle, submission_id döner."""
    submission = SAPSubmission(
        document_id=document.id,
        idempotency_key=f"submit:{document.id}:{new_uuid()}",
        target_endpoint=_endpoint_for(document.kind),
        request_payload={},
        attempt=1,
    )
    db.add(submission)
    document.status = DocumentStatus.SUBMITTING
    db.add(
        DocumentEvent(
            document_id=document.id,
            actor_id=actor_id,
            event_type="submit_requested",
            payload={"submission_id": submission.id},
            created_at=utcnow(),
        )
    )
    await db.flush()
    submission_id = submission.id
    if settings.app_env == "test":
        return submission_id
    if settings.celery_enabled:
        submit_document.delay(submission_id)
    else:
        try:
            await _submit_document_async(submission_id)
        except Exception:
            logger.exception("submit_document inline run hatası (sub=%s)", submission_id)
    return submission_id


# --- Celery tasks ---


@celery_app.task(name="app.workers.tasks.process_document", bind=True, max_retries=3)
def process_document(self, document_id: str) -> dict[str, Any]:
    return asyncio.run(_process_document_async(document_id))


@celery_app.task(name="app.workers.tasks.submit_document", bind=True, max_retries=3)
def submit_document(self, submission_id: str) -> dict[str, Any]:
    return asyncio.run(_submit_document_async(submission_id))


# --- Async implementation ---


async def _process_document_async(document_id: str) -> dict[str, Any]:
    logger.info("[process_document] başladı doc=%s", document_id)
    async with SessionFactory() as db:
        # Upload sonrası FastAPI BackgroundTasks bazen dependency cleanup (commit)
        # tamamlanmadan tetikleniyor; document yeni session'a görünmüyor olabilir.
        # Kısa retry — exponential backoff, max ~1.5s.
        doc = None
        for delay in (0.0, 0.2, 0.4, 0.8):
            if delay:
                await asyncio.sleep(delay)
            doc = await _get_document(db, document_id)
            if doc:
                break
        if not doc:
            logger.error("[process_document] belge bulunamadı doc=%s", document_id)
            return {"error": "document_not_found"}
        doc.status = DocumentStatus.READING
        await db.flush()
        await db.commit()  # status değişimi UI'da hemen görünsün

    # Yeni session — agent run sırasında bağımsız transaction
    async with SessionFactory() as db:
        doc = await _get_document(db, document_id)
        if not doc:
            return {"error": "document_not_found"}
        try:
            ctx = AgentContext(document_id=document_id)
            orchestrator = OrchestratorAgent()
            result = await orchestrator.run(ctx, file_path=doc.storage_path, db=db)
        except Exception as exc:
            logger.exception("[process_document] orchestrator çöktü doc=%s", document_id)
            doc.status = DocumentStatus.ERROR
            doc.error_message = f"AI işlemi başarısız: {type(exc).__name__}: {exc}"
            db.add(
                DocumentEvent(
                    document_id=document_id,
                    event_type="processing_failed",
                    payload={"error": str(exc), "type": type(exc).__name__},
                    created_at=utcnow(),
                )
            )
            await db.commit()
            return {"error": str(exc)}

        extracted = (result.data or {}).get("extracted") or {}
        if extracted:
            await _persist_extracted(db, doc, extracted, result.data)
            doc.kind = _kind_from(extracted.get("kind"))

        if not result.success:
            doc.status = DocumentStatus.ERROR
            doc.error_message = result.error or "Bilinmeyen AI hatası"
            logger.warning("[process_document] başarısız doc=%s err=%s", document_id, result.error)
        else:
            lines = (result.data or {}).get("extracted", {}).get("lines", [])
            if not lines:
                doc.status = DocumentStatus.ERROR
                doc.error_message = "AI herhangi bir satır cıkaramadı. Lutfen belgeyi kontrol edip tekrar deneyin."
                logger.warning("[process_document] bos extraction doc=%s", document_id)
            else:
                doc.status = DocumentStatus.READY
            logger.info("[process_document] tamam doc=%s status=%s", document_id, doc.status.value)

        db.add(
            DocumentEvent(
                document_id=document_id,
                event_type="processed",
                payload={
                    "confidence": result.confidence,
                    "needs_human": result.needs_human,
                    "reason": result.human_reason,
                },
                created_at=utcnow(),
            )
        )
        await db.commit()
        return {"status": doc.status.value, "confidence": result.confidence}


async def _submit_document_async(submission_id: str) -> dict[str, Any]:
    async with SessionFactory() as db:
        result = await db.execute(select(SAPSubmission).where(SAPSubmission.id == submission_id))
        submission = result.scalar_one_or_none()
        if not submission:
            return {"error": "submission_not_found"}

        doc = await _get_document(db, submission.document_id)
        if not doc or not doc.extracted:
            return {"error": "document_or_extraction_missing"}

        payload = _build_sap_payload(doc.extracted.payload, doc.kind)
        submission.request_payload = payload

        redis = Redis.from_url(settings.redis_url)
        store = IdempotencyStore(redis)

        try:
            agent_result = await SAPWriterAgent().run(
                AgentContext(document_id=doc.id, metadata={"idempotency_source": doc.file_hash}),
                kind=_kind_to_writer(doc.kind),
                payload=payload,
                idempotency_store=store,
            )
        finally:
            await redis.aclose()

        if agent_result.success:
            sap = agent_result.data.get("sap") or {}
            submission.sap_doc_entry = sap.get("sap_doc_entry")
            submission.sap_doc_num = sap.get("sap_doc_num")
            submission.response_payload = sap
            submission.http_status = 201
            doc.status = DocumentStatus.SUBMITTED
            event_type = "sap_submitted"
        else:
            submission.error_message = agent_result.error
            submission.http_status = agent_result.data.get("http_status")
            doc.status = DocumentStatus.ERROR
            doc.error_message = agent_result.error
            event_type = "sap_submit_failed"

        db.add(
            DocumentEvent(
                document_id=doc.id,
                event_type=event_type,
                payload={"submission_id": submission.id, **agent_result.data},
                created_at=utcnow(),
            )
        )
        await db.commit()
        return {
            "submission_id": submission.id,
            "status": doc.status.value,
            "sap_doc_entry": submission.sap_doc_entry,
        }


async def _persist_extracted(
    db: AsyncSession, doc: Document, extracted: dict[str, Any], full_result: dict[str, Any]
) -> None:
    if doc.extracted is None:
        doc.extracted = ExtractedData(
            document_id=doc.id,
            version=1,
            payload=extracted,
            confidence={
                "overall": full_result.get("overall_confidence"),
                **extracted.get("confidence", {}),
            },
        )
    else:
        doc.extracted.version += 1
        doc.extracted.payload = extracted


async def _get_document(db: AsyncSession, document_id: str) -> Document | None:
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Document)
        .options(selectinload(Document.extracted))
        .where(Document.id == document_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _kind_from(raw: str | None) -> DocumentKind:
    if raw == "sales_order":
        return DocumentKind.SALES_ORDER
    if raw == "quotation":
        return DocumentKind.QUOTATION
    return DocumentKind.UNKNOWN


def _endpoint_for(kind: DocumentKind) -> str:
    return "/Orders" if kind == DocumentKind.SALES_ORDER else "/Quotations"


def _kind_to_writer(kind: DocumentKind) -> str:
    return "sales_order" if kind == DocumentKind.SALES_ORDER else "quotation"


def _build_sap_payload(extracted: dict[str, Any], kind: DocumentKind) -> dict[str, Any]:
    """ExtractedData payload'undan SAP POST payload'ı üretir.

    Bu MVP'de mapping form'da operatör tarafından netleştirilmiş `extracted`
    payload'unu temel alır — yani CardCode, ItemCode, fiyatlar form içinde
    bağlanmış olmalı.
    """
    customer = extracted.get("customer") or {}
    lines = extracted.get("lines") or []
    return {
        "CardCode": customer.get("card_code") or customer.get("CardCode"),
        "DocDate": extracted.get("doc_date"),
        "DocDueDate": extracted.get("due_date") or extracted.get("doc_date"),
        "DocCurrency": extracted.get("currency"),
        "NumAtCard": extracted.get("reference_no"),
        "Comments": extracted.get("notes"),
        "DocumentLines": [
            {
                "ItemCode": line.get("item_code") or line.get("ItemCode"),
                "Quantity": line.get("quantity") or line.get("Quantity"),
                "UnitPrice": line.get("unit_price") or line.get("UnitPrice"),
                "DiscountPercent": line.get("discount_pct") or line.get("DiscountPercent"),
                "TaxCode": line.get("tax_code") or line.get("TaxCode"),
            }
            for line in lines
        ],
    }
