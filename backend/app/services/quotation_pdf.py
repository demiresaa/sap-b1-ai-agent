"""Teklif PDF üretimi — Jinja2 + WeasyPrint.

ExtractedData payload + tenant default'ları → HTML render → WeasyPrint PDF bytes.
Çağıran (route) bytes'ı S3'e yazıp `quotation_pdfs` tablosuna versiyonlu kayıt ekler.
"""
from __future__ import annotations

import logging
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

TEMPLATE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "templates" / "quotation"


@dataclass(slots=True)
class TenantInfo:
    name: str
    slug: str


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _compute_totals(quote: dict[str, Any]) -> dict[str, float]:
    grand = 0.0
    for line in quote.get("lines") or []:
        qty = float(line.get("quantity") or 0)
        price = float(line.get("unit_price") or 0)
        disc = float(line.get("discount_pct") or 0)
        explicit_total = line.get("total")
        if explicit_total is not None:
            grand += float(explicit_total)
        else:
            grand += qty * price * (1 - disc / 100.0)
    return {"grand_total": round(grand, 2)}


def render_quotation_pdf(
    extracted: dict[str, Any],
    tenant: TenantInfo,
    template_name: str = "default",
) -> bytes:
    """Extracted data + tenant'tan PDF bytes üret.

    `template_name`: TEMPLATE_ROOT/<template_name>.html dosyasını arar.
    """
    env = _env()
    tpl = env.get_template(f"{template_name}.html")

    # Ensure customer dict exists
    quote = dict(extracted)
    quote.setdefault("customer", {})

    html_str = tpl.render(
        tenant=tenant,
        quote=quote,
        totals=_compute_totals(quote),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    )

    # Lazy import — WeasyPrint native libleri (libpango/libcairo) gerektirir; bunlar
    # Docker imajında var, local macOS'ta yoksa modül import'u patlamasın.
    from weasyprint import CSS, HTML  # noqa: PLC0415

    css_path = TEMPLATE_ROOT / f"{template_name}.css"
    stylesheets = [CSS(filename=str(css_path))] if css_path.exists() else []
    pdf_bytes = HTML(string=html_str, base_url=str(TEMPLATE_ROOT)).write_pdf(
        stylesheets=stylesheets
    )
    logger.info(
        "[quotation_pdf] tenant=%s template=%s lines=%d size=%d bytes",
        tenant.slug,
        template_name,
        len(quote.get("lines") or []),
        len(pdf_bytes),
    )
    return pdf_bytes
