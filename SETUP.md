# SAP B1 AI Agent — Kurulum ve Geliştirme Kılavuzu

## İçindekiler

1. [Ön Koşullar](#1-ön-koşullar)
2. [Repo ve İlk Kurulum](#2-repo-ve-ilk-kurulum)
3. [Ortam Değişkenleri](#3-ortam-değişkenleri)
4. [Docker ile Altyapıyı Ayağa Kaldırma](#4-docker-ile-altyapıyı-ayağa-kaldırma)
5. [Veritabanı Migration](#5-veritabanı-migration)
6. [Uygulamayı Çalıştırma](#6-uygulamayı-çalıştırma)
7. [VS Code Entegrasyonu](#7-vs-code-entegrasyonu)
8. [Debug ve Breakpoint](#8-debug-ve-breakpoint)
9. [Servis Adresleri](#9-servis-adresleri)
10. [Testler](#10-testler)
11. [Sık Karşılaşılan Sorunlar](#11-sık-karşılaşılan-sorunlar)

---

## 1. Ön Koşullar

| Araç | Minimum Versiyon | Kontrol |
|---|---|---|
| Git | herhangi | `git --version` |
| Python | **3.12+** | `python3 --version` |
| Node.js | **20+** | `node --version` |
| Docker Desktop | **24+** | `docker --version` |
| VS Code | herhangi | — |

**macOS kurulumu (Homebrew):**

```bash
# Homebrew yoksa önce kur
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.12
brew install node@20
echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
brew install --cask docker
```

**Windows:** Docker Desktop, Python 3.12 (python.org), Node 20 (nodejs.org) kur. Komutları PowerShell veya WSL2 terminalinde çalıştır.

---

## 2. Repo ve İlk Kurulum

```bash
# Repoyu klonla
git clone <repo-url> sap-b1-ai-agent
cd sap-b1-ai-agent

# Branch'e geç
git checkout feat/sap-db-integration

# Otomatik kurulum — venv, npm install, .env kopyalama
bash scripts/setup.sh
```

Script şunları yapar:

- `backend/.env.example` → `backend/.env` kopyalar (dosya yoksa)
- `frontend/.env.example` → `frontend/.env` kopyalar (dosya yoksa)
- `backend/.venv` Python sanal ortamını oluşturur ve tüm paketleri kurar
- `frontend/node_modules` npm bağımlılıklarını kurar

---

## 3. Ortam Değişkenleri

### `backend/.env`

Script .env.example'ı kopyaladıktan sonra aşağıdaki alanları doldur:

```dotenv
# ── ZORUNLU ──────────────────────────────────────────────────────────

# Postgres — Docker 5433 portunda açıyor
DATABASE_URL=postgresql+asyncpg://sapai:sapai@localhost:5433/sapai

# Redis — Docker 6380 portunda açıyor
REDIS_URL=redis://localhost:6380/0

# OpenRouter API anahtarı — https://openrouter.ai → API Keys
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxx

# Uygulama güvenlik anahtarı (prod'da: openssl rand -hex 32)
APP_SECRET_KEY=dev-secret-change-in-production

# ── SAP B1 SERVICE LAYER ─────────────────────────────────────────────
# Gerçek sunucu yoksa boş bırak — SAP_DRY_RUN=true ile çalışır
SAP_SERVICE_LAYER_URL=https://192.168.x.x:50000/b1s/v1
SAP_COMPANY_DB=SBODemoTR
SAP_USERNAME=manager
SAP_PASSWORD=xxxxxx
SAP_VERIFY_SSL=false
SAP_DRY_RUN=true   # true: SAP'a yazma yapmaz, sadece JSON üretir

# ── OPSİYONEL ────────────────────────────────────────────────────────

APP_ENV=development
APP_BASE_URL=http://localhost:8000
CELERY_ENABLED=false   # false: arka plan görevleri aynı process'te çalışır

# MinIO (Docker'da hazır)
STORAGE_BACKEND=minio
S3_ENDPOINT_URL=http://localhost:9002
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=sapb1-agent

# Vault (dev'de devre dışı bırakılabilir)
VAULT_ENABLED=false
VAULT_ADDR=http://localhost:8201
VAULT_TOKEN=dev-token

# Aşağıdakiler varsayılan olarak kapalı — ihtiyaç olunca aç
MS_GRAPH_ENABLED=false
EINVOICE_ENABLED=false
OIDC_ENABLED=false
```

> **Not:** `SAP_DRY_RUN=true` ile SAP sunucusuna erişim olmadan tüm sistemi test edebilirsin. Yazma işlemleri JSON çıktısı üretir ama SAP'a POST atmaz.

### `frontend/.env`

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 4. Docker ile Altyapıyı Ayağa Kaldırma

Geliştirme ortamında sadece **veri servisleri** Docker'da, backend ve frontend **lokal** çalışır. Bu sayede VS Code debug tam çalışır.

```bash
# Sadece altyapı servislerini başlat
docker compose -f docker/docker-compose.yml up -d postgres redis vault minio

# Servislerin durumunu kontrol et
docker compose -f docker/docker-compose.yml ps
```

| Servis | İç Port | Dışarıya Açılan Port | Açıklama |
|---|---|---|---|
| PostgreSQL 16 + pgvector | 5432 | **5433** | Ana veritabanı |
| Redis 7 | 6379 | **6380** | Cache + Celery kuyruğu |
| HashiCorp Vault | 8200 | **8201** | Secret yönetimi |
| MinIO | 9000 / 9001 | **9002 / 9003** | Dosya depolama |

Standart portlar yerine üsteki numaraların kullanılması, makinanda çalışan başka bir Postgres/Redis ile çakışmayı önler.

```bash
# Logları izle
docker compose -f docker/docker-compose.yml logs -f postgres
docker compose -f docker/docker-compose.yml logs -f redis

# Servisleri durdur (veri kaybolmaz)
docker compose -f docker/docker-compose.yml stop

# Servisleri ve verileri tamamen sil
docker compose -f docker/docker-compose.yml down -v
```

---

## 5. Veritabanı Migration

Altyapı ayaktayken **bir kez** çalıştırılır. Yeni migration eklenince tekrar çalıştırılır.

```bash
cd backend
source .venv/bin/activate

alembic upgrade head
```

Başarılı çıktı:

```
INFO  [alembic] Running upgrade  -> 0001_initial
INFO  [alembic] Running upgrade 0001 -> 0002_tenants_and_user_clerk
...
INFO  [alembic] Running upgrade 0010 -> 0011_approval_tables
```

**Yeni migration oluştururken:**

```bash
alembic revision --autogenerate -m "aciklama"
alembic upgrade head
```

---

## 6. Uygulamayı Çalıştırma

### Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Çalışıyor mu kontrol et:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"sap-b1-ai-agent",...}
```

Swagger UI: `http://localhost:8000/docs`

### Frontend

Yeni bir terminal aç:

```bash
cd frontend
npm run dev
```

Uygulama: `http://localhost:3000`

### İlk Kullanıcıyı Oluştur

Migration'dan sonra admin kullanıcısı yoktur. Aşağıdaki script ile oluştur:

```bash
cd backend && source .venv/bin/activate

python3 - <<'EOF'
import asyncio
from app.db.session import SessionFactory
from app.db.models.user import User, UserRole, UserRoleAssignment
from app.core.security import hash_password
from app.db.base import new_uuid, utcnow

async def main():
    async with SessionFactory() as db:
        now = utcnow()
        user = User(
            id=new_uuid(), email="admin@firma.com",
            hashed_password=hash_password("Admin1234!"),
            full_name="Admin", is_active=True,
            created_at=now, updated_at=now,
        )
        db.add(user)
        await db.flush()
        db.add(UserRoleAssignment(
            id=new_uuid(), user_id=user.id, role=UserRole.ADMIN,
            created_at=now, updated_at=now,
        ))
        await db.commit()
        print("Admin oluşturuldu:", user.email)

asyncio.run(main())
EOF
```

Login testi:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@firma.com","password":"Admin1234!"}'
```

### (Opsiyonel) Celery Worker

Belge işleme, email polling, SLA kontrolü gibi arka plan görevleri için:

```bash
cd backend && source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info
```

> `CELERY_ENABLED=false` iken bu gerekmez — görevler FastAPI BackgroundTasks ile aynı process'te çalışır.

---

## 7. VS Code Entegrasyonu

Repo `.vscode/` dizininde hazır konfigürasyon içeriyor. Ekstra ayar gerekmez.

### Eklentileri Kur

`Ctrl+Shift+P` → **Extensions: Show Recommended Extensions** → hepsini kur.

| Eklenti | Amaç |
|---|---|
| Python (ms-python.python) | Dil desteği, IntelliSense |
| Black Formatter | Python otomatik biçimlendirme |
| Ruff (charliermarsh.ruff) | Python linter |
| Prettier | TypeScript / JSX biçimlendirme |
| ESLint | JS/TS lint |
| Tailwind CSS IntelliSense | CSS class önerileri |
| Docker | Container görselleştirme |

### Python Interpreter Seç

`Ctrl+Shift+P` → **Python: Select Interpreter** → `./backend/.venv/bin/python` seç.

`settings.json` bunu otomatik ayarlıyor ama ilk açılışta onay isteyebilir.

### Workspace Kökünü Aç

Repo kökünü (`sap-b1-ai-agent/`) workspace olarak aç. Alt dizinleri (`backend/` veya `frontend/`) ayrı pencerede açma — `.vscode/` ayarları sadece kökten çalışır.

### Mevcut VS Code Task'ları

`Ctrl+Shift+P` → **Tasks: Run Task** ile erişilir:

| Task | Açıklama |
|---|---|
| `infra: up (data services)` | Postgres + Redis + Vault + MinIO başlatır |
| `infra: up (postgres+redis)` | Sadece Postgres + Redis (minimal) |
| `infra: down` | Tüm Docker servislerini durdurur |
| `backend: alembic upgrade head` | Migration çalıştırır |
| `backend: alembic revision (autogenerate)` | Yeni migration oluşturur |
| `backend: ruff check` | Lint çalıştırır |
| `backend: mypy` | Tip kontrolü |
| `backend: pytest (coverage)` | Testleri coverage ile çalıştırır |
| `frontend: type-check` | TypeScript kontrolü |
| `frontend: lint` | ESLint |
| `frontend: build` | Production build |

---

## 8. Debug ve Breakpoint

### Mod A — Lokal Debug (Önerilen)

**F5** tuşuna bas veya sol panelden **Run and Debug** → aşağıdaki konfigürasyonlardan birini seç:

| Konfigürasyon | Ne Çalıştırır |
|---|---|
| `▶ Backend (lokal)` | FastAPI + debugpy, reload aktif |
| `▶ Frontend (lokal)` | Next.js dev server |
| `▶▶ Full Stack (backend + frontend lokal)` | İkisini birden başlatır |

**"▶ Backend (lokal)"** seçilince VS Code otomatik olarak:

1. `infra: up (data services)` task'ını çalıştırır (Docker servisleri hazır değilse başlatır)
2. `backend/.venv/bin/python` ile `uvicorn --reload` başlatır
3. Debug modu aktif olur — breakpoint'ler çalışır

### Breakpoint Koymak

1. Herhangi bir `.py` dosyasında satır numarasının soluna tıkla → kırmızı nokta belirir
2. Tarayıcıdan veya Swagger'dan (`http://localhost:8000/docs`) ilgili endpoint'i çağır
3. VS Code o satırda durur, sol panelde değişkenleri inceleyebilirsin

**Örnek — agent akışını izle:**

```
backend/app/agents/product_matcher.py  →  _match_line() içine breakpoint
Swagger → POST /api/documents/{id}/process
→ VS Code durur, line_no / description / match sonuçları görünür
```

**Örnek — SAP payload'ını yakala:**

```
backend/app/sap/modules/sales_orders.py  →  create() içine breakpoint
→ SAP'a gidecek tam JSON payload'ı durdurup inceleyebilirsin
```

### Debug İpuçları

**SQL sorgularını görmek için** (`session.py` geçici değişiklik):
```python
engine = create_async_engine(settings.database_url, echo=True, ...)
```

**LLM çağrılarını izlemek için** terminal loguna bak:
```
[llm_client] model=anthropic/claude-sonnet-4.5 tokens=1247 cost=$0.0031
```

**Redis'i doğrudan sorgulamak için:**
```bash
docker exec -it $(docker ps -qf name=redis) redis-cli
> KEYS *
> GET "doc:xyz"
```

---

## 9. Servis Adresleri

Tüm servisler çalışırken:

| Servis | URL | Kimlik Bilgisi |
|---|---|---|
| FastAPI Swagger | `http://localhost:8000/docs` | — |
| FastAPI Health | `http://localhost:8000/health` | — |
| Next.js UI | `http://localhost:3000` | admin@firma.com / Admin1234! |
| Postgres | `localhost:5433` | sapai / sapai / db: sapai |
| Redis | `localhost:6380` | — |
| Vault UI | `http://localhost:8201/ui` | Token: `dev-token` |
| MinIO Console | `http://localhost:9003` | minioadmin / minioadmin |

**MinIO bucket oluşturma** (ilk kurulumda bir kez):

```bash
# MinIO istemcisi ile bucket oluştur
docker run --rm --network host \
  minio/mc alias set local http://localhost:9002 minioadmin minioadmin && \
  mc mb local/sapb1-agent
```

Veya `http://localhost:9003` adresindeki web arayüzünden `sapb1-agent` bucket'ı oluştur.

---

## 10. Testler

```bash
cd backend && source .venv/bin/activate

# Tüm testler
pytest tests/ -v

# Belirli modül
pytest tests/sap/ -v        # SAP wrapper testleri
pytest tests/agents/ -v     # Agent testleri
pytest tests/api/ -v        # API contract testleri

# Coverage raporu
pytest --cov=app --cov-report=term-missing

# Sadece başarısız olanları tekrar çalıştır
pytest --lf
```

VS Code'da test panelini açmak için sol kenardaki **beaker (test tüpü) ikonuna** tıkla. Testler otomatik keşfedilir, tek tek veya toplu çalıştırılabilir.

---

## 11. Sık Karşılaşılan Sorunlar

**`connection refused` — Postgres veya Redis bağlanamıyor**

```bash
# Servisler ayakta mı?
docker compose -f docker/docker-compose.yml ps

# Ayakta değilse başlat
docker compose -f docker/docker-compose.yml up -d postgres redis
```

**`alembic upgrade head` — "relation already exists" hatası**

```bash
# Veritabanını sıfırla (sadece dev — tüm veri silinir)
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d postgres
alembic upgrade head
```

**`openrouter_api_key field required` validation hatası**

```bash
# .env okunmuyordur — dosyanın var olduğunu kontrol et
ls -la backend/.env

# Yoksa kopyala ve doldur
cp backend/.env.example backend/.env
# Sonra OPENROUTER_API_KEY satırını düzenle
```

**`pgvector extension does not exist`**

Docker image'in `pgvector/pgvector:pg16` olması gerekiyor, `postgres:16` değil. `docker-compose.yml` dosyasını kontrol et:

```yaml
postgres:
  image: pgvector/pgvector:pg16   # bu satır bu şekilde olmalı
```

Düzelttikten sonra:

```bash
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d postgres
alembic upgrade head
```

**`DYLD_LIBRARY_PATH` / `cairo` / `pango` hataları (macOS Apple Silicon)**

```bash
brew install cairo pango gdk-pixbuf
# launch.json'da DYLD_LIBRARY_PATH=/opt/homebrew/lib zaten ayarlı
```

**Frontend API'ye bağlanamıyor (`CORS` veya `network error`)**

```bash
# frontend/.env dosyasını kontrol et
cat frontend/.env
# Şunu içermeli:
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Celery task'ları çalışmıyor**

`CELERY_ENABLED=false` iken Celery worker gerekmez — görevler FastAPI ile aynı process'te çalışır. Celery istiyorsan:

```bash
# backend/.env
CELERY_ENABLED=true

# Ayrı terminalde worker başlat
cd backend && source .venv/bin/activate
celery -A app.workers.celery_app worker -l info
```

**`ModuleNotFoundError` — paket bulunamıyor**

```bash
cd backend
source .venv/bin/activate
pip install -e ".[dev]"   # tüm paketleri yeniden kur
```
