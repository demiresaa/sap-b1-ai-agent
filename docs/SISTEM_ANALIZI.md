# SAP B1 AI Agent — Sistem Analiz Dokümanı

**Versiyon:** 1.0
**Tarih:** Mayıs 2026
**Kapsam:** MVP (Satış Siparişi) + Modüler Genişleme Altyapısı
**Hedef:** SAP Business One Service Layer üzerinde çalışan, PDF/e-posta'dan otomatik sipariş/teklif işleyen multi-agent AI platformu

---

## 1. Yönetici Özeti

SAP Business One kullanan şirketlerde teklif ve sipariş mühendisleri, müşteriden gelen PDF/e-posta taleplerini manuel okuyup SAP'a tek tek giriyor. Bu süreç teklif/sipariş başına 45-90 dakika sürüyor, %3-5 hata oranı içeriyor ve mühendis zamanının büyük kısmını veri girişine harcatıyor.

Bu projede, **multi-agent yapay zeka mimarisi** ile bu süreci 5-10 dakikaya indiriyoruz. Mühendis sadece kontrol ve onay rolünde kalıyor. SAP'a yazım Service Layer REST API üzerinden otomatik yapılıyor.

**MVP odağı: Satış Siparişi (Sales Order).** Mevcut ön-MVP teklif (Quotation) akışı da korunuyor. Lojistik, Muhasebe, Satınalma, Stok, Üretim modülleri için **kod yerleri ve plan dosyaları hazır**, entegrasyon anı geldiğinde hızla devreye alınacak.

---

## 2. Problem Tanımı

### 2.1 Mevcut Süreç
1. Müşteri e-posta ile PDF sipariş/teklif talebi gönderir.
2. Mühendis e-postayı yakalar, PDF'i açar, okur.
3. SAP B1'i açar, ilgili formu (Quotation / Sales Order) manuel doldurur.
4. Müşteriyi cariden seçer, her ürünü stok kartından arar, fiyat/iskonto/tarih girer.
5. Kaydeder, müşteriye onay döner.

### 2.2 Tespit Edilen Sorunlar
| Sorun | Etki |
|---|---|
| 45-90 dk/teklif manuel giriş | Mühendis günde 4-6 belge tıkanıyor |
| %3-5 elle giriş hatası | Yanlış fiyat/ürün → sevkiyat-iade zinciri |
| SAP arayüzü karmaşık | Yeni kullanıcı öğrenme eğrisi uzun |
| Yöneticide görünürlük yok | Hangi teklif nerede tıkalı bilinmiyor |
| Geç dönüş | Rakip aynı gün cevap verirken siz 1-2 gün sonra |
| Mühendis morali | İş zamanı veri girişiyle dolu, değerli işe zaman yok |

### 2.3 Hedef Süreç
1. E-posta otomatik yakalanır VEYA mühendis PDF yükler.
2. AI document reader → müşteri, ürünler, miktar, fiyat, tarih çıkarır.
3. AI customer matcher → SAP BP'lerle eşler (fuzzy + vergi no + e-posta).
4. AI product matcher → SAP Items ile eşler (alias, barkod, semantic).
5. Pricing/Stock agent → fiyat ve stok kontrolü, uyarı/öneri.
6. Mühendis formu görür (AI doldurduğu alanlar yeşil), kontrol/düzeltme yapar.
7. "SAP'a Gönder" → Service Layer üzerinden POST.
8. SAP'tan DocEntry/DocNum gelir, ekranda gösterilir, audit log'a yazılır.

