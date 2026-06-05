"""document_status enum'una yeni değerler ekle: PDF akışı ve müşteri kabulü.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-17

Postgres native enum'a ALTER TYPE ... ADD VALUE ile yeni label'lar eklenir.
Bu işlem transactional değildir (Postgres kısıtı), ayrıca çalışır.
"""
from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

NEW_VALUES = [
    "PDF_GENERATED",
    "CUSTOMER_ACCEPTED",
    "CUSTOMER_REJECTED",
    "EDITED_AFTER_ACCEPTANCE",
]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        row[0]
        for row in conn.execute(
            __import__("sqlalchemy").text(
                "SELECT unnest(enum_range(NULL::document_status))"
            )
        )
    }
    for val in NEW_VALUES:
        if val not in existing:
            # ADD VALUE transactional olamaz — execute dışında çalışır.
            op.execute(f"ALTER TYPE document_status ADD VALUE '{val}'")


def downgrade() -> None:
    # Postgres enum'dan değer silmek doğrudan desteklenmiyor.
    # Downgrade gerekirse enum'u yeniden oluşturmak gerekir — şimdilik no-op.
    pass
