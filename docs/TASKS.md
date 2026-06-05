# TASK LİSTESİ — SAP B1 AI Agent

Bu doküman, projenin tüm fazlarındaki çalışma kalemlerini sprint/epic mantığıyla listeler. MVP (Faz 1) detaylı, sonraki fazlar başlık seviyesinde verilmiştir.

**Format:** `[durum] EPIC.TASK — başlık (tahmini süre, sahip)`
Durumlar: `[ ]` yapılacak · `[~]` devam ediyor · `[x]` tamamlandı · `[!]` engel/risk

---

## DURUM ÖZETİ (Mayıs 2026)

**Faz 1 — MVP kod implementasyonu tamam.** Pilot sahasına götürülebilir.

| Epic | Durum | Not |
|---|---|---|
| EPIC 1 — Altyapı | 8/10 (80%) | git init + CI kullanıcı tarafı |
| EPIC 2 — SAP Wrapper | 14/15 (93%) | gerçek B1 DEMO testi pilot sahasında |
| EPIC 3 — DB Şema | 12/13 (92%) | seed script tamam |
| EPIC 4 — Agents | 14/15 (93%) | tool use pattern + OTEL trace Faz 2 |
| EPIC 5 — Doküman Alımı | 7/8 (88%) | Microsoft Graph Faz 2 |
| EPIC 6 — Backend API | 13/17 (76%) | audit timeline + websocket Faz 2 |
| EPIC 7 — Frontend UI | 15/18 (83%) | audit timeline + analytics chart Faz 2 |
| EPIC 8 — Onay | 5/5 (100%) | SMTP/Teams bildirim Faz 2 |
| EPIC 9 — Güvenlik | 7/8 (88%) | Vault entegrasyonu Faz 2 |
| EPIC 10 — Test/Pilot | 5/8 (63%) | gerçek SAP DEMO + UAT pilot sahasında |
| EPIC 11 — Observability | 6/6 (100%) | — |
| **TOPLAM** | **106/123 (86%)** | Kalan kısımlar pilot sahası gerektirir |

**Backend test:** 60/60 yeşil · **Frontend build:** 10 route temiz · **Toplam kod:** ~5000 satır

---

## FAZ 1 — MVP (4-6 hafta, Sales Order odaklı)

### EPIC 1 — Proje Altyapısı (Sprint 0, 3 gün)

- [x] 1.1 — Proje klasör iskeleti (backend, frontend, docs, docker, scripts)
- [x] 1.2 — Sistem analiz dökümanı + CLAUDE.md + KVKK envanter + Pilot kurulum
- [x] 1.3 — Task listesi (bu dosya)
- [ ] 1.4 — Git repo init + GitHub repo (kullanıcı yapacak)
- [x] 1.5 — `.gitignore`, `.env.example`, `README.md`
- [x] 1.6 — `docker-compose.yml`: postgres (pgvector), redis, backend, worker, frontend
- [ ] 1.7 — Pre-commit hooks (ruff, black, prettier, eslint)
- [ ] 1.8 — GitHub Actions: lint + test on PR
- [x] 1.9 — `pyproject.toml` (backend bağımlılıkları + dev + observability)
- [x] 1.10 — `package.json` (frontend bağımlılıkları + Playwright)

### EPIC 2 — SAP Service Layer Wrapper (Sprint 1, 5 gün)

- [x] 2.1 — `sap/client.py`: httpx async, base URL, retry, transient hata exp backoff
- [x] 2.2 — `sap/session.py`: Login/Logout, B1SESSION + ROUTEID cookie yönetimi
- [x] 2.3 — Session pool (lisans bazlı semaphore + idle reuse)
- [x] 2.4 — Auto re-login on 401 + bir kez retry
- [x] 2.5 — OData query builder ($filter, $select, $top, $skip, $orderby, $expand) + literal kaçışı
- [x] 2.6 — Hata mapping (SAP error kodu → TR mesaj sözlüğü, `SAPError` exception)
- [x] 2.7 — `sap/modules/business_partners.py`: list, get, search by name/tax_id/email
- [x] 2.8 — `sap/modules/items.py`: list, get, search by code/name/barcode, availability
- [x] 2.9 — `sap/modules/quotations.py`: create, get, list, cancel
- [x] 2.10 — `sap/modules/sales_orders.py`: create, create_from_quotation, get, list, update, cancel, close ← **MVP ana endpoint**
- [x] 2.11 — `sap/modules/items.py::availability` — ItemsService_GetItemAvailability wrapper
- [x] 2.12 — Stub dosyalar: delivery_notes, invoices, payments, purchase_orders, inventory, production_orders, service_calls, opportunities
- [x] 2.13 — Idempotency layer (UUID + hash, Redis store)
- [x] 2.14 — Birim test: respx ile contract test (23 test, %100 yeşil)
- [ ] 2.15 — Entegrasyon test: gerçek B1 DEMO sandbox

