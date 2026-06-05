# Modül: Payments (Tahsilat & Tediye)

**Durum:** Faz 2 (hazır placeholder)
**SAP Endpoint:** `/b1s/v1/IncomingPayments`, `/VendorPayments`
**Backend:** `backend/app/sap/modules/payments.py` (stub)
**Faz:** 2

---

## Amaç
Tahsilat (müşteriden gelen) ve tediye (tedarikçiye giden) ödeme kayıtları. Banka mutabakatı için temel.

## Aktif Olduğunda Yapılacaklar (TODO)

- [ ] IncomingPayment POST (Invoice'a tahsilat)
- [ ] VendorPayment POST (PurchaseInvoice'a ödeme)
- [ ] Banka ekstresi (CSV/MT940) parse edip otomatik mutabakat önerisi
- [ ] Çek/senet (BillOfExchange) takibi
- [ ] Vade uyarı sistemi (vadesi gelen, gecikmiş)
- [ ] **Finance Agent**: ekstre satırını fatura ile eşle (fuzzy)

## Use Cases
- Banka ekstresinde X TL tahsilat → AI hangi faturaya gittiğini bulur, IncomingPayment önerir
- Vadesi geçmiş alacak listesi + otomatik hatırlatma e-postası
- Tedarikçi vadesi → VendorPayment auto-draft

## Bağımlılıklar
- Invoices modülü aktif
- Banka ekstresi formatı standartlaşmış olmalı

## Faz 2 Sprint Tahmin
~7 iş günü
