# KVKK / Veri Sahipliği Envanteri

Bu doküman SAP B1 AI Agent platformunun **kişisel veri işleme envanteri**dir. KVKK (Kişisel Verilerin Korunması Kanunu) kapsamında **Veri Sorumlusu** rolünü üstlenen müşteri şirketinin kullanması içindir. Pilot/SaaS sözleşmesinde bu envantere referans verilmesi tavsiye edilir.

**Sürüm:** 1.0 — Mayıs 2026
**İlgili kanun:** KVKK 6698, AB GDPR (gerektiğinde)
**İrtibat:** veri sorumlusu / DPO

---

## 1. Veri Kategorileri ve Saklama Yeri

| Kategori | İçerik | Tablo | Saklama Süresi | Yasal Dayanak |
|---|---|---|---|---|
| Kullanıcı kimlik | ad, e-posta, hashed parola, rol | `users`, `user_roles` | Hesap aktif olduğu sürece + 1 yıl | Sözleşme |
| Müşteri (BP) cache | CardName, CardCode, vergi no, e-posta, telefon | `bp_cache` | SAP master'da bulunduğu sürece | Meşru menfaat |
| Müşteri özel alias | öğrenilmiş ürün/cari eşleşmeleri | `customer_alias` | Müşteri hesabı kapanmasından 1 yıl sonra silinir | Meşru menfaat |
| Belge metadata | dosya adı, e-posta konusu, kaynak adresi | `documents` | `data_retention_days_documents` (varsayılan 365 gün) | Sözleşme |
| Belge ham içeriği | PDF dosyası (storage) | `storage_path` (disk/S3) | Belge ile aynı | Sözleşme |
| AI çıkarımı | extracted_data JSONB (müşteri ad, ürün, tutar) | `extracted_data` | Belge ile aynı | Sözleşme |
| LLM çağrıları | prompt hash, token, maliyet (içerik **tutulmaz**) | `llm_calls` | `data_retention_days_llm_calls` (730 gün) | Meşru menfaat (audit) |
| Onay geçmişi | onaycı id, gerekçe | `approval_requests` | Audit ile aynı | Hukuki yükümlülük |
| Audit log | her önemli aksiyon | `audit_log` | `data_retention_days_audit_log` (7 yıl) | Hukuki yükümlülük |
| SAP submission | belge POST kaydı, idempotency key | `sap_submissions` | Audit ile aynı | Hukuki yükümlülük |
| Document events | timeline (status değişimleri) | `document_events` | Belge ile aynı | Sözleşme |

**Not:** LLM çağrılarında **prompt içeriği saklanmaz**, sadece SHA-256 hash + token sayısı + maliyet tutulur. Bu, müşteri PII'sinin sürekli olarak OpenRouter/LLM sağlayıcısına gönderilmesini değil, sadece anlık çağrı sırasında geçici işlemeyi gerektirir.

---

## 2. Veri Aktarımı (Yurt Dışı Dahil)

| Hedef | Veri | Mekanizma | Açıklama |
|---|---|---|---|
| OpenRouter API | Belge text/görsel (geçici), prompt — OpenRouter seçilen modele yönlendirir (Anthropic/OpenAI/Google vb.) | HTTPS, TLS 1.3 | AB/US sunucuları; sözleşme öncesi müşteriye bildirilir; OpenRouter "logging=false" ve "data retention=0" header'ları desteklenir |
| SAP Service Layer | BP/Item/Doc payload | mTLS tunnel (on-prem) | Müşteri kendi sunucusu, dışarı çıkmaz |
| E-posta (IMAP/Graph) | Müşteri inbox'tan attachment | TLS | Müşteri onayıyla |
| Sentry (opsiyonel) | Hata stack trace, request id | TLS | PII maskeli (e-posta, vergi no `[REDACTED]`) |

---

## 3. Veri Sahibi Hakları (KVKK m.11)

| Hak | Endpoint / Süreç |
|---|---|
| Erişim | `GET /api/auth/me` (kendi) · Admin → DB sorgu (başka kullanıcı) |
| Düzeltme | `PATCH /api/documents/{id}` · Settings UI |
| Silme | Manuel: admin → `DELETE FROM ... WHERE actor_id=...`. Yedek 30 gün sonra silinir. |
| İşlemeyi sınırlama | Audit log içinde `consent_revoked` event |
| Veri taşınabilirliği | Belge JSON export (`GET /api/documents/{id}` çıktısı, JSON) |
| İtiraz | İletişim adresi DPO |

**SLA:** veri sahibi talepleri 30 gün içinde yanıtlanır.

---

## 4. Teknik Güvenlik Önlemleri

- **At-rest:** Postgres + S3 disk encryption (cloud provider native)
- **In-transit:** TLS 1.2+; SAP Connector ↔ Cloud arasında mTLS
- **Erişim:** RBAC (Operator/Manager/Admin); en az ayrıcalık prensibi
- **Parola:** bcrypt cost ≥ 12
- **Token:** JWT 60 dk access + 7 gün refresh; rotation Faz 2'de
- **Audit:** `audit_log` Postgres trigger ile UPDATE/DELETE engelli (append-only)
- **Backup:** günlük tam yedek, 30 gün, encrypted
- **Pen-test:** Pilot öncesi OWASP Top 10 review (Sprint 5)
- **Secret yönetimi:** `.env` dosyaları repo dışı; production'da Vault/Key Vault önerilir

---

## 5. Veri İhlali Bildirim Prosedürü

1. **Tespit:** monitoring (Sentry/OTEL) → DPO bilgilendirilir.
2. **Kapsam analizi:** 6 saat içinde etkilenen kullanıcı/belge listesi çıkarılır.
3. **KVKK kuruluna bildirim:** 72 saat içinde (zorunlu).
4. **Veri sahiplerine bildirim:** etkileri yüksekse 30 gün içinde.
5. **Kapanış raporu:** root cause, alınan önlemler, audit log'da kayıt.

---

## 6. Üçüncü Taraflarla Sözleşmeler

- **OpenRouter + arka uç sağlayıcılar (Anthropic/OpenAI/Google):** OpenRouter DPA + müşteriye seçtiğimiz modelin DPA'sı bildirilir.
- **Cloud provider:** Standard Contractual Clauses (SCC) yurt dışı aktarım için.
- **SAP Türkiye:** mevcut SAP B1 lisans sözleşmesi kapsamında.

---

## 7. Yıllık Gözden Geçirme

Bu doküman **yılda 1 kez** ve veri akışı değiştiğinde **revize edilir**. Sürüm git tag ile (`v1.0`, `v1.1`).

---

**İmza:** Veri Sorumlusu (müşteri) · DPO · Sistem geliştirici (tedarikçi)
