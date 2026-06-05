# Quotations — SAP B1 Service Layer Field Mapping

> Kaynak: `SAP_B1_SatisTeklifi_FieldMapping.xlsx` (müşteri tarafından sağlanan resmi alan kılavuzu, 2026-05-20).
> AI Ajan, Quotation (`/Quotations`) payload'unu **bu dokümana** göre üretir. Müşteri-özel UDF alanları (`U_*`) ve iş kuralları burada otoritedir.

---

## POST Değerleri — Legend

| Sembol | Anlam |
|---|---|
| ✔ Evet | Payload'a **gönderilecek** — zorunlu alan |
| ✘ Hayır | SAP kendi oluşturur / hesaplar — **gönderilmez** |
| ◎ Opsiyonel | Kullanıcı seçerse veya değer varsa gönderilir |
| ⚑ Şartlı | Belirli kurala göre zorunlu hale gelir |

---

## Kritik İş Kuralları

1. **CardName ekranda gösterilir** ama POST'a **GÖNDERİLMEZ** — `CardCode` yeterlidir.
2. **DocType** şimdilik gönderilmez — SAP default kalem türünü kullanır. Bu versiyon yalnızca **kalem bazlı** teklif oluşturur, hizmet tipi satır kapsam dışı.
3. **ItemDescription** sadece arama/gösterim/eşleştirme için kullanılır. POST'a sadece `ItemCode` gider.
4. **Teklif Türü** `Key_Account` seçilirse → `U_Proje_Adi` **ZORUNLU** olur.
5. **`DocumentsOwner` ≠ `SalesPersonCode`.** `DocumentsOwner` → `OHEM.empID` (belge sahibi çalışan). `SalesPersonCode` → `OSLP.SlpCode` (satış çalışanı). Karıştırma!
6. **İlgili kişi (ContactPersonCode)** müşteri kartından default gelir. Kullanıcı farklı seçerse POST'a gider.
7. **SAP üretir, GÖNDERİLMEZ:** `DocNum`, `DocEntry`, `DocStatus`, `DocTotal`, `VatSum`, `LineTotal`, `OpenQuantity`, `TaxTotal`.

---

## 1️⃣ Başlık Alanları (Header)

| Ekrandaki Alan | SAP DB | Service Layer | POST? | Not / İş Kuralı |
|---|---|---|---|---|
| Müşteri | OQUT.CardCode | `CardCode` | ✔ Evet | ZORUNLU. Müşteri adı ekranda seçilebilir, POST'a CardCode gider. |
| Ad (Müşteri Adı) | OQUT.CardName | `CardName` | ✘ Hayır | Arayüz gösterimi. SAP CardCode'dan getirir. |
| İlgili Kişi | OQUT.CntctCode | `ContactPersonCode` | ◎ Opsiyonel | Müşteri kartından default. Kullanıcı değişirse gönderilir. |
| Proje Adı (NumAtCard) | OQUT.NumAtCard | `NumAtCard` | ✔ Evet | ZORUNLU. İlgili kişi altındaki proje adı. Örn: `"Çorum AVM"`. |
| Muhatabın Para Birimi | OQUT.DocCur | `DocCurrency` | ◎ Opsiyonel | Müşteri kartından otomatik. Değişirse gönderilir. |
| Şube | OQUT.U_Branch | `U_Branch` | ✔ Evet | ZORUNLU. Örn: `"Elekon"`. |
| Teklif Türü | OQUT.U_Teklif_Turu | `U_Teklif_Turu` | ⚑ Şartlı | Kullanıcı seçerse gönderilir. `Key_Account` → `U_Proje_Adi` ZORUNLU. |
| Teklif Aşaması | OQUT.U_Teklif_Durumu | `U_Teklif_Durumu` | ◎ Opsiyonel | Valid value listesi gerekir. |
| Takip Aşaması | OQUT.U_Takip_Asamasi | `U_Takip_Asamasi` | ◎ Opsiyonel | — |
| Teminat Mektubu | OQUT.U_LB_TemMektubu | `U_LB_TemMektubu` | ◎ Opsiyonel | Var / Yok. |
| Teminat Mektubu Tutarı | OQUT.U_LB_TemMektubuTutar | `U_LB_TemMektubuTutar` | ◎ Opsiyonel | Teminat varsa tutar. |
| Teminat Mektubu Oran | OQUT.U_LB_TemMektubuOran | `U_LB_TemMektubuOran` | ◎ Opsiyonel | Teminat oran. |
| Proje Adı (U_Proje_Adi) | OQUT.U_Proje_Adi | `U_Proje_Adi` | ⚑ Şartlı | Teklif Türü `Key_Account` ise ZORUNLU. |
| Çoklu Teklif | OQUT.U_coklu_teklif | `U_coklu_teklif` | ◎ Opsiyonel | — |
| No. | OQUT.DocNum | `DocNum` | ✘ Hayır | SAP üretir. |
| Durum | OQUT.DocStatus | `DocumentStatus` | ✘ Hayır | SAP belirler. |
| Geçerlilik Bitişi | OQUT.DocDueDate | `DocDueDate` | ◎ Opsiyonel | Değişirse gönderilir. |
| Belge Tarihi | OQUT.TaxDate | `TaxDate` | ◎ Opsiyonel | SAP default verir. |
| Kayıt Tarihi | OQUT.DocDate | `DocDate` | ◎ Opsiyonel | SAP işlem tarihi kullanabilir. |
| Tahmini Gerçekleştirme Tarihi | OQUT.U_Tahimini_Gercek_Tarih | `U_Tahimini_Gercek_Tarih` | ✔ Evet | ZORUNLU. **DİKKAT:** SAP'de alan adı `Tahimini` (typo) — payload'da aynen böyle gönder. |

