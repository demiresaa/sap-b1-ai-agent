# CLAUDE.md — SAP B1 AI Agent Geliştirme Rehberi

> Bu dosya bu repo'da çalışan Claude (ve insan geliştirici) için **çalışma kuralları + hızlı navigasyon** rehberidir. Detaylı ürün/mimari için `docs/SISTEM_ANALIZI.md`, task ayrımı için `docs/TASKS.md`.

---

## 1. Proje Özeti

**Ne yapıyor:** Müşteriden gelen PDF/e-posta satış taleplerini multi-agent AI ile okuyup SAP B1 Service Layer üzerinden Quotation/Sales Order olarak yazan platform.

**MVP odağı:** Sales Order (`/Orders`). Mevcut Quotation (`/Quotations`) akışı korunuyor.

**Mimari özet:**
```
Next.js UI ↔ FastAPI ↔ Orchestrator + Specialist Agents ↔ Postgres/pgvector + Redis/Celery + OpenRouter
                                            ↓                                                  ↓
                                    SAP Connector                                   (Claude/GPT/Gemini)
                                            ↓ HTTPS:50000
                                       SAP B1 Service Layer
```

**LLM erişimi:** OpenRouter (OpenAI-uyumlu API). Model adı `.env`'den (`LLM_MODEL_DEFAULT`).
Varsayılan: `anthropic/claude-sonnet-4.5` · hard: `anthropic/claude-opus-4.1` · fast: `anthropic/claude-haiku-4.5`.

---

## 2. Dil ve İletişim Kuralları

- **Kod yorumları, docstring'ler, hata mesajları, UI metinleri: Türkçe.** Müşteri ve geliştirici TR konuşuyor.
- **Değişken/fonksiyon/sınıf isimleri: İngilizce** (kod okunabilirliği, SAP API alan adlarıyla uyum için).
- Kullanıcıya cevap: **Türkçe**, kısa, doğrudan.
- Commit mesajları: İngilizce, conventional commits (`feat:`, `fix:`, `chore:`...).

---

## 3. Dizin Haritası

```
backend/app/
  main.py                  ← FastAPI entry
  core/config.py           ← Pydantic settings, .env okur
  sap/
    client.py              ← Service Layer HTTP client (httpx async)
    session.py             ← Session pool (lisans bazlı semaphore)
    errors.py              ← SAP error kodu → TR mesaj
    modules/
      sales_orders.py      ← MVP ANA — /Orders POST/GET
      quotations.py        ← MVP — /Quotations POST/GET
      business_partners.py ← MVP — /BusinessPartners GET + search
      items.py             ← MVP — /Items GET + search
      delivery_notes.py    ← Faz 2 stub
      invoices.py          ← Faz 2 stub
      payments.py          ← Faz 2 stub
      purchase_orders.py   ← Faz 2 stub
      inventory.py         ← Faz 3 stub
      production_orders.py ← Faz 3 stub
      opportunities.py     ← Faz 3 stub
      service_calls.py     ← Faz 3 stub
  agents/
    base.py                ← BaseAgent abstract
    orchestrator.py        ← State machine, dispatch
    document_reader.py     ← PDF → JSON (Claude vision)
    customer_matcher.py    ← BP eşleştirme
    product_matcher.py     ← Item eşleştirme (pgvector)
    pricing.py             ← Fiyat/iskonto doğrulama
    stock.py               ← Availability sorgu
    sap_writer.py          ← Idempotent POST + retry
    approval.py            ← Eşik kontrolü
    notification.py        ← E-posta/Teams bildirim
  api/routes/              ← FastAPI endpoint dosyaları
  db/                      ← SQLAlchemy modelleri + Alembic
  workers/                 ← Celery task'ları
  schemas/                 ← Pydantic request/response modelleri
  services/                ← Business logic katmanı

frontend/
  app/(dashboard)/         ← pipeline, orders, quotes, settings
  app/(portal)/[token]/    ← müşteri portalı (Faz 2)
  lib/api.ts               ← backend client

docs/
  SISTEM_ANALIZI.md        ← Detaylı sistem analizi (16 bölüm)
  TASKS.md                 ← Tüm fazların task ayrımı
  modules/00-09            ← Her SAP modülü için ayrı plan
```

---

## 4. Komutlar

### Backend (Python 3.12+)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Geliştirme sunucusu
uvicorn app.main:app --reload --port 8000

# Test
pytest                          # tüm testler
pytest tests/sap/ -v            # sadece SAP wrapper
pytest --cov=app --cov-report=term-missing

# Lint + format
ruff check app tests
ruff format app tests
mypy app

# Alembic
alembic revision --autogenerate -m "açıklama"
alembic upgrade head
```

### Frontend (Node 20+)
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev      # http://localhost:3000
npm run build
npm run lint
npm run type-check
```

### Docker (full stack)
```bash
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml logs -f backend
```

---

## 5. Geliştirme Kuralları

