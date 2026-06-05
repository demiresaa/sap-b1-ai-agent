# Çoklu SAP Backend Mimarisi — Sistem Analizi

**Versiyon:** 1.0
**Tarih:** Mayıs 2026
**Kapsam:** Aynı AI orkestrasyon platformunun hem **SAP Business One (B1)** hem **SAP ECC / S/4HANA** müşterilerine hizmet vermesi
**Durum:** Karar verildi, B1 adapter mevcut (working) · ECC adapter eklenecek

---

## 1. Yönetici Özeti

Mevcut platform `httpx` + OData üzerinden **SAP B1 Service Layer'a** bağlanan tek-backend bir mimaridir. Yeni gereksinim: bazı müşteriler **SAP ECC veya S/4HANA** kullanıyor; bunlara `pyrfc` ile **RFC/BAPI** üzerinden bağlanmamız gerekiyor. İki ürün **bambaşka API'lere** sahip olduğu için backend katmanını **Adapter pattern** ile soyutluyoruz. Multi-agent orkestrasyon, doküman okuma, eşleştirme, onay, audit, frontend — **bunlar değişmiyor**. Sadece SAP'a yazım/okuma katmanı çift implementasyonlu hale geliyor.

Müşteri başına `.env`'deki `SAP_BACKEND=b1|ecc` flag'iyle adapter seçilir. Multi-tenant Faz 3'te tenant tablosundan okunur. **Sıfır kod değişimi hedefi:** agent'lar, orchestrator, API route'ları, frontend ortak ara yüzü kullanır.

---

## 2. Problem ve Motivasyon

### 2.1 Pazar gerçekliği
| Segment | Kullanıcı sayısı (TR tahmini) | API teknolojisi |
|---|---|---|
| SAP B1 | 5.000+ şirket (KOBİ) | Service Layer (REST/OData v3) |
| SAP ECC | 1.500+ şirket (orta+kurumsal) | RFC/BAPI (NetWeaver) |
| SAP S/4HANA | 500+ şirket (yeni geçişler) | RFC/BAPI **veya** OData v4 (Gateway/Cloud) |

Tek bir ürüne kilitlenirsek pazarın yarısını kaçırıyoruz. Aynı AI değer önerisi (PDF → otomatik sipariş) her üç ortam için de geçerli; sadece "son adım yazım" farklı.

### 2.2 Teknik gerçeklik
- B1 ve ECC **aynı şirketin (SAP) ama bambaşka ürünleri**. Veri modeli, protokol, terim, lisans modeli farklı.
- Bir SAP B1 sertifikası ECC için geçerli değil; tersi de doğru.
- ECC'de RFC + pyrfc native bir SDK gerektirir (SAP NWRFC SDK), kurulum karmaşık → Docker zorunlu.

### 2.3 Karar
**Adapter (Port/Adapter, Hexagonal) pattern.** Tek bir `SAPBackend` Protocol'ü, iki concrete implementation (`B1Backend`, `ECCBackend`). Domain mantığı (agent + DB + UI) yalnızca abstract'a bakar.

---

## 3. Mevcut Durum (B1-only)

```
agents → app.sap.modules.SalesOrdersModule(client)
       → app.sap.modules.BusinessPartnersModule(client)
       → app.sap.modules.ItemsModule(client)

client = SAPServiceLayerClient (httpx, B1 Service Layer)
```

