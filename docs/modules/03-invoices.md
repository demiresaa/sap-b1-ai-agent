# Modül: Invoices (A/R Fatura)

**Durum:** Faz 2 (hazır placeholder)
**SAP Endpoint:** `/b1s/v1/Invoices`
**Backend:** `backend/app/sap/modules/invoices.py` (stub)
**Faz:** 2

---

## Amaç
A/R fatura otomasyonu. Delivery Note → Invoice zinciri. **Türkiye e-fatura/e-arşiv entegrasyonu** kritik.

## Aktif Olduğunda Yapılacaklar (TODO)

- [ ] POST /Invoices (yeni A/R fatura)
- [ ] DN referanslı kopya (BaseType: 15)
- [ ] Doğrudan SO → Invoice (DN atlayarak, mevzuata uygun ürünlerde)
- [ ] **e-Fatura UBL 2.1 üretimi** (TR)
- [ ] **e-Arşiv** opsiyonu (B2C)
- [ ] GİB entegratör servisi (Logo, Foriba, vb.) bağlantısı
- [ ] CreditNote oluşturma (iade durumu)
- [ ] PDF fatura çıktısı + müşteri portala link

## Endpoint Özeti
- `POST /Invoices`
- `POST /Invoices({DocEntry})/Cancel`
- `POST /CreditNotes` (iade)

## Minimum Payload (DN Referanslı)
```json
{
  "CardCode": "C00001",
  "DocDate": "2026-05-14",
  "DocumentLines": [
    {
      "BaseType": 15,
      "BaseEntry": 3010,
      "BaseLine": 0
    }
  ]
}
```
(`BaseType: 15` = Delivery Note)

## Agent Genişlemeleri
- **Finance Agent** (yeni): KDV hesaplama doğrulama, vade kontrolü
- Mevzuat kuralları motoru (Türkiye)

## Bağımlılıklar
- Delivery Notes (veya direkt SO) modülü
- GİB e-fatura entegratör hesabı
- KDV kodu master data senkronizasyonu

## Faz 2 Sprint Tahmin
~10 iş günü (e-fatura yüzünden uzun)
