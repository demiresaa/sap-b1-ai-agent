# Modül: Production (Üretim)

**Durum:** Faz 3 (hazır placeholder)
**SAP Endpoint:** `/b1s/v1/ProductionOrders`, `/ProductTrees` (BoM), `/Resources`
**Backend:** `backend/app/sap/modules/production_orders.py`, `product_trees.py` (stub)
**Faz:** 3

---

## Amaç
Üretim emri otomasyonu, BoM (Bill of Materials / ürün ağacı) analizi, kapasite planlama önerileri. Sektöre bağlı — üretim yapan müşterilerde değerli.

## Aktif Olduğunda Yapılacaklar (TODO)

- [ ] ProductionOrder POST (üretim emri)
- [ ] ProductTrees (BoM) GET (reçete oku)
- [ ] IssueForProduction (hammadde sarfı) — InventoryGenExit Type=ReceiptFromProduction
- [ ] ReceiptFromProduction (mamul giriş) — InventoryGenEntry
- [ ] **Production Agent** (Opus 4.7): BoM kullanılabilirlik analizi
- [ ] Kapasite planlama (Resources)
- [ ] Sales Order → otomatik ProductionOrder oluştur

## Use Cases
- Müşteri özel sipariş (MTO): SO oluştuğunda BoM patla, eksik hammadde için PR aç
- Üretim emri kapanışında otomatik mamul giriş + KDS'lerden veri toplama
- Kapasite optimizasyonu (Opus karmaşık karar)

## Agent Genişlemeleri
- **Production Agent**: BoM ağacını yürür, alt seviye stoğu kontrol eder, PurchaseRequest tetikler

## Bağımlılıklar
- Inventory modülü aktif
- Resources master data
- Sales Orders (MTO senaryosu için)

## Faz 3 Sprint Tahmin
~15 iş günü