### 5.1 Genel
- **YAGNI:** İhtiyaç olmayan abstraction, fallback, "future-proof" katman ekleme. MVP scope dışı şeyler stub olarak kalır.
- **Stub dosyalar:** `delivery_notes.py`, `invoices.py` vb. modüller MVP'de **boş + docstring + TODO** olarak duruyor — silme, dolduracağımız iskelet.
- **Comment yok varsayılan:** Sadece WHY non-obvious ise comment. Türkçe docstring kısa ve öz olsun.
- **Type hints zorunlu** (Python 3.12 modern syntax: `list[str]`, `dict[str, Any]`, `|` union).

### 5.2 SAP Service Layer Entegrasyonu
- **Her SAP modülü kendi dosyasında**, `client: SAPServiceLayerClient` constructor parametresi alır.
- POST'lar **idempotent** olmalı (UUID + Redis kontrolü, `sap/idempotency.py`).
- 401 → otomatik re-login + retry (`client._request` içinde mevcut).
- Hata mesajları `sap/errors.py` üzerinden TR'ye çevrilir. SAP raw error asla kullanıcıya gösterilmez.
- Session pool semaphore'undan geçer — direkt `SAPServiceLayerClient()` yerine `pool.acquire()` kullan.

### 5.3 Multi-Agent
- Tüm agent'lar `BaseAgent` extend eder.
- Her agent çağrısı `agent_runs` + `agent_steps` tablosuna yazılır.
- LLM çağrıları `llm_calls` tablosuna yazılır (model, prompt hash, tokens, cost).
- LLM router: **OpenRouter** (OpenAI SDK + `https://openrouter.ai/api/v1`). Tek API üzerinden Claude/GPT/Gemini.
- Tier: default=Sonnet 4.5, fast=Haiku 4.5 (ucuz/hızlı), hard=Opus 4.1 (karmaşık eskalasyon).

### 5.4 Human-in-the-Loop
Aşağıdaki durumlarda otomatik SAP POST **yapılmaz**, onay zorunlu:
- Müşteri/Ürün eşleşme confidence < 0.85
- İskonto > %15 veya tutar > config eşik
- Stok yetersizliği
- Yeni BP/Item yaratma talebi (sadece öneri sunulur, auto-create YOK)

### 5.5 Güvenlik
- SAP credential, anthropic key vb. **asla** repo'ya commit edilmez (`.env` `.gitignore`'da).
- Audit log append-only — UPDATE/DELETE yok.
- LLM call kayıtları immutable.
- PII (cari adı, vergi no) log'larda maskelenir.

---

## 6. Test Stratejisi

| Tip | Konum | Araç | Hedef coverage |
|---|---|---|---|
| Unit (SAP wrapper) | `backend/tests/sap/` | pytest + respx | %85+ |
| Unit (agents) | `backend/tests/agents/` | pytest + mock Anthropic | %70+ |
| Integration | `backend/tests/integration/` | pytest + gerçek B1 DEMO | smoke |
| API contract | `backend/tests/api/` | pytest + httpx TestClient | %80+ |
| E2E | `frontend/tests/e2e/` | Playwright | 5 senaryo |
| Load | `backend/tests/load/` | locust | 50 eş zamanlı |

---

## 7. Risk Noktaları (sürekli akılda tut)

1. **SAP session pool tükenmesi** — `sap_max_concurrent_sessions` config, semaphore zorunlu.
2. **PDF format çeşitliliği** — pdfplumber boş dönerse vision fallback (Claude image input).
3. **Idempotency** — aynı PDF iki kez işlenebilir, UUID + file hash zorunlu.
4. **AI maliyeti** — prompt caching, Haiku önce, Opus sadece eskalasyonda.
5. **Türkçe karakter / encoding** — her HTTP istek `utf-8`, DB collation `tr_TR.UTF-8`.
6. **SAP lisans tipi** — Indirect Access uyumu; SAP Writer'da kullanıcı temsili dikkat.

---

## 8. Çalışma Akışı (Claude için)

Bir task'a başlarken:
1. `docs/TASKS.md`'de ilgili epic'i bul, sahip ol.
2. Varsa `docs/modules/<modul>.md` planını oku.
3. Mevcut stub/iskeleti oku (silme, doldur).
4. Type hints + Türkçe docstring + minimal yorum yaz.
5. Unit test ekle (`tests/`).
6. `ruff check && pytest` yeşil olduğunda task'ı kapat.

Kod yaparken **mevcut dosyaları düzenle**, yeni dosya açmaktan kaçın (modül zaten varsa).

UI değişikliği yaptıysan `npm run dev` çalıştırıp tarayıcıda kontrol et — type check yetmez.

---

## 9. Hızlı Referans

- **Sistem analizi:** `docs/SISTEM_ANALIZI.md`
- **Task listesi:** `docs/TASKS.md`
- **Modül planları:** `docs/modules/01-sales-orders.md` (MVP ana)
- **Stack:** FastAPI + Next.js 14 + Postgres 16 (pgvector) + Redis + Celery + OpenAI SDK → OpenRouter
- **Modeller (OpenRouter):** `anthropic/claude-sonnet-4.5` (default), `anthropic/claude-opus-4.1` (hard), `anthropic/claude-haiku-4.5` (fast). `.env` ile değiştirilebilir (örn. `openai/gpt-4o`, `google/gemini-pro-1.5`).
- **Service Layer base:** `https://{HOST}:50000/b1s/v1/`
