"""item_embeddings — IVFFlat index (ANN cosine search).

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-10

IVFFlat: Approximate Nearest Neighbor arama için. lists=100 —
beklenen item sayısı 1K-10K için optimum (sqrt(n) ≈ 100).
Migration öncesi item_embeddings tablosu boşsa index anında oluşur;
doluysa CONCURRENTLY seçeneği kullanılmalı (prod ortamda lock almaz).
"""
from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_item_emb_ivfflat
        ON item_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_item_emb_ivfflat")
