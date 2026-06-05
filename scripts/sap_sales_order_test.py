"""
SAP Service Layer — Sales Order test scripti.

Kullanim:
    python scripts/sap_sales_order_test.py
    python scripts/sap_sales_order_test.py --card-code C20000   # CardCode override

Gereklilik: pip install requests
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib3

import requests

# ---------------------------------------------------------------------------
# Konfigürasyon
# ---------------------------------------------------------------------------

SAP_URL      = "https://10.11.10.46:50000/b1s/v1"
COMPANY_DB   = "2026_Test"
USERNAME     = "manager"
PASSWORD     = "NyNl.2021"
VERIFY_SSL   = False   # self-signed sertifika

# SSL uyarılarını sustur
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Kaynak JSON (extracted payload)
# ---------------------------------------------------------------------------

EXTRACTED: dict = {
    "kind": "sales_order",
    "lines": [
        {"unit": "Koli",  "total": 87000,  "barcode": None, "line_no": 1,  "quantity": 60,  "tax_code": "20", "unit_price": 1450,  "description": "Fotokopi Kağıdı — A4 80 gr (5 top × 500 sayfa)",       "discount_pct": 0, "item_code_raw": "KGT-A4-80"},
        {"unit": "Koli",  "total": 32250,  "barcode": None, "line_no": 2,  "quantity": 15,  "tax_code": "20", "unit_price": 2150,  "description": "Fotokopi Kağıdı — A3 80 gr (3 top × 500 sayfa)",       "discount_pct": 0, "item_code_raw": "KGT-A3-80"},
        {"unit": "Adet",  "total": 26000,  "barcode": None, "line_no": 3,  "quantity": 400, "tax_code": "20", "unit_price": 65,    "description": "Plastik Klasör — A4 geniş, mekanizmalı",               "discount_pct": 0, "item_code_raw": "KLM-PLT-A4"},
        {"unit": "Paket", "total": 11600,  "barcode": None, "line_no": 4,  "quantity": 80,  "tax_code": "20", "unit_price": 145,   "description": "Telli Dosya — A4 plastik şeffaf (10'lu paket)",         "discount_pct": 0, "item_code_raw": "DSY-TLN-A4"},
        {"unit": "Paket", "total": 9500,   "barcode": None, "line_no": 5,  "quantity": 100, "tax_code": "20", "unit_price": 95,    "description": "Poşet Dosya — A4 100'lü (40 mikron)",                   "discount_pct": 0, "item_code_raw": "DSY-POS-100"},
        {"unit": "Kutu",  "total": 11400,  "barcode": None, "line_no": 6,  "quantity": 40,  "tax_code": "20", "unit_price": 285,   "description": "Tükenmez Kalem — Mavi 1.0 mm (50'li kutu)",             "discount_pct": 0, "item_code_raw": "TKB-MV-1"},
        {"unit": "Kutu",  "total": 8550,   "barcode": None, "line_no": 7,  "quantity": 30,  "tax_code": "20", "unit_price": 285,   "description": "Tükenmez Kalem — Siyah 1.0 mm (50'li kutu)",            "discount_pct": 0, "item_code_raw": "TKB-SY-1"},
        {"unit": "Paket", "total": 9500,   "barcode": None, "line_no": 8,  "quantity": 100, "tax_code": "20", "unit_price": 95,    "description": "Kurşun Kalem — 2B siyah tahta (12'li paket)",           "discount_pct": 0, "item_code_raw": "KRS-2B"},
        {"unit": "Set",   "total": 9750,   "barcode": None, "line_no": 9,  "quantity": 150, "tax_code": "20", "unit_price": 65,    "description": "Fosforlu Kalem — 4'lü set (sarı/yeşil/pembe/turuncu)", "discount_pct": 0, "item_code_raw": "FOS-FLR4"},
        {"unit": "Paket", "total": 14800,  "barcode": None, "line_no": 10, "quantity": 80,  "tax_code": "20", "unit_price": 185,   "description": "Yapışkan Not — 76×76 mm sarı (12'li)",                  "discount_pct": 0, "item_code_raw": "PST-7676"},
        {"unit": "Kutu",  "total": 5700,   "barcode": None, "line_no": 11, "quantity": 200, "tax_code": "20", "unit_price": 28.5,  "description": "Zımba Teli — No.10 (5000'lik kutu)",                    "discount_pct": 0, "item_code_raw": "ZMP-NO10"},
        {"unit": "Kutu",  "total": 2250,   "barcode": None, "line_no": 12, "quantity": 100, "tax_code": "20", "unit_price": 22.5,  "description": "Ataç — 33 mm renkli (100'lü kutu)",                     "discount_pct": 0, "item_code_raw": "ATC-PAP100"},
        {"unit": "Paket", "total": 5100,   "barcode": None, "line_no": 13, "quantity": 60,  "tax_code": "20", "unit_price": 85,    "description": "Şeffaf Bant — 24 mm × 33 m (6'lı)",                    "discount_pct": 0, "item_code_raw": "BNT-SKT24"},
        {"unit": "Adet",  "total": 3080,   "barcode": None, "line_no": 14, "quantity": 80,  "tax_code": "20", "unit_price": 38.5,  "description": "İnce Kesici Maket Bıçağı — 9 mm yedekli",              "discount_pct": 0, "item_code_raw": "KSI-INK-OFC"},
        {"unit": "Adet",  "total": 106250, "barcode": None, "line_no": 15, "quantity": 25,  "tax_code": "20", "unit_price": 4250,  "description": "Toner — HP CF258A LaserJet uyumlu",                    "discount_pct": 0, "item_code_raw": "TNR-HP58A"},
        {"unit": "Adet",  "total": 37000,  "barcode": None, "line_no": 16, "quantity": 20,  "tax_code": "20", "unit_price": 1850,  "description": "Toner — Brother TN-2380 uyumlu",                       "discount_pct": 0, "item_code_raw": "TNR-BR350"},
        {"unit": "Paket", "total": 7250,   "barcode": None, "line_no": 17, "quantity": 50,  "tax_code": "20", "unit_price": 145,   "description": "Zarf — Diplomat C5 (162×229 mm, 100'lü)",              "discount_pct": 0, "item_code_raw": "ZRF-DL11"},
        {"unit": "Adet",  "total": 27400,  "barcode": None, "line_no": 18, "quantity": 40,  "tax_code": "20", "unit_price": 685,   "description": "Ajanda — 2026 cilt bezli A5 günlük",                   "discount_pct": 0, "item_code_raw": "AJN-2026"},
        {"unit": "Adet",  "total": 12125,  "barcode": None, "line_no": 19, "quantity": 25,  "tax_code": "20", "unit_price": 485,   "description": "Hesap Makinesi — Masa üstü 12 hane güneş enerjili",    "discount_pct": 0, "item_code_raw": "TKR-2X"},
        {"unit": "Paket", "total": 20550,  "barcode": None, "line_no": 20, "quantity": 30,  "tax_code": "20", "unit_price": 685,   "description": "Kargo Kolisi — 40×30×25 cm karton (50'li)",             "discount_pct": 0, "item_code_raw": "AMB-KK4060"},
    ],
    "notes": "Teslimat: DDP şartlarında 22.05.2026 tarihine kadar. Ödeme: 30 gün vadeli banka havalesi. Geç teslimat cezası: günlük %0,3. Muayene süresi: 10 iş günü. Garanti: 24 ay.",
    "currency": "TRY",
    "customer": {
        "name": "BAŞARI EĞİTİM KURUMLARI A.Ş.",
        "email": "idari@basariegitim.k12.tr",
        "phone": "+90 (216) 360 22 00",
        "tax_id": "1523456789",
        "address": "Caddebostan Mah. Bağdat Cad. No: 247, Kadıköy / İSTANBUL 34728",
    },
    "doc_date": "2026-05-17",
    "due_date": "2026-05-22",
    "reference_no": "SP-2026-KR-7752",
}


# ---------------------------------------------------------------------------
# SAP payload dönüşümü
# ---------------------------------------------------------------------------

def build_sales_order_payload(data: dict, card_code: str) -> dict:
    lines = []
    for line in data["lines"]:
        sap_line: dict = {
            "ItemCode":        line["item_code_raw"],
            "Quantity":        line["quantity"],
            "UnitPrice":       line["unit_price"],
            "DiscountPercent": line.get("discount_pct") or 0,
        }
        if line.get("tax_code"):
            sap_line["TaxCode"] = line["tax_code"]
        lines.append(sap_line)

    return {
        "CardCode":      card_code,
        "DocDate":       data.get("doc_date"),
        "DocDueDate":    data.get("due_date"),
        "DocCurrency":   data.get("currency"),
        "NumAtCard":     data.get("reference_no"),
        "Comments":      data.get("notes"),
        "DocumentLines": lines,
    }


# ---------------------------------------------------------------------------
# SAP Service Layer istemcisi
# ---------------------------------------------------------------------------

class SAPClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.verify = VERIFY_SSL
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept":       "application/json",
        })
        self._logged_in = False

    def login(self) -> None:
        print(f"\n[1] Login → {SAP_URL}/Login")
        resp = self.session.post(
            f"{SAP_URL}/Login",
            json={
                "CompanyDB": COMPANY_DB,
                "UserName":  USERNAME,
                "Password":  PASSWORD,
            },
        )
        _check(resp, "Login")
        self._logged_in = True
        print(f"    ✓ Giriş başarılı (HTTP {resp.status_code})")

    def logout(self) -> None:
        if not self._logged_in:
            return
        try:
            self.session.post(f"{SAP_URL}/Logout")
            print("\n[4] Logout ✓")
        except Exception:
            pass

    def create_sales_order(self, payload: dict) -> dict:
        print(f"\n[3] POST /Orders")
        print(f"    CardCode     : {payload['CardCode']}")
        print(f"    DocDate      : {payload['DocDate']}")
        print(f"    DocDueDate   : {payload['DocDueDate']}")
        print(f"    NumAtCard    : {payload['NumAtCard']}")
        print(f"    Satır sayısı : {len(payload['DocumentLines'])}")

        resp = self.session.post(f"{SAP_URL}/Orders", json=payload)
        _check(resp, "Orders POST")
        data = resp.json()
        return data

    def get_item(self, item_code: str) -> dict | None:
        """ItemCode SAP'ta var mı kontrol eder."""
        resp = self.session.get(
            f"{SAP_URL}/Items('{item_code}')",
            params={"$select": "ItemCode,ItemName,OnHand"},
        )
        if resp.status_code == 404:
            return None
        _check(resp, f"Items('{item_code}')")
        return resp.json()


