"""Tenant'ın SAP $metadata + UserFieldsMD + master data cache modelleri.

Her tenant'ın SAP DB'sindeki UDF setleri farklı olabileceği için (UDF'ler standart
değil, müşteriye özel) bu cache tablolarına onboarding sırasında dump edilir ve
AI prompt'larına dinamik olarak enjekte edilir.

Tablolar şu an public schema'da (B retrofit'inde tenant schema'sına taşınacak;
çoklu tenant'ta `tenant_id` kolonuyla mantıksal izolasyon yeterli kabul ediliyor).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class TenantSapEntity(Base, TimestampMixin):
    """$metadata XML'den parse edilen entity tanımı (Quotation, Order, BP, Item vs.)."""

    __tablename__ = "tenant_sap_entities"
    __table_args__ = (
        Index("ix_tenant_sap_entities_tenant_entity", "tenant_id", "entity_name", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    entity_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # Property listesi: [{"name":"CardCode","type":"Edm.String","nullable":false}, ...]
    properties: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TenantUdf(Base, TimestampMixin):
    """UserFieldsMD'den parse edilen UDF tanımı.

    `valid_values_json`: enum UDF'lerin ValidValuesMD listesi.
    """

    __tablename__ = "tenant_udfs"
    __table_args__ = (
        Index(
            "ix_tenant_udfs_tenant_table_name",
            "tenant_id",
            "table_name",
            "name",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    table_name: Mapped[str] = mapped_column(String(64), nullable=False)  # OQUT, ORDR vs.
    name: Mapped[str] = mapped_column(String(64), nullable=False)  # U_Branch vs.
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_type: Mapped[str] = mapped_column(String(32), nullable=False)  # String/Date/Numeric...
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_values_json: Mapped[list[dict[str, str]] | None] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TenantMasterData(Base, TimestampMixin):
    """SalesPersons, Projects, Warehouses, Currencies, VatGroups, PriceLists vs."""

    __tablename__ = "tenant_master_data"
    __table_args__ = (
        Index(
            "ix_tenant_master_data_kind_code",
            "tenant_id",
            "kind",
            "code",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # sales_person/project/...
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
