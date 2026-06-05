"""Seed: ilk tenant (Elekon) + kullanıcılar + örnek approval kuralı.

Kullanım:
    cd backend && .venv/bin/python scripts/seed.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import (
    ApprovalRule,
    Tenant,
    User,
    UserRole,
    UserRoleAssignment,
)
from app.db.session import SessionFactory


TENANTS = [
    {
        "slug": "elekon",
        "name": "Elekon",
        "schema_name": "tenant_elekon",
        "sl_base_url": "https://10.11.10.46:50000/b1s/v1",
        "company_db": "2026_Test",
        "vault_secret_path": "tenants/elekon/sap",
        "sap_dry_run": True,
        "default_warehouse": "02",
        "default_sales_person_id": 14,
        "default_currency": "EUR",
    },
]


USERS = [
    {
        "email": "admin@example.com",
        "full_name": "Sistem Yöneticisi",
        "first_name": "Sistem",
        "last_name": "Yöneticisi",
        "password": "admin123",
        "roles": [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR],
        "tenant_slug": "elekon",
    },
    {
        "email": "manager@example.com",
        "full_name": "Satış Müdürü",
        "first_name": "Satış",
        "last_name": "Müdürü",
        "password": "manager123",
        "roles": [UserRole.MANAGER, UserRole.OPERATOR],
        "tenant_slug": "elekon",
    },
    {
        "email": "operator@example.com",
        "full_name": "Satış Mühendisi",
        "first_name": "Satış",
        "last_name": "Mühendisi",
        "password": "operator123",
        "roles": [UserRole.OPERATOR],
        "tenant_slug": "elekon",
    },
]


RULES = [
    {
        "name": "Yüksek tutar onayı (≥ 100.000 TRY)",
        "description": "TRY cinsinden 100k üstü siparişler müdür onayına gider.",
        "condition": {
            "all_of": [
                {"field": "currency", "op": "==", "value": "TRY"},
                {"field": "total_amount", "op": ">=", "value": 100_000},
            ]
        },
        "required_role": "manager",
        "priority": 100,
    },
    {
        "name": "Yüksek iskonto onayı (> %15)",
        "description": "%15 üstü iskonto müdür onayına gider.",
        "condition": {"field": "discount_pct", "op": ">", "value": 15},
        "required_role": "manager",
        "priority": 90,
    },
]


async def main() -> None:
    async with SessionFactory() as db:
        # 1) Tenants
        tenant_by_slug: dict[str, Tenant] = {}
        for t in TENANTS:
            existing_t = (
                await db.execute(select(Tenant).where(Tenant.slug == t["slug"]))
            ).scalar_one_or_none()
            if existing_t:
                tenant_by_slug[t["slug"]] = existing_t
                continue
            tenant = Tenant(**t)
            db.add(tenant)
            await db.flush()
            tenant_by_slug[t["slug"]] = tenant
            print(f"+ tenant {t['slug']} ({t['name']})")

        # 2) Users
        for u in USERS:
            existing = (
                await db.execute(select(User).where(User.email == u["email"]))
            ).scalar_one_or_none()
            if existing:
                continue
            tenant = tenant_by_slug.get(u["tenant_slug"]) if u.get("tenant_slug") else None
            user = User(
                email=u["email"],
                full_name=u["full_name"],
                first_name=u.get("first_name"),
                last_name=u.get("last_name"),
                hashed_password=hash_password(u["password"]),
                tenant_id=tenant.id if tenant else None,
            )
            user.role_assignments = [UserRoleAssignment(role=r) for r in u["roles"]]
            db.add(user)
            print(f"+ user {u['email']} (tenant={u.get('tenant_slug')})")

        # 3) Approval rules
        for r in RULES:
            existing = (
                await db.execute(select(ApprovalRule).where(ApprovalRule.name == r["name"]))
            ).scalar_one_or_none()
            if existing:
                continue
            db.add(ApprovalRule(**r))
            print(f"+ rule {r['name']}")

        await db.commit()
    print("✓ Seed tamam.")


if __name__ == "__main__":
    asyncio.run(main())