# ---------------------------------------------------------------------------
# Yardımcı
# ---------------------------------------------------------------------------

def _check(resp: requests.Response, label: str) -> None:
    if not resp.ok:
        try:
            err = resp.json()
            msg = err.get("error", {}).get("message", {})
            detail = msg.get("value") if isinstance(msg, dict) else msg
        except Exception:
            detail = resp.text[:300]
        print(f"\n✗ {label} başarısız — HTTP {resp.status_code}")
        print(f"  Hata: {detail}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="SAP Sales Order test scripti")
    parser.add_argument(
        "--card-code",
        default=None,
        help="SAP müşteri kodu (CardCode). Belirtilmezse item doğrulama yapılır, CardCode sorulur.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="SAP'a POST atmadan payload'ı ekrana yazdır.",
    )
    args = parser.parse_args()

    client = SAPClient()

    try:
        # 1. Login
        client.login()

        # 2. CardCode belirle
        card_code = args.card_code
        if not card_code:
            print("\n[2] CardCode girilmedi.")
            card_code = input("    SAP CardCode (örn. C20000): ").strip()
            if not card_code:
                print("    CardCode boş olamaz.")
                sys.exit(1)

        # 2b. Satırlardaki item kodlarını doğrula (opsiyonel)
        print(f"\n[2] Item kodu doğrulama ({len(EXTRACTED['lines'])} satır)...")
        missing = []
        for line in EXTRACTED["lines"]:
            item = client.get_item(line["item_code_raw"])
            status = "✓" if item else "✗ BULUNAMADI"
            stock  = f"  (stok: {item['OnHand']})" if item else ""
            print(f"    {status}  {line['item_code_raw']:20s} — {line['description'][:50]}{stock}")
            if not item:
                missing.append(line["item_code_raw"])

        if missing:
            print(f"\n  ⚠  {len(missing)} item SAP'ta bulunamadı: {missing}")
            cont = input("  Yine de devam et? (e/H): ").strip().lower()
            if cont != "e":
                print("  İptal edildi.")
                sys.exit(0)

        # 3. Payload oluştur
        payload = build_sales_order_payload(EXTRACTED, card_code)

        if args.dry_run:
            print("\n[DRY-RUN] SAP'a gönderilecek payload:")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            print("\nDry-run modunda POST yapılmadı.")
            return

        # 4. Sipariş oluştur
        result = client.create_sales_order(payload)

        doc_entry = result.get("DocEntry")
        doc_num   = result.get("DocNum")
        total     = result.get("DocTotal")

        print(f"\n✓ Sipariş oluşturuldu!")
        print(f"  DocEntry : {doc_entry}")
        print(f"  DocNum   : {doc_num}")
        print(f"  DocTotal : {total} {result.get('DocCurrency', '')}")
        print(f"  NumAtCard: {result.get('NumAtCard')}")

        # Tam yanıtı dosyaya yaz
        out_file = f"sap_order_{doc_entry}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  Tam yanıt → {out_file}")

    finally:
        client.logout()


if __name__ == "__main__":
    main()
