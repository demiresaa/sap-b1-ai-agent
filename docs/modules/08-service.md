# Modül: Service Calls (Servis Çağrısı)

**Durum:** Faz 3 (hazır placeholder)
**SAP Endpoint:** `/b1s/v1/ServiceCalls`, `/Contracts`, `/CustomerEquipmentCards`
**Backend:** `backend/app/sap/modules/service_calls.py` (stub)
**Faz:** 3

---

## Amaç
Saha servis çağrı yönetimi, müşteri ekipman takibi, garanti kontrolü. Servis ağırlıklı müşteri segmenti için ayrı vertical.

## Aktif Olduğunda Yapılacaklar (TODO)

- [ ] ServiceCall POST
- [ ] CustomerEquipmentCard GET (seri no ile ekipman bul)
- [ ] Contract GET (garanti süresi kontrol)
- [ ] Resolution güncelleme
- [ ] **Service Agent**: e-posta/WhatsApp'tan çağrı açma, teknisyen önerme

## Use Cases
- Müşteri WhatsApp: "X cihazım çalışmıyor seri no Y" → Service Call auto-create
- Garanti durumu kontrol → ücretli/ücretsiz flag
- Teknisyen rota optimizasyonu (Faz 4)

## Bağımlılıklar
- WhatsApp Business entegrasyonu (Faz 2'den geliyor)
- Equipment master data

## Faz 3 Sprint Tahmin
~8 iş günü
