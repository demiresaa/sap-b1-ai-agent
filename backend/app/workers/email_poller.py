"""IMAP inbox poller — periyodik olarak yeni e-postaları çekip belge oluşturur.

Sprint 2'de tek hesap (config'den), Faz 2'de Microsoft Graph + multi-account.
"""
from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

from imap_tools import AND, MailBox, MailMessage

from app.core.config import settings
from app.db.models import DocumentSource
from app.db.session import SessionFactory
from app.services.documents import DuplicateDocument, upload_document
from app.workers.celery_app import celery_app
from app.workers.tasks import enqueue_process_document

logger = logging.getLogger(__name__)

ALLOWED_ATTACHMENT_SUFFIXES = (".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg")


@celery_app.task(name="app.workers.email_poller.poll_inbox")
def poll_inbox() -> dict[str, Any]:
    if not settings.email_imap_host or not settings.email_username:
        logger.info("E-posta polling konfigure değil, atlanıyor.")
        return {"skipped": True}
    return asyncio.run(_poll_async())


async def _poll_async() -> dict[str, Any]:
    processed = 0
    duplicates = 0
    with MailBox(settings.email_imap_host, port=settings.email_imap_port).login(
        settings.email_username, settings.email_password, settings.email_folder
    ) as mailbox:
        async with SessionFactory() as db:
            for msg in mailbox.fetch(AND(seen=False), mark_seen=True, bulk=True):
                ingested = await _ingest_message(db, msg)
                processed += ingested.created
                duplicates += ingested.duplicates
            await db.commit()
    return {"processed": processed, "duplicates": duplicates}


class _IngestionResult:
    def __init__(self) -> None:
        self.created = 0
        self.duplicates = 0


async def _ingest_message(db, msg: MailMessage) -> _IngestionResult:
    result = _IngestionResult()
    for att in msg.attachments:
        if not att.filename:
            continue
        lower = att.filename.lower()
        if not lower.endswith(ALLOWED_ATTACHMENT_SUFFIXES):
            continue
        try:
            doc = await upload_document(
                db,
                io.BytesIO(att.payload),
                original_filename=att.filename,
                mime_type=att.content_type,
                uploaded_by_id=None,
                source=DocumentSource.EMAIL,
                source_email=msg.from_,
                source_subject=msg.subject,
            )
            await db.flush()
            enqueue_process_document(doc.id)
            result.created += 1
        except DuplicateDocument:
            result.duplicates += 1
    return result
