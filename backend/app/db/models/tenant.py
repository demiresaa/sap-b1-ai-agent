"""Tenant modeli — multi-tenant config'in kök kaydı.

Her tenant kendi SAP server'ına bağlı (sl_base_url + company_db), kendi UDF setine sahip
ve kendi `tenant_<slug>` Postgres schema'sında verisini tutar (B2 sonrası).
SAP credential'ları Vault'ta (`kv/tenants/<slug>/sap`); bu tabloda sadece path tutulur.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Tenant(Base, TimestampMixin):
    """Tenant — SaaS müşterisi.

    `slug`: URL-safe identifier (örn. `elekon`). Schema adı `tenant_<slug>`.
    `vault_secret_path`: KV v2 path — `tenants/<slug>/sap` (mount prefix dahil değil).
    `sap_dry_run`: true ise SAP'a yazma yapılmaz, JSON payload üretilir.
    """

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # SAP bağlantı bilgileri (credential'lar Vault'ta)
    sl_base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    company_db: Mapped[str] = mapped_column(String(128), nullable=False)
    vault_secret_path: Mapped[str] = mapped_column(String(255), nullable=False)

    # Davranış flag'leri
    sap_dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Default değerler (tenant başına)
    default_warehouse: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_sales_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    default_pdf_template: Mapped[str] = mapped_column(
        String(64), default="default", nullable=False
    )

    # Onay eşikleri vb. tenant başına config — şimdilik JSON serbest alan
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
