# Modül: Ürün Eşleştirme (Product Matching) — Tam Otomasyon Mimarisi

> PDF'ten okunan ürün tanımlarını → SAP B1 `ItemCode`'larına otomatik bağlayan pipeline.
> Bu doküman hem mimari kararları hem de eksik implementation adımlarını listeler.

**Durum:** Kod iskeleti var, SAP sync task'ı eksik — manuel giriş bu yüzden.  
**Hedef:** %85+ ürün satırını insan müdahalesi olmadan otomatik eşleştir.

---

## 1. Sorunun Kökü (Neden Hâlâ Manuel?)

```
SAP B1 (Items)  ←─────────── BAĞLANTI YOK ───────────→  item_cache (Postgres)
                                                               ↑
                                                         ProductMatcherAgent
                                                         buraya bakıyor ama
                                                         tablo boş!
```

`ProductMatcherAgent` (`agents/product_matcher.py`) kodlanmış ve çalışıyor.
`item_cache` Postgres tablosu DB şemasında var (`db/models/sap_cache.py`).
Ama SAP'taki ürünleri Postgres'e çeken **Celery sync task yazılmamış**.

Bu tek eksikliği tamamlayınca manuel girişin büyük kısmı ortadan kalkar.

---

## 2. Hedef Akış (End-to-End)

```
PDF / Excel
    │
    ▼
DocumentReader (AI)
    │  description="Helvar 321 LED Armatür", item_code_raw="HELVAR-321"
    ▼
ProductMatcherAgent  ──→ Katman 1: Barkod exact → BULDU? → item_code
                     ──→ Katman 2: ItemCode exact → BULDU? → item_code
                     ──→ Katman 3: Müşteri alias → BULDU? → item_code
                     ──→ Katman 4: Fuzzy metin (rapidfuzz ≥85) → item_code
                     ──→ Katman 5: Semantic (pgvector cosine) → item_code   [Faz 2]
                     ──→ Katman 6: LLM yardımlı açıklama → item_code        [Faz 2]
                         │
                         ▼ score < 0.85? → Human Review
                         ▼ score ≥ 0.85? → Otomatik kabul
                                  │
                                  ▼
                          Operatör onay/düzelt
                                  │
                          CustomerAlias öğren  (bir daha sorma)
                                  │
                                  ▼
                           SAP B1 POST (Orders / Quotations)
```

---

## 3. SAP Sync Mimarisi — EKSİK OLAN PARÇA

### 3.1 Ne Yapalım?

SAP B1 `Items` endpoint'inden tüm aktif ürünleri çek, `item_cache` tablosuna upsert et.

```
SAP B1 /b1s/v1/Items
    │  (her gün tam sync + her saat incremental)
    ▼
Celery Beat Task: sync_items_cache
    │
    ├─ item_cache upsert (ItemCode, ItemName, BarCode, ForeignName...)
    └─ item_embeddings upsert (text → OpenAI embedding → pgvector)  [Faz 2]
```

### 3.2 SAP API Çağrısı

```python
# GET /b1s/v1/Items?$select=ItemCode,ItemName,ForeignName,BarCode,
#     ItemsGroupCode,SalesUnit,InventoryUoM,SalesItem,InventoryItem
#     &$filter=Valid eq 'tYES' and SalesItem eq 'tYES'
#     &$top=500&$skip=0
```

Sayfalama: `$top=500` + `$skip` ile tüm catalog'u çek (Elekon ~3000-10000 item).

### 3.3 Sync Task Dosyası

**Nereye yazılacak:** `backend/app/workers/sync_tasks.py` (yeni dosya)

```python
# Tam sync: her gece 02:00 (cron)
@celery_app.task(name="sync.items.full")
def sync_items_full(): ...

# Incremental: her saat (UpdateDate >= dün)
@celery_app.task(name="sync.items.incremental")
def sync_items_incremental(): ...
```

