# SAP B1 AI Agent

PDF ve e-postadan gelen satış taleplerini yapay zeka ile okuyup **SAP Business One Service Layer** üzerinden otomatik teklif/sipariş işleyen çoklu-ajan platformu.

> **Faz 1 (MVP) odağı:** Satış Siparişi (Sales Order) + mevcut Quotation akışı.
> **Modüler genişleme:** Delivery Notes, Invoices, Purchasing, Inventory, Production, CRM — kod yerleri ve plan dosyaları hazır, sıra geldiğinde aktive edilecek.

---

## Hızlı Başlangıç

```bash
# 1. Repo'yu klonla
git clone <repo-url> && cd sap-b1-ai-agent

# 2. .env dosyalarını hazırla
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# (içerikleri gerçek değerlerle doldur)

# 3. Docker Compose ile ayağa kaldır
docker compose -f docker/docker-compose.yml up -d

# 4. Frontend: http://localhost:3000
# 5. Backend API:  http://localhost:8000/docs
```

---

## Mimari (Özet)

```
[ Next.js Web UI ]  ⇄  [ FastAPI ]  ⇄  [ Multi-Agent Orchestrator ]
                                ↓                       ↓
                         [ Postgres + pgvector ]   [ OpenRouter API ]
                         [ Redis + Celery ]              ↓
                                ↓               [ SAP Connector ]
                                                        ↓
                                                [ SAP B1 Service Layer ]
```

Detay için **`docs/SISTEM_ANALIZI.md`**.

---

## Proje Yapısı

```
sap-b1-ai-agent/
├── docs/
│   ├── SISTEM_ANALIZI.md       ← detaylı sistem analizi (16 bölüm)
│   ├── TASKS.md                ← epic/sprint bazlı tüm tasklar
│   └── modules/                ← her SAP modülü için ayrı plan
│       ├── 00-quotations.md
│       ├── 01-sales-orders.md  ← MVP ANA
│       ├── 02-delivery-notes.md
│       ├── 03-invoices.md
│       ├── 04-purchasing.md
│       ├── 05-inventory.md
│       ├── 06-production.md
│       ├── 07-crm.md
│       ├── 08-service.md
│       └── 09-payments.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/               ← config, security
│   │   ├── agents/             ← multi-agent orchestrator + 8 specialist
│   │   ├── sap/                ← Service Layer wrapper
│   │   │   ├── client.py
│   │   │   ├── session.py      ← lisans bazlı pool
│   │   │   ├── errors.py       ← SAP error → TR
│   │   │   └── modules/        ← her SAP modülü ayrı dosya
│   │   ├── api/routes/         ← FastAPI endpoint'leri
│   │   ├── db/                 ← SQLAlchemy + Alembic
│   │   ├── workers/            ← Celery task'ları
│   │   ├── schemas/            ← Pydantic modeller
│   │   └── services/           ← business logic
│   └── tests/
├── frontend/
│   ├── app/
│   │   ├── (dashboard)/        ← pipeline, orders, quotes, settings
│   │   └── (portal)/[token]/   ← müşteri portalı (Faz 2)
│   ├── components/
│   └── lib/
├── docker/
│   └── docker-compose.yml
└── scripts/
```

---

## Geliştirme

### Backend (Python 3.12+)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend (Node 20+)

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

### Test

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm run lint && npm run type-check
```

---

## Yol Haritası (Özet)

| Faz | Süre | Kapsam |
|---|---|---|
| **Faz 1 — MVP** | 4-6 hafta | Sales Order + Quotation + e-posta inbox + pipeline |
| Faz 2 — Pro | 2-3 ay | Delivery + Invoice + Purchase + müşteri portalı + WhatsApp + multi-tenant |
| Faz 3 — Platform | 6-12 ay | Stok + Üretim + CRM + Service + marketplace + mobil |

Detay: `docs/TASKS.md`

---

## Dokümanlar

- **`docs/SISTEM_ANALIZI.md`** — kapsamlı sistem analizi (problem, mimari, gereksinim, roadmap)
- **`docs/TASKS.md`** — tüm task'lar ve sprint planı
- **`docs/modules/*.md`** — her SAP modülü için plan ve teknik detay

---

## Lisans

Proprietary — © 2026