**Hedef performans:** Teklif/sipariş başına 5-10 dk, %1 altında hata, no-touch oranı (hiç dokunmadan SAP'a giden) %40+.

---

## 3. Ürün Vizyonu ve Pazar Konumu

### 3.1 Vizyon
SAP B1 Türkiye pazarında **5.000+ şirket** kullanıyor. Hepsi aynı manuel giriş acısını çekiyor. Bizim ürün, SAP'ı değiştirmeden üstüne takılan bir **AI katmanı** olarak çalışacak. İlk müşteride satış siparişi ile başlayıp aynı altyapı üzerine lojistik, muhasebe, satınalma, üretim modüllerini ekleyerek müşteri başı geliri 5-10x büyütüyoruz.

### 3.2 Rakip Manzarası
| Rakip Kategorisi | Örnek | B1 Durumu | Boşluk |
|---|---|---|---|
| Global CPQ | SAP CPQ, Tacton, DealHub | S/4 odaklı, pahalı | B1 için aşırı |
| Doküman AI | Rossum, Hyperscience, Klippa | API var, yazım yok | "SAP'a yazım" eksik |
| RPA | UiPath, Automation Anywhere | GUI bot, kırılgan | TR + Service Layer zayıf |
| iPaaS | Boomi, Workato | Connector var | AI/agent değil |
| TR Entegratör | Detaysoft, NTT, BiTeknoloji | AI ürünü yok | Pazar boş |

**Pozisyonumuz:** SAP B1 native, Service Layer ile uçtan uca, Türkçe PDF/e-posta anlayan, **yerli ve dünyada niş** AI agent paketi.

### 3.3 Fiyatlandırma Modeli (Yön)
- **Base platform fee:** ₺15K–50K/ay (müşteri büyüklüğüne göre)
- **Doküman başı ücret:** ₺2–10 (kullanım üzerinden)
- **Modül başı ek lisans:** Faz 2+ modüller için aylık ek ücret
- Pilot/POC: 30 gün ücretsiz, sonra base + kullanım

---

## 4. Sistem Mimarisi

### 4.1 Yüksek Seviye Diyagram
```
┌──────────────────────────────────────────────────────────┐
│                   KULLANICI KATMANI                       │
│  Next.js Web (dashboard, pipeline, form) + Müşteri Portal │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTPS / WebSocket
┌────────────────────────▼─────────────────────────────────┐
│                    API KATMANI (FastAPI)                  │
│   Auth · RBAC · REST endpoints · WebSocket events         │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│              ORCHESTRATOR (Claude Sonnet 4.6)             │
│                 + Specialist Agents                       │
│  DocReader · CustomerMatcher · ProductMatcher · Pricing   │
│  Stock · SAPWriter · Approval · Notification              │
└──┬──────────────┬──────────────┬─────────────┬──────────┘
   │              │              │             │
   ▼              ▼              ▼             ▼
┌─────────┐  ┌─────────┐  ┌──────────┐  ┌─────────────┐
│Postgres │  │ Redis   │  │ Celery   │  │ OpenRouter  │
│ +vector │  │ cache   │  │ workers  │  │   API       │
└─────────┘  └─────────┘  └──────────┘  └─────────────┘
                                              │
                                              ▼
                                  ┌───────────────────────┐
                                  │ SAP CONNECTOR (on-prem)│
                                  │  Service Layer wrapper │
                                  │  Session pool, retry   │
                                  └───────────┬───────────┘
                                              │ HTTPS:50000
                                              ▼
                                       ┌──────────────┐
                                       │  SAP B1      │
                                       │ Service Layer│
                                       └──────────────┘
```

### 4.2 Deployment Modeli (Hibrit Öneri)
- **On-prem (müşteri network'ünde):** SAP Connector Agent — Service Layer'a tek erişim noktası. Lightweight Python servis. mTLS tunnel ile buluta bağlanır.
- **Bulutta:** Web UI, FastAPI, AI çağrıları, Postgres, Redis, Celery. Türkiye region (Azure West Europe / AWS Frankfurt) — KVKK için TR data center opsiyonu Faz 2'de.
- **Alternatif tam on-prem:** Aynı Docker Compose ile müşteri kendi sunucusunda çalıştırabilir (yüksek güvenlik isteyen müşteri için).

### 4.3 Multi-Agent Topolojisi

| Agent | Model | Görev |
|---|---|---|
| **Orchestrator** | Sonnet 4.6 | State machine, agent çağırma sırası, hata yönetimi |
| **Document Reader** | Sonnet 4.6 (vision) | PDF/DOCX/image → yapılandırılmış JSON |
| **Customer Matcher** | Sonnet 4.6 | BP eşleştirme: fuzzy + vergi no + e-posta + alias |
| **Product Matcher** | Sonnet 4.6 + pgvector | ItemCode eşleştirme: semantic + SKU + barkod + müşteri alias |
| **Pricing** | Sonnet 4.6 | Fiyat listesi + iskonto + kampanya kontrolü |
| **Stock** | Haiku | Anlık availability, alternatif depo/ürün |
| **SAP Writer** | (LLM gerektirmez) | Idempotent POST, retry, DocEntry yönetimi |
| **Approval** | Haiku | Eşik kontrolü, onaycı belirleme |
| **Notification** | Haiku | E-posta/WhatsApp/Teams mesajı |
| **Hard Cases (escalation)** | Opus 4.7 | Çok belgeli karmaşık siparişler, müzakere mantığı |

### 4.4 Human-in-the-Loop Kuralları
Aşağıdaki durumlarda **otomatik SAP yazım YAPILMAZ**, mühendis onayı zorunludur:
- Müşteri eşleşme güveni < 0.85
- Ürün eşleşme güveni < 0.85
- Yeni müşteri/ürün yaratma talebi (otomatik açılmaz, öneri sunulur)
- İskonto > %15 veya tutar > eşik (config'de tanımlı)
- Stok yetersizliği — alternatif kabul gerekiyor
- AI tarafından "düşük güven" flag'i konmuş herhangi bir alan

### 4.5 Hata Kurtarma
- **Saga pattern:** Her agent compensating action tanımlar.
- **Idempotency key:** Her SAP POST'unda UUID gönderilir, duplicate detection.
- **Retry:** 3 deneme, exponential backoff (1s → 4s → 16s).
- **Partial failure:** Header oluştu lines hata → DocEntry cancel veya manuel kuyruğa.
- **Event-sourced state:** Tüm agent kararları replayable.

---

## 5. MVP Kapsamı — Satış Siparişi (Sales Order)

### 5.1 MVP'de VAR
| Bileşen | Açıklama |
|---|---|
| PDF yükleme | Web arayüzünden tek dosya upload |
| E-posta inbox | IMAP/Microsoft Graph polling (tek hesap) |
| AI doküman okuma | Müşteri, ürünler, miktar, fiyat, tarih, para birimi |
| SAP müşteri eşleştirme | BusinessPartners GET + fuzzy match |
| SAP ürün eşleştirme | Items GET + alias tablosu + pgvector |
| Stok kontrolü | ItemsService_GetItemAvailability |
| Quotation POST | Mevcut MVP korunuyor |
| **Sales Order POST** | **MVP ana özelliği** |
| Form arayüzü | AI doldurduğu alanlar yeşil, manuel düzenleme |
| Pipeline (Kanban) | Gelen / İşleniyor / Onay / SAP'a yazıldı / Hata |
| Audit log | Her agent kararı + LLM call + kullanıcı eylemi |
| RBAC | 3 rol: Operatör, Müdür, Admin |
| Türkçe arayüz + hata mesajları | Tamamı Türkçe |

### 5.2 MVP'de YOK (Sonraki fazlar — klasör yapısında yeri hazır)
- Lojistik (Delivery Notes, sevkiyat) → `docs/modules/02-delivery-notes.md`
- Muhasebe (Invoices, Payments) → `docs/modules/03-invoices.md`
- Satınalma (Purchase Orders) → `docs/modules/04-purchasing.md`
- Stok yönetimi (Transfers, Counting) → `docs/modules/05-inventory.md`
- Üretim (Production Orders, BOM) → `docs/modules/06-production.md`
- CRM (Opportunities, Activities) → `docs/modules/07-crm.md`
- Servis (Service Calls) → `docs/modules/08-service.md`
- Müşteri portalı (magic link)
- WhatsApp Business entegrasyonu
- Multi-tenant SaaS
- Çok aşamalı onay (multi-stage approval)
- Marketplace / 3. parti agent

### 5.3 Kullanım Akışı (MVP)
1. Mühendis sisteme login olur (web tarayıcı).
2. Pipeline ekranında "Yeni Sipariş" diyerek PDF yükler **veya** sistem e-posta inbox'tan otomatik çekmiştir.
3. Orchestrator çalışır → DocumentReader, CustomerMatcher, ProductMatcher, Pricing, Stock peş peşe.
4. Form ekranı açılır: AI doldurduğu alanlar yeşil, düşük güvenli alanlar sarı, boş alanlar beyaz.
5. Mühendis kontrol eder, müşteri dropdown'undan onaylar, ürün satırlarını doğrular, gerekirse fiyat/iskonto düzeltir.
6. "SAP'a Gönder" butonuna basar → SAPWriter agent Sales Order POST atar.
7. Başarılı: DocEntry + DocNum ekranda gösterilir, pipeline'da "SAP'a yazıldı" sütununa geçer.
8. Hata: Türkçe çevirilmiş hata mesajı + retry butonu.

### 5.4 Kabul Kriterleri (Definition of Done)
| # | Senaryo | Beklenen Sonuç |
|---|---|---|
| 1 | Standart formatlı müşteri PDF yüklenir | Müşteri + 1+ ürün + miktar + fiyat otomatik dolar |
| 2 | AI yanlış müşteri eşler, mühendis düzeltir | Düzeltme kaydedilir, POST doğru CardCode ile gider |
| 3 | AI ürün kodu bulamaz | Alan boş kalır, mühendis dropdown'dan seçer |
| 4 | "SAP'a Gönder" basılır | Sales Order oluşur, DocNum gösterilir |
| 5 | Zorunlu alan boş | Gönder devre dışı, Türkçe uyarı |
| 6 | SAP bağlantısı yok | Türkçe bağlantı hatası, retry seçeneği |
| 7 | SAP POST başarısız | SAP hata detayı Türkçe gösterilir |
| 8 | E-posta inbox'tan otomatik çekildi | Pipeline'da "yeni" olarak görünür |
| 9 | Stok yetersiz uyarısı | Form'da kırmızı flag, alternatif öneri |
| 10 | İskonto eşik aşıldı | Müdür onayı istenir, operatör direkt yazamaz |

---

## 6. Fonksiyonel Gereksinimler

### 6.1 Doküman Alımı
| ID | Gereksinim | Öncelik | Faz |
|---|---|---|---|
| F01 | PDF yükleme (drag-drop + buton) | KRİTİK | MVP |
| F02 | E-posta inbox polling (IMAP/Graph) | KRİTİK | MVP |
| F03 | DOCX/XLSX yükleme | YÜKSEK | Faz 2 |
| F04 | Image OCR (jpg/png faks) | ORTA | Faz 2 |
| F05 | WhatsApp Business entegrasyonu | ORTA | Faz 2 |
| F06 | UBL/e-Fatura XML import | ORTA | Faz 2 |
| F07 | Web form (müşteri direkt giriş) | DÜŞÜK | Faz 3 |

### 6.2 AI İşleme
| ID | Gereksinim | Öncelik | Faz |
|---|---|---|---|
| F10 | PDF'den yapılandırılmış JSON çıkarma | KRİTİK | MVP |
| F11 | Müşteri/BP fuzzy eşleştirme | KRİTİK | MVP |
| F12 | Ürün/Item semantic eşleştirme | KRİTİK | MVP |
| F13 | Para birimi tespiti (TRY/EUR/USD) | KRİTİK | MVP |
| F14 | Tarih tespiti (DocDate, DocDueDate) | KRİTİK | MVP |
| F15 | Referans no (NumAtCard) tespiti | YÜKSEK | MVP |
| F16 | Stok availability sorgu | YÜKSEK | MVP |
| F17 | Fiyat doğrulama (liste vs PDF) | YÜKSEK | MVP |
| F18 | Alternatif ürün önerisi | ORTA | Faz 2 |
| F19 | Geçmiş tekliflerden RAG | ORTA | Faz 2 |
| F20 | Müşteri-özel ürün alias öğrenme | ORTA | Faz 2 |

### 6.3 Arayüz
| ID | Gereksinim | Öncelik | Faz |
|---|---|---|---|
| F30 | Kanban pipeline (5 sütun) | KRİTİK | MVP |
| F31 | AI alanları yeşil renkle işaretle | KRİTİK | MVP |
| F32 | Düşük güven alanları sarı | KRİTİK | MVP |
| F33 | Müşteri dropdown (canlı SAP) | KRİTİK | MVP |
| F34 | Ürün dropdown (canlı SAP) | KRİTİK | MVP |
| F35 | Satır ekle/sil | KRİTİK | MVP |
| F36 | Toplam otomatik hesap | KRİTİK | MVP |
| F37 | Side-by-side: PDF ↔ Form | YÜKSEK | MVP |
| F38 | Audit log timeline | YÜKSEK | MVP |
| F39 | Full-text arama | YÜKSEK | MVP |
| F40 | Bulk action | ORTA | Faz 2 |
| F41 | Mobil onay UI | ORTA | Faz 2 |
| F42 | Müşteri portalı (magic link) | ORTA | Faz 2 |

### 6.4 SAP Entegrasyonu
| ID | Gereksinim | Öncelik | Faz |
|---|---|---|---|
| F50 | Service Layer Login + session pool | KRİTİK | MVP |
| F51 | BusinessPartners GET (cache + canlı) | KRİTİK | MVP |
| F52 | Items GET (cache + canlı) | KRİTİK | MVP |
| F53 | Quotations POST | KRİTİK | MVP (mevcut) |
| F54 | Orders POST (Sales Order) | KRİTİK | MVP |
| F55 | ItemsService_GetItemAvailability | YÜKSEK | MVP |
| F56 | Idempotency + retry | KRİTİK | MVP |
| F57 | Türkçe hata çevirisi | YÜKSEK | MVP |
| F58 | DeliveryNotes POST | YÜKSEK | Faz 2 |
| F59 | Invoices POST | YÜKSEK | Faz 2 |
| F60 | PurchaseOrders POST | ORTA | Faz 2 |
| F61 | StockTransfers POST | ORTA | Faz 3 |
| F62 | ProductionOrders POST | ORTA | Faz 3 |
| F63 | $batch toplu işlem | ORTA | Faz 2 |
| F64 | B1if webhook (reverse sync) | ORTA | Faz 3 |

### 6.5 İş Akışı / Onay
| ID | Gereksinim | Öncelik | Faz |
|---|---|---|---|
| F70 | Tek seviyeli onay (operator → manager) | KRİTİK | MVP |
| F71 | İskonto/tutar eşik kuralları | KRİTİK | MVP |
| F72 | Çok aşamalı approval chain | YÜKSEK | Faz 2 |
| F73 | SLA timer + eskalasyon | ORTA | Faz 2 |
| F74 | Delegation (izindeki onaycı) | DÜŞÜK | Faz 3 |

### 6.6 Operasyon & Yönetim
| ID | Gereksinim | Öncelik | Faz |
|---|---|---|---|
| F80 | RBAC (3 rol) | KRİTİK | MVP |
| F81 | SSO (Azure AD) | YÜKSEK | Faz 2 |
| F82 | Audit log (append-only) | KRİTİK | MVP |
| F83 | Analitik dashboard | YÜKSEK | Faz 2 |
| F84 | Prompt/eşleşme kural editörü | ORTA | Faz 2 |
| F85 | Multi-tenant | YÜKSEK | Faz 3 |
| F86 | Tenant onboarding wizard | ORTA | Faz 3 |
| F87 | Billing entegrasyonu | ORTA | Faz 3 |

---

## 7. Fonksiyonel Olmayan Gereksinimler

### 7.1 Güvenlik
- SAP credential **Vault/Key Vault**'ta, koda asla yazılmaz.
- `.env` `.gitignore`'a girer, repo'ya gitmez.
- mTLS tunnel: SAP Connector ↔ Cloud.
- Audit log **append-only** (Postgres + WORM S3 backup).
- KVKK: PII envanteri, veri saklama süresi, silme talebi prosedürü.
- LLM çağrıları: model + prompt hash + response + token + maliyet immutable kayıt.
- Multi-tenant: row-level security + tenant başı şifreleme anahtarı.

### 7.2 Performans
- PDF analizi (AI dahil): **≤ 15 sn**
- Dropdown yüklemesi (BP/Item): **≤ 5 sn** (cache hit < 1 sn)
- SAP POST yanıt süresi: **≤ 10 sn**
- Pipeline ekran açılış: **≤ 2 sn**
- Eş zamanlı kullanıcı (MVP): **20 user**
- Eş zamanlı kullanıcı (Faz 3): **500+ user (multi-tenant)**

### 7.3 Kullanılabilirlik
- Arayüz SAP B1 formuna benzer yapıda (alışkanlık korunsun).
- AI doldurduğu alanlar **yeşil**, düşük güven **sarı**, boş **beyaz**.
- Tüm hata mesajları **Türkçe ve aksiyon önerili** ("Müşteri bulunamadı → yeni cari oluştur" gibi).
- Klavye kısayolları (Tab navigation, Enter submit).
- Mobile-responsive (onaycılar için).

### 7.4 Gözlemlenebilirlik
- Tüm agent çağrıları **OpenTelemetry trace**.
- LLM token kullanımı + maliyet dashboard.
- SAP API hata oranı + latency metric.
- "No-touch ratio" KPI (otomatik geçen / toplam).
- Sentry/Datadog entegrasyonu.

### 7.5 Güvenilirlik
- API uptime hedefi: **%99.5**
- Disaster recovery: günlük Postgres backup + S3, RPO 24sa / RTO 4sa.
- SAP Connector kapalıyken: kuyruğa alınır, retry on reconnect.

---

## 8. Teknik Yığın (Stack)

| Katman | Teknoloji | Gerekçe |
|---|---|---|
| Frontend | **Next.js 14 App Router** + TypeScript + TailwindCSS + shadcn/ui | SSR + müşteri portalı + dashboard tek codebase |
| State (FE) | TanStack Query + Zustand | Server state + client state ayrımı |
| Backend | **FastAPI** (Python 3.12) | AI ekosistemi (OpenAI SDK, pdfplumber, pgvector) olgun |
| ORM | SQLAlchemy 2.x + Alembic | Migration standart |
| DB | **Postgres 16 + pgvector** | İlişkisel + embedding |
| Cache/Queue | **Redis 7** | Session + Celery broker + idempotency |
| Job runner | **Celery** | OCR/AI long-running task |
| AI | OpenAI SDK → **OpenRouter** (Claude Sonnet/Opus/Haiku, GPT, Gemini) | Tek API, multi-model, multi-tier maliyet/latency |
| PDF | pdfplumber + pypdf + pdf2image (OCR fallback) | Metin + tablo + görsel |
| OCR | Tesseract + Claude vision fallback | Image PDF'ler için |
| Auth | NextAuth.js (FE) + JWT (API) | SSO genişletilebilir |
| Secrets | HashiCorp Vault / Doppler / Azure Key Vault | Production secret yönetimi |
| Observability | OpenTelemetry + Sentry + Prometheus | Trace + error + metric |
| Container | Docker + Docker Compose | Local + on-prem deploy |
| CI/CD | GitHub Actions | Lint + test + build + deploy |

---

## 9. Veri Modeli (Yüksek Seviye)

### 9.1 Ana Entity'ler
```
Tenant (faz 3) ── Users ── Roles
                    │
                    ▼
Document ── DocumentVersion ── ExtractedData (JSONB)
   │
   ├── DocumentEvents (audit timeline)
   ├── LLMCalls (model, prompt hash, tokens, cost)
   └── SAPSubmissions (DocEntry, DocNum, status, retry log)

BPCache (SAP BusinessPartners snapshot)
ItemCache (SAP Items snapshot + embedding)
CustomerAlias (öğrenilmiş ad/ürün eşleşmeleri)
ApprovalRule (eşik, kim onaylar)
ApprovalRequest (pending/approved/rejected)

AgentRun (orchestrator session)
  ├── AgentStep (her agent çağrısı)
  └── ToolCall (her tool kullanımı)
```

### 9.2 Önemli Tablolar (özet)
- `documents` — yüklenen/alınan tüm belgeler
- `extracted_data` — AI çıkarımı (JSONB, schema validated)
- `bp_cache`, `item_cache` — SAP master data lokal kopya
- `item_embeddings` — pgvector (ürün semantic search)
- `customer_alias` — öğrenilen eşleşmeler (RAG için)
- `sap_submissions` — her SAP POST denemesi
- `agent_runs`, `agent_steps`, `tool_calls` — multi-agent audit
- `llm_calls` — maliyet ve audit
- `approval_requests`, `approval_rules`
- `users`, `roles`, `audit_log`

---

## 10. SAP B1 Service Layer Entegrasyonu

### 10.1 Bağlantı
- Base: `https://{HOST}:50000/b1s/v1/`
- Login: `POST /Login` body `{CompanyDB, UserName, Password}` → `B1SESSION` + `ROUTEID` cookies
- Session TTL: 30 dk (her istekle yenilenir)
- Lisans bazlı session slot (default 4). **Session pool gerekli.**

### 10.2 Kullanılan/Kullanılacak Endpoint'ler

| Modül | Endpoint | Faz |
|---|---|---|
| Auth | `/Login`, `/Logout` | MVP |
| Master | `/BusinessPartners` | MVP |
| Master | `/Items` | MVP |
| Master | `/SBOCurrencies`, `/PaymentTermsTypes` | MVP |
| **Satış** | **`/Quotations`** | MVP (mevcut) |
| **Satış** | **`/Orders`** | **MVP (yeni)** |
| Stok | `/ItemsService_GetItemAvailability` | MVP |
| Sorgu | `/SQLQueries('id')/List` | MVP |
| Lojistik | `/DeliveryNotes` | Faz 2 |
| Muhasebe | `/Invoices`, `/IncomingPayments` | Faz 2 |
| Satınalma | `/PurchaseOrders`, `/PurchaseQuotations`, `/PurchaseRequests` | Faz 2 |
| Stok | `/StockTransfers`, `/InventoryGenEntries`, `/InventoryGenExits` | Faz 3 |
| Üretim | `/ProductionOrders`, `/ProductTrees` | Faz 3 |
| Servis | `/ServiceCalls` | Faz 3 |
| Toplu | `/$batch` | Faz 2 |
| Event | B1if HTTP push | Faz 3 |

### 10.3 OData Parametreleri (kullanılacak)
`$filter`, `$select`, `$expand`, `$orderby`, `$top`, `$skip`, `Prefer: odata.maxpagesize=N`

### 10.4 Hata Yönetimi
| Kod | Anlam | Aksiyon |
|---|---|---|
| 400 (-10/-2028) | Validation/iş kuralı | Türkçe açıklama + form'a flag |
| 401 | Session expired | Re-login, retry |
| 403 | Lisans/yetki | Admin'e bildirim |
| 404 | DocEntry yok | Kullanıcıya "kayıt silinmiş" mesajı |
| 405 | Yöntem desteklenmiyor (örn. Invoice DELETE) | Alternatif öner (CreditNote) |
| 409 | Concurrency | Re-fetch + merge önerisi |
| 500 (-5002) | DB constraint / UDF | Admin paneline log |

---

## 11. Modüler Genişleme — Klasör Yapısı

Her modül kendi klasöründe, MVP'de **boş placeholder** olarak duruyor; entegrasyon vakti gelince hızlıca dolacak.

```
backend/app/sap/modules/
  quotations.py           ← MVP (mevcut, port)
  sales_orders.py         ← MVP (yeni, ana odak)
  business_partners.py    ← MVP
  items.py                ← MVP
  delivery_notes.py       ← Faz 2 (boş + docstring TODO)
  invoices.py             ← Faz 2 (boş)
  payments.py             ← Faz 2 (boş)
  purchase_orders.py      ← Faz 2 (boş)
  purchase_requests.py    ← Faz 2 (boş)
  inventory.py            ← Faz 3 (boş)
  stock_transfers.py      ← Faz 3 (boş)
  production_orders.py    ← Faz 3 (boş)
  product_trees.py        ← Faz 3 (boş)
  service_calls.py        ← Faz 3 (boş)
  opportunities.py        ← Faz 3 (boş)
```

Her modülün karşılığında `docs/modules/<modul>.md` planı vardır.

---

## 12. Geliştirme Yol Haritası

### Faz 1 — MVP (4-6 hafta)
- Repo iskeleti + Docker Compose
- SAP Connector (Service Layer wrapper, session pool, retry)
- Multi-agent orchestrator + DocReader/CustomerMatcher/ProductMatcher/Pricing/Stock/SAPWriter agentları
- Web UI: Pipeline, Form, Login, Settings (basit)
- Quotation POST + Sales Order POST
- E-posta inbox polling (tek hesap, IMAP)
- Audit log + LLM cost tracking
- RBAC (3 rol)
- Pilot müşteride 50 belge/gün hedef

### Faz 2 — Pro (2-3 ay sonra)
- Multi-format (DOCX, XLSX, image OCR, UBL/e-Fatura XML)
- Delivery Notes + Invoices modülleri
- Çok aşamalı approval chain + SLA + eskalasyon
- Müşteri portalı (magic link)
- WhatsApp Business
- Analitik dashboard
- Prompt/eşleşme kuralları yönetim UI (no-code)
- SaaS multi-tenant altyapı
- Vault entegrasyonu

### Faz 3 — Platform (6-12 ay sonra)
- Purchase + Production + Inventory modülleri
- Reverse sync (B1if webhook + polling)
- Marketplace (sektör özel template'ler)
- Public API + webhook
- SOC2/ISO27001 hazırlığı
- EDI partner network
- Mobil onay app

---

## 13. Riskler ve Azaltma

| Risk | Seviye | Azaltma |
|---|---|---|
| AI yanlış müşteri/ürün eşler | YÜKSEK | Human-in-the-loop zorunlu + confidence threshold + alias öğrenme |
| Farklı PDF formatları | YÜKSEK | Vision + text fallback, esnek prompt, az şablon-bağımlı |
| SAP session timeout | ORTA | Connection pool + auto re-login |
| SAP POST hata | ORTA | Türkçe çeviri + retry + manuel kuyruk |
| Performans (büyük PDF) | ORTA | Sayfa segmentasyonu, parallel chunk |
| LLM maliyeti | DÜŞÜK | Multi-tier model (Haiku→Sonnet→Opus), cache, prompt caching |
| KVKK uyumluluk | YÜKSEK | TR data center opsiyonu + PII tokenization + denetim izi |
| Müşteri lisans yetersiz (B1) | ORTA | Session pool + named user önerisi |
| Network/VPN sorunu (on-prem) | ORTA | mTLS tunnel + reconnect + queue |

---

## 14. Başarı Kriterleri (KPI)

| Metrik | Hedef (3 ay) | Hedef (12 ay) |
|---|---|---|
| Belge başı ortalama süre | 5-10 dk | 2-5 dk |
| No-touch oranı | %30 | %60 |
| SAP yazım hata oranı | < %2 | < %0.5 |
| Müşteri sayısı | 3-5 pilot | 50+ aktif |
| Aylık tekrarlı gelir | ₺150K | ₺3M+ |
| Kullanıcı memnuniyeti (NPS) | 30+ | 50+ |

---

## 15. Teslim Çıktıları (Faz 1 MVP)

1. Çalışan web uygulaması (Next.js + FastAPI + Postgres + Redis + Celery)
2. SAP Connector (on-prem servis)
3. Docker Compose ile tek komut deploy
4. `.env.example` (gerçek değer olmadan)
5. Kurulum + kullanıcı dökümanı (TR)
6. 5+ farklı gerçek PDF ile uçtan uca test sonuçları
7. Audit log + analitik mini dashboard
8. Bu sistem analizi dökümanı + tüm modül planları + task listesi

---

## 16. Ekler

- **`TASKS.md`** — tüm fazların task ayrımı, sprint planı
- **`modules/01-sales-orders.md`** — MVP ana modül planı
- **`modules/00-quotations.md`** — Mevcut MVP'nin taşınması
- **`modules/02-delivery-notes.md`** ... **`08-service.md`** — Sonraki modüller için placeholder + Service Layer detay
- **`README.md`** — proje root, kurulum komutları

---

**Bu doküman canlıdır.** Faz tamamlandıkça, gerçek müşteri geri bildirimi geldikçe revize edilir. Versiyon kontrolü `git tag` ile yapılır (`v1.0`, `v1.1` ...).
