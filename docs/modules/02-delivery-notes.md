# Modül: Delivery Notes (İrsaliye / Sevkiyat)

**Durum:** Faz 2 (hazır placeholder)
**SAP Endpoint:** `/b1s/v1/DeliveryNotes`
**Backend:** `backend/app/sap/modules/delivery_notes.py` (stub)
**Faz:** 2

---

## Amaç
Sales Order'dan sevkiyat çekme; partial delivery; sevkiyat planlaması; e-irsaliye entegrasyonu (TR).

## Aktif Olduğunda Yapılacaklar (TODO)

- [ ] `delivery_notes.py` stub'ını implementasyona dönüştür
- [ ] POST /DeliveryNotes (yeni irsaliye)
- [ ] BaseType: 17 (Sales Order) ile referanslı kopya
- [ ] Partial delivery (satır bazında miktar)
- [ ] WarehouseCode + bin location desteği
- [ ] Carrier (TransportationCode), Tracking number alanları
- [ ] e-İrsaliye XML üretimi (TR mevzuat)
- [ ] UI: "Sevkiyat planla" butonu Sales Order detayında

## Endpoint Özeti
- `POST /DeliveryNotes`
- `GET /DeliveryNotes({DocEntry})`
- `POST /DeliveryNotes({DocEntry})/Cancel`

## Minimum Payload (SO Referanslı)
```json
{
  "CardCode": "C00001",
  "DocDate": "2026-05-14",
  "DocumentLines": [
    {
      "BaseType": 17,
      "BaseEntry": 2050,
      "BaseLine": 0,
      "Quantity": 5
    }
  ]
}
```
(`BaseType: 17` = Sales Order)

## Agent Genişlemeleri
- **Logistics Agent** (yeni): sevkiyat planı önerir (tarih, taşıyıcı, parsel)
- **ProductMatcher** mevcut, sadece BaseLine referans çözer

## Bağımlılıklar
- Sales Orders modülü tamamlanmış olmalı
- Stok modülü (envanter düşürme otomatik SAP yapar)

## Faz 2 Sprint Tahmin
~5 iş günü