**Sorun:** Agent kodu direkt `SalesOrdersModule` (B1'e özel) çağırıyor. ECC desteklenirse bu çağrılar kırılır.

---

## 4. Hedef Mimari

```
agents / services →  SAPBackend (Protocol)
                          ▲
                    ┌─────┴─────┐
                    │           │
            B1Backend        ECCBackend
                │                │
        SAPServiceLayerClient    pyrfc.Connection
                │                │
        REST :50000 /b1s/v1      RFC :33<sysnr>
```

- **`app.sap.base`** — Protocol + DTO'lar + fabrika
- **`app.sap.b1`** — mevcut kodun bu klasöre taşınmış hâli
- **`app.sap.ecc`** — yeni RFC adapter
- **`app.sap.factory.get_backend()`** — config'e göre instance döner
- Agent'lar yalnızca `get_backend()` üzerinden çağırır

---

## 5. Kavram Eşleme Tablosu (B1 ↔ ECC)

| Kavram | SAP B1 | SAP ECC / S4 | Birleşik DTO alanı |
|---|---|---|---|
| Müşteri kodu | `CardCode` (string, custom) | `KUNNR` (10 haneli sıfır dolgulu) | `customer.code` |
| Müşteri adı | `CardName` | `NAME1` (+ NAME2…) | `customer.name` |
| Vergi no | `FederalTaxID` | `STCD1` / `STCEG` | `customer.tax_id` |
| Müşteri tipi | `CardType=cCustomer` | Account Group + Sales Area | `customer.kind="customer"` |
| Ürün kodu | `ItemCode` | `MATNR` (18 haneli sıfır dolgulu) | `item.code` |
| Ürün adı | `ItemName` | `MAKTX` (description) | `item.name` |
| Barkod | `BarCode` | `EAN11` | `item.barcode` |
| Satış birimi | `SalesUnit` | `VRKME` | `item.unit` |
| Sipariş belgesi | Sales Order (DocEntry) | Sales Document (VBELN) | `doc_id`, `doc_number` |
| Sipariş tipi | (yok — tek tip) | `DOC_TYPE` (`TA`, `ZOR`, …) | `backend_options.doc_type` |
| Organizasyon | Branch (opsiyonel) | Sales Org + Distr Chan + Division | `backend_options.sales_area` |
| Partner | Tek BP | `AG` (Sold-to) + `WE` (Ship-to) + … | `backend_options.partners` |
| Satır no | `LineNum` (0-based) | `ITM_NUMBER` (10'arlı: 000010…) | `lines[i].line_no` |
| Miktar | `Quantity` | `TARGET_QTY` + Schedule Lines `REQ_QTY` | `lines[i].quantity` |
| Birim fiyat | `UnitPrice` | `COND_VALUE` (KONV) | `lines[i].unit_price` |
| Vade tarihi | `DocDueDate` | `REQ_DATE_H` veya schedule line | `due_date` |
| Para birimi | `DocCurrency` | `WAERK` (header) / `KOEIN` | `currency` |
| Müşteri referans | `NumAtCard` | `PURCH_NO_C` | `reference_no` |
| Açıklama | `Comments` | Text Item / `Z*` UDF | `notes` |
| Commit | otomatik (POST) | manuel `BAPI_TRANSACTION_COMMIT` | adapter dahili |
| Hata format | HTTP 4xx + JSON `error.code` | `RETURN[]` tablosu — TYPE: S/W/E/A | adapter normalize |
| Stok | `ItemsService_GetItemAvailability` | `BAPI_MATERIAL_AVAILABILITY` | `availability.available_qty` |
| Quotation | `/Quotations` (POST) | `BAPI_QUOTATION_CREATEFROMDATA2` | `create_quotation` |

---

## 6. Abstract Backend Interface

`backend/app/sap/base.py` (yeni dosya):

```python
from __future__ import annotations
from datetime import date
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class CustomerDTO(BaseModel):
    code: str
    name: str
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    currency: str | None = None
    payment_terms: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)  # vendor-specific tüm alanlar


class ItemDTO(BaseModel):
    code: str
    name: str
    barcode: str | None = None
    unit: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class AvailabilityDTO(BaseModel):
    code: str
    available_qty: float | None
    in_stock_qty: float | None = None
    committed_qty: float | None = None
    ordered_qty: float | None = None


class OrderLineDTO(BaseModel):
    line_no: int
    item_code: str
    quantity: float
    unit_price: float | None = None
    discount_pct: float | None = None
    tax_code: str | None = None


class SalesOrderRequest(BaseModel):
    customer_code: str
    doc_date: date
    due_date: date | None = None
    currency: str | None = None
    reference_no: str | None = None
    notes: str | None = None
    lines: list[OrderLineDTO]
    # Backend-specific overrides — ilgili adapter okur, diğeri yok sayar
    # B1: {"price_list_num": 1, "branch_id": 0}
    # ECC: {"doc_type": "TA", "sales_org": "0001", "distr_chan": "01",
    #       "division": "01", "ship_to_code": None}
    backend_options: dict[str, Any] = Field(default_factory=dict)


class SalesOrderResult(BaseModel):
    doc_id: str          # B1 DocEntry str(int) · ECC VBELN
    doc_number: str      # kullanıcının gördüğü no (B1 DocNum · ECC VBELN aynı)
    warnings: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class SAPBackend(Protocol):
    """Tüm SAP backend'lerinin uyacağı kontrat.

    `connect()` lifespan'da çağrılır; `close()` shutdown'da.
    Tüm metodlar idempotent değildir; idempotency üst katmanda (`IdempotencyStore`).
    """

    backend_name: str  # "b1" | "ecc"

    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def health(self) -> dict[str, Any]: ...

    # Master data — read
    async def search_customers(
        self, query: str, *, top: int = 50, skip: int = 0
    ) -> list[CustomerDTO]: ...
    async def get_customer(self, code: str) -> CustomerDTO | None: ...
    async def search_customers_by_tax_id(self, tax_id: str) -> list[CustomerDTO]: ...

    async def search_items(
        self, query: str, *, top: int = 50, skip: int = 0
    ) -> list[ItemDTO]: ...
    async def get_item(self, code: str) -> ItemDTO | None: ...
    async def get_availability(self, code: str) -> AvailabilityDTO: ...

    # Sales documents — write
    async def create_sales_order(self, request: SalesOrderRequest) -> SalesOrderResult: ...
    async def create_quotation(self, request: SalesOrderRequest) -> SalesOrderResult: ...
    async def cancel_sales_order(self, doc_id: str) -> None: ...
```

Notlar:
- DTO'lar **vendor-bağımsız** — agent ve UI yalnızca bunları görür.
- `raw` alanı vendor-özel veriyi taşır (debug, audit, ileride özelleştirme için).
- `backend_options` write akışında esneklik sağlar; B1 adapter ECC alanlarını yok sayar, ECC adapter B1 alanlarını yok sayar.
- Quotation `SalesOrderRequest`'i kullanır (alanlar aynı); ileride farklılaşırsa ayrı DTO çıkarırız.

---

## 7. Backend Seçim Mekanizması

### 7.1 Faz 1 (tek tenant, .env tabanlı)
`backend/.env`:
```bash
SAP_BACKEND=b1               # b1 | ecc

# B1 ayarları (mevcut)
SAP_SERVICE_LAYER_URL=https://...:50000/b1s/v1
SAP_COMPANY_DB=...
SAP_USERNAME=...
SAP_PASSWORD=...

# ECC ayarları (yeni)
SAP_ECC_ASHOST=5.180.184.100
SAP_ECC_SYSNR=60
SAP_ECC_CLIENT=100
SAP_ECC_USER=...
SAP_ECC_PASSWORD=...
SAP_ECC_LANG=EN
SAP_ECC_POOL_SIZE=4
SAP_ECC_DEFAULT_SALES_ORG=0001
SAP_ECC_DEFAULT_DISTR_CHAN=01
SAP_ECC_DEFAULT_DIVISION=01
SAP_ECC_DEFAULT_DOC_TYPE=TA
```

`backend/app/sap/factory.py`:
```python
from app.core.config import settings
from app.sap.base import SAPBackend


_instance: SAPBackend | None = None


async def get_backend() -> SAPBackend:
    global _instance
    if _instance is None:
        if settings.sap_backend == "ecc":
            from app.sap.ecc.adapter import ECCBackend
            _instance = ECCBackend()
        else:
            from app.sap.b1.adapter import B1Backend
            _instance = B1Backend()
        await _instance.connect()
    return _instance


async def close_backend() -> None:
    global _instance
    if _instance is not None:
        await _instance.close()
        _instance = None
```

### 7.2 Faz 3 (multi-tenant)
`tenants` tablosu:
```sql
ALTER TABLE tenants ADD COLUMN sap_backend VARCHAR(10) NOT NULL DEFAULT 'b1';
ALTER TABLE tenants ADD COLUMN sap_config_json JSONB NOT NULL DEFAULT '{}';
```
`get_backend(tenant_id)` cache + tenant-config'ten okur. Anahtarlar Vault'ta tutulur.

---

## 8. B1 Adapter — Mevcut Kodun Refactor'u

Yeni dizin yapısı:
```
backend/app/sap/
  __init__.py            ← pool, errors, SAPError export
  base.py                ← Protocol + DTO'lar (yeni)
  factory.py             ← backend seçici (yeni)
  client.py              ← B1 HTTP client (mevcut, taşımıyoruz; b1/ altına alalım)
  session.py             ← B1 session pool (mevcut)
  errors.py              ← Türkçe error mapping (mevcut, ortak)
  odata.py               ← OData builder (mevcut, sadece B1)
  idempotency.py         ← Redis cache (mevcut, ortak)
  b1/
    __init__.py
    adapter.py           ← B1Backend (SAPBackend protokolünü implement eder)
    client.py            ← mevcut client.py'nin taşınmışı (opsiyonel)
    modules/             ← mevcut modules/ (BusinessPartners, Items, SalesOrders, Quotations…)
  ecc/
    __init__.py
    adapter.py           ← ECCBackend
    connection.py        ← pyrfc bağlantı pool
    customers.py         ← BAPI_CUSTOMER_GETLIST / GETDETAIL2
    materials.py         ← BAPI_MATERIAL_GETLIST / GET_DETAIL
    sales_orders.py      ← BAPI_SALESORDER_CREATEFROMDAT2 + commit
    quotations.py        ← BAPI_QUOTATION_CREATEFROMDATA2
    availability.py      ← BAPI_MATERIAL_AVAILABILITY
    errors.py            ← RETURN tablosu → SAPError TR mesaj
    padding.py           ← KUNNR/MATNR sıfır dolgu yardımcıları
```

`b1/adapter.py` taslağı:
```python
from app.sap.base import SAPBackend, CustomerDTO, ItemDTO, SalesOrderRequest, SalesOrderResult, AvailabilityDTO
from app.sap.session import pool
from app.sap.b1.modules import BusinessPartnersModule, ItemsModule, SalesOrdersModule, QuotationsModule


class B1Backend:
    backend_name = "b1"

    async def connect(self) -> None:
        # session pool zaten lazy; burada warmup yapabiliriz
        async with pool.acquire():
            pass

    async def close(self) -> None:
        await pool.close_all()

    async def search_customers(self, query, *, top=50, skip=0):
        async with pool.acquire() as client:
            rows = await BusinessPartnersModule(client).list_customers(top=top, skip=skip, search=query)
            return [self._customer_from_b1(r) for r in rows]

    async def create_sales_order(self, request):
        payload = self._b1_payload_from(request)
        async with pool.acquire() as client:
            resp = await SalesOrdersModule(client).create(payload)
            return SalesOrderResult(
                doc_id=str(resp["DocEntry"]),
                doc_number=str(resp.get("DocNum") or resp["DocEntry"]),
                raw=resp,
            )

    # ... (search_items, get_availability, create_quotation, vs.)

    @staticmethod
    def _customer_from_b1(row) -> CustomerDTO:
        return CustomerDTO(
            code=row["CardCode"],
            name=row["CardName"],
            tax_id=row.get("FederalTaxID"),
            email=row.get("EmailAddress"),
            phone=row.get("Phone1"),
            currency=row.get("Currency"),
            raw=row,
        )

    @staticmethod
    def _b1_payload_from(req: SalesOrderRequest) -> dict:
        return {
            "CardCode": req.customer_code,
            "DocDate": req.doc_date.isoformat(),
            "DocDueDate": (req.due_date or req.doc_date).isoformat(),
            "DocCurrency": req.currency,
            "NumAtCard": req.reference_no,
            "Comments": req.notes,
            "DocumentLines": [
                {
                    "ItemCode": l.item_code,
                    "Quantity": l.quantity,
                    "UnitPrice": l.unit_price,
                    "DiscountPercent": l.discount_pct,
                    "TaxCode": l.tax_code,
                }
                for l in req.lines
            ],
        }
```

**Refactor maliyeti:** ~2 saat. Mevcut B1 testleri (16 test) küçük dokunuşlarla yeşil kalır.

---

## 9. ECC Adapter — BAPI Eşlemesi

### 9.1 Bağlantı (`connection.py`)
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import pyrfc

from app.core.config import settings


class ECCConnectionPool:
    """RFC bağlantıları pahalıdır; bir process'te kaç tane açabileceğimiz
    sınırlıdır. ThreadPoolExecutor + asyncio.to_thread ile blocking pyrfc
    çağrılarını event-loop'tan ayırıyoruz.
    """

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=settings.sap_ecc_pool_size)
        self._lock = asyncio.Lock()
        self._idle: list[pyrfc.Connection] = []
        self._max = settings.sap_ecc_pool_size

    @asynccontextmanager
    async def acquire(self):
        conn = None
        async with self._lock:
            if self._idle:
                conn = self._idle.pop()
        if conn is None:
            conn = await asyncio.to_thread(self._create)
        try:
            yield conn
        finally:
            async with self._lock:
                self._idle.append(conn)

    def _create(self) -> pyrfc.Connection:
        return pyrfc.Connection(
            ashost=settings.sap_ecc_ashost,
            sysnr=settings.sap_ecc_sysnr,
            client=settings.sap_ecc_client,
            user=settings.sap_ecc_user,
            passwd=settings.sap_ecc_password,
            lang=settings.sap_ecc_lang,
        )

    async def close_all(self) -> None:
        async with self._lock:
            while self._idle:
                conn = self._idle.pop()
                await asyncio.to_thread(conn.close)


pool = ECCConnectionPool()


async def call_rfc(func_name: str, **kwargs) -> dict:
    """Blocking RFC çağrısını event-loop dışına it."""
    async with pool.acquire() as conn:
        return await asyncio.to_thread(conn.call, func_name, **kwargs)
```

### 9.2 Müşteri sorgu (`customers.py`)
```python
from app.sap.base import CustomerDTO
from app.sap.ecc.connection import call_rfc
from app.sap.ecc.padding import pad_kunnr, unpad_kunnr


async def search_customers(query: str, top: int = 50) -> list[CustomerDTO]:
    """BAPI_CUSTOMER_GETLIST + isim filtresi.

    Geniş katalogda yavaş olabilir; canlı SAP yerine `bp_cache`'ten okumayı
    tercih ediyoruz (Sprint 3'te master sync).
    """
    result = await call_rfc(
        "BAPI_CUSTOMER_GETLIST",
        IDRANGE=[{"SIGN": "I", "OPTION": "CP", "LOW": f"*{query.upper()}*"}],
        MAXROWS=top,
    )
    return [
        CustomerDTO(
            code=unpad_kunnr(row["CUSTOMER"]),
            name=row["NAME"],
            raw=row,
        )
        for row in result.get("ADDRESSDATA", [])
    ]


async def get_customer(code: str) -> CustomerDTO | None:
    kunnr = pad_kunnr(code)
    result = await call_rfc("BAPI_CUSTOMER_GETDETAIL2", CUSTOMERNO=kunnr)
    addr = result.get("CUSTOMERADDRESS") or {}
    if not addr.get("CUSTOMER"):
        return None
    return CustomerDTO(
        code=unpad_kunnr(addr["CUSTOMER"]),
        name=addr.get("NAME") or "",
        tax_id=addr.get("TAX_NUMBER_1") or addr.get("VAT_REG_NO"),
        email=addr.get("E_MAIL"),
        phone=addr.get("TELEPHONE"),
        raw=result,
    )
```

### 9.3 Malzeme sorgu (`materials.py`)
```python
from app.sap.base import ItemDTO, AvailabilityDTO
from app.sap.ecc.connection import call_rfc
from app.sap.ecc.padding import pad_matnr, unpad_matnr


async def search_materials(query: str, top: int = 50) -> list[ItemDTO]:
    result = await call_rfc(
        "BAPI_MATERIAL_GETLIST",
        MATNRLIST=[],
        MATNRSELECTION=[{"SIGN": "I", "OPTION": "CP", "MATNR_LOW": f"*{query.upper()}*"}],
        # MAXROWS pyrfc'de bazı versiyonlarda yok — kısıtlama uygulama tarafında
    )
    return [
        ItemDTO(
            code=unpad_matnr(row["MATERIAL"]),
            name=row.get("MATL_DESC") or "",
            raw=row,
        )
        for row in (result.get("MATNRLIST") or [])[:top]
    ]


async def get_material(code: str) -> ItemDTO | None:
    matnr = pad_matnr(code)
    result = await call_rfc("BAPI_MATERIAL_GET_DETAIL", MATERIAL=matnr)
    data = result.get("MATERIAL_GENERAL_DATA")
    if not data:
        return None
    return ItemDTO(
        code=unpad_matnr(matnr),
        name=data.get("MATL_DESC") or "",
        barcode=data.get("EAN_UPC"),
        unit=data.get("BASE_UOM"),
        raw=result,
    )


async def get_availability(code: str, *, plant: str | None = None) -> AvailabilityDTO:
    matnr = pad_matnr(code)
    result = await call_rfc(
        "BAPI_MATERIAL_AVAILABILITY",
        PLANT=plant or "1000",
        MATERIAL=matnr,
        UNIT="EA",
    )
    return AvailabilityDTO(
        code=code,
        available_qty=float(result.get("AV_QTY_PLT") or 0),
        in_stock_qty=float(result.get("ENDLEAD_TME") or 0) if "ENDLEAD_TME" in result else None,
        committed_qty=float(result.get("COMMT_QTY") or 0) if "COMMT_QTY" in result else None,
    )
```

### 9.4 Sales Order yazımı (`sales_orders.py`)
```python
from app.core.config import settings
from app.sap.base import SalesOrderRequest, SalesOrderResult
from app.sap.ecc.connection import pool
from app.sap.ecc.errors import parse_return_messages
from app.sap.ecc.padding import pad_kunnr, pad_matnr
import asyncio


async def create_sales_order(req: SalesOrderRequest) -> SalesOrderResult:
    opts = {
        "doc_type": settings.sap_ecc_default_doc_type,
        "sales_org": settings.sap_ecc_default_sales_org,
        "distr_chan": settings.sap_ecc_default_distr_chan,
        "division": settings.sap_ecc_default_division,
        **req.backend_options,
    }
    ship_to = opts.get("ship_to_code", req.customer_code)

    header_in = {
        "DOC_TYPE": opts["doc_type"],
        "SALES_ORG": opts["sales_org"],
        "DISTR_CHAN": opts["distr_chan"],
        "DIVISION": opts["division"],
        "PURCH_NO_C": req.reference_no or "",
        "REQ_DATE_H": (req.due_date or req.doc_date).strftime("%Y%m%d"),
    }
    header_inx = {k: "X" for k in header_in} | {"UPDATEFLAG": "I"}

    partners = [
        {"PARTN_ROLE": "AG", "PARTN_NUMB": pad_kunnr(req.customer_code)},
        {"PARTN_ROLE": "WE", "PARTN_NUMB": pad_kunnr(ship_to)},
    ]

    items_in, items_inx, schedules_in, schedules_inx = [], [], [], []
    for i, line in enumerate(req.lines, start=1):
        item_no = f"{i*10:06d}"  # 000010, 000020, …
        items_in.append({
            "ITM_NUMBER": item_no,
            "MATERIAL": pad_matnr(line.item_code),
            "TARGET_QTY": str(line.quantity),
        })
        items_inx.append({
            "ITM_NUMBER": item_no,
            "UPDATEFLAG": "I",
            "MATERIAL": "X",
            "TARGET_QTY": "X",
        })
        schedules_in.append({
            "ITM_NUMBER": item_no,
            "SCHED_LINE": "0001",
            "REQ_QTY": str(line.quantity),
        })
        schedules_inx.append({
            "ITM_NUMBER": item_no,
            "SCHED_LINE": "0001",
            "UPDATEFLAG": "I",
            "REQ_QTY": "X",
        })

    async with pool.acquire() as conn:
        # BAPI çağrısı sync; thread'e at
        result = await asyncio.to_thread(
            conn.call,
            "BAPI_SALESORDER_CREATEFROMDAT2",
            ORDER_HEADER_IN=header_in,
            ORDER_HEADER_INX=header_inx,
            ORDER_PARTNERS=partners,
            ORDER_ITEMS_IN=items_in,
            ORDER_ITEMS_INX=items_inx,
            ORDER_SCHEDULES_IN=schedules_in,
            ORDER_SCHEDULES_INX=schedules_inx,
        )

        errors, warnings = parse_return_messages(result.get("RETURN", []))
        sales_doc = result.get("SALESDOCUMENT")

        if errors or not sales_doc:
            await asyncio.to_thread(conn.call, "BAPI_TRANSACTION_ROLLBACK")
            # SAPError fırlat (üst katman Türkçe gösterecek)
            raise build_sap_error_from(errors, raw=result)

        await asyncio.to_thread(conn.call, "BAPI_TRANSACTION_COMMIT", WAIT="X")

    return SalesOrderResult(
        doc_id=sales_doc,
        doc_number=sales_doc,
        warnings=warnings,
        raw=result,
    )
```

### 9.5 Hata mapping (`errors.py`)
```python
from app.sap.errors import SAPError


# Yaygın ECC mesaj sınıflarını TR'ye çevir
ECC_MESSAGE_MAP = {
    "V1042": "Müşteri bulunamadı.",
    "V4220": "Malzeme satılabilir değil ya da satış görünümünde yok.",
    "VK087": "Fiyat koşulu eksik.",
    "V1": "Doğrulama hatası (genel).",
}


def parse_return_messages(return_table: list[dict]) -> tuple[list[dict], list[str]]:
    """RETURN[] tablosunu E/A → errors, W/I → warnings olarak ayırır.
    S (success) yutulur."""
    errors, warnings = [], []
    for msg in return_table:
        if msg.get("TYPE") in ("E", "A"):
            errors.append(msg)
        elif msg.get("TYPE") == "W":
            warnings.append(_format(msg))
    return errors, warnings


def _format(msg: dict) -> str:
    code = f"{msg.get('ID')}{msg.get('NUMBER')}"
    tr = ECC_MESSAGE_MAP.get(code) or msg.get("MESSAGE", "")
    return f"{tr} (SAP: {msg.get('MESSAGE')})"


def build_sap_error_from(errors: list[dict], raw: dict) -> SAPError:
    if not errors:
        return SAPError("Bilinmeyen SAP hatası.", status_code=502, raw=raw)
    first = errors[0]
    code = f"{first.get('ID')}{first.get('NUMBER')}"
    tr = ECC_MESSAGE_MAP.get(code) or first.get("MESSAGE", "")
    return SAPError(tr, code=code, status_code=400, raw={"errors": errors, "raw": raw})
```

### 9.6 Padding (`padding.py`)
```python
def pad_kunnr(code: str) -> str:
    """ECC müşteri kodu 10-haneli sıfır dolgulu olmalı.

    >>> pad_kunnr("1")
    '0000000001'
    """
    digits = code.lstrip("0") or "0"
    return digits.rjust(10, "0")


def unpad_kunnr(kunnr: str) -> str:
    """SAP'tan dönen '0000000001' → '1' (görüntüleme için)."""
    return kunnr.lstrip("0") or "0"


def pad_matnr(code: str) -> str:
    """Malzeme kodu 18-haneli sıfır dolgulu (numeric malzemelerde).

    Alphanumeric matnr varsa olduğu gibi bırak.
    """
    if code.isdigit():
        return code.rjust(18, "0")
    return code


def unpad_matnr(matnr: str) -> str:
    if matnr.isdigit():
        return matnr.lstrip("0") or "0"
    return matnr
```

---

## 10. Agent ve Servis Etkileri

### 10.1 Değişmeyenler
- `agents/orchestrator.py` — sadece DTO görür
- `agents/customer_matcher.py` — `bp_cache` tablosuna bakar (zaten DTO-benzeri yapı)
- `agents/product_matcher.py` — `item_cache` tablosuna bakar
- `agents/pricing.py`, `approval.py`, `notification.py` — SAP'la doğrudan konuşmuyor
- Frontend — `lib/types.ts`'deki tipler DTO ile uyumlu

### 10.2 Değişenler
- `agents/sap_writer.py` — `B1Backend.create_sales_order()` veya `ECCBackend.create_sales_order()` doğrudan; ortak `get_backend()` üzerinden
- `agents/stock.py` — `get_availability()` ortak DTO döner
- `services/documents.py` (`_build_sap_payload`) → silinir; payload artık `SalesOrderRequest` DTO'su; conversion adapter'da
- `api/routes/sap.py` — `BusinessPartnersModule` direkt çağırmıyor, `get_backend().search_customers(...)` çağırıyor
- `workers/tasks.py` (`_build_sap_payload`) → DTO build'e döner

### 10.3 Migration kodu örneği
Önce (B1-only):
```python
async with pool.acquire() as client:
    module = SalesOrdersModule(client)
    response = await module.create(payload_dict)
return AgentResult(data={"sap": {"DocEntry": response["DocEntry"], ...}})
```

Sonra (adapter):
```python
backend = await get_backend()
result = await backend.create_sales_order(request_dto)
return AgentResult(data={
    "sap": {
        "doc_id": result.doc_id,
        "doc_number": result.doc_number,
        "backend": backend.backend_name,
    }
})
```

---

## 11. DB Şema Etkileri

`bp_cache` ve `item_cache` zaten **vendor-bağımsız alan adlarına yakın** (`card_code`, `card_name`, `item_code`, `item_name`). İki dokunuş yeterli:

```sql
ALTER TABLE bp_cache ADD COLUMN backend VARCHAR(10) NOT NULL DEFAULT 'b1';
ALTER TABLE item_cache ADD COLUMN backend VARCHAR(10) NOT NULL DEFAULT 'b1';
ALTER TABLE sap_submissions ADD COLUMN backend VARCHAR(10) NOT NULL DEFAULT 'b1';
```

Faz 3 multi-tenant'ta `(tenant_id, backend, code)` composite primary key olur.

`raw` JSONB sütunu adapter'ın kendi formatını taşır — değişiklik yok.

---

## 12. Idempotency Stratejisi

| Strateji | B1 | ECC |
|---|---|---|
| Native key | ❌ (`SAP-IDEMPOTENT-KEY` header desteği yok, 409 mevcut belge kontrolü tek yol) | ❌ (BAPI key kabul etmez) |
| Bizim çözüm | Redis cache (`sap:idem:order:<hash>` → DocEntry) | Aynı Redis cache; ek olarak `BAPI_SALESORDER_GETLIST` ile duplicate yakalama opsiyonu |
| 2-fazlı commit risk | yok (tek POST) | rollback'i de cache'lemeli — yarıda kalan transaction'ı işaretle |

Yeni davranış (`IdempotencyStore`):
1. Acquire `__pending__` → çağrı
2. Başarılı → result yaz, TTL 24sa
3. Hata → key sil, retry yapılabilir
4. Pool ölürse `__pending__` 24sa kalır; manuel kuyruğa düşer

Bu strateji **iki backend için de aynı**, fark yok.

---

## 13. pyrfc + SAP NWRFC SDK Kurulumu

### 13.1 Yerel geliştirme (macOS)
1. SAP Marketplace'ten NWRFC SDK indir (`nwrfc750P_*-XXXX.zip`) — SAP partner hesabı gerekir.
2. `/usr/local/sap/nwrfcsdk/` altına aç.
3. `~/.zshrc`:
   ```bash
   export SAPNWRFC_HOME=/usr/local/sap/nwrfcsdk
   export DYLD_LIBRARY_PATH=$SAPNWRFC_HOME/lib:$DYLD_LIBRARY_PATH
   ```
4. `pip install pyrfc`

Sorunlu olmaya meyilli. **Önerim: Docker.**

### 13.2 Docker (önerilen)
`docker/Dockerfile.backend.ecc`:
```dockerfile
FROM python:3.12-slim

# SAP NWRFC SDK kopyala (repo'da DEĞİL — build-arg veya secret mount)
ARG NWRFC_SDK_PATH=./vendor/nwrfcsdk
COPY $NWRFC_SDK_PATH /usr/local/sap/nwrfcsdk

ENV SAPNWRFC_HOME=/usr/local/sap/nwrfcsdk
ENV LD_LIBRARY_PATH=/usr/local/sap/nwrfcsdk/lib:$LD_LIBRARY_PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libxml2 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/pyproject.toml /app/
RUN pip install --no-cache-dir -e ".[ecc]"

COPY backend/ /app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`pyproject.toml` opsiyonel deps:
```toml
[project.optional-dependencies]
ecc = ["pyrfc>=3.3"]
```

Bu sayede B1-only müşteri pyrfc'siz Docker image kullanır; ECC müşteri ayrı image. **SDK repo'ya commit edilmez** (lisans + boyut).

### 13.3 Lisans uyarısı
SAP NWRFC SDK redistribution'ı kısıtlı. Üretimde müşteri kendi SAP lisansı altında SDK'yı sağlar; bizim Docker image'ında SDK olmaz, runtime'da volume mount edilir:
```yaml
services:
  backend:
    volumes:
      - /opt/sap/nwrfcsdk:/usr/local/sap/nwrfcsdk:ro
```

---

## 14. Connection Pool Stratejisi

| Boyut | B1 | ECC |
|---|---|---|
| Açık session/connection limiti | SAP B1 lisansı (4–8 slot) | SAP work process limiti (sistem genelinde 30–60) |
| Idle reuse | http session pool (mevcut) | RFC connection pool (yeni) |
| Re-auth | 401 → re-login | RFC connection drop → recreate |
| Block model | async (httpx) | sync (pyrfc) → `asyncio.to_thread` |
| Önerilen havuz boyutu | 4 (config) | 4–6 (config) |

ECC'de blocking pyrfc çağrılarını ThreadPoolExecutor'a yönlendirip event loop'u serbest bırakmak kritik.

---

## 15. Frontend Etkileri (Minimal)

- `lib/types.ts` — `BusinessPartner` ve `Item` arayüzleri DTO'ya hizalanır: `CardCode` → `code`, `CardName` → `name`, vb. **Veya** alias bırakırız (`code === CardCode`).
- API yanıt formatı: `/api/sap/business-partners` artık `[{code, name, tax_id, ...}]` döner.
- Sidebar/Settings — Backend bilgisi (`b1` / `ecc`) gösterilebilir (Settings sayfasında badge).

Frontend için **breaking change minimumda**. Backend'in alan adlarını yumuşak şekilde değiştirmek 1-2 saat iş.

---

## 16. Migration Planı (Sprint Sırası)

Toplam efor: **1.5–2 gün** (sen B1 testlerini yaparken yapılabilir).

| Sıra | İş | Süre | Etkilenenler | Status |
|---|---|---|---|---|
| 1 | `app/sap/base.py` — Protocol + DTO'lar | 1 sa | yeni dosya | hazır |
| 2 | `app/sap/b1/` altına mevcut B1 kodunu taşı | 1 sa | imports update | hazır |
| 3 | `B1Backend` adapter + factory | 2 sa | adapter.py | hazır |
| 4 | `agents/sap_writer.py` + `services/documents.py` → DTO bazlı | 1.5 sa | iki dosya | hazır |
| 5 | `api/routes/sap.py` → `get_backend()` çağırır | 30 dk | tek dosya | hazır |
| 6 | Frontend `lib/types.ts` alan rename + tests | 1 sa | tipler | hazır |
| 7 | **B1 testlerini yeşil tut** (regresyon) | — | mevcut 66 test | bekleyen |
| 8 | `app/sap/ecc/connection.py` + `padding.py` | 1.5 sa | yeni | bekleyen |
| 9 | `customers.py` + unit test | 1 sa | yeni | bekleyen |
| 10 | `materials.py` + `availability.py` + tests | 1.5 sa | yeni | bekleyen |
| 11 | `sales_orders.py` (BAPI çağrısı) + tests (mock pyrfc) | 2 sa | yeni | bekleyen |
| 12 | `quotations.py` (`BAPI_QUOTATION_CREATEFROMDATA2`) | 1 sa | yeni | bekleyen |
| 13 | `errors.py` + RETURN tablosu parser + TR mapping | 1 sa | yeni | bekleyen |
| 14 | Docker image ECC variant + NWRFC SDK volume | 1 sa | docker | bekleyen |
| 15 | Gerçek ECC test sunucusuyla E2E | 1.5 sa | manuel | bekleyen |

### Sprint 1 (sen B1 test ederken):
**Sıra 1–6:** B1 adapter refactor. Mevcut 66 test yeşil kalır. Sen test ederken bozulmaz.

### Sprint 2 (B1 testin bittikten sonra):
**Sıra 7–15:** ECC adapter. Senin verdiğin örnek kod referans.

---

## 17. Risk Analizi

| Risk | Seviye | Azaltma |
|---|---|---|
| pyrfc kurulumu macOS'ta çalışmaz | YÜKSEK | Docker zorunlu; native build sadece Linux'ta |
| NWRFC SDK lisansı | YÜKSEK | Müşteri sağlar; image'ımıza commit etmeyiz |
| ECC versiyonu farklı BAPI sürümü ister (örn. CREATEFROMDAT3) | ORTA | Config'ten BAPI adı seçilebilir; v2 default |
| Connection drop → uzun süreli takılma | ORTA | Timeout (30sn) + retry tek seferlik + circuit breaker |
| Schedule line zorunluluğu (sevkiyat senaryosu yoksa) | ORTA | Tek dummy schedule line (current code'daki gibi) |
| Sales Org / Distr Chan müşteriye göre değişir | DÜŞÜK | `backend_options` ile request bazında override |
| MATNR padding hatası → "malzeme yok" | DÜŞÜK | `pad_matnr` + alphanumeric tespit |
| 2-fazlı commit yarıda kalır (network drop) | DÜŞÜK | Idempotency cache + `BAPI_SALESORDER_GETLIST` retry tarama |
| RETURN tablosu W (warning) ile gelen success'i hata sanmak | DÜŞÜK | Yalnız E/A → error, W → warning, S → yutulur |
| AI doc reader ECC alanlarını bilmiyor (Sales Org gibi) | DÜŞÜK | Config'ten default; PDF'te yoksa otomatik atanır |

---

## 18. Açık Sorular (Cevaplanmalı)

1. **Sen B1 testini bitirir bitirmez ECC'ye geçer miyiz, yoksa B1 pilotu sonrası mı?**
   - B1 pilot canlı olduktan sonra ECC'ye geçmek riski azaltır.
   - Ama paralel ilerleyebilirsek 2 hafta kazanırız.
2. **ECC test sunucusu (5.180.184.100) public mi, VPN mi?**
   - Public ise direkt bağlanırız; VPN'lı ise Docker network ayarı gerekli.
3. **Müşteri ECC kullanıyorsa AI doc reader'a "müşteri SAP organizasyonu" bilgilerini de mi çıkartmalı?**
   - Hayır. `backend_options` config-default'tan gelir, AI sadece müşteri/ürün/miktar/fiyat odaklanır.
4. **ECC'de Quotation BAPI farklı (`BAPI_QUOTATION_CREATEFROMDATA2`). Quotation flow'unu hemen mi yoksa Faz 2'de mi yaparız?**
   - MVP: sales_order. Quotation Faz 2.
5. **ECC'de stok sorgu standardı plant + storage location ister. Hangi plant'i varsayalım?**
   - Config'ten: `SAP_ECC_DEFAULT_PLANT=1000`.
6. **Müşterinin S/4HANA versiyonu varsa, RFC yerine OData Gateway tercih edilebilir mi?**
   - Evet. `SAP_BACKEND=s4_odata` 3. backend olarak eklenebilir. Faz 2 hedefi.
7. **Geçmiş B1 testlerinde gerçek SAP'a bağlanıldı mı?**
   - Cevabını bekliyorum (paralel olarak `curl /Login` ile test ediyoruz).

---

## 19. Tahminler ve Sonraki Adım

**Eforun:**
- Sprint 1 (B1 refactor): 0.5 gün → senin testini bozmadan tamamlanır
- Sprint 2 (ECC adapter): 1 gün → senin verdiğin örnek kodu referans alarak
- Test + E2E: 0.5 gün (gerçek ECC sunucusunda)

**Önerilen sıra:**
1. ✅ Bu doküman (şimdi)
2. ⏭ Sen B1 ile lokal test başlat (`.env` doldur, `alembic upgrade head`, `uvicorn`, PDF yükle)
3. ⏭ Sen test ederken ben **Sprint 1**'i başlatayım — B1 refactor (testler yeşil kalır)
4. ⏭ B1 pilot canlı + Sen ECC'ye geçmek istediğin gün → Sprint 2

**Karar:** Bu plan onaylanırsa Sprint 1'i şimdi başlatabilirim — senin B1 testin bozulmaz (gerçek SAP bağlantısı yoksa zaten test edilen kısımlar değişmez). Onay ver, başlayayım.

---

**Bu doküman canlıdır.** ECC adapter implementasyonu sırasında öğrenilen detaylar buraya işlenir (özellikle BAPI versiyonu farklılıkları, müşteri-özel field mapping).
