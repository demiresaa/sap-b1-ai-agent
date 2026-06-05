"""Tenant onboarding: SAP $metadata + UserFieldsMD + master data cache.

Kullanım:
  cd backend
  .venv/bin/python scripts/onboard_tenant.py \\
      --slug elekon \\
      --name "Elekon" \\
      --sl-url https://10.11.10.46:50000/b1s/v1 \\
      --company-db 2026_Test \\
      --sap-user manager \\
      --sap-pass NyNl.2021 \\
      [--no-fetch]   # sadece tenant satırı + Vault push (SAP'a dokunma)

Adımlar:
  1. tenants tablosuna satır insert (yoksa).
  2. Vault'a credential push (vault_enabled ise).
  3. (--no-fetch yoksa) SAP'a bağlan: $metadata + UserFieldsMD (OQUT/QUT1/ORDR/RDR1/
     OCRD/OITM) + master data → cache tablolarına yaz.

Hata olursa hata kodu 1, başarı 0 döner.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.vault import vault as vault_client
from app.db.base import new_uuid
from app.db.models import (
    Tenant,
    TenantMasterData,
    TenantSapEntity,
    TenantUdf,
)
from app.db.session import SessionFactory

logger = logging.getLogger("onboard")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

UDF_TABLES = ("OQUT", "QUT1", "ORDR", "RDR1", "OCRD", "OITM")

MASTER_ENDPOINTS = {
    "sales_person": ("SalesPersons", "SalesEmployeeCode", "SalesEmployeeName"),
    "project": ("Projects", "Code", "Name"),
    "warehouse": ("Warehouses", "WarehouseCode", "WarehouseName"),
    "currency": ("Currencies", "Code", "Name"),
    "price_list": ("PriceLists", "PriceListNo", "PriceListName"),
}


async def main() -> int:
    args = _parse_args()
    async with SessionFactory() as db:
        tenant = await _upsert_tenant(db, args)
        if vault_client.is_enabled():
            _push_to_vault(args)
            logger.info("Vault'a credential yazıldı.")
        else:
            logger.warning("Vault disabled — credential .env'den okunacak (dev mode).")

        if args.no_fetch:
            await db.commit()
            logger.info("--no-fetch verildi, SAP fetch atlandı.")
            return 0

        sap_client = _build_sap_client(args)
        try:
            await _login(sap_client, args)
            await _fetch_metadata(sap_client, db, tenant)
            for table in UDF_TABLES:
                await _fetch_udfs(sap_client, db, tenant, table)
            for kind, (endpoint, code_field, name_field) in MASTER_ENDPOINTS.items():
                await _fetch_master(
                    sap_client, db, tenant, kind, endpoint, code_field, name_field
                )
            tenant.onboarded_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Onboarding tamam: tenant=%s", tenant.slug)
        finally:
            await _logout(sap_client)
            await sap_client.aclose()
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tenant onboarding")
    p.add_argument("--slug", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--sl-url", required=True, help="https://host:50000/b1s/v1")
    p.add_argument("--company-db", required=True)
    p.add_argument("--sap-user", required=True)
    p.add_argument("--sap-pass", required=True)
    p.add_argument("--default-warehouse", default=None)
    p.add_argument("--default-sales-person", type=int, default=None)
    p.add_argument("--default-currency", default=None)
    p.add_argument(
        "--no-fetch",
        action="store_true",
        help="Tenant + Vault yaz, SAP'a bağlanma (test/iskelet için)",
    )
    return p.parse_args()


async def _upsert_tenant(db: Any, args: argparse.Namespace) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.slug == args.slug))
    tenant = result.scalar_one_or_none()
    vault_path = f"tenants/{args.slug}/sap"
    if tenant is None:
        tenant = Tenant(
            id=new_uuid(),
            slug=args.slug,
            name=args.name,
            schema_name=f"tenant_{args.slug}",
            sl_base_url=args.sl_url,
            company_db=args.company_db,
            vault_secret_path=vault_path,
            sap_dry_run=True,
            default_warehouse=args.default_warehouse,
            default_sales_person_id=args.default_sales_person,
            default_currency=args.default_currency,
        )
        db.add(tenant)
        await db.flush()
        logger.info("Tenant oluşturuldu: %s (%s)", args.slug, tenant.id)
    else:
        tenant.name = args.name
        tenant.sl_base_url = args.sl_url
        tenant.company_db = args.company_db
        tenant.vault_secret_path = vault_path
        if args.default_warehouse is not None:
            tenant.default_warehouse = args.default_warehouse
        if args.default_sales_person is not None:
            tenant.default_sales_person_id = args.default_sales_person
        if args.default_currency is not None:
            tenant.default_currency = args.default_currency
        logger.info("Tenant güncellendi: %s", args.slug)
    return tenant


def _push_to_vault(args: argparse.Namespace) -> None:
    """Vault KV v2'ye credential yaz. hvac sync, basit POST."""
    import hvac

    client = hvac.Client(url=settings.vault_addr, token=settings.vault_token)
    client.secrets.kv.v2.create_or_update_secret(
        path=f"tenants/{args.slug}/sap",
        secret={
            "username": args.sap_user,
            "password": args.sap_pass,
            "company_db": args.company_db,
            "sl_base_url": args.sl_url,
        },
        mount_point=settings.vault_kv_mount,
    )


