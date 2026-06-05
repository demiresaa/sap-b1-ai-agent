# Sistem Nasıl Çalışıyor?

> End-to-end akış, bileşenler ve sorumluluk sınırları.

---

## 1. Genel Bakış

Müşteriden gelen PDF / e-posta / Excel siparişini alıp SAP B1'e Quotation veya Sales Order olarak yazan bir **multi-agent AI platformu**.

```
Müşteri Belgesi (PDF/Excel/E-posta)
         │
         ▼
   [Upload API]  ──→  S3/MinIO (dosya depolama)
         │
         ▼
   [Celery Task]
         │
   ┌─────▼──────────────────────────────────────┐
   │          Orchestrator (State Machine)       │
   │                                             │
   │  DocumentReader → CustomerMatcher           │
   │      → ProductMatcher → Pricing             │
   │          → Stock → Approval                 │
   └─────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
 APPROVAL   READY
 (İnsan)  (Otomatik)
    │         │
    └────┬────┘
         │
   [Submit API]
         │
         ▼
   [SAPWriter] ──→ SAP B1 Service Layer
                        /Orders veya /Quotations
```

---

## 2. Katmanlar

### 2.1 Frontend — Next.js 14

```
/app/login/               → JWT login
/(dashboard)/pipeline/    → Belge kuyruğu (status listesi)
/(dashboard)/documents/[id]/ → Belge detayı + extraction editörü
/(dashboard)/approvals/   → Onay bekleyen işlemler
/(dashboard)/orders/      → Oluşturulan siparişler
/(dashboard)/quotes/      → Oluşturulan teklifler
/(dashboard)/settings/    → Ayarlar
/(portal)/[token]/        → Müşteri kabul/ret portalı (Faz 2)
```

**lib/api.ts** — Tüm backend istekleri buradan geçer:
- Bearer token + `X-Tenant-Slug` header otomatik eklenir
- 401 → `/login` yönlendirmesi
- Refresh token mekanizması

### 2.2 Backend — FastAPI

7 router grubu:

| Router | Temel İş |
|---|---|
| `auth` | Login, refresh, /me |
| `documents` | Upload, process, submit, PDF üret |
| `sap` | BP/Item arama, stok sorgusu |
| `approvals` | Onay listesi, karar ver |
| `analytics` | KPI özeti (başarı oranı, LLM maliyet) |
| `admin` | Tenant yönetimi |
| `debug` | LLM test, config görüntüle (dev) |

### 2.3 Workers — Celery + Redis

İki tip background task:

