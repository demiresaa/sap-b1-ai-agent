"""DocumentReader Excel ingest — mock LLM ile mapping davranışı."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from openpyxl import Workbook

from app.agents import document_reader as dr_mod
from app.agents.base import AgentContext
from app.agents.document_reader import DocumentReaderAgent


def _make_xlsx(tmp_path: Path, rows: list[list[object]], name: str = "siparis.xlsx") -> Path:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Sipariş"
    for row in rows:
        ws.append(row)
    path = tmp_path / name
    wb.save(path)
    return path


def _fake_llm_response(item_code: str = "H000106") -> dict:
    """Excel'den çıkarılması beklenen kanonik response."""
    return {
        "kind": "sales_order",
        "customer": {"name": "Test Müşteri A.Ş.", "tax_id": "1234567890"},
        "doc_date": "2026-05-17",
        "currency": "TRY",
        "lines": [
            {
                "line_no": 1,
                "description": "Test Ürün",
                "item_code_raw": item_code,
                "quantity": 5,
                "unit_price": 250.5,
                "discount_pct": 0,
            }
        ],
        "confidence": {"customer.name": 0.92, "lines": 0.88},
    }


@pytest.mark.asyncio
async def test_excel_uses_excel_parser_and_llm(tmp_path: Path) -> None:
    path = _make_xlsx(
        tmp_path,
        [
            ["Stok Kodu", "Açıklama", "Miktar", "Birim Fiyat"],
            ["H000106", "Test Ürün", 5, 250.5],
        ],
    )
    agent = DocumentReaderAgent()
    ctx = AgentContext(document_id="doc-1")

    async def fake_call(**kwargs):
        # Doğrula: prompt'ta gerçek excel verisi var
        assert "Stok Kodu" in kwargs["user_message"]
        assert "H000106" in kwargs["user_message"]
        return _fake_llm_response()

    with patch.object(dr_mod, "call_anthropic_json", side_effect=fake_call):
        result = await agent._run(ctx, file_path=str(path))

    assert result.success
    assert result.data["source"] == "excel"
    assert result.data["used_vision"] is False
    assert result.data["extracted"]["kind"] == "sales_order"
    assert len(result.data["extracted"]["lines"]) == 1


@pytest.mark.asyncio
async def test_excel_with_alternative_headers(tmp_path: Path) -> None:
    """Header'lar farklı isimle gelse de AI map etmeli (test mock — gerçek mapping LLM'de)."""
    path = _make_xlsx(
        tmp_path,
        [
            ["Ürün Kodu", "Tanım", "Adet", "Fiyat"],
            ["A1", "ürün", 2, 100],
            ["A2", "ürün2", 3, 200],
        ],
    )
    agent = DocumentReaderAgent()
    ctx = AgentContext(document_id="doc-2")

    async def fake_call(**kwargs):
        # Mapping LLM tarafında olur — biz iki satır döneceğini bekliyoruz
        return {
            "kind": "sales_order",
            "customer": {"name": "X"},
            "currency": "TRY",
            "lines": [
                {"line_no": 1, "description": "ürün", "item_code_raw": "A1", "quantity": 2, "unit_price": 100},
                {"line_no": 2, "description": "ürün2", "item_code_raw": "A2", "quantity": 3, "unit_price": 200},
            ],
            "confidence": {"lines": 0.9},
        }

    with patch.object(dr_mod, "call_anthropic_json", side_effect=fake_call):
        result = await agent._run(ctx, file_path=str(path))

    assert result.success
    assert len(result.data["extracted"]["lines"]) == 2


@pytest.mark.asyncio
async def test_raises_for_missing_file(tmp_path: Path) -> None:
    agent = DocumentReaderAgent()
    ctx = AgentContext(document_id="doc-3")
    with pytest.raises(FileNotFoundError):
        await agent._run(ctx, file_path=str(tmp_path / "yok.xlsx"))
