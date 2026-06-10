"""pg_trgm + unaccent — Türkçe fuzzy matching için GIN trigram index'leri.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-10

pg_trgm: "Arçelik" vs "ARCELIK AS" tarzı yazım farklarını yakalar.
unaccent: Türkçe İ/ı, Ş/ş, Ç/ç gibi aksan karakterlerini normalize eder.
Mevcut satırlar migrate sırasında unaccent(lower(...)) ile yeniden normalize edilir.
"""
from __future__ import annotations

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    # GIN trigram index — LIKE '%...%' ve similarity() sorguları için
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_item_cache_name_trgm
        ON item_cache USING GIN (item_name_lower gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_bp_cache_name_trgm
        ON bp_cache USING GIN (card_name_lower gin_trgm_ops)
        """
    )

    # Mevcut satırları unaccent ile normalize et
    op.execute(
        """
        UPDATE item_cache
        SET item_name_lower = unaccent(lower(item_name))
        WHERE item_name IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE bp_cache
        SET card_name_lower = unaccent(lower(card_name))
        WHERE card_name IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_item_cache_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_bp_cache_name_trgm")
