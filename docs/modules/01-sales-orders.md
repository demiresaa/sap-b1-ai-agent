# Modül: Sales Orders (Satış Siparişi) — **MVP ANA MODÜL**

> Elekon'a özel alan eşlemesi. Kaynak: `docs/sap-info/elekon_sap_dump_2026-05-21`.
> OQUT/ORDR UDF yapısı **birebir aynı**; bu belge Quotation'ı da kapsar.

**Durum:** MVP aktif geliştirme
**SAP Endpoint:** `/b1s/v1/Orders`
**Backend:** `backend/app/sap/modules/sales_orders.py`
**Faz:** 1 (MVP)

---

## Elekon Ortam Sabitleri

| Parametre | Değer |
|---|---|
| `Series` (Orders) | `8` |
| `Series` (Quotations) | `14` |
| `DocCurrency` default | `"EUR"` (DocRate=1.0) |
| `DefaultWarehouse` | `"01"` (Ana Depo) |
| `U_Branch` | `"Elekon"` (sabit) |
| `U_Teklif_Turu` default | `"Standart_Teklif"` (✋ `"---------------"` geçersiz!) |
| `U_SatinAlmaci` (satır) | `"1"` (Gizem Bedir — mandatory) |
| VatGroup default | `"S01"` (%20 KDV) |
| LocalCurrency | TRY |
| SystemCurrency | EUR |

> ⚠️ **`EnableApprovalProcedureInDI: tYES`** — SAP DI API POST'ları onay prosedürünü tetikleyebilir.
> `SAPWriter` bu durumu `Document_ApprovalRequests` response alanını okuyarak algılar.

---

## POST Değerleri — Legend

| Sembol | Anlam |
|---|---|
| ✔ Evet | Payload'a gönderilecek — zorunlu |
| ✘ Hayır | SAP hesaplar / oluşturur — gönderilmez |
| ◎ Opsiyonel | Değer varsa gönderilir |
| ⚑ Şartlı | Belirli kurala göre zorunlu |

---

## Kritik İş Kuralları

1. `Series: 8` her Sales Order POST'una gönderilir.
2. `DocCurrency: "EUR"` default — Elekon EUR bazlı çalışıyor.
3. `U_Teklif_Turu` mandatory; `"---------------"` değeri geçersiz, her zaman gerçek bir değer seç.
4. `U_SatinAlmaci` satır UDF'i mandatory — default `"1"`.
5. `U_Branch: "Elekon"` her belgede sabit.
6. `DocumentsOwner` ≠ `SalesPersonCode` — `DocumentsOwner` SAP `OHEM.empID`.
7. `Key_Account` → `U_Proje_Adi` ZORUNLU.
8. `Project` (header) ile `DocumentLines[].ProjectCode` genellikle aynı değer.
9. SAP onay prosedürü aktif; POST başarılı olsa bile `Document_ApprovalRequests` dolu gelebilir.

---

## 1. Header Alanları

