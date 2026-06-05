"""Document service — upload, dedupe, agent run kuyruğu (Sprint sonrasında Celery)."""
from __future__ import annotations

from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models import (
    Document,
    DocumentEvent,
    DocumentKind,
    DocumentSource,
    DocumentStatus,
)
from app.services.storage import Storage, StoredFile, storage as default_storage


class DuplicateDocument(Exception):
    """Aynı dosya hash'i ile var olan belge."""

    def __init__(self, existing: Document) -> None:
        super().__init__(f"Belge zaten yüklenmiş: {existing.id}")
        self.existing = existing


async def upload_document(
    db: AsyncSession,
    stream: BinaryIO,
    *,
    original_filename: str | None,
    mime_type: str | None,
    uploaded_by_id: str | None,
    source: DocumentSource = DocumentSource.UPLOAD,
    source_email: str | None = None,
    source_subject: str | None = None,
    storage_backend: Storage | None = None,
) -> Document:
    backend = storage_backend or default_storage
    stored = backend.save_stream(stream, original_filename, mime_type)
    existing = await _find_by_hash(db, stored.file_hash)
    if existing:
        backend.delete(stored.storage_path)
        raise DuplicateDocument(existing)

    doc = _build_document(
        stored,
        original_filename=original_filename,
        mime_type=mime_type,
        uploaded_by_id=uploaded_by_id,
        source=source,
        source_email=source_email,
        source_subject=source_subject,
    )
    db.add(doc)
    await db.flush()
    db.add(
        DocumentEvent(
            document_id=doc.id,
            actor_id=uploaded_by_id,
            event_type="document_received",
            payload={
                "source": source.value,
                "filename": original_filename,
                "size_bytes": stored.size_bytes,
            },
            created_at=utcnow(),
        )
    )
    return doc


async def _find_by_hash(db: AsyncSession, file_hash: str) -> Document | None:
    result = await db.execute(select(Document).where(Document.file_hash == file_hash))
    return result.scalars().first()


def _build_document(
    stored: StoredFile,
    *,
    original_filename: str | None,
    mime_type: str | None,
    uploaded_by_id: str | None,
    source: DocumentSource,
    source_email: str | None,
    source_subject: str | None,
) -> Document:
    return Document(
        source=source,
        kind=DocumentKind.UNKNOWN,
        status=DocumentStatus.RECEIVED,
        original_filename=original_filename,
        storage_path=stored.storage_path,
        file_hash=stored.file_hash,
        file_size_bytes=stored.size_bytes,
        mime_type=mime_type,
        source_email=source_email,
        source_subject=source_subject,
        uploaded_by_id=uploaded_by_id,
    )
