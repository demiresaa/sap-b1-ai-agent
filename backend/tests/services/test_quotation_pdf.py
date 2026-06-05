"""Quotation PDF — HTML render + totals (PDF binary'si WeasyPrint native lib gerektirdiği
için CI/Docker'da test edilir; burada Jinja render katmanını test ederiz)."""
from __future__ import annotations

from app.services.quotation_pdf import TEMPLATE_ROOT, TenantInfo, _compute_totals, _env


def test_totals_from_explicit_total() -> None:
    quote = {
        "lines": [
            {"quantity": 5, "unit_price": 100, "discount_pct": 10, "total": 450.0},
            {"quantity": 2, "unit_price": 200, "discount_pct": 0, "total": 400.0},
        ]
    }
    assert _compute_totals(quote)["grand_total"] == 850.0


def test_totals_computed_when_total_missing() -> None:
    quote = {
        "lines": [
            {"quantity": 5, "unit_price": 100, "discount_pct": 10},
        ]
    }
    # 5 * 100 * 0.9 = 450
    assert _compute_totals(quote)["grand_total"] == 450.0


def test_totals_empty_lines() -> None:
    assert _compute_totals({})["grand_total"] == 0.0


def test_template_renders_html() -> None:
    env = _env()
    tpl = env.get_template("default.html")
    quote = {
        "kind": "quotation",
        "customer": {"name": "Test Müşteri", "tax_id": "1234567890"},
        "doc_date": "2026-05-17",
        "currency": "TRY",
        "lines": [
            {"line_no": 1, "item_code_raw": "X1", "description": "T", "quantity": 5, "unit_price": 100}
        ],
    }
    html = tpl.render(
        tenant=TenantInfo(name="Elekon", slug="elekon"),
        quote=quote,
        totals=_compute_totals(quote),
        generated_at="2026-05-17 12:00",
    )
    assert "Elekon" in html
    assert "Test Müşteri" in html
    assert "X1" in html
    assert "TRY" in html


def test_template_root_exists() -> None:
    assert (TEMPLATE_ROOT / "default.html").exists()
    assert (TEMPLATE_ROOT / "default.css").exists()