def _build_sap_client(args: argparse.Namespace) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=args.sl_url,
        verify=settings.sap_verify_ssl,
        timeout=30.0,
    )


async def _login(client: httpx.AsyncClient, args: argparse.Namespace) -> None:
    resp = await client.post(
        "/Login",
        json={
            "CompanyDB": args.company_db,
            "UserName": args.sap_user,
            "Password": args.sap_pass,
        },
    )
    resp.raise_for_status()
    logger.info("SAP login OK (CompanyDB=%s)", args.company_db)


async def _logout(client: httpx.AsyncClient) -> None:
    try:
        await client.post("/Logout")
    except Exception:
        pass


async def _fetch_metadata(client: httpx.AsyncClient, db: Any, tenant: Tenant) -> None:
    resp = await client.get("/$metadata")
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    # OData EDM namespace
    ns = {"edm": "http://docs.oasis-open.org/odata/ns/edm"}
    entities_added = 0
    # Sadece ilgilendiğimiz entity'ler — tüm $metadata büyük olabilir
    targeted = {"Quotation", "Order", "BusinessPartner", "Item"}
    for et in root.iter("{%s}EntityType" % ns["edm"]):
        name = et.attrib.get("Name", "")
        if name not in targeted:
            continue
        props = []
        for prop in et.findall("edm:Property", ns):
            props.append(
                {
                    "name": prop.attrib.get("Name"),
                    "type": prop.attrib.get("Type"),
                    "nullable": prop.attrib.get("Nullable", "true") == "true",
                }
            )
        await db.execute(
            delete(TenantSapEntity).where(
                TenantSapEntity.tenant_id == tenant.id,
                TenantSapEntity.entity_name == name,
            )
        )
        db.add(
            TenantSapEntity(
                id=new_uuid(),
                tenant_id=tenant.id,
                entity_name=name,
                properties=props,
                fetched_at=datetime.now(timezone.utc),
            )
        )
        entities_added += 1
    logger.info("$metadata: %d entity cache'lendi", entities_added)


async def _fetch_udfs(
    client: httpx.AsyncClient, db: Any, tenant: Tenant, table_name: str
) -> None:
    resp = await client.get(
        "/UserFieldsMD", params={"$filter": f"TableName eq '{table_name}'"}
    )
    if resp.status_code == 404:
        logger.warning("UserFieldsMD endpoint 404 (%s)", table_name)
        return
    resp.raise_for_status()
    rows = resp.json().get("value", [])

    await db.execute(
        delete(TenantUdf).where(
            TenantUdf.tenant_id == tenant.id, TenantUdf.table_name == table_name
        )
    )
    for r in rows:
        name = r.get("Name") or ""
        if not name:
            continue
        if not name.startswith("U_"):
            name = f"U_{name}"
        db.add(
            TenantUdf(
                id=new_uuid(),
                tenant_id=tenant.id,
                table_name=table_name,
                name=name,
                description=r.get("Description"),
                field_type=str(r.get("Type") or "String"),
                size=r.get("Size"),
                valid_values_json=r.get("ValidValuesMD"),
                fetched_at=datetime.now(timezone.utc),
            )
        )
    logger.info("UDFs cached: %s = %d adet", table_name, len(rows))


async def _fetch_master(
    client: httpx.AsyncClient,
    db: Any,
    tenant: Tenant,
    kind: str,
    endpoint: str,
    code_field: str,
    name_field: str,
) -> None:
    resp = await client.get(f"/{endpoint}", params={"$top": 500})
    if resp.status_code == 404:
        logger.warning("Master data endpoint 404 (%s)", endpoint)
        return
    resp.raise_for_status()
    rows = resp.json().get("value", [])

    await db.execute(
        delete(TenantMasterData).where(
            TenantMasterData.tenant_id == tenant.id, TenantMasterData.kind == kind
        )
    )
    for r in rows:
        code = r.get(code_field)
        if code is None:
            continue
        db.add(
            TenantMasterData(
                id=new_uuid(),
                tenant_id=tenant.id,
                kind=kind,
                code=str(code),
                name=r.get(name_field),
                payload=r,
                fetched_at=datetime.now(timezone.utc),
            )
        )
    logger.info("Master '%s': %d kayıt", kind, len(rows))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
