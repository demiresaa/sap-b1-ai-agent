"""Excel teklif/sipariş dosyasını PDF'e çevirir.

Kullanım:
    python scripts/excel_to_pdf.py <excel_dosyasi.xlsx> [--output cikti.pdf]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd
from weasyprint import HTML


def load_sheet(path: str) -> pd.DataFrame:
    xl = pd.ExcelFile(path)
    sheet = xl.sheet_names[0]
    return xl.parse(sheet, header=None)


def extract_project_info(df: pd.DataFrame) -> dict:
    info = {"is_adi": "", "is_bolumu": ""}
    for _, row in df.iterrows():
        for cell in row:
            if isinstance(cell, str) and "İŞİN ADI" in cell.upper():
                idx = row.tolist().index(cell)
                for j in range(idx + 1, len(row)):
                    if isinstance(row[j], str) and row[j].strip():
                        info["is_adi"] = row[j].strip()
                        break
            if isinstance(cell, str) and "İŞ BÖLÜMÜ" in cell.upper():
                idx = row.tolist().index(cell)
                for j in range(idx + 1, len(row)):
                    if isinstance(row[j], str) and row[j].strip():
                        info["is_bolumu"] = row[j].strip()
                        break
    return info


def extract_lines(df: pd.DataFrame) -> list[dict]:
    """Tablo satırlarını çıkarır. Header satırını arar ve altındaki veriyi alır."""
    header_row_idx = None
    col_map: dict[str, int] = {}

    for i, row in df.iterrows():
        row_vals = [str(v).strip().upper() if pd.notna(v) else "" for v in row]
        if "MİKTAR" in row_vals or "MIKTAR" in row_vals:
            header_row_idx = i
            for j, val in enumerate(row_vals):
                if "POZ" in val:
                    col_map["poz"] = j
                elif "TANIM" in val or "ADI" in val:
                    col_map["tanim"] = j
                elif "MARKA" in val or "MODEL" in val:
                    col_map["marka"] = j
                elif "BİRİM" in val and "FİYAT" not in val and "FIYAT" not in val:
                    col_map["birim"] = j
                elif "MİKTAR" in val or "MIKTAR" in val:
                    col_map["miktar"] = j
                elif "BİRİM FİYAT" in val or "BIRIM FIYAT" in val:
                    col_map["birim_fiyat"] = j
                elif "TOPLAM" in val and ("FİYAT" in val or "FIYAT" in val):
                    col_map["toplam"] = j
            break

    if header_row_idx is None:
        return []

    lines = []
    for i, row in df.iterrows():
        if i <= header_row_idx:
            continue

        poz = row.iloc[col_map.get("poz", 3)] if "poz" in col_map else ""
        tanim = row.iloc[col_map.get("tanim", 4)] if "tanim" in col_map else ""
        marka = row.iloc[col_map.get("marka", 5)] if "marka" in col_map else ""
        birim = row.iloc[col_map.get("birim", 6)] if "birim" in col_map else ""
        miktar = row.iloc[col_map.get("miktar", 7)] if "miktar" in col_map else ""
        birim_fiyat = row.iloc[col_map.get("birim_fiyat", 8)] if "birim_fiyat" in col_map else ""
        toplam = row.iloc[col_map.get("toplam", 9)] if "toplam" in col_map else ""

        def clean(v: object) -> str:
            if pd.isna(v) if isinstance(v, float) else False:
                return ""
            s = str(v).strip()
            return "" if s in ("nan", "NaN", "None") else s

        tanim_str = clean(tanim)
        if not tanim_str:
            continue
        if "Teklifimize dahil olmayıp" in tanim_str:
            continue
        if "KDV" in tanim_str.upper() and "TOPLAM" in tanim_str.upper():
            continue

        miktar_val = clean(miktar)
        birim_fiyat_val = clean(birim_fiyat)
        toplam_val = clean(toplam)

        try:
            if miktar_val:
                float(miktar_val)
        except ValueError:
            continue

        lines.append({
            "poz": clean(poz),
            "tanim": tanim_str,
            "marka": clean(marka),
            "birim": clean(birim),
            "miktar": miktar_val,
            "birim_fiyat": birim_fiyat_val,
            "toplam": toplam_val,
        })

    return lines


def format_number(val: str) -> str:
    try:
        f = float(val)
        if math.isnan(f):
            return ""
        return f"{f:,.2f}"
    except (ValueError, TypeError):
        return val


def render_html(info: dict, lines: list[dict]) -> str:
    rows_html = ""
    for line in lines:
        rows_html += f"""
        <tr>
            <td class="center">{line['poz']}</td>
            <td>{line['tanim']}</td>
            <td class="center">{line['marka']}</td>
            <td class="center">{line['birim']}</td>
            <td class="right">{format_number(line['miktar'])}</td>
            <td class="right">{format_number(line['birim_fiyat'])}</td>
            <td class="right">{format_number(line['toplam'])}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  @page {{ margin: 15mm 12mm; size: A4 landscape; }}
  body {{ font-family: Arial, sans-serif; font-size: 9pt; color: #222; }}
  h1 {{ font-size: 11pt; text-align: center; margin-bottom: 2mm; }}
  h2 {{ font-size: 9pt; text-align: center; color: #555; margin-top: 0; margin-bottom: 6mm; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    background: #1a3a5c; color: white; font-size: 8pt;
    padding: 4px 6px; border: 1px solid #ccc; text-align: center;
  }}
  td {{ padding: 3px 5px; border: 1px solid #ddd; font-size: 8pt; vertical-align: top; }}
  tr:nth-child(even) {{ background: #f5f8fc; }}
  .center {{ text-align: center; }}
  .right {{ text-align: right; }}
  .footer {{ margin-top: 8mm; font-size: 8pt; color: #555; text-align: right; }}
</style>
</head>
<body>
  <h1>{info['is_adi']}</h1>
  <h2>{info['is_bolumu']}</h2>
  <table>
    <thead>
      <tr>
        <th>POZ NO</th>
        <th>İŞİN TANIMI</th>
        <th>MARKA / MODEL</th>
        <th>BİRİM</th>
        <th>MİKTAR</th>
        <th>BİRİM FİYAT (€)</th>
        <th>TOPLAM FİYAT (€)</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <p class="footer">Para Birimi: EUR &nbsp;|&nbsp; KDV Hariç</p>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("excel", help="Excel dosyası yolu")
    parser.add_argument("--output", "-o", default=None, help="Çıktı PDF yolu")
    args = parser.parse_args()

    excel_path = args.excel
    output_path = args.output or str(Path(excel_path).with_suffix(".pdf"))

    print(f"Okunuyor: {excel_path}")
    df = load_sheet(excel_path)

    info = extract_project_info(df)
    print(f"Proje: {info['is_adi']}")
    print(f"Bölüm: {info['is_bolumu']}")

    lines = extract_lines(df)
    print(f"Satır sayısı: {len(lines)}")

    if not lines:
        print("HATA: Hiç satır bulunamadı.", file=sys.stderr)
        sys.exit(1)

    html = render_html(info, lines)
    HTML(string=html).write_pdf(output_path)
    print(f"PDF oluşturuldu: {output_path}")


if __name__ == "__main__":
    main()