| Alan | Service Layer | POST? | Not |
|---|---|---|---|
| Seri Numarası | `Series` | ✔ Evet | `8` sabit |
| Müşteri | `CardCode` | ✔ Evet | ZORUNLU |
| Müşteri Adı | `CardName` | ✘ Hayır | SAP getirir |
| Para Birimi | `DocCurrency` | ✔ Evet | default `"EUR"` |
| Satış Çalışanı | `SalesPersonCode` | ✔ Evet | ZORUNLU (OSLP.SlpCode) |
| Belge Sahibi | `DocumentsOwner` | ✔ Evet | ZORUNLU (OHEM.empID ≠ SlpCode!) |
| Proje | `Project` | ✔ Evet | ZORUNLU — header seviye |
| Müşteri Ref. | `NumAtCard` | ◎ Opsiyonel | Müşteri kendi PO/proje adı |
| Belge Tarihi | `DocDate` | ◎ Opsiyonel | SAP işlem tarihini kullanır |
| Teslim Tarihi | `DocDueDate` | ◎ Opsiyonel | — |
| Açıklama | `Comments` | ◎ Opsiyonel | — |
| İlgili Kişi | `ContactPersonCode` | ◎ Opsiyonel | Müşteri kartından default |
| Şube | `U_Branch` | ✔ Evet | `"Elekon"` sabit |
| Teklif Türü | `U_Teklif_Turu` | ✔ Evet | Mandatory (geçersiz default `"---------------"`) |
| Teklif Aşaması | `U_Teklif_Durumu` | ◎ Opsiyonel | Hazırlanıyor/Gönderildi/İptal/Kaybedildi/Kazanıldı/Beklemede |
| Ödeme Koşulları | `U_Odeme_Kosullari` | ◎ Opsiyonel | Nakit/30 Gun/45 Gun/60 Gun/90 Gün/120 Gün/Kredi_Karti |
| Ödeme Türü | `U_Odm_Tr` | ◎ Opsiyonel | Çek/Senet/Havale/Peşin/Bedelsiz/Numune |
| Kur Değerleme | `U_Kur_Degerleme` | ◎ Opsiyonel | Var / Yok |
| Proje Adı (Key Acc.) | `U_Proje_Adi` | ⚑ Şartlı | `U_Teklif_Turu == "Key_Account"` ise ZORUNLU |
| Tahmini Gerçek Tarih | `U_Tahimini_Gercek_Tarih` | ◎ Opsiyonel | Alan adı typo — aynen bu şekilde gönder |
| Takip Çalışanı | `U_Takip_Calisani` | ◎ Opsiyonel | — |
| Teminat Mektubu | `U_LB_TemMektubu` | ◎ Opsiyonel | — |
| Teminat Tutarı | `U_LB_TemMektubuTutar` | ◎ Opsiyonel | — |
| Teminat Oranı | `U_LB_TemMektubuOran` | ◎ Opsiyonel | — |
| Çoklu Teklif | `U_coklu_teklif` | ◎ Opsiyonel | — |
| DocNum | `DocNum` | ✘ Hayır | SAP üretir |
| DocEntry | `DocEntry` | ✘ Hayır | SAP üretir |
| DocTotal | `DocTotal` | ✘ Hayır | SAP hesaplar |
| VatSum | `VatSum` | ✘ Hayır | SAP hesaplar |

---

## 2. Satır Alanları (DocumentLines)

| Alan | Service Layer | POST? | Not |
|---|---|---|---|
| Ürün Kodu | `ItemCode` | ✔ Evet | ZORUNLU |
| Miktar | `Quantity` | ✔ Evet | ZORUNLU |
| Birim Fiyat | `UnitPrice` | ✔ Evet | ZORUNLU |
| Depo | `WarehouseCode` | ✔ Evet | default `"01"` |
| Proje | `ProjectCode` | ✔ Evet | header `Project` ile genellikle aynı |
| Satın Almacı | `U_SatinAlmaci` | ✔ Evet | **MANDATORY**, default `"1"` (Gizem Bedir) |
| Satır İndirimi | `DiscountPercent` | ◎ Opsiyonel | — |
| Vergi Kodu | `VatGroup` | ◎ Opsiyonel | default `"S01"` (%20) |
| Ürün Açıklaması | `ItemDescription` | ✘ Hayır | SAP ItemCode'dan getirir |
| Satır Toplamı | `LineTotal` | ✘ Hayır | SAP hesaplar |
| Vergi Tutarı | `TaxTotal` | ✘ Hayır | SAP hesaplar |

---

## 3. KDV Grupları (VatGroup)

| Kod | Oran | Açıklama |
|---|---|---|
| `S01` | %20 | **Default** — Standart KDV |
| `S02` | %10 | İndirimli oran |
| `S03` | %1 | — |
| `S04` | %0 | İhracat (TAM-ISTISNA-301) |
| `S05` | %0 | Muaf (TAM-ISTISNA-308) |
| `S06` | %20 | Tevkifat 5/10 (TEVKIFAT-616) |
| `S11` | %0 | Hizmet İhracatı |
| `S12` | %20 | Tevkifat 7/10 (TEVKIFAT-603) |
| `S14` | %20 | Tevkifat 4/10 (TEVKIFAT-601) |
| `S18` | %18 | Eski oran (hâlâ aktif) |
| `S19` | %20 | Tevkifat 9/10 (TEVKIFAT-602) |
| `SXX` | %0 | KDV'ye tabi değil |

---

## 4. Depolar

| Kod | Ad |
|---|---|
| `01` | Ana Depo **(default)** |
| `02` | Servis Bakım Deposu |
| `02A` | İstanbul Servis Bakım Deposu |
| `03` | Müşteri Deposu |
| `04` | Component Depo |
| `04A` | İstanbul Component Deposu |
| `05` | İade Depo |
| `06` | Atıl Depo |
| `07` | Tarım Genel Depo |
| `08` | Ar-Ge Üretim Depo |
| `09` | FASON DEPO |
| `10` | Gazi Teknokent |

---

## 5. Satış Çalışanları (aktif)