### EPIC 3 — Veritabanı Şeması (Sprint 1, 2 gün)

- [x] 3.1 — Alembic kurulumu (alembic.ini + env.py async)
- [x] 3.2 — `users`, `user_roles` modelleri
- [x] 3.3 — `documents`, `extracted_data` (JSONB)
- [x] 3.4 — `document_events` (audit timeline)
- [x] 3.5 — `bp_cache`, `item_cache` (SAP master data snapshot)
- [x] 3.6 — `item_embeddings` (pgvector, 1536 dim)
- [x] 3.7 — `customer_alias` (öğrenilen eşleşmeler)
- [x] 3.8 — `sap_submissions` (her POST denemesi, idempotency_key)
- [x] 3.9 — `agent_runs`, `agent_steps`
- [x] 3.10 — `llm_calls` (model, prompt hash, tokens, cost, latency)
- [x] 3.11 — `approval_rules`, `approval_requests`
- [x] 3.12 — `audit_log` (append-only trigger)
- [ ] 3.13 — Seed script: test kullanıcılar, demo verisi

### EPIC 4 — Multi-Agent Orchestrator (Sprint 2, 7 gün)

- [x] 4.1 — `agents/base.py`: BaseAgent abstract + duration_ms + log wrap
- [x] 4.2 — `agents/orchestrator.py`: 6 step state machine + agent run/step persistence
- [x] 4.3 — `agents/document_reader.py`: pdfplumber text + vision fallback (Claude)
- [x] 4.4 — `agents/customer_matcher.py`: tax_id + email + alias + rapidfuzz
- [x] 4.5 — `agents/product_matcher.py`: barcode + code + alias + fuzzy (pgvector Faz 2)
- [x] 4.6 — `agents/pricing.py`: fiyat sapma %5 + iskonto %15 eşik DSL
- [x] 4.7 — `agents/stock.py`: ItemsService_GetItemAvailability + deterministik
- [x] 4.8 — `agents/sap_writer.py`: idempotent POST (Redis cache) + Türkçe hata
- [x] 4.9 — `agents/approval.py`: JSONB kural DSL (any_of/all_of, total/discount/currency)
- [x] 4.10 — `agents/notification.py`: log kanalı (SMTP/Teams Sprint 4-5)
- [ ] 4.11 — Tool use pattern (Anthropic SDK tools parameter)
- [x] 4.12 — Agent runs persistence (her step DB'ye yazılıyor)
- [ ] 4.13 — OpenTelemetry trace
- [x] 4.14 — Birim test her agent için (10 test yeşil)
- [ ] 4.15 — End-to-end test: 5 farklı PDF → SAP DEMO

### EPIC 5 — Doküman Alımı (Sprint 2, 3 gün)

- [x] 5.1 — Upload endpoint (FastAPI multipart, 25 MB limit, MIME whitelist)
- [x] 5.2 — PDF text + tablo extraction (pdfplumber)
- [x] 5.3 — Vision fallback (Claude image input, ilk 3 sayfa, 150 DPI)
- [x] 5.4 — IMAP poller (Celery beat, interval config'ten)
- [ ] 5.5 — Microsoft Graph poller (alternatif, OAuth) — Faz 2
- [x] 5.6 — Attachment ayıklama + filter (PDF/DOCX/XLSX/PNG/JPG)
- [x] 5.7 — Duplicate detection (file hash + 409 Conflict)
- [x] 5.8 — Document status state machine (RECEIVED→READING→READY→SUBMITTING→SUBMITTED veya ERROR)

### EPIC 6 — Backend API (Sprint 3, 5 gün)

- [x] 6.1 — FastAPI app skeleton + middleware (CORS, exception handlers)
- [x] 6.2 — JWT auth + refresh token (`/api/auth/login`, `/refresh`, `/me`)
- [x] 6.3 — RBAC dependency (`require_roles(operator, manager, admin)`)
- [~] 6.4 — `POST /documents/upload` (route var, 501 — Sprint 2 implementation)
- [x] 6.5 — `GET /documents` (status filter + pagination)
- [x] 6.6 — `GET /documents/{id}` (detay + extracted_data)
- [~] 6.7 — `PATCH /documents/{id}` (route var, 501 — Sprint 3)
- [~] 6.8 — `POST /documents/{id}/process` (route var, 501 — Sprint 2)
- [~] 6.9 — `POST /documents/{id}/submit` (route var, 501 — Sprint 3)
- [x] 6.10 — `GET /sap/business-partners` (canlı Service Layer)
- [x] 6.11 — `GET /sap/items` (canlı Service Layer + search)
- [x] 6.12 — `GET /sap/items/{code}/availability`
- [x] 6.13 — `POST /approvals/{id}/decision` (manager/admin)
- [ ] 6.14 — `GET /audit/{document_id}` (timeline)
- [ ] 6.15 — `GET /analytics/summary` (no-touch %, throughput, error rate)
- [ ] 6.16 — WebSocket: real-time pipeline update
- [ ] 6.17 — OpenAPI dökümanı tamamla

### EPIC 7 — Frontend Web UI (Sprint 3-4, 8 gün)

- [x] 7.1 — Next.js 14 + TS + Tailwind + lucide-react
- [x] 7.2 — JWT auth (login → access/refresh, localStorage, axios interceptor)
- [x] 7.3 — Sidebar layout + AuthGuard wrap
- [x] 7.4 — Login sayfası (e-posta + şifre)
- [x] 7.5 — Pipeline (Kanban): 5 sütun + 10sn polling
- [x] 7.6 — Document Detail sayfası (form + AI durum + reprocess)
- [x] 7.7 — Form bileşeni: AI alanları yeşil (filled)/sarı (uncertain)/beyaz (empty)
- [x] 7.8 — Müşteri combobox (canlı SAP arama, ≥2 karakter)
- [x] 7.9 — Ürün combobox (canlı SAP arama, kod+isim+barkod)
- [x] 7.10 — Satır ekle/sil, anlık toplam hesaplama
- [x] 7.11 — "SAP'a Gönder" akışı (validation + loading + error message)
- [ ] 7.12 — Audit timeline component (`document_events` görüntüleyici)
- [x] 7.13 — Settings: hesap + e-posta/SAP placeholder
- [x] 7.14 — Onay paneli (manager): bekleyen approval requests + karar
- [ ] 7.15 — Analytics mini dashboard (kart bazlı KPI)
- [x] 7.16 — Türkçe lokalizasyon (tüm UI metni TR, lang="tr")
- [x] 7.17 — Responsive (md/lg breakpoint Pipeline + Form grid)
- [ ] 7.18 — Klavye kısayolları + accessibility

### EPIC 8 — İş Akışı / Onay (Sprint 4, 3 gün)

- [x] 8.1 — Approval rule engine (any_of/all_of DSL, 6 operatör)
- [x] 8.2 — Eşik aşıldığında otomatik ApprovalRequest + APPROVAL durumu
- [~] 8.3 — Onaycı bildirimi (log; SMTP/Teams Faz 2)
- [x] 8.4 — Onayla/reddet endpoint + manager UI
- [x] 8.5 — Red durumunda REJECTED durumu + sebep kaydı

### EPIC 9 — Güvenlik ve Uyum (Sprint 4-5, 3 gün)

- [x] 9.1 — `.env` yönetimi (Pydantic Settings + production validation)
- [ ] 9.2 — Secret rotation hook (Vault entegrasyonu Faz 2'de)
- [x] 9.3 — Audit log append-only constraint (Postgres trigger)
- [x] 9.4 — PII envanteri dökümanı (`docs/KVKK_PII_ENVANTERI.md`)
- [x] 9.5 — Data retention policy (config: docs 365, llm 730, audit 2555 gün)
- [x] 9.6 — User session timeout (JWT 60 dk access)
- [x] 9.7 — Rate limit (per-IP, ASGI middleware: auth 10/dk, genel 300/dk)
- [x] 9.8 — Input validation (Pydantic body + frontend type)

### EPIC 10 — Test ve Pilot Hazırlık (Sprint 5, 3 gün)

- [x] 10.1 — Birim test coverage > %70 (60 yeşil test, kritik path %85+)
- [ ] 10.2 — Entegrasyon test (gerçek SAP DEMO — pilot sahasında)
- [x] 10.3 — Load test (locust scenarios, 50 eş zamanlı user)
- [x] 10.4 — E2E test (Playwright smoke: login, redirect, hata)
- [ ] 10.5 — 5 farklı gerçek müşteri PDF'i ile UAT (pilot sahasında)
- [x] 10.6 — Pilot kurulum dökümanı (`docs/PILOT_KURULUM.md`)
- [ ] 10.7 — Kullanıcı eğitim videosu (TR, 10 dk) — pilot öncesi
- [x] 10.8 — Kurulum dökümanı + seed script (`backend/scripts/seed.py`)

### EPIC 11 — Gözlemlenebilirlik (Sprint 5, 2 gün)

- [x] 11.1 — Sentry entegrasyonu (`init_sentry`, DSN config'ten)
- [x] 11.2 — OpenTelemetry trace → OTLP exporter (env DSN ile)
- [x] 11.3 — Prometheus metric (`/metrics`: documents, sap, llm cost, agent süresi)
- [x] 11.4 — Health check endpoint (`/health` + env bilgisi)
- [x] 11.5 — Structured JSON logging (`JsonFormatter`)
- [x] 11.6 — LLM maliyet endpoint (`GET /api/analytics/summary`)

---

## FAZ 2 — Pro (2-3 ay, MVP sonrası)

### Yüksek seviye epic'ler

- [ ] F2.1 — Delivery Notes modülü (sevkiyat, partial delivery)
- [ ] F2.2 — Invoices modülü (A/R fatura + e-fatura/UBL import)
- [ ] F2.3 — Incoming Payments modülü (tahsilat)
- [ ] F2.4 — Purchase Orders + Purchase Quotations modülü
- [ ] F2.5 — Multi-format ingestion (DOCX, XLSX, image OCR)
- [ ] F2.6 — Çok aşamalı approval chain + SLA + eskalasyon
- [ ] F2.7 — Müşteri portalı (magic link, kabul/red/revize)
- [ ] F2.8 — WhatsApp Business Cloud API entegrasyonu
- [ ] F2.9 — Analitik dashboard (Recharts, drill-down)
- [ ] F2.10 — No-code prompt/eşleşme kuralı editörü
- [ ] F2.11 — SaaS multi-tenant altyapı (şema-per-tenant)
- [ ] F2.12 — Tenant onboarding wizard
- [ ] F2.13 — HashiCorp Vault / Azure Key Vault entegrasyonu
- [ ] F2.14 — SSO (Azure AD, Google Workspace, Okta)
- [ ] F2.15 — $batch toplu işlem desteği
- [ ] F2.16 — Geçmiş teklif RAG (pgvector + few-shot)
- [ ] F2.17 — Alias öğrenme (operatör düzeltmelerinden)
- [ ] F2.18 — Pricing rule editor (kampanya, müşteri-özel)

**Plan detayları:** `docs/modules/02-delivery-notes.md`, `03-invoices.md`, `04-purchasing.md`

---

## FAZ 3 — Platform (6-12 ay, SaaS + üretim/stok)

- [ ] F3.1 — Stock Transfers + Inventory Counting + Postings
- [ ] F3.2 — Production Orders + BOM (ProductTrees)
- [ ] F3.3 — Service Calls + Customer Equipment
- [ ] F3.4 — Sales Opportunities + Activities (CRM)
- [ ] F3.5 — Reverse sync: B1if webhook + polling fallback
- [ ] F3.6 — Marketplace / template store (sektör-özel matcher)
- [ ] F3.7 — Public API + webhook (3rd party entegrasyon)
- [ ] F3.8 — Mobil onay app (React Native)
- [ ] F3.9 — EDI partner network
- [ ] F3.10 — SOC2 Type II + ISO 27001 hazırlığı
- [ ] F3.11 — TR data center deploy (KVKK)
- [ ] F3.12 — White-label opsiyonu

**Plan detayları:** `docs/modules/05-inventory.md`, `06-production.md`, `07-crm.md`, `08-service.md`

---

## Sprint Takvimi (Önerilen)

| Sprint | Süre | Odak | Çıktı |
|---|---|---|---|
| Sprint 0 | 3 gün | Altyapı, repo, docker | Çalışır boş iskelet |
| Sprint 1 | 1 hafta | SAP wrapper + DB şema | Login + GET çalışıyor |
| Sprint 2 | 1.5 hafta | Multi-agent + ingestion | PDF → JSON çıkıyor |
| Sprint 3 | 1.5 hafta | Backend API + UI temel | Pipeline ekranı + upload |
| Sprint 4 | 1 hafta | Onay akışı + form düzenleme | E2E manuel akış |
| Sprint 5 | 4 gün | Test + pilot + observability | UAT geçti, pilot deploy |

**Toplam:** ~6 hafta MVP.

---

## Tanım Sözlüğü

- **No-touch ratio:** AI'ın hiç insan müdahalesi olmadan SAP'a yazdığı belge oranı
- **DocEntry:** SAP B1'de belgenin teknik PK'sı
- **DocNum:** Kullanıcının gördüğü belge numarası
- **B1SESSION:** Service Layer session cookie
- **ROUTEID:** Load-balanced kurulumda sticky session
- **BP:** Business Partner (müşteri veya tedarikçi)
- **BoM / ProductTrees:** Ürün ağacı (üretim reçetesi)
- **B1if:** SAP B1 Integration Framework (event push)