---

## 2️⃣ Muhasebe

> Bu versiyonda Muhasebe sekmesinden **SADECE** bu iki alan dikkate alınır. Yevmiye açıklaması, Ödeme biçimi vb. **kapsam dışı**.

| Ekrandaki Alan | SAP DB | Service Layer | POST? | Not / İş Kuralı |
|---|---|---|---|---|
| Muhatap Projesi | OQUT.Project | `Project` | ✔ Evet | ZORUNLU. Header proje kodu. Örn: `"10006"`. Satır `ProjectCode` ile aynı değer gönderilebilir. |
| Ödeme Koşulları | OQUT.GroupNum | `PaymentGroupCode` | ◎ Opsiyonel | Müşteri kartından gelir. Değişirse gönderilir. |

---

## 3️⃣ Alt Alanlar

> ⚠ `DocumentsOwner` ≠ `SalesPersonCode`. `DocumentsOwner` → `OHEM.empID` (teklifin belge sahibi).

| Ekrandaki Alan | SAP DB | Service Layer | POST? | Not / İş Kuralı |
|---|---|---|---|---|
| Satış Çalışanı | OQUT.SlpCode | `SalesPersonCode` | ✔ Evet | ZORUNLU. Örn: `14`. Kaynak: `OSLP.SlpCode`. |
| Belge Sahibi | OQUT.OwnerCode | `DocumentsOwner` | ✔ Evet | ZORUNLU. Kaynak: `OHEM.empID`. **Satış çalışanı DEĞİLDİR.** |
| Takip Çalışanı | OQUT.U_Takip_Calisani | `U_Takip_Calisani` | ◎ Opsiyonel | — |
| Belge Altı İndirim | OQUT.DiscPrcnt | `DiscountPercent` | ◎ Opsiyonel | Belge geneli indirim. Satır indirimiyle karıştırma. |
| Açıklamalar | OQUT.Comments | `Comments` | ◎ Opsiyonel | Kullanıcı / sistem notu. |

---

## 4️⃣ İçerikler — Satırlar (DocumentLines)

> ⚠ `ItemDescription` POST'a gönderilmez — sadece arama/gösterim/eşleştirme.

| Ekrandaki Alan | SAP DB | Service Layer | POST? | Not / İş Kuralı |
|---|---|---|---|---|
| Kalem / Hizmet Türü | OQUT.DocType | `DocType` | ✘ Hayır | Şimdilik default kalem türü. |
| Kalem Numarası | QUT1.ItemCode | `DocumentLines.ItemCode` | ✔ Evet | ZORUNLU. AI bunu yakalayınca sistem `OITM`'den tanımı getirir. |
| Kalem Tanımı | QUT1.Dscription | `DocumentLines.ItemDescription` | ◎ Opsiyonel | Normalde ItemCode'dan SAP getirir. Özel açıklama isterse gönderilebilir. |
| Miktar | QUT1.Quantity | `DocumentLines.Quantity` | ✔ Evet | ZORUNLU. Boş / 0 olmamalı. |
| Birim Fiyat | QUT1.Price / PriceBefDi | `DocumentLines.UnitPrice` | ✔ Evet | ZORUNLU. SAP ekranında görünmeyebilir ama Service Layer `UnitPrice` bekler. |
| Satır İndirimi | QUT1.DiscPrcnt | `DocumentLines.DiscountPercent` | ◎ Opsiyonel | Kalem satırı indirimi. Belge altı indirimle karıştırma. |
| Vergi Kodu | QUT1.VatGroup | `DocumentLines.TaxCode` | ◎ Opsiyonel | Ürün kartından otomatik gelebilir. |
| Proje | QUT1.Project | `DocumentLines.ProjectCode` | ✔ Evet | ZORUNLU. Genelde header `Project` ile aynı değer. |
| Depo | QUT1.WhsCode | `DocumentLines.WarehouseCode` | ◎ Opsiyonel | Sabit depo kullanılacaksa gönderilir. |
| Satır Toplamı | QUT1.LineTotal | `DocumentLines.LineTotal` | ✘ Hayır | SAP hesaplar. |
| Açık Miktar | QUT1.OpenQty | `DocumentLines.OpenQuantity` | ✘ Hayır | SAP hesaplar. |
| Vergi Tutarı | QUT1.VatSum | `DocumentLines.TaxTotal` | ✘ Hayır | SAP hesaplar. |
| Stokta (Depodaki Miktar) | OITW.OnHand | — | ✘ Hayır | Sadece gösterim/validasyon. |

