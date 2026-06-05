"""Document API şemaları."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.db.models.document import DocumentKind, DocumentSource, DocumentStatus




class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: DocumentSource
    kind: DocumentKind
    status: DocumentStatus
    original_filename: str | None
    file_size_bytes: int | None
    source_email: str | None
    source_subject: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ExtractedDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    payload: dict[str, Any]
    confidence: dict[str, Any] | None = None


class DocumentDetail(DocumentOut):
    extracted: ExtractedDataOut | None = None


class DocumentPatch(BaseModel):
    """Operatör düzeltmesi — extracted_data payload'unu günceller."""

    payload: dict[str, Any]


class SubmitResponse(BaseModel):
    submission_id: str
    sap_doc_entry: int | None = None
    sap_doc_num: int | None = None
    dry_run: bool = False
    sap_endpoint: str | None = None
    sap_payload: dict[str, Any] | None = None
    message: str | None = None


class ConvertToOrderResponse(BaseModel):
    """Teklif → SAP Order dönüşüm sonucu."""

    order_doc_entry: int
    order_doc_num: int | None = None
    dry_run: bool = False
    message: str


class OrderCandidateOut(BaseModel):
    """Sipariş aday listesi satırı — CUSTOMER_ACCEPTED + ORDER_SUBMITTED teklifleri."""

    document_id: str
    status: str                      # "candidate" | "converted"
    card_code: str | None = None
    card_name: str | None = None
    doc_currency: str | None = None
    doc_total: float | None = None
    original_filename: str | None = None
    quotation_doc_entry: int | None = None
    quotation_doc_num: int | None = None
    order_doc_entry: int | None = None
    order_doc_num: int | None = None
    created_at: datetime
    converted_at: datetime | None = None
