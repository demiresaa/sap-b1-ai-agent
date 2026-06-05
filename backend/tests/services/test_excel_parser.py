"""Excel parser — header tespiti, normalize, prompt text."""
from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.excel_parser import ExcelSheet, parse_excel


def _make_xlsx(tmp_path: Path, rows: list[list[object]]) -> Path:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Sipariş"
    for row in rows:
        ws.append(row)
    path = tmp_path / "siparis.xlsx"
    wb.save(path)
    return path


def test_parses_simple_header_and_rows(tmp_path: Path) -> None:
    path = _make_xlsx(
        tmp_path,
        [
            ["Stok Kodu", "Açıklama", "Miktar", "Birim Fiyat"],
            ["H000106", "Test Ürün", 5, 250.5],
            ["H000107", "Test 2", 1, 100.0],
        ],
    )
    sheet = parse_excel(path)
    assert isinstance(sheet, ExcelSheet)
    assert sheet.name == "Sipariş"
    assert sheet.headers == ["Stok Kodu", "Açıklama", "Miktar", "Birim Fiyat"]
    assert len(sheet.rows) == 2
    assert sheet.rows[0]["Stok Kodu"] == "H000106"
    assert sheet.rows[0]["Miktar"] == 5
    assert sheet.rows[1]["Birim Fiyat"] == 100.0


def test_handles_empty_leading_rows(tmp_path: Path) -> None:
    path = _make_xlsx(
        tmp_path,
        [
            [None, None, None],
            ["", "", ""],
            ["Ürün Kodu", "Adı", "Adet"],
            ["X1", "A", 3],
        ],
    )
    sheet = parse_excel(path)
    assert sheet.headers == ["Ürün Kodu", "Adı", "Adet"]
    assert sheet.rows == [{"Ürün Kodu": "X1", "Adı": "A", "Adet": 3}]


def test_dedup_header_names(tmp_path: Path) -> None:
    path = _make_xlsx(
        tmp_path,
        [
            ["Kod", "Açıklama", "Kod"],
            ["A", "first", "B"],
        ],
    )
    sheet = parse_excel(path)
    assert "Kod" in sheet.headers and "Kod__2" in sheet.headers


def test_prompt_text_format(tmp_path: Path) -> None:
    path = _make_xlsx(
        tmp_path,
        [
            ["Kod", "Adet"],
            ["A1", 2],
            ["A2", 3],
        ],
    )
    sheet = parse_excel(path)
    text = sheet.to_prompt_text()
    assert "Sheet: " in text
    assert "Kod\tAdet" in text
    assert "A1\t2" in text


def test_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_excel(tmp_path / "yok.xlsx")