---

## 5️⃣ Kalem Eşleştirme Kuralları (AI)

> POST'a **her zaman sadece `ItemCode`** gider. `ItemDescription` sadece arama/gösterim/eşleştirme amaçlıdır.

| Senaryo | Sistem Davranışı | POST'a Giden |
|---|---|---|
| AI PDF/Excel'den **kalem numarası** yakalarsa | `OITM.ItemCode` üzerinden ana veri getir, ekranda göster, kullanıcı doğrular. | ✔ ItemCode |
| AI PDF/Excel'den **kalem tanımı** yakalarsa | `OITM.ItemName` / açıklama üzerinden uygun ItemCode bulmaya çalış. Kullanıcı doğrular. | ✔ ItemCode |
| AI **hem kalem no hem tanım** yakalarsa | İkisinin aynı kalem kartına ait olup olmadığını kontrol et. Uyuşmazlık varsa UYARI. | ✔ Doğrulanan ItemCode |
| AI kalemi **net eşleştiremezse** | Kullanıcı arayüzde MANUEL seçer. | ✔ Manuel seçilen ItemCode |

---

## 6️⃣ SAP Üretilen Alanlar — POST'a GÖNDERİLMEZ

| Seviye | Ekrandaki Alan | Service Layer | Not |
|---|---|---|---|
| Header | DocEntry | `DocEntry` | SAP iç anahtarı. |
| Header | No. (Teklif No) | `DocNum` | SAP üretir. |
| Header | Müşteri Adı | `CardName` | CardCode üzerinden gelir. |
| Header | Durum | `DocumentStatus` | SAP yönetir. |
| Header | İptal | `CANCELED` | SAP yönetir. |
| Header | Belge Toplamı | `DocTotal` | SAP hesaplar. |
| Header | Vergi Toplamı | `VatSum` | SAP hesaplar. |
| Satır | Satır Toplamı | `DocumentLines.LineTotal` | SAP hesaplar. |
| Satır | Açık Miktar | `DocumentLines.OpenQuantity` | SAP hesaplar. |

---

## 7️⃣ Minimum Çalışan Payload — Örnek JSON

```json
{
  "CardCode": "120.01.1119",
  "SalesPersonCode": 14,
  "DocumentsOwner": 20,
  "U_Branch": "Elekon",
  "Project": "10006",
  "NumAtCard": "Çorum AVM",
  "U_Tahimini_Gercek_Tarih": "2026-02-23",
  "DocumentLines": [
    {
      "ItemCode": "H000106",
      "Quantity": 1,
      "UnitPrice": 500,
      "ProjectCode": "10006"
    }
  ]
}
```

### Şartlı genişletme örneği — `Key_Account`

```json
{
  "CardCode": "120.01.1119",
  "SalesPersonCode": 14,
  "DocumentsOwner": 20,
  "U_Branch": "Elekon",
  "U_Teklif_Turu": "Key_Account",
  "U_Proje_Adi": "Çorum AVM Aydınlatma",
  "Project": "10006",
  "NumAtCard": "Çorum AVM",
  "U_Tahimini_Gercek_Tarih": "2026-02-23",
  "DocumentLines": [
    { "ItemCode": "H000106", "Quantity": 1, "UnitPrice": 500, "ProjectCode": "10006" }
  ]
}
```

---

## Backend / Agent İçin Uygulama Notları

- **`backend/app/sap/modules/quotations.py`** — POST payload builder bu mapping'i takip eder. UDF alanları (`U_*`) tipli (typed) bir Pydantic modelde tanımlanmalı.
- **`backend/app/schemas/quotation.py`** (yeni) — Pydantic model bu tabloya birebir uymalı; opsiyonel alanlar `None | T`, şartlı alanlar validator ile kontrol edilmeli (`U_Teklif_Turu == "Key_Account"` → `U_Proje_Adi` zorunlu).
- **`backend/app/agents/sap_writer.py`** — Yazma öncesi `model_validate` ile şartlı kuralları doğrula; `U_Tahimini_Gercek_Tarih` typo'sunu aynen kullan, düzeltme.
- **AI çıktı şeması (DocumentReader)** — PDF/Excel'den çıkarılan JSON bu alanlara mapping'lenir. Eşleşmeyen alanlar `null`, agent doldurur (CustomerMatcher → CardCode, ProductMatcher → ItemCode, vb.).
- **Validation katmanı** — `LineTotal`, `DocTotal`, `VatSum` AI tarafından önerilse bile payload'a **konmaz** (SAP hesaplar). Validator bu alanları silmeli.
- **Onay (HITL) eşikleri** — Belge toplamı eşik üstü, iskonto %15+, eşleşme confidence < 0.85 → kullanıcı onayı (CLAUDE.md §5.4).