- **process_document** — AI pipeline (ağır, async)
- **submit_document** — SAP'a POST (idempotent)
- **poll_imap_inbox** — E-posta kutusu tarama (5 dk'da bir, Beat)

`CELERY_ENABLED=false` iken her şey FastAPI `BackgroundTasks` ile aynı process'te çalışır — geliştirme için ideal.

### 2.4 Database — PostgreSQL + pgvector

```
documents          → Belge yaşam döngüsü (status machine)
extracted_data     → AI çıktısı (versioned JSON)
document_events    → Audit log (her status değişimi)
agent_runs         → Orchestrator session kaydı
agent_steps        → Her agent çağrısının kaydı
llm_calls          → LLM maliyeti + token takibi
approval_rules     → Eşik kuralları (JSONB DSL)
approval_requests  → Bekleyen/karar verilmiş onaylar
bp_cache           → SAP BusinessPartner snapshot
item_cache         → SAP Item snapshot
item_embeddings    → pgvector (semantik arama, Faz 2)
customer_alias     → Öğrenilen müşteri mapping'leri
users              → Kullanıcılar
tenants            → SaaS kiracılar (multi-tenant)
sap_submissions    → SAP POST denemeleri (idempotency)
```

### 2.5 SAP Bağlantısı

`SAPServiceLayerClient` (httpx async):
- `https://{HOST}:50000/b1s/v1/` base URL
- Login → `B1SESSION` + `ROUTEID` cookie
- 401 → otomatik re-login + tek retry
- 502/503/504 → exponential backoff
- Ham SAP hatası → Türkçe mesaja çevrilir, kullanıcıya gösterilmez

**Mevcut modüller:** `/BusinessPartners`, `/Items`, `/Orders`, `/Quotations`

---

## 3. Belge Akışı (Adım Adım)

### Adım 1 — Upload
```
POST /api/v1/documents/upload
```
1. Dosya hash'i hesaplanır → duplicate kontrolü
2. S3/MinIO'ya yüklenir
3. `documents` tablosuna `RECEIVED` statüsünde kayıt
4. `enqueue_process_document(doc_id)` → Celery kuyruğuna

---

### Adım 2 — AI Pipeline (Orchestrator)

Her adım `agent_steps` tablosuna yazılır.

#### DocumentReader
- PDF → `pdfplumber` ile metin çıkarma
- Metin < 50 karakter → görsel olarak JPEG'e çevir → Claude vision
- LLM'e yapılandırılmış JSON şeması gönderilir
- Çıktı: `ExtractedDocument` (müşteri, satırlar, tarihler, para birimi)

#### CustomerMatcher
LLM yok, deterministik:
1. Vergi No tam eşleşmesi → `score: 1.0, strategy: "tax_id_exact"`
2. E-posta tam eşleşmesi → `score: 0.95`
3. `rapidfuzz.token_set_ratio` → `score: 0.0–1.0`
4. `CustomerAlias` tablosu (öğrenilmiş mapping)
- score < 0.85 → `needs_human = True` (manuel seçim)

#### ProductMatcher
1. Barkod tam eşleşmesi → `score: 1.0`
2. Item kodu eşleşmesi → `score: 1.0`
3. `rapidfuzz` açıklama fuzzy → `score: 0.0–1.0`
4. (Faz 2) pgvector semantik arama
- score < 0.85 → `needs_human = True`

#### Pricing
- Her satır için: `Δ% = (pdf_price - sap_price) / sap_price × 100`
- `discount_pct > %15` → `breaches_threshold = True`
- Eşik aşımı → Approval kuralı tetiklenir

#### Stock
- Sales Order: stok yetersizse `in_stock = False` → onay zorunlu
- Quotation: uyarı, bloklama yok

#### Approval
JSONB DSL kural motoru:
```json
{"any_of": [
  {"field": "total_amount",   "op": ">",  "value": 100000},
  {"field": "max_discount",   "op": ">",  "value": 15},
  {"field": "new_customer",   "op": "==", "value": true}
]}
```
- Kural eşleşirse → `ApprovalRequest` oluşturulur → `APPROVAL` statüsü

---

### Adım 3 — Human-in-the-Loop

**`READY`** statüsü: AI güvenlidir, operatör son kontrol yapar.  
**`APPROVAL`** statüsü: Manager onayı zorunlu.

Operatör:
- UI'da çıkarılan veriyi düzenler → `PATCH /documents/{id}`
- SAP önerilerinden doğru BP/Item seçer
- `extracted_data` tablosuna yeni versiyon kaydedilir

Manager:
- `POST /approvals/{id}/decision` → `APPROVED` veya `REJECTED`

---

### Adım 4 — SAP Submit
```
POST /api/v1/documents/{id}/submit
```
1. `SAPSubmission` kaydı oluşturulur (idempotency_key = UUID)
2. Redis'te key kontrolü — aynı belge iki kez submit edilemez
3. `SAPWriter`:
   - `sap_dry_run = True` → JSON payload üretilir, SAP'a gönderilmez
   - `sap_dry_run = False` → `/Orders` veya `/Quotations` POST
4. Başarı: `DocEntry` + `DocNum` kaydedilir, status → `SUBMITTED`

---

### Adım 5 — PDF & Portal (Faz 2)
```
POST /documents/{id}/generate-pdf  → Teklif PDF üretilir, S3'e yüklenir
GET  /documents/{id}/quotation.pdf → İndir
```
Müşteriye token'lı link gönderilir → `/(portal)/[token]/`  
Müşteri kabul → `POST /customer-accepted` → `CUSTOMER_ACCEPTED`

---

## 4. LLM Kullanımı

| Tier | Model | Ne zaman |
|---|---|---|
| **default** | `anthropic/claude-3.5-sonnet` | DocumentReader standart |
| **fast** | `anthropic/claude-3.5-haiku` | Basit sınıflandırma |
| **hard** | `anthropic/claude-3-opus` | Karmaşık belge eskalasyonu |

Tüm LLM çağrıları `llm_calls` tablosuna kaydedilir: model, token sayısı, maliyet, gecikme.  
OpenRouter kullanılır — tek API key ile Claude/GPT/Gemini geçişi yapılabilir.

---

## 5. Belge Statü Makinesi

```
RECEIVED
   │
READING (DocumentReader çalışıyor)
   │
MATCHING (CustomerMatcher + ProductMatcher)
   │
   ├──→ APPROVAL (onay eşiği aşıldı)
   │         │
   │    APPROVED / REJECTED
   │
READY (operatör inceliyor)
   │
SUBMITTING
   │
SUBMITTED ──→ PDF_GENERATED ──→ CUSTOMER_ACCEPTED
                                    CUSTOMER_REJECTED
ERROR (herhangi bir adımda)
```

---

## 6. Çalışan Servisler (Docker)

| Servis | Port | İş |
|---|---|---|
| backend | 8000 | FastAPI |
| frontend | 3000 | Next.js |
| worker | — | Celery |
| postgres | 5433 | Ana veritabanı |
| redis | 6380 | Broker + cache |
| vault | 8201 | Secret yönetimi |
| minio | 9002/9003 | Dosya depolama |

**Geliştirme ortamında SAP bağlantısı yok** — `SAP_DRY_RUN=true` ile tüm akış simüle edilir, SAP'a gerçek POST gönderilmez.

---

## 7. Güvenlik Notları

- SAP credential, API key → asla repoya commit edilmez (`.env` `.gitignore`'da)
- Vault entegrasyonu hazır (`vault_enabled=true` ile açılır)
- Audit log append-only (UPDATE/DELETE yok)
- PII (cari adı, vergi no) loglarda maskelenir
- Production'da `SAP_VERIFY_SSL=true` zorunlu

---

*Detaylı mimari: `docs/SISTEM_ANALIZI.md` · Task planı: `docs/TASKS.md`*
