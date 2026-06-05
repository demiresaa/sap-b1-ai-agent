# Modül: Purchasing (Satınalma)

**Durum:** Faz 2 (hazır placeholder)
**SAP Endpoint:** `/b1s/v1/PurchaseOrders`, `/PurchaseQuotations`, `/PurchaseRequests`, `/PurchaseDeliveryNotes`, `/PurchaseInvoices`
**Backend:** `backend/app/sap/modules/purchase_orders.py` (stub) + alt modüller
**Faz:** 2

---

## Amaç
Tedarikçiden gelen PDF/e-posta teklif/proforma → SAP Purchase Order. Düşük stokta otomatik Purchase Request. Mevcut satış akışının "ters" versiyonu — aynı agent altyapısı tedarikçi tarafında çalışır.

## Aktif Olduğunda Yapılacaklar (TODO)

- [ ] PurchaseRequest POST (stok min altına düştüğünde AI tetikler)
- [ ] PurchaseQuotation POST (tedarikçiden gelen teklif)
- [ ] PurchaseOrder POST (onaylı satınalma)
- [ ] PR → PQ → PO dönüşüm akışı
- [ ] PurchaseDeliveryNote (mal kabul)
- [ ] PurchaseInvoice (tedarikçi faturası)
- [ ] **Vendor Matcher Agent** (BP CardType='S' fuzzy match)
- [ ] Çoklu tedarikçi karşılaştırma (fiyat-vade analizi)

## Endpoint Özeti
- `POST /PurchaseRequests`
- `POST /PurchaseQuotations`
- `POST /PurchaseOrders`
- `POST /PurchaseDeliveryNotes`
- `POST /PurchaseInvoices`

## Agent Akışı (yeni)
1. DocumentReader → tedarikçi PDF JSON
2. **VendorMatcher** → BP (CardType=S) eşle
3. ProductMatcher → ItemCode eşle (mevcut)
4. Pricing → tedarikçi fiyat tarihçesi karşılaştır
5. SAPWriter → PurchaseOrder POST

## Use Case: Stoktan Tetiklenen Otomatik Talep
- Cron job: `/Items` stok seviyesi tara
- Min altında: PurchaseRequest auto-create
- Manager onayı: PR → PO dönüşüm
- En ucuz tedarikçi: geçmiş PO analizi

## Bağımlılıklar
- BusinessPartners (CardType=S) cache
- Items master data
- Approval workflow (PO eşik onayı)

## Faz 2 Sprint Tahmin
~10 iş günü
