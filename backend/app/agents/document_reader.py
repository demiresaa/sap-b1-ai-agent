"""DocumentReader — PDF/Excel/DOCX/image → yapılandırılmış JSON.

Akış:
  1. Dosya uzantısı `.xlsx`/`.xls` ise `excel_parser` ile tabular okuyup AI'ya kolon
     mapping prompt'u gönder.
  2. PDF ise `pdfplumber` ile text + tablo çıkar.
  3. Text boşsa veya çok kısa ise (image-only PDF) `pdf2image` + Claude vision fallback.
  4. Claude'a Türkçe sistem promptu + JSON schema (Pydantic) gönder, yanıtı parse et.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import pathlib
from typing import Any

import pdfplumber

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.llm_client import call_anthropic_json, call_llm_with_tools
from app.agents.schemas import ExtractedDocument
from app.services.excel_parser import ExcelSheet, parse_excel

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 50

EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}

SYSTEM_PROMPT = """You are a document processing assistant for SAP Business One.
Extract structured sales order / quotation data from the provided document (PDF or Excel).

Column names in Excel vary by company — map them to SAP fields yourself:
"Stok Kodu" / "Ürün Kodu" / "Item Code" / "Model No" → item_code_raw
"Açıklama" / "Tanım" / "Description" → description
"Miktar" / "Qty" / "Quantity" → quantity
"Birim Fiyat" / "Unit Price" → unit_price
"İndirim" / "Discount" → discount_pct

Extract the following fields:
- kind: "sales_order" or "quotation"
  (sipariş/order → sales_order, teklif/quotation → quotation)
- customer: { name, tax_id, email, phone, address }
- reference_no: customer's own reference number (NumAtCard)
- doc_date: document date (YYYY-MM-DD)
- due_date: delivery / due date (YYYY-MM-DD)
- currency: TRY, EUR, or USD (infer from ₺/€/$ symbols)
- lines: array of line items, each with:
  { line_no, description, item_code_raw, barcode, quantity, unit,
    unit_price, discount_pct, tax_code, total }
- notes: free-text remarks
- confidence: 0–1 score per top-level field (e.g. {"customer.name": 0.95, "lines": 0.8})

CRITICAL — item_code_raw rules:
- item_code_raw must be the manufacturer's product/stock/model code (e.g. "HELVAR-321", "ABC-100").
- If the document has an explicit "Stok Kodu" / "Ürün Kodu" / "Item Code" /
  "Model No" column, use that value.
- If no such column exists, use the brand/model identifier (e.g. "Helvar 321") as item_code_raw.
- NEVER use a position number / BOQ sequence number as item_code_raw.
  In Turkish tender / metraj / BOQ documents, values like "E02.01" or "A01.03" are
  position/section numbers (poz numarası), NOT product codes. Write them into line_no instead.
- If no item code can be determined, set item_code_raw to null and put the brand/model in barcode.

barcode: manufacturer barcode, catalogue code, or secondary model reference (e.g. "Helvar 321").
  May overlap with item_code_raw; both fields can be populated simultaneously.

