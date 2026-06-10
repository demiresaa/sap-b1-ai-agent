"""customer_alias — embedding kolonu + IVFFlat index (RAG semantic arama).

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-10

CustomerAlias tablosuna pgvector sütunu eklenir. Operatör onayladığı her
description→item eşleşmesinin embedding'i burada tutulur. ProductMatcher,
yeni satır için tam eşleşme bulamazsa bu geçmiş onaylı eşleşmelerden
semantik arama yapar (RAG few-shot).

IVFFlat lists=50: customer_alias genellikle item_embeddings'den daha küçük
(binlerce kayıt), bu yüzden daha az list yeterli.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

EMBEDDING_DIM = 1536

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_alias",
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_customer_alias_emb_ivfflat
        ON customer_alias
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_customer_alias_emb_ivfflat")
    op.drop_column("customer_alias", "embedding")