**Celery Beat schedule** (`celery_app.py`'ye eklenir):
```python
beat_schedule = {
    "sync-items-full-daily": {
        "task": "sync.items.full",
        "schedule": crontab(hour=2, minute=0),
    },
    "sync-items-incremental-hourly": {
        "task": "sync.items.incremental",
        "schedule": crontab(minute=30),
    },
    "sync-bp-full-daily": {
        "task": "sync.bp.full",
        "schedule": crontab(hour=2, minute=15),
    },
}
```

### 3.4 Upsert Mantığı

```python
# PostgreSQL ON CONFLICT DO UPDATE ile idempotent:
INSERT INTO item_cache (...) VALUES (...)
ON CONFLICT (item_code) DO UPDATE SET
  item_name = EXCLUDED.item_name,
  item_name_lower = EXCLUDED.item_name_lower,
  bar_code = EXCLUDED.bar_code,
  raw = EXCLUDED.raw,
  last_synced_at = NOW();
```

---

## 4. Eşleştirme Katmanları (Detay)

### Katman 1 — Barkod Exact (`strategy: "barcode"`, score: 1.0)

PDF'te barkod varsa → `item_cache.bar_code = ?` exact match.
Elekon'da barkod olmayan ürünler çok → bu katman boş kalabilir, sorun değil.

### Katman 2 — ItemCode Exact (`strategy: "code"`, score: 1.0)

PDF'te üretici kodu varsa (ör. `HELVAR-321`) → `item_cache.item_code = ?` exact.
DocumentReader `item_code_raw` alanını "Stok Kodu" / "Model No" sütunundan doldurur.

### Katman 3 — Müşteri Alias (`strategy: "alias"`, score: 1.0)

`customer_alias` tablosunda `(card_code, alias_lower) → item_code` eşlemesi.
Operatör bir kez doğru ItemCode'u seçince otomatik kaydedilir.
Aynı müşteriden gelen sonraki PDF'lerde bu satır artık 1.0 skorla geçer.

### Katman 4 — Fuzzy Metin (`strategy: "fuzzy_name"`, score: 0.0–1.0)

`rapidfuzz.token_set_ratio` ile PDF açıklaması ↔ `item_cache.item_name`.
Eşik: **85/100** → 0.85 skor, human-in-the-loop sınırının tam üstü.

**Optimizasyon:** İlk token ile `LIKE '%token%'` pre-filter, tüm tabloyu taramaz.
Limit: 300 aday → en iyisini seç.

**Zaafiyeti:** Türkçe karakter duyarsız. Çözüm: `item_name_lower` kolonunda `unaccent` + `lower`.

### Katman 5 — Semantic Arama (`strategy: "semantic"`, score: 0.0–1.0) — FAZ 2

`item_embeddings` tablosunda pgvector cosine similarity.

```sql
SELECT item_code, 1 - (embedding <=> :query_vec) AS score
FROM item_embeddings
ORDER BY embedding <=> :query_vec
LIMIT 5;
```

Embedding modeli: `text-embedding-3-small` (OpenAI, 1536 dim) veya
`voyage-3-lite` (Anthropic, 1024 dim — daha ucuz).

**Neden fuzzy'den iyi?** "Kompakt floresan lamba" → "CFL Armatür 18W" gibi anlam
benzerliklerini yakalar; karakter benzerliğine bakmaz.

### Katman 6 — LLM Yardımlı — FAZ 2

Semantic de 0.85 altında kalırsa Claude'a sor:
- Input: PDF açıklaması + top-5 candidate list
- Output: En iyi eşleşme ItemCode + reasoning
- Maliyet: Haiku ($0.25/M token) — sadece eşleşemeyen satırlar için

---

## 5. Human-in-the-Loop Akışı

```
score < 0.85 veya item bulunamadı
        │
        ▼
UI'da satır kırmızı/sarı
Operatör combobox'tan doğru ürünü seçer
        │
        ├─ CustomerAlias kaydedilir (card_code + alias_text → item_code)
        │   confidence = 1.0, confirmed_by = user_id
        └─ ExtractedData güncellenir (item_code set)
```

**Öğrenme döngüsü:** 10 farklı PDF'te aynı müşteriden aynı ürün geldiğinde
11. PDF'te artık hiç müdahale gerekmez. No-touch ratio zamanla artar.

---

## 6. Implementation Öncelik Sırası

### Adım 1 — SAP Sync Task (1-2 gün) ← EN KRİTİK
`backend/app/workers/sync_tasks.py` yazılır:
- `sync_items_full()`: Tüm aktif Items → `item_cache` upsert
- `sync_bp_full()`: Tüm aktif BP'ler → `bp_cache` upsert  
- `sync_items_incremental()`: `UpdateDate >= bugün-1gün` filter

Celery Beat schedule `celery_app.py`'ye eklenir.

Manuel tetikleme endpoint'i:  
`POST /api/admin/sync/items` (admin role) — ilk kurulumda manuel çalıştır.

### Adım 2 — Fuzzy Eşleştirme İyileştirme (0.5 gün)
- `item_name_lower` kolonunda `unaccent` (Türkçe İ/ı, Ş/ş sorunları)
- `foreign_name` da arama alanına ekle (üretici adı burada olabilir)
- Pre-filter: sadece ilk token değil, ilk 2 token AND ile filtrele

### Adım 3 — Alias Öğrenme API'si (0.5 gün)
`PATCH /documents/{id}/lines/{line_no}` endpoint'inde:
```json
{ "item_code": "H000106", "learn_alias": true }
```
→ `customer_alias` insert

### Adım 4 — Semantic Embedding Sync (1 gün) — Faz 2
`sync_tasks.py`'ye `sync_item_embeddings()` ekle:
- Yeni/değişen item'lar için embedding üret
- `item_embeddings` upsert
- `ProductMatcherAgent`'a 5. katmanı ekle

---

## 7. Performans ve Ölçeklenme

| Metrik | Hedef | Notlar |
|---|---|---|
| Tam sync süresi | < 5 dk | 10K item, 500/page batch |
| Fuzzy match süresi (satır başı) | < 50ms | 300 candidate limit |
| Semantic search (satır başı) | < 10ms | pgvector HNSW index |
| item_cache boyutu | ~10K row | Elekon için yeterli |
| Cache tazeliği | 1 saat max gecikme | Incremental sync |

### pgvector HNSW Index (Faz 2'ye hazır)
```sql
CREATE INDEX ix_item_emb_hnsw ON item_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 8. Konfigurasyon (`.env`)

```env
# Sync ayarları
ITEM_SYNC_BATCH_SIZE=500          # SAP'tan kaç item'da bir çekilir
ITEM_SYNC_FULL_CRON="0 2 * * *"  # Her gece 02:00
ITEM_SYNC_INC_CRON="30 * * * *"  # Her saat :30

# Matching eşikleri
FUZZY_MATCH_THRESHOLD=85          # rapidfuzz token_set_ratio min puan
SEMANTIC_MATCH_THRESHOLD=0.82     # cosine similarity min (Faz 2)
HIGH_CONFIDENCE=0.85              # Bu altı → human-in-the-loop

# Embedding (Faz 2)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

---

## 9. Monitoring

Sync task sonrası Prometheus metrikleri:

```
sap_sync_items_total{status="success|error"} - toplam sync sayısı
sap_sync_items_duration_seconds - sync süresi
item_cache_count - cache'deki ürün sayısı
item_match_score_histogram - eşleştirme skoru dağılımı
item_match_strategy_counter{strategy="barcode|code|alias|fuzzy|semantic|none"}
```

`item_match_strategy_counter{strategy="none"}` yükseliyorsa → catalog sync bozuk veya
PDF formatı değişmiş demektir; alert kur.

---

## 10. Dosya Haritası (Mevcut + Eksik)

```
backend/app/
  agents/
    product_matcher.py     ✅ var — 6 katman iskelet (pgvector Faz 2 notu var)
  db/models/
    sap_cache.py           ✅ var — ItemCache, ItemEmbedding, CustomerAlias
  workers/
    tasks.py               ✅ var — belge işleme task'ları
    sync_tasks.py          ❌ EKSİK — SAP sync task'ları (YAZAR: Sprint 2)
    celery_app.py          ⚠️  beat_schedule boş — sync schedule eklenmeli

backend/tests/
  workers/
    test_sync_tasks.py     ❌ EKSİK — sync task unit testleri (respx mock)
```

---

## 11. Kabul Kriterleri

- [ ] `sync_items_full` task'ı çalıştırıldıktan sonra `item_cache` boş değil
- [ ] Barkod ile exact match yapılabiliyor (score: 1.0)
- [ ] Fuzzy eşleştirme "Helvar 321 LED" → `H000321` yakalıyor (score ≥ 0.85)
- [ ] score < 0.85 satırlar UI'da sarı, top-5 candidate gösteriyor
- [ ] Operatör düzeltmesi → `customer_alias` kaydı → sonraki PDF'te 1.0 skor
- [ ] Incremental sync, sadece UpdateDate değişenleri günceller
- [ ] Manuel tetikleme: `POST /api/admin/sync/items` 200 döner
