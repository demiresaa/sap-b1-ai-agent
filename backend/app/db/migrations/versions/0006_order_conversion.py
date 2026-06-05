"""document_status enum'una order dönüşüm değerleri ekle; sap_submissions'a parent_submission_id FK.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-20

Postgres native enum ALTER TYPE ... ADD VALUE transactional değildir.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

NEW_STATUS_VALUES = [
    "converting_to_order",
    "order_submitted",
]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        row[0]
        for row in conn.execute(
            sa.text("SELECT unnest(enum_range(NULL::document_status))")
        )
    }
    for val in NEW_STATUS_VALUES:
        if val not in existing:
            op.execute(f"ALTER TYPE document_status ADD VALUE '{val}'")

    op.add_column(
        "sap_submissions",
        sa.Column(
            "parent_submission_id",
            sa.String(36),
            sa.ForeignKey("sap_submissions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("sap_submissions", "parent_submission_id")
    # Enum değer silmek Postgres'te desteklenmiyor — no-op.
