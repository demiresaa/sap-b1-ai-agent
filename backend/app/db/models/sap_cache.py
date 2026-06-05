"""SAP master data (BusinessPartners, Items) lokal cache modelleri.

Senkron işlem: Celery task'ı periyodik olarak SAP'tan fetch eder, upsert eder.
Item için pgvector embedding tutulur (semantic ürün eşleştirme).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

EMBEDDING_DIM = 1536  # OpenAI/Voyage default — modele göre ayarla


class BusinessPartnerCache(Base, TimestampMixin):
    __tablename__ = "bp_cache"
    __table_args__ = (
        Index("ix_bp_cache_name_lower", "card_name_lower"),
        Index("ix_bp_cache_tax_id", "federal_tax_id"),
        Index("ix_bp_cache_email", "email_address"),
    )

    card_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    card_name: Mapped[str] = mapped_column(String(255), nullable=False)
    card_name_lower: Mapped[str] = mapped_column(String(255), nullable=False)
    card_type: Mapped[str] = mapped_column(String(10), nullable=False)
    federal_tax_id: Mapped[str | None] = mapped_column(String(50))
    email_address: Mapped[str | None] = mapped_column(String(255))
    phone1: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str | None] = mapped_column(String(10))
    price_list_num: Mapped[int | None] = mapped_column(Integer)
    payment_terms_group_code: Mapped[int | None] = mapped_column(Integer)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ItemCache(Base, TimestampMixin):
    __tablename__ = "item_cache"
    __table_args__ = (
        Index("ix_item_cache_name_lower", "item_name_lower"),
        Index("ix_item_cache_barcode", "bar_code"),
    )

    item_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    item_name_lower: Mapped[str] = mapped_column(String(255), nullable=False)
    foreign_name: Mapped[str | None] = mapped_column(String(255))
    bar_code: Mapped[str | None] = mapped_column(String(100))
    items_group_code: Mapped[int | None] = mapped_column(Integer)
    sales_unit: Mapped[str | None] = mapped_column(String(50))
    inventory_uom: Mapped[str | None] = mapped_column(String(50))
    sales_item: Mapped[bool] = mapped_column(default=True, nullable=False)
    inventory_item: Mapped[bool] = mapped_column(default=True, nullable=False)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ItemEmbedding(Base, TimestampMixin):
    """pgvector embedding — semantic ürün arama için."""

    __tablename__ = "item_embeddings"

    item_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)


class CustomerAlias(Base, TimestampMixin):
    """Öğrenilen müşteri-özel ürün/cari adı eşleşmesi.

    Örnek: müşteri PDF'te "Vana 1/2 inch" yazıyor, gerçek ItemCode "A0001".
    Operatör düzeltmesi sonrası alias kaydedilir, sonraki sefer otomatik eşler.
    """

    __tablename__ = "customer_alias"
    __table_args__ = (
        Index("ix_customer_alias_lookup", "card_code", "alias_lower"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_code: Mapped[str] = mapped_column(String(50), nullable=False)
    alias_text: Mapped[str] = mapped_column(String(500), nullable=False)
    alias_lower: Mapped[str] = mapped_column(String(500), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # 'item' | 'bp'
    target_code: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)
    confirmed_by_user_id: Mapped[str | None] = mapped_column(String(36))
