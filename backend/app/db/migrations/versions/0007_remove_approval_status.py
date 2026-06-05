"""document_status enum'undan APPROVAL değerini kaldır.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-30

Onay sistemi kaldırıldı (insan-loop zaten READY adımında var).
Mevcut APPROVAL satırları READY'ye taşınır, sonra enum yeniden yaratılır.
"""
from __future__ import annotations

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

NEW_VALUES = (
    "RECEIVED",
    "READING",
    "MATCHING",
    "READY",
    "PDF_GENERATED",
    "CUSTOMER_ACCEPTED",
    "CUSTOMER_REJECTED",
    "EDITED_AFTER_ACCEPTANCE",
    "SUBMITTING",
    "SUBMITTED",
    "CONVERTING_TO_ORDER",
    "ORDER_SUBMITTED",
    "ERROR",
    "REJECTED",
)


def upgrade() -> None:
    # 1) APPROVAL kayıtları READY'ye taşı
    op.execute("UPDATE documents SET status = 'READY' WHERE status = 'APPROVAL'")

    # 2) Eski enum'u yeniden adlandır, yenisini oluştur, sütunu çevir, eskiyi düşür
    values_sql = ", ".join(f"'{v}'" for v in NEW_VALUES)
    op.execute("ALTER TYPE document_status RENAME TO document_status_old")
    op.execute(f"CREATE TYPE document_status AS ENUM ({values_sql})")
    op.execute(
        "ALTER TABLE documents ALTER COLUMN status TYPE document_status "
        "USING status::text::document_status"
    )
    op.execute("DROP TYPE document_status_old")


def downgrade() -> None:
    # APPROVAL değerini geri ekle
    op.execute("ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'APPROVAL'")
