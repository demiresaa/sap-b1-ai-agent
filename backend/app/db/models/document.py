"""Belge (PDF/e-posta) ve çıkarılan veri modelleri."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class DocumentStatus(str, enum.Enum):
    RECEIVED = "received"                  # alındı
    READING = "reading"                    # AI okuyor
    MATCHING = "matching"                  # müşteri/ürün eşleştirme
    READY = "ready"                        # operatör için hazır
    PDF_GENERATED = "pdf_generated"        # bizim ürettiğimiz teklif PDF'i hazır
    CUSTOMER_ACCEPTED = "customer_accepted"  # müşteri kabul etti, sipariş kesilebilir
    CUSTOMER_REJECTED = "customer_rejected"  # müşteri reddetti
    EDITED_AFTER_ACCEPTANCE = "edited_after_acceptance"  # kabul sonrası düzenlendi
    SUBMITTING = "submitting"              # SAP'a yazılıyor
    SUBMITTED = "submitted"                # SAP'a yazıldı
    CONVERTING_TO_ORDER = "converting_to_order"  # teklif → sipariş dönüşümü SAP'a yazılıyor
    ORDER_SUBMITTED = "order_submitted"    # SAP Order oluşturuldu (teklif → sipariş)
    ERROR = "error"                        # hata
    REJECTED = "rejected"                  # operatör/manager reddetti


class DocumentSource(str, enum.Enum):
    UPLOAD = "upload"
    EMAIL = "email"
    API = "api"


class DocumentKind(str, enum.Enum):
    QUOTATION = "quotation"
    SALES_ORDER = "sales_order"
    UNKNOWN = "unknown"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_status_created", "status", "created_at"),
        Index("ix_documents_file_hash", "file_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source: Mapped[DocumentSource] = mapped_column(
        Enum(DocumentSource, name="document_source"), nullable=False
    )
    kind: Mapped[DocumentKind] = mapped_column(
        Enum(DocumentKind, name="document_kind"), default=DocumentKind.UNKNOWN, nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        default=DocumentStatus.RECEIVED,
        nullable=False,
    )
    original_filename: Mapped[str | None] = mapped_column(String(500))
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    file_hash: Mapped[str | None] = mapped_column(String(64))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    source_email: Mapped[str | None] = mapped_column(String(255))
    source_subject: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )

    extracted: Mapped["ExtractedData | None"] = relationship(
        back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    events: Mapped[list["DocumentEvent"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["SAPSubmission"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class ExtractedData(Base, TimestampMixin):
    """AI tarafından PDF'ten çıkarılan yapılandırılmış veri.

    `payload` JSONB — schema validated, mutable. Her düzenleme `version` artırır.
    """

    __tablename__ = "extracted_data"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    document: Mapped[Document] = relationship(back_populates="extracted")


class DocumentEvent(Base):
    """Audit timeline: her durum değişimi, kullanıcı eylemi, agent kararı."""

    __tablename__ = "document_events"
    __table_args__ = (Index("ix_document_events_doc_time", "document_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    document: Mapped[Document] = relationship(back_populates="events")


class SAPSubmission(Base, TimestampMixin):
    """SAP'a yapılan her POST denemesi."""

    __tablename__ = "sap_submissions"
    __table_args__ = (Index("ix_sap_submissions_doc", "document_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    target_endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sap_doc_entry: Mapped[int | None] = mapped_column(Integer)
    sap_doc_num: Mapped[int | None] = mapped_column(Integer)
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Quotation → Order dönüşümü için referans: order submission → quotation submission bağlantısı
    parent_submission_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sap_submissions.id", ondelete="SET NULL")
    )

    document: Mapped[Document] = relationship(back_populates="submissions")
