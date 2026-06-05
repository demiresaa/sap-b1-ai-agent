"""quotation_pdfs tablosu — bizim ürettiğimiz teklif PDF versiyon kayıtları.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotation_pdfs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "template_name",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'default'"),
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
            name="fk_quotation_pdfs_document_id_documents",
        ),
    )
    op.create_index(
        "ix_quotation_pdfs_document_id", "quotation_pdfs", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_quotation_pdfs_document_id", table_name="quotation_pdfs")
    op.drop_table("quotation_pdfs")
