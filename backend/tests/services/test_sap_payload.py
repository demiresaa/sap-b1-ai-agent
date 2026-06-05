"""ExtractedData → SAP payload builder."""
from __future__ import annotations

from app.db.models import DocumentKind
from app.workers.tasks import _build_sap_payload, _endpoint_for, _kind_from, _kind_to_writer


def test_build_payload_maps_lines_and_customer() -> None:
    extracted = {
        "customer": {"card_code": "C001"},
        "doc_date": "2026-05-14",
        "due_date": "2026-06-14",
        "currency": "TRY",
        "reference_no": "PO-99",
        "notes": "Test",
        "lines": [
            {"item_code": "A001", "quantity": 2, "unit_price": 100.5, "discount_pct": 5, "tax_code": "OG18"},
            {"item_code": "A002", "quantity": 1, "unit_price": 50},
        ],
    }
    payload = _build_sap_payload(extracted, DocumentKind.SALES_ORDER)

    assert payload["CardCode"] == "C001"
    assert payload["DocCurrency"] == "TRY"
    assert payload["NumAtCard"] == "PO-99"
    assert len(payload["DocumentLines"]) == 2
    first = payload["DocumentLines"][0]
    assert first["ItemCode"] == "A001"
    assert first["Quantity"] == 2
    assert first["UnitPrice"] == 100.5
    assert first["DiscountPercent"] == 5


def test_kind_helpers() -> None:
    assert _kind_from("sales_order") == DocumentKind.SALES_ORDER
    assert _kind_from("quotation") == DocumentKind.QUOTATION
    assert _kind_from(None) == DocumentKind.UNKNOWN
    assert _endpoint_for(DocumentKind.SALES_ORDER) == "/Orders"
    assert _endpoint_for(DocumentKind.QUOTATION) == "/Quotations"
    assert _kind_to_writer(DocumentKind.QUOTATION) == "quotation"