| SalesEmployeeCode | Ad |
|---|---|
| 1 | Yener Çelebi |
| 3 | Celal Ceylan |
| 4 | Cengiz Gürbüzdal |
| 5 | Gözde Teke |
| 6 | Zafer Karabacak |
| 7 | Yıldırım Arslan |
| 10 | Utku Harpaslan |
| 11 | Ayşe Uygun |
| 12 | Ozan İhsan Onurhan |
| 13 | Gizem Bedir |
| 14 | Sonay Uzun |
| 19 | Alican Gezici |

> Pasif (Active=tNO): 2, 8, 9, 15, 16, 17, 18 — bunlara SalesPersonCode atama.

---

## 6. Çalışan Payload Örnekleri

### Yeni Sipariş (doğrudan)

```json
{
  "Series": 8,
  "CardCode": "120.01.0511",
  "DocCurrency": "EUR",
  "SalesPersonCode": 13,
  "DocumentsOwner": 16,
  "Project": "1212",
  "U_Branch": "Elekon",
  "U_Teklif_Turu": "Standart_Teklif",
  "NumAtCard": "urfa",
  "DocumentLines": [
    {
      "ItemCode": "134B",
      "Quantity": 1,
      "UnitPrice": 60.0,
      "WarehouseCode": "01",
      "ProjectCode": "1212",
      "VatGroup": "S01",
      "U_SatinAlmaci": "1"
    }
  ]
}
```

### Key_Account Siparişi

```json
{
  "Series": 8,
  "CardCode": "120.01.1119",
  "DocCurrency": "EUR",
  "SalesPersonCode": 14,
  "DocumentsOwner": 20,
  "Project": "10006",
  "U_Branch": "Elekon",
  "U_Teklif_Turu": "Key_Account",
  "U_Proje_Adi": "Çorum AVM Aydınlatma",
  "NumAtCard": "Çorum AVM",
  "U_Tahimini_Gercek_Tarih": "2026-06-30",
  "DocumentLines": [
    {
      "ItemCode": "H000106",
      "Quantity": 1,
      "UnitPrice": 500.0,
      "WarehouseCode": "01",
      "ProjectCode": "10006",
      "VatGroup": "S01",
      "U_SatinAlmaci": "1"
    }
  ]
}
```

### Quotation → Sipariş Dönüşümü

```json
{
  "Series": 8,
  "CardCode": "120.01.1119",
  "DocCurrency": "EUR",
  "Project": "10006",
  "U_Branch": "Elekon",
  "U_Teklif_Turu": "Standart_Teklif",
  "DocumentLines": [
    {
      "BaseType": 23,
      "BaseEntry": 7505,
      "BaseLine": 0,
      "Quantity": 1
    }
  ]
}
```

---

## 7. SAP Onay Prosedürü

`EnableApprovalProcedureInDI: tYES` aktif. POST başarılı (`200 OK`) olsa bile SAP onay prosedürüne girebilir.

**`SAPWriter` davranışı:**
- Response'da `Document_ApprovalRequests` dolu → `needs_human=True`, `sap_approval_pending=True`
- Belge SAP'ta oluşmuştur ama `Pending` modda
- UI'da "SAP onay bekliyor" gösterilir
- `DocEntry` + `DocNum` yine de kaydedilir

---

## 8. Stok Kontrolü

```python
GET /ItemsServiceGroups_GetItemAvailability
```

Yetersizse: UI'da kırmızı flag + alternatif depo öner + manager onayına gönder.

---

## 9. Backend Sınıf Kullanımı

```python
from app.sap.modules.sales_orders import SalesOrdersModule

payload = SalesOrdersModule.build_payload(
    card_code="120.01.0511",
    documents_owner=16,
    sales_person_code=13,
    project="1212",
    lines=[
        {
            "item_code": "134B",
            "quantity": 1,
            "unit_price": 60.0,
        }
    ],
    num_at_card="urfa",
)
```

---

## 10. Kabul Kriterleri

- [ ] Elekon örnek siparişi (`sample_orders.json`) ile eşleşen payload POST edilebiliyor
- [ ] Quotation'dan dönüşüm çalışıyor (BaseType=23)
- [ ] `U_Teklif_Turu="Key_Account"` → `U_Proje_Adi` eksikse `ValueError` fırlatıyor
- [ ] SAP onay prosedürü algılanıyor (`Document_ApprovalRequests`)
- [ ] İskonto > %15 manager onayı isteniyor
- [ ] Idempotent POST çalışıyor
