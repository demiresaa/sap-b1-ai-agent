"""Tenants tablosu + User Clerk uyumlu kolonları + User.tenant_id FK.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-17

Multi-tenant pivot ilk migration'ı:
  - `tenants` tablosu (public schema)
  - `users` tablosuna `clerk_user_id`, `first_name`, `last_name`, `tenant_id` ekle
  - `users.hashed_password` nullable yapılır (Clerk migrasyonunda null'a düşecek)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("schema_name", sa.String(length=64), nullable=False),
        sa.Column("sl_base_url", sa.String(length=255), nullable=False),
        sa.Column("company_db", sa.String(length=128), nullable=False),
        sa.Column("vault_secret_path", sa.String(length=255), nullable=False),
        sa.Column(
            "sap_dry_run",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("default_warehouse", sa.String(length=32), nullable=True),
        sa.Column("default_sales_person_id", sa.Integer(), nullable=True),
        sa.Column("default_currency", sa.String(length=8), nullable=True),
        sa.Column(
            "default_pdf_template",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'default'"),
        ),
        sa.Column(
            "settings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
        sa.UniqueConstraint("schema_name", name="uq_tenants_schema_name"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # users tablosuna Clerk uyumlu kolonlar + tenant_id
    op.add_column(
        "users", sa.Column("clerk_user_id", sa.String(length=64), nullable=True)
    )
    op.add_column("users", sa.Column("first_name", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("tenant_id", sa.String(length=36), nullable=True))

    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_foreign_key(
        "fk_users_tenant_id_tenants",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # hashed_password nullable
    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.drop_constraint("fk_users_tenant_id_tenants", "users", type_="foreignkey")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_column("users", "tenant_id")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_column("users", "clerk_user_id")
    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=False)

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