OUTPUT: Return valid JSON only — no explanation, no markdown. Set unknown fields to null."""


class DocumentReaderAgent(BaseAgent):
    name = "document_reader"

    async def _run(
        self,
        ctx: AgentContext,
        file_path: str | None = None,
        sap_client: Any | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if not file_path:
            raise ValueError("file_path zorunlu")
        path = pathlib.Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Belge bulunamadı: {file_path}")

        suffix = path.suffix.lower()
        used_vision = False
        raw_text_length = 0

        if suffix in EXCEL_EXTENSIONS:
            logger.info("[doc_reader] Excel ingest: %s", path.name)
            sheet = parse_excel(path)
            extracted = await _extract_via_excel(sheet)
            raw_text_length = len(sheet.to_prompt_text())
        else:
            text = _extract_text(path)
            raw_text_length = len(text)
            logger.info("[doc_reader] PDF text uzunluğu=%d karakter", len(text))
            if len(text.strip()) < MIN_TEXT_LENGTH:
                logger.info("[doc_reader] text kısa, vision fallback'e geçiliyor")
                extracted = await _extract_via_vision(path)
                used_vision = True
            elif sap_client is not None:
                logger.info("[doc_reader] tool use aktif, SAP araçları etkin")
                extracted = await _extract_via_text_with_tools(text, sap_client)
            else:
                extracted = await _extract_via_text(text)

        logger.info(
            "[doc_reader] çıkarım tamam: kind=%s customer=%r lines=%d",
            extracted.kind,
            extracted.customer.name,
            len(extracted.lines),
        )

        confidence = _aggregate_confidence(extracted.confidence)
        needs_human = confidence < 0.6 or not extracted.lines
        reason: str | None = None
        if needs_human:
            reason = (
                "Satır bulunamadı, manuel giriş gerekli"
                if not extracted.lines
                else "Çıkarım güveni düşük, lütfen kontrol edin"
            )

        return AgentResult(
            agent_name=self.name,
            success=True,
            confidence=confidence,
            data={
                "extracted": extracted.model_dump(mode="json"),
                "used_vision": used_vision,
                "raw_text_length": raw_text_length,
                "source": "excel" if suffix in EXCEL_EXTENSIONS else "pdf",
            },
            needs_human=needs_human,
            human_reason=reason,
        )


def _extract_text(path: pathlib.Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
            for table in page.extract_tables() or []:
                for row in table:
                    parts.append(" | ".join(c or "" for c in row))
    return "\n".join(parts)


async def _extract_via_text(text: str) -> ExtractedDocument:
    raw = await call_anthropic_json(
        system=SYSTEM_PROMPT,
        user_message=f"PDF içeriği:\n\n{text}",
        max_tokens=4096,
    )
    return _parse_extracted(raw)


async def _extract_via_excel(sheet: ExcelSheet) -> ExtractedDocument:
    user_message = (
        "Aşağıdaki Excel sipariş listesini SAP B1 alanlarına çevir.\n"
        "Header'ları SAP alanlarına SEN map et (Stok Kodu/Ürün Kodu/Item Code → "
        "item_code_raw; Açıklama/Tanım/Description → description; Miktar/Qty → "
        "quantity; Birim Fiyat/Unit Price → unit_price; İndirim/Discount → "
        "discount_pct).\n\n"
        f"{sheet.to_prompt_text()}"
    )
    raw = await call_anthropic_json(
        system=SYSTEM_PROMPT,
        user_message=user_message,
        max_tokens=4096,
    )
    return _parse_extracted(raw)


async def _extract_via_vision(path: pathlib.Path) -> ExtractedDocument:
    images_b64 = _render_pages_b64(path)
    raw = await call_anthropic_json(
        system=SYSTEM_PROMPT,
        user_message="PDF görselleri verildi, içeriği çıkar.",
        images_b64=images_b64,
        max_tokens=4096,
    )
    return _parse_extracted(raw)


def _render_pages_b64(path: pathlib.Path, max_pages: int = 3) -> list[str]:
    images_b64: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:max_pages]:
            img = page.to_image(resolution=150).original
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            images_b64.append(base64.b64encode(buf.getvalue()).decode("ascii"))
    return images_b64


def _parse_extracted(raw: dict[str, Any] | str) -> ExtractedDocument:
    if isinstance(raw, str):
        raw = json.loads(raw)
    return ExtractedDocument.model_validate(raw)


def _aggregate_confidence(confidence: dict[str, float]) -> float:
    if not confidence:
        return 0.7
    return sum(confidence.values()) / len(confidence)


# ---------------------------------------------------------------------------
# Tool use pattern — Claude SAP'ı sorgulayarak belirsiz alanları doldurabilir
# ---------------------------------------------------------------------------

SAP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "sap_search_items",
        "description": (
            "SAP'ta stok kartı ara. Ürün adı veya kodu belirsizse kullan. "
            "item_code_raw veya description ile SAP ItemCode'u doğrula."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Arama terimi (ürün adı, kodu veya barkod)",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "sap_search_bp",
        "description": (
            "SAP'ta iş ortağı (müşteri/tedarikçi) ara. "
            "Müşteri adı veya vergi numarası belirsizse kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Müşteri adı"},
                "tax_id": {"type": "string", "description": "Vergi numarası (opsiyonel)"},
            },
            "required": ["name"],
        },
    },
]


async def _sap_tool_handler(
    tool_name: str,
    tool_input: dict[str, Any],
    sap_client: Any | None,
) -> Any:
    """SAP araç çağrılarını yürütür.

    sap_client None ise (örn. birim testlerde) boş liste döner.
    """
    if sap_client is None:
        return []
    try:
        if tool_name == "sap_search_items":
            return await sap_client.get("/Items", **{
                "$filter": f"contains(ItemName,'{tool_input['query']}')",
                "$select": "ItemCode,ItemName,BarCode",
                "$top": "10",
            })
        if tool_name == "sap_search_bp":
            params: dict[str, str] = {
                "$filter": f"contains(CardName,'{tool_input['name']}')",
                "$select": "CardCode,CardName,FederalTaxID",
                "$top": "5",
            }
            return await sap_client.get("/BusinessPartners", **params)
    except Exception as exc:
        logger.warning("[doc_reader] SAP araç çağrısı başarısız: %s", exc)
    return []


async def _extract_via_text_with_tools(text: str, sap_client: Any) -> ExtractedDocument:
    """Araç destekli PDF çıkarma — Claude belirsiz alanlarda SAP'ı sorgulayabilir."""
    import functools

    handler = functools.partial(_sap_tool_handler, sap_client=sap_client)
    raw = await call_llm_with_tools(
        system=SYSTEM_PROMPT,
        user_message=f"PDF içeriği:\n\n{text}",
        tools=SAP_TOOLS,
        tool_handler=handler,
        max_tokens=4096,
    )
    return _parse_extracted(raw)
