# Pilot Kurulum Rehberi

Müşteri pilotu için **uçtan uca kurulum** rehberi. Test ortamında 1-2 saat, müşteri ortamında 4-6 saat sürer.

---

## 1. Önkoşullar

### Müşteri tarafı (on-prem)
- SAP B1 9.3+ kurulu, Service Layer aktif
- Service Layer'a erişim hesabı: `SAP_USERNAME` (yeni Named User önerilir)
- SAP B1 lisans: en az 4 boş session slot
- Linux sunucu (8 vCPU, 16 GB RAM, 200 GB SSD) **veya** Docker destekli Windows
- TR/TLS sertifikası (mTLS tunnel için — opsiyonel, Faz 2)

### Cloud tarafı (bizim)
- Postgres 16 + pgvector
- Redis 7
- OpenRouter API key (production) — https://openrouter.ai/keys
- Domain + Let's Encrypt sertifikası
- SMTP veya IMAP/Microsoft Graph erişim hesabı

---

## 2. Kurulum Adımları

### 2.1 Repo'yu hazırla
```bash
git clone <repo-url> sap-b1-ai-agent
cd sap-b1-ai-agent
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`backend/.env` doldur:
```
APP_ENV=production
APP_SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...

SAP_SERVICE_LAYER_URL=https://sap.musteri.local:50000/b1s/v1
SAP_COMPANY_DB=SBODEMO_TR
SAP_USERNAME=...
SAP_PASSWORD=...
SAP_VERIFY_SSL=true
SAP_MAX_CONCURRENT_SESSIONS=4

OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL_DEFAULT=anthropic/claude-sonnet-4.5
LLM_MODEL_FAST=anthropic/claude-haiku-4.5
LLM_MODEL_HARD=anthropic/claude-opus-4.1

EMAIL_IMAP_HOST=imap.example.com
EMAIL_USERNAME=siparis@example.com
EMAIL_PASSWORD=...

CORS_ORIGINS=["https://panel.musteri.com"]
```

### 2.2 Docker Compose ile ayağa kaldır
```bash
docker compose -f docker/docker-compose.yml up -d
```

### 2.3 DB şemasını migrate et
```bash
docker compose exec backend alembic upgrade head
```

### 2.4 Seed (admin, manager, operator kullanıcıları + örnek approval kuralı)
```bash
docker compose exec backend python scripts/seed.py
```
**Çıktı:** `admin@example.com / admin123` — ilk girişte değiştir.

### 2.5 SAP master cache'i ilk doldur
```bash
docker compose exec backend python -m app.scripts.sync_sap_master   # TODO: Faz 2'de scriptleyeceğiz
# Geçici: dropdown sorguları SAP'a doğrudan gider; cache Faz 2'de eklenir.
```

### 2.6 Sağlık kontrolü
```bash
curl https://api.musteri.com/health
# {"status":"ok"}

curl -H "Authorization: Bearer $TOKEN" https://api.musteri.com/api/sap/business-partners?search=test
# SAP DEMO'dan müşteri listesi gelmeli
```

---

## 3. Kabul Testleri (Definition of Done)

Aşağıdakiler **mutlaka geçmeli**:

| # | Senaryo | Beklenen |
|---|---|---|
| 1 | Tarayıcı → /login → admin@example.com | Pipeline ekranı açılır |
| 2 | Yeni belge yükle (örnek PDF) | Pipeline'da "AI İşliyor" sütununda görünür |
| 3 | 30 sn sonra "Hazır" sütununa geçer | Belgeye tıkla → form AI verisi ile dolu |
| 4 | Müşteri combobox'tan arama | SAP'tan canlı sonuç gelir (≥2 karakter) |
| 5 | Ürün satırını düzelt → Kaydet | "✓ Kaydedildi" mesajı |
| 6 | "SAP'a Gönder" | DocEntry/DocNum döner, "SAP'a Yazıldı" sütununa geçer |
| 7 | Aynı belgeyi tekrar yükle | 409 Conflict (dedupe) |
| 8 | 100k üstü Sales Order | Pipeline "Onay Bekliyor" sütununa düşer |
| 9 | Manager hesabıyla giriş → Onaylar | Bekleyen approval görünür, Onayla butonu çalışır |
| 10 | Operator manager-only endpoint'i çağırır | 403 Türkçe mesaj |

---

## 4. Pilot İzleme Metrikleri

İlk 30 günde haftalık takip:

- **No-touch oranı** — `agent_runs.summary` içinde `needs_human=false` / toplam
- **Belge başı süre** — receive → submitted arasındaki ortalama
- **AI hata oranı** — `documents.status='error'` / toplam
- **SAP yazım hata oranı** — `sap_submissions` failed / toplam
- **LLM maliyeti** — `llm_calls.cost_usd` günlük toplam
- **Kullanıcı geri bildirimi** — haftalık 30 dk demo + NPS

Hedef ilk 30 gün:
- No-touch %25+
- Belge başı süre < 10 dk
- AI hata < %3
- Aylık LLM maliyeti < ₺3.000

---

## 5. Geri Sarma (Rollback)

Sorun olursa:
1. `docker compose stop backend worker` — yazımı durdur.
2. Mevcut işteki belgeler READY/APPROVAL'da bekler — kayıp olmaz.
3. Sorun çözüldükten sonra `docker compose start backend worker`.
4. Pilot iptal: `docker compose down -v` + DB backup arşivi.

---

## 6. Destek SLA (Pilot Dönemi)

- **P1 (sistem kapalı):** 1 saat içinde yanıt
- **P2 (özellik bozuk):** 4 saat içinde yanıt
- **P3 (sorum/UI):** 1 iş günü içinde yanıt
- Pilot süresince Slack/Teams kanalı açılır.

---

**Versiyon:** 1.0 — Mayıs 2026
