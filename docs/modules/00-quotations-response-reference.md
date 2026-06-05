# Quotations — POST Sonrası SAP Çıktısı Referansı

> Kaynak: `elek - Sayfa1.csv` (müşteri DB'sinden alınmış OQUT + QUT1 JOIN raporu, DocEntry 7357, 1 başlık + 17 satır, 2026-05-20).
>
> Bu dosya **POST cevabı + DB'de oluşması gereken kanonik kayıt**ın referansıdır. Service Layer JSON formatı CSV'den farklı olur, ama **alanlar ve değerler** aynıdır.

---

## 1. CSV ≠ Service Layer Response

| Konu | CSV (DB export) | Service Layer (POST cevabı) |
|---|---|---|
| Format | Satır-bazlı, OQUT+QUT1 JOIN, 840 sütun | JSON, hiyerarşik (`DocumentLines` array içinde) |
| Sayısal lokalizasyon | Türk Excel binlik/ondalık karışık (`1.000.000` = 1, `61.600.000` = 61.60) | Düz desimal (`1`, `61.60`) |
| Eksik alanlar | NULL string | `null` |
| Boolean | `Y` / `N` | `"tYES"` / `"tNO"` |
| Satır numarası | `LineNum` (silinmişler atlanabilir, atlanan 5 örneği var) | Aynı |

**AI'a CSV vermek = riskli.** `1.000.000` görür, 1 milyon adet zanneder. Eğer müşteri Excel/CSV ile teklif yollarsa, parser **Türkçe lokalizasyon-aware** olmalı (`pandas.read_csv(decimal=',', thousands='.')` veya `babel.numbers.parse_decimal('1.000.000', locale='tr_TR')`).

---

## 2. POST Sonrası Bizde Olması Gereken Alanlar

### 2.1 Bizim Gönderdiğimiz (echo back gelir)

Bunlar payload'da neyi yolladıysak aynısı geri gelir. Validate ederken karşılaştır.

| Alan | Örnek |
|---|---|
| `CardCode` | `"120.01.1158"` |
| `NumAtCard` | `"tesisi"` |
| `DocDate` | `"2026-01-23"` |
| `DocDueDate` | `"2026-02-23"` |
| `DocCurrency` | `"EUR"` |
| `SalesPersonCode` | `10` |
| `DocumentsOwner` | `19` |
| `Project` | `"2776"` |
| `U_Branch` | `"Elek233"` |
| `U_Teklif_Turu` | `"Hedef_Teklif"` |
| `U_Teklif_Durumu` | `"Gönderildi"` |
| `U_Takip_Asamasi` | `"Sıcak"` |
| `U_Takip_Calisani` | `11` |
| `U_SatinAlmaci` | `1` |
| `U_Proje_Adi` | `"THY"` |
| `U_Tahimini_Gercek_Tarih` | `"2026-02-19"` |
| `U_coklu_teklif` | `"Mükerrer"` |

### 2.2 SAP Üretti (response'tan oku, DB'ye yaz)

| Alan | Örnek | Notu |
|---|---|---|
| `DocEntry` | `7357` | İç anahtar — `external_id` olarak bizde tutulur |
| `DocNum` | `7357` | Kullanıcıya gösterilen teklif no |
| `DocStatus` | `"O"` → `"C"` (Open → Closed) | Polling/sync ile mirror'la |
| `DocTotal` | `129.457.68` (CSV bozuk; gerçek `129.46`) | KDV dahil toplam |
| `VatSum` | `21.58` | KDV toplamı |
| `DocRate` | `50.6345` | TRY ↔ EUR kuru (POST anındaki) |
| `Series` | `14` | Numaralandırma serisi |
| `CreateDate` / `UpdateDate` | `"2026-01-23"` / `"2026-05-18"` | SAP zaman damgaları |
| `UserSign` / `UserSign2` | `22` | SAP içi user id |
| `Address` | `" Merkez Siirt / TURKEY"` | Cariden kopyalanır |
| `FinncPriod` | `121` | Mali dönem |
| `ConfrmedBy` / `ConfrmedOn` | `22` / `"2026-01-23"` | Onay bilgisi |

### 2.3 Satır Bazında SAP Üretti

| Alan | Örnek | Notu |
|---|---|---|
| `LineNum` | `0, 1, 2, 3, 4, 6, 7...` | Silinmişler atlanır. Sıralama için `VisOrder` kullan |
| `LineTotal` | `31.19` (CSV'de `3.119.090.000` → gerçek `31.19`) | Qty × Price × (1 - Disc%) |
| `VatSum` (satır) | `6.24` | Satır KDV |
| `OpenQty` | `1.00` | Başlangıçta `Quantity`'e eşit |
| `Currency` / `Rate` | `EUR` / `50.6345` | Header'dan miras |
| `GrossBuyPr` | `13.31` | Maliyet (SAP item master) |
| `GrssProfit` / `GrssProfFC` | `1.79` | Brüt kâr — SAP hesaplar |
| `LineStatus` | `"O"` | Açık/Kapalı |

---

## 3. UDF Valid-Value Yakalamaları (Önemli!)

Bu CSV'den çıkardığımız gerçek değerler — Excel'de sadece birer örnek vardı. **Tam set müşteriden istenmeli**, AI enum olarak doğrulamalı.

| Alan | Görülen Değer | Başka Olası (Excel'den) |
|---|---|---|
| `U_Teklif_Turu` | `Hedef_Teklif` | `Key_Account` |
| `U_Teklif_Durumu` | `Gönderildi` | ? |
| `U_Takip_Asamasi` | `Sıcak` | (muhtemelen Soğuk, Orta...) |
| `U_coklu_teklif` | `Mükerrer` | ? |
| `U_Branch` | `Elek233`, `Elekon` | (multi-branch — şube listesi var) |
| `U_LB_TemMektubu` | (boş) | "Var" / "Yok" Excel'de |

**TODO (müşteri sorulacak):**
- Her UDF için tam valid value listesi (sayı + label).
- `OSLP` (SalesPerson) listesi.
- `OHEM` (Employee) listesi → DocumentsOwner, U_Takip_Calisani, U_SatinAlmaci için.
- `OPRJ` (Project) listesi.
- Şube (`U_Branch`) listesi.

---

## 4. Bizim DB Şemamızda Quotation Tablosu

`quotations` (örnek; gerçek alanlar `app/db/models/quotation.py`):

```python
class Quotation(Base):
    id: UUID                          # PK
    tenant_id: UUID
    sap_doc_entry: int | None         # SAP DocEntry — POST sonrası
    sap_doc_num: int | None           # SAP DocNum — gösterim
    sap_doc_status: str | None        # 'O' | 'C'
    sap_doc_total: Decimal | None
    sap_vat_sum: Decimal | None
    sap_doc_rate: Decimal | None
    sap_create_date: datetime | None
    sap_update_date: datetime | None

    # Input snapshot (bizim payload'umuz)
    card_code: str
    card_name_snapshot: str           # response'tan, audit
    num_at_card: str
    doc_currency: str
    doc_date: date
    doc_due_date: date | None
    sales_person_code: int
    documents_owner: int
    project_code: str
    payment_group_code: int | None
    discount_percent: Decimal | None
    comments: str | None

    # UDF (müşteri-özel)
    u_branch: str
    u_teklif_turu: str | None
    u_teklif_durumu: str | None
    u_takip_asamasi: str | None
    u_takip_calisani: int | None
    u_satin_almaci: int | None
    u_lb_tem_mektubu: str | None
    u_lb_tem_mektubu_tutar: Decimal | None
    u_lb_tem_mektubu_oran: Decimal | None
    u_proje_adi: str | None
    u_coklu_teklif: str | None
    u_tahimini_gercek_tarih: date     # ZORUNLU, typo'lu

    # Lifecycle
    status: QuotationStatus           # bizim FSM'imiz
    created_at: datetime
    updated_at: datetime
    payload_json: JSONB               # gönderdiğimiz tam payload (audit)
    response_json: JSONB              # SAP'ın döndüğü tam JSON (audit)
```

`quotation_lines`:

```python
class QuotationLine(Base):
    id: UUID
    quotation_id: UUID (FK)
    sap_line_num: int | None          # SAP LineNum (atlanan olabilir)
    vis_order: int                    # sıralama
    item_code: str
    item_description_snapshot: str    # SAP'tan, audit
    quantity: Decimal
    unit_price: Decimal
    currency: str                     # header'dan
    discount_percent: Decimal | None
    tax_code: str | None
    project_code: str                 # header'la aynı
    warehouse_code: str | None
    # SAP üretti
    sap_line_total: Decimal | None
    sap_vat_sum: Decimal | None
    sap_open_qty: Decimal | None
    sap_line_status: str | None       # 'O' | 'C'
```

---

## 5. Lifecycle / Status Akışı

```
DRAFT          → AI çıkardı, kullanıcı henüz onaylamadı
PENDING_APPROVAL → Eşik aşımı / düşük confidence — HITL bekliyor
APPROVED       → Kullanıcı onayladı, SAP'a yazıma hazır
SENT_TO_SAP    → POST yapıldı, DocEntry alındı
                  ↳ sap_doc_status = 'O'
SAP_CLOSED     → Sync ile DocStatus 'C' geldi
CUSTOMER_SENT  → Bizim ürettiğimiz PDF müşteriye gönderildi (faz 2)
ACCEPTED       → Müşteri onayladı → Order'a dönüştürüldü
REJECTED       → Müşteri reddetti / iptal
```

**Önemli:** SAP DocStatus mirror'lama için periyodik `GET /Quotations(DocEntry)` çağrısı (Celery task, 15dk).

---

## 6. Attachment (`AtcEntry`)

CSV'de `AtcEntry=15655` — bu teklife dosya eklenmiş. Bizim akışta:
1. Quotation SAP'a POST edildi → `DocEntry` alındı.
2. Biz teklif PDF'i üretiyoruz (kendi şablonumuzla).
3. `/Attachments2` endpoint'ine PDF yükle.
4. `PATCH /Quotations(DocEntry)` ile `AttachmentEntry` alanını set et.

→ **Faz 2** kapsamı, MVP'de stub.

---

## 7. Validate Adımları (POST Sonrası)

Response döndüğünde:

1. **`DocEntry` ve `DocNum` doluysa** → başarı, DB'ye yaz.
2. **`DocTotal` ≈ bizim hesapladığımız toplam** olmalı (±%0.1 kur farkı toleransı).
3. **Satır sayısı eşit** olmalı (`len(response.DocumentLines) == len(payload.DocumentLines)`).
4. **Her satırın `LineTotal`** ≈ `Quantity × UnitPrice × (1 - DiscountPercent/100)`.
5. **Toplamlardan biri tutmuyorsa** → kullanıcıyı uyar, ama POST geri alınamaz (idempotency key'i kaydet, manuel müdahale).
