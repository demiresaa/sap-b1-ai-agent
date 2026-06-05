# Modül: Quotations (Satış Teklifi)

**Durum:** MVP (ön-MVP'den port edilecek)
**SAP Endpoint:** `/b1s/v1/Quotations`
**Backend:** `backend/app/sap/modules/quotations.py`
**Faz:** 1 (MVP)

> 📌 **Alan haritası ve UDF'ler:** Detaylı Service Layer field mapping, müşteri-özel UDF alanları (`U_Branch`, `U_Teklif_Turu`, `U_Proje_Adi`, `U_Tahimini_Gercek_Tarih`...) ve iş kuralları için → **[00-quotations-field-mapping.md](./00-quotations-field-mapping.md)** (otorite kaynak).
>
> 📌 **POST sonrası SAP çıktısı:** Müşteri DB'sinden alınmış gerçek örnek + DB şema önerisi + UDF valid-value yakalamaları → **[00-quotations-response-reference.md](./00-quotations-response-reference.md)**.

---

## Amaç
Mevcut Streamlit MVP'sinde çalışan PDF → Quotation akışını yeni Next.js + FastAPI altyapısına taşımak. Ürünün referans akışı.

## SAP Service Layer Detayları

### Endpoint
- `POST /Quotations` — yeni teklif oluştur
- `GET /Quotations({DocEntry})` — tek teklif getir
- `GET /Quotations?$filter=...` — listele
- `PATCH /Quotations({DocEntry})` — güncelle
- `POST /Quotations({DocEntry})/Cancel` — iptal

### Minimum Payload
```json
{
  "CardCode": "C00001",
  "DocDate": "2026-05-14",
  "DocDueDate": "2026-06-14",
  "DocCurrency": "TRY",
  "NumAtCard": "REF-2026-001",
  "Comments": "AI tarafından oluşturuldu",
  "DocumentLines": [
    {
      "ItemCode": "ITM-001",
      "Quantity": 10,
      "UnitPrice": 250.00,
      "DiscountPercent": 0
    }
  ]
}
```

### Önemli Alanlar
| Alan | Tip | Kaynak |
|---|---|---|
| CardCode | string | AI önerir, kullanıcı onaylar |
| DocDate | date | AI doldurur |
| DocDueDate | date | AI doldurur |
| DocCurrency | string | AI tespit |
| NumAtCard | string | AI tespit (referans no) |
| ContactPersonCode | int | Faz 2 |
| SalesPersonCode | int | Faz 2 |
| DocumentLines[] | array | Her satır AI çıkarımı |

## Backend Sorumlulukları
- `quotations.create(payload)` → POST + idempotency key
- `quotations.get(doc_entry)`
- `quotations.list(filters)`
- `quotations.update(doc_entry, patch)`
- Hata mapping → Türkçe

## Agent Akışı
1. DocumentReader → JSON çıkar
2. CustomerMatcher → CardCode
3. ProductMatcher → her satır ItemCode
4. Pricing → UnitPrice doğrula
5. (Stock kontrolü teklif aşamasında **opsiyonel**, sipariş'te zorunlu)
6. SAPWriter → Quotations POST

## Kabul Kriterleri
- 5 farklı PDF formatı doğru parse
- Eksik müşteri durumu graceful (boş bırak, kullanıcı seçer)
- Idempotent: aynı belge iki kez POST edilmez
- Türkçe hata mesajları

## Test Senaryoları
- Standart format (referans MVP PDF'leri)
- Eksik bilgi (müşteri adı yok)
- Çoklu para birimi
- Yüksek iskontolu (eşik üstü → onay)
- Çok satırlı (50+ satır)
