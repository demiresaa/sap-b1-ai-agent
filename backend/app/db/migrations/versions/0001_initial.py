"""Initial schema — kullanıcılar, belgeler, agent runs, SAP cache, onaylar, audit log.

Revision ID: 0001
Revises:
Create Date: 2026-05-14

Bu ilk migration tüm MVP tablolarını üretir. pgvector extension de burada açılır.
İleriki değişiklikler için `alembic revision --autogenerate -m "..."` kullanılır.
"""
from __future__ import annotations

from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401 — Base.metadata'ya tabloları kaydetmek için

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    # Audit log: UPDATE/DELETE engelle (append-only)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_log_block_modify()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log append-only: % engellendi', TG_OP;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_no_update
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_block_modify()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_block_modify()")
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    op.execute("DROP EXTENSION IF EXISTS vector")
