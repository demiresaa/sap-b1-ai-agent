"""SAP B1 Quotations — Satış Teklifi.

Plan: docs/modules/00-quotations-field-mapping.md
Endpoint: /Quotations
"""
from __future__ import annotations

from typing import Any

from app.sap.client import SAPServiceLayerClient

# Elekon şirketi sabit değerleri — SAP dump 2026-05-21
SERIES = 14              # OQUT serisi
DEFAULT_CURRENCY = "EUR"
DEFAULT_WAREHOUSE = "01"
DEFAULT_BRANCH = "Elekon"
DEFAULT_TEKLIF_TURU = "Standart_Teklif"   # geçerli bir değer; "---------------" geçersiz
DEFAULT_SATIN_ALMACI = "1"                 # Gizem Bedir — QUT1 satır UDF mandatory


class QuotationsModule:
    PATH = "/Quotations"

    def __init__(self, client: SAPServiceLayerClient) -> None:
        self.client = client

    @classmethod
    def build_payload(
        cls,
        *,
        card_code: str,
        documents_owner: int,
        sales_person_code: int,
        project: str,
        lines: list[dict[str, Any]],
        num_at_card: str | None = None,
        doc_currency: str = DEFAULT_CURRENCY,
        doc_date: str | None = None,
        due_date: str | None = None,
        comments: str | None = None,
        teklif_turu: str = DEFAULT_TEKLIF_TURU,
        teklif_durumu: str = "Hazırlanıyor",
        odeme_kosullari: str | None = None,
        odm_tr: str | None = None,
        kur_degerleme: str | None = None,
        proje_adi: str | None = None,
        tahmini_gercek_tarih: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Elekon'a özgü Quotation payload'u oluşturur.

        Satır her biri şunları içermeli:
          item_code, quantity, unit_price, project_code
          (opsiyonel) discount_pct, vat_group, warehouse_code
        """
        if teklif_turu == "Key_Account" and not proje_adi:
            raise ValueError("U_Teklif_Turu 'Key_Account' ise U_Proje_Adi ZORUNLU.")

        payload: dict[str, Any] = {
            "Series": SERIES,
            "CardCode": card_code,
            "DocCurrency": doc_currency,
            "SalesPersonCode": sales_person_code,
            "DocumentsOwner": documents_owner,
            "Project": project,
            "U_Branch": DEFAULT_BRANCH,
            "U_Teklif_Turu": teklif_turu,
            "U_Teklif_Durumu": teklif_durumu,
            "DocumentLines": [
                cls._build_line(line, project) for line in lines
            ],
        }

        if num_at_card:
            payload["NumAtCard"] = num_at_card
        if doc_date:
            payload["DocDate"] = doc_date
        if due_date:
            payload["DocDueDate"] = due_date
        if comments:
            payload["Comments"] = comments
        if odeme_kosullari:
            payload["U_Odeme_Kosullari"] = odeme_kosullari
        if odm_tr:
            payload["U_Odm_Tr"] = odm_tr
        if kur_degerleme:
            payload["U_Kur_Degerleme"] = kur_degerleme
        if proje_adi:
            payload["U_Proje_Adi"] = proje_adi
        if tahmini_gercek_tarih:
            payload["U_Tahimini_Gercek_Tarih"] = tahmini_gercek_tarih

        if overrides:
            payload.update(overrides)

        return payload

    @classmethod
    def _build_line(cls, line: dict[str, Any], default_project: str) -> dict[str, Any]:
        built: dict[str, Any] = {
            "ItemCode": line["item_code"],
            "Quantity": line["quantity"],
            "UnitPrice": line["unit_price"],
            "WarehouseCode": line.get("warehouse_code", DEFAULT_WAREHOUSE),
            "ProjectCode": line.get("project_code") or default_project,
            "U_SatinAlmaci": line.get("satin_almaci", DEFAULT_SATIN_ALMACI),
        }
        if line.get("discount_pct") is not None:
            built["DiscountPercent"] = line["discount_pct"]
        if line.get("vat_group"):
            built["VatGroup"] = line["vat_group"]
        return built

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /Quotations → tam SAP response (DocEntry, DocNum, Document_ApprovalRequests...)."""
        return await self.client.post(self.PATH, payload)

    async def get(self, doc_entry: int) -> dict[str, Any]:
        return await self.client.get(f"{self.PATH}({doc_entry})")

    async def list(
        self, *, top: int = 50, filter_expr: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"$top": top, "$orderby": "DocEntry desc"}
        if filter_expr:
            params["$filter"] = filter_expr
        resp = await self.client.get(self.PATH, **params)
        return resp.get("value", [])

    async def cancel(self, doc_entry: int) -> None:
        await self.client.post(f"{self.PATH}({doc_entry})/Cancel", {})
