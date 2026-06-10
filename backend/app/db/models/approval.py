"""Onay talebi ve kural modelleri.

ApprovalRule: Hangi koşullarda onay gerektiğini tanımlar (yapılandırılabilir DSL).
ApprovalRequest: Bir belge için oluşturulan onay talebi (multi-stage chain desteği).
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class ApprovalStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class ApprovalAction(enum.StrEnum):
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"           # otomatik reddeder, operatör geçemez
    WARN = "warn"             # approval oluşturmaz, sadece uyarı


class ApprovalRule(Base, TimestampMixin):
    """Hangi koşulda onay gerektiğini tanımlayan kural.

    Örnekler:
      discount_pct > 15    → require_approval (manager)
      doc_total > 100000   → require_approval (admin)
      confidence < 0.6     → warn
    """

    __tablename__ = "approval_rules"
    __table_args__ = (
        Index("ix_approval_rules_active_priority", "is_active", "priority"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Koşul alanı: discount_pct | doc_total | confidence | item_count | new_customer
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    # Karşılaştırma operatörü: gt | lt | gte | lte | eq | neq
    operator: Mapped[str] = mapped_column(String(10), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    action: Mapped[ApprovalAction] = mapped_column(
        Enum(ApprovalAction, name="approval_action"),
        nullable=False,
        default=ApprovalAction.REQUIRE_APPROVAL,
    )
    # Onayı kimin vermesi gerektiği
    required_role: Mapped[str] = mapped_column(String(20), nullable=False, default="manager")
    # SLA: onay verilmezse kaç saat sonra eskalasyon
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )


class ApprovalRequest(Base, TimestampMixin):
    """Bir belge için oluşturulan onay talebi.

    `parent_id`: multi-stage zincir — level 1 onayı level 2'yi tetikler.
    `escalation_level`: 0=ilk seviye, 1+=eskalasyon.
    """

    __tablename__ = "approval_requests"
    __table_args__ = (
        Index("ix_approval_requests_doc_status", "document_id", "status"),
        Index("ix_approval_requests_deadline", "deadline_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("approval_rules.id", ondelete="SET NULL"), nullable=True
    )
    # Zincir: bu talep, parent tamamlandığında oluşturuldu
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("approval_requests.id", ondelete="SET NULL"), nullable=True
    )
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )
    approver_role: Mapped[str] = mapped_column(String(20), nullable=False)
    decided_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[str | None] = mapped_column(String(10))  # approve | reject
    comments: Mapped[str | None] = mapped_column(Text)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rule_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
