"""tenant_sap_entities + tenant_udfs + tenant_master_data — onboarding cache tabloları.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_sap_entities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("entity_name", sa.String(length=64), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE",
            name="fk_tenant_sap_entities_tenant_id_tenants",
        ),
    )
    op.create_index(
        "ix_tenant_sap_entities_tenant_entity",
        "tenant_sap_entities",
        ["tenant_id", "entity_name"],
        unique=True,
    )

    op.create_table(
        "tenant_udfs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("table_name", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("field_type", sa.String(length=32), nullable=False),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("valid_values_json", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE",
            name="fk_tenant_udfs_tenant_id_tenants",
        ),
    )
    op.create_index(
        "ix_tenant_udfs_tenant_table_name",
        "tenant_udfs",
        ["tenant_id", "table_name", "name"],
        unique=True,
    )

    op.create_table(
        "tenant_master_data",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE",
            name="fk_tenant_master_data_tenant_id_tenants",
        ),
    )
    op.create_index(
        "ix_tenant_master_data_kind_code",
        "tenant_master_data",
        ["tenant_id", "kind", "code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_master_data_kind_code", table_name="tenant_master_data")
    op.drop_table("tenant_master_data")
    op.drop_index("ix_tenant_udfs_tenant_table_name", table_name="tenant_udfs")
    op.drop_table("tenant_udfs")
    op.drop_index("ix_tenant_sap_entities_tenant_entity", table_name="tenant_sap_entities")
    op.drop_table("tenant_sap_entities")
