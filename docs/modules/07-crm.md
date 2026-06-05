# Modül: CRM (Fırsat ve Aktivite)

**Durum:** Faz 3 (hazır placeholder)
**SAP Endpoint:** `/b1s/v1/SalesOpportunities`, `/Activities`, `/ContactEmployees`
**Backend:** `backend/app/sap/modules/opportunities.py` (stub)
**Faz:** 3

---

## Amaç
Gelen e-posta/PDF'lerden satış fırsatı otomatik oluşturma, takip aktivitesi açma, pipeline besleme. Satış ekibine context.

## Aktif Olduğunda Yapılacaklar (TODO)

- [ ] SalesOpportunity POST
- [ ] Stage geçişleri (10 stage default SAP)
- [ ] Activity POST (görev, randevu, telefon)
- [ ] ContactEmployee yönetimi (yeni iletişim kişisi öneri)
- [ ] **CRM Agent**: e-postadan fırsat çıkar, stage öner

## Use Cases
- "Fiyat öğrenebilir miyim" e-postası → Opportunity (Prospect stage) + Activity (geri dön)
- Quotation gönderildi → Opportunity stage "Proposal" yükselt
- Sales Order oluştu → Opportunity stage "Won" + kapanış

## Bağımlılıklar
- Sales Orders + Quotations modülleri

## Faz 3 Sprint Tahmin
~6 iş günü
