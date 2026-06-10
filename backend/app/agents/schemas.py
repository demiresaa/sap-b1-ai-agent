"""Agent'lar arasında paylaşılan Pydantic veri modelleri.

`ExtractedDocument` — DocumentReader çıktısı; pipeline boyunca enrich edilerek
SAPWriter'a verilecek payload'ı oluşturur.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class ExtractedCustomer(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None


class ExtractedLine(BaseModel):
    line_no: int | str
    description: str
    item_code_raw: str | None = None
    barcode: str | None = None
    quantity: float
    unit: str | None = None
    unit_price: float | None = None
    discount_pct: float | None = None
    tax_code: str | None = None
    total: float | None = None

    # Operatör / eşleştirme aşamasında doldurulur
    item_code: str | None = None        # ItemCode (SAP kodu)
    vat_group: str = "S01"              # VatGroup
    warehouse_code: str = "01"          # WarehouseCode
    project_code: str | None = None     # ProjectCode (satır seviyesi)
    currency: str = "EUR"               # Currency


class ExtractedDocument(BaseModel):
    """AI'ın PDF'ten çıkardığı yapılandırılmış belge.

    `confidence` alan başına 0-1 puan içerir; düşük olanlar UI'da sarı.
    Operatör form'dan SAP alanlarını (sales_person_code vb.) doldurur.
    """

    kind: str = "sales_order"  # sales_order | quotation | unknown
    customer: ExtractedCustomer = Field(default_factory=ExtractedCustomer)
    reference_no: str | None = None       # NumAtCard
    doc_date: date | None = None
    tax_date: date | None = None          # TaxDate (boşsa doc_date kullanılır)
    due_date: date | None = None
    currency: str = "EUR"
    lines: list[ExtractedLine] = Field(default_factory=list)
    notes: str | None = None
    confidence: dict[str, float] = Field(default_factory=dict)

    # Operatör tarafından doldurulur (form / PATCH)
    sales_person_code: int | None = None       # SalesPersonCode
    documents_owner: int | None = None         # DocumentsOwner
    project: str | None = None                 # Project (belge seviyesi)
    payment_group_code: int | None = None      # PaymentGroupCode
    ship_to_code: str | None = None            # ShipToCode
    pay_to_code: str | None = None             # PayToCode
    u_branch: str = "Elekon"                   # U_Branch
    u_teklif_turu: str = "Standart_Teklif"     # U_Teklif_Turu
    u_teklif_durumu: str = "Hazırlanıyor"      # U_Teklif_Durumu
    u_tahmini_gercek_tarih: date | None = None # U_Tahimini_Gercek_Tarih


class CustomerMatch(BaseModel):
    card_code: str | None = None
    card_name: str | None = None
    score: float = 0.0
    strategy: str = "none"  # tax_id | email | alias | fuzzy_name | none
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class ProductMatch(BaseModel):
    line_no: int | str
    item_code: str | None = None
    item_name: str | None = None
    score: float = 0.0
    strategy: str = "none"  # barcode | code | alias | semantic | fuzzy_name | none
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class PricingCheck(BaseModel):
    line_no: int | str
    extracted_price: float | None
    sap_list_price: float | None
    delta_pct: float | None
    discount_pct: float | None
    breaches_threshold: bool = False
    note: str | None = None


class StockCheck(BaseModel):
    line_no: int | str
    item_code: str
    requested_qty: float
    available_qty: float | None
    in_stock: bool
    note: str | None = None
    suggested_alternatives: list[dict[str, Any]] = Field(default_factory=list)
