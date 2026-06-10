"""approval_rules + approval_requests tabloları.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-10

D1 Sprint: Multi-stage onay sistemi.
  - approval_rules: koşul DSL (field/operator/threshold/action/sla_hours)
  - approval_requests: belge başına onay talebi, parent_id ile zincir
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE IF NOT EXISTS approval_action AS ENUM "
               "('require_approval', 'block', 'warn')")
    op.execute("CREATE TYPE IF NOT EXISTS approval_status AS ENUM "
               "('pending', 'approved', 'rejected', 'escalated', 'expired')")

    op.create_table(
        "approval_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("operator", sa.String(10), nullable=False),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("action", sa.Enum("require_approval", "block", "warn",
                                    name="approval_action", create_type=False), nullable=False),
        sa.Column("required_role", sa.String(20), nullable=False, server_default="manager"),
        sa.Column("sla_hours", sa.Integer, nullable=False, server_default="24"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tenant_id", sa.String(36),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approval_rules_active_priority", "approval_rules",
                    ["is_active", "priority"])

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.String(36),
                  sa.ForeignKey("approval_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_id", sa.String(36),
                  sa.ForeignKey("approval_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("escalation_level", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("pending", "approved", "rejected", "escalated", "expired",
                                    name="approval_status", create_type=False), nullable=False),
        sa.Column("approver_role", sa.String(20), nullable=False),
        sa.Column("decided_by_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision", sa.String(10), nullable=True),
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rule_context", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approval_requests_doc_status", "approval_requests",
                    ["document_id", "status"])
    op.create_index("ix_approval_requests_deadline", "approval_requests", ["deadline_at"])

    # Varsayılan kurallar: iskonto > %15 → manager onayı
    op.execute("""
        INSERT INTO approval_rules (id, name, field, operator, threshold, action,
            required_role, sla_hours, priority, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid()::text, 'Yüksek iskonto onayı', 'discount_pct', 'gt', 15,
             'require_approval', 'manager', 24, 10, true, now(), now()),
            (gen_random_uuid()::text, 'Büyük tutar onayı', 'doc_total', 'gt', 100000,
             'require_approval', 'admin', 48, 20, true, now(), now()),
            (gen_random_uuid()::text, 'Düşük güven uyarısı', 'confidence', 'lt', 0.6,
             'warn', 'operator', 0, 30, true, now(), now())
    """)


def downgrade() -> None:
    op.drop_table("approval_requests")
    op.drop_table("approval_rules")
    op.execute("DROP TYPE IF EXISTS approval_status")
    op.execute("DROP TYPE IF EXISTS approval_action")
