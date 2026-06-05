"""SAP Service Layer hata yönetimi ve Türkçe çevirisi."""
from __future__ import annotations

from typing import Any

import httpx

# SAP B1 hata kodu → Türkçe açıklama
SAP_ERROR_MAP: dict[str, str] = {
    "-10": "Geçersiz veri: zorunlu alan eksik veya yanlış format.",
    "-12": "Bu kayıt zaten var (anahtar tekrarı).",
    "-1029": "Müşteri (BusinessPartner) bulunamadı.",
    "-1102": "Stok kartı (Item) bulunamadı.",
    "-2028": "İş kuralı ihlali: belge oluşturulamadı.",
    "-2035": "Stok yetersiz veya tarih çakışması.",
    "-5002": "Veritabanı kısıtlaması: zorunlu UDF veya constraint ihlali.",
    "-5008": "Bu belge zaten oluşturulmuş (duplicate).",
    "-5564": "Belge kapalı veya iptal edilmiş, değişiklik yapılamaz.",
    "-5566": "Para birimi uyuşmazlığı.",
    "100000001": "Service Layer iç hatası, yeniden deneyin.",
    "301": "Yetkiniz yok.",
    "302": "Lisans yetersiz veya kullanıcı oturumu bulunamadı.",
    "304": "Bu yöntem desteklenmiyor (örn. Invoice DELETE).",
}

# HTTP durum kodu → kullanıcıya gösterilecek mesaj
HTTP_STATUS_MAP: dict[int, str] = {
    400: "İstek hatalı: gönderilen veri SAP kurallarına uymuyor.",
    401: "Oturum süresi doldu, yeniden bağlanılıyor.",
    403: "Bu işlem için yetkiniz yok.",
    404: "Kayıt bulunamadı.",
    405: "Bu yöntem SAP tarafında desteklenmiyor.",
    409: "Kayıt başka bir kullanıcı tarafından güncellendi (conflict).",
    500: "SAP Service Layer iç hatası.",
    502: "SAP Service Layer'a ulaşılamıyor.",
    503: "SAP Service Layer geçici olarak hizmet veremiyor.",
    504: "SAP Service Layer zaman aşımı.",
}


class SAPError(Exception):
    """SAP Service Layer'dan dönen hata. `message_tr` kullanıcıya gösterilir."""

    def __init__(
        self,
        message_tr: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        raw: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message_tr)
        self.message_tr = message_tr
        self.code = code
        self.status_code = status_code
        self.raw = raw or {}

    def __repr__(self) -> str:
        return f"SAPError(code={self.code!r}, status={self.status_code}, msg={self.message_tr!r})"


def translate_sap_error(error_payload: dict[str, Any] | None) -> tuple[str, str | None]:
    """SAP hata JSON'unu (kullanıcı mesajı, hata kodu) tuple'ına çevirir.

    SAP error format: `{"error": {"code": "-10", "message": {"value": "..."}}}`
    """
    if not error_payload:
        return "SAP'tan bilinmeyen hata.", None
    err = error_payload.get("error", {}) or {}
    code = err.get("code")
    code_str = str(code) if code is not None else None
    raw_message = ""
    message = err.get("message")
    if isinstance(message, dict):
        raw_message = message.get("value", "") or ""
    elif isinstance(message, str):
        raw_message = message
    tr = SAP_ERROR_MAP.get(code_str or "")
    if tr:
        return (f"{tr} (SAP: {raw_message})" if raw_message else tr), code_str
    if raw_message:
        return f"SAP hatası ({code_str}): {raw_message}", code_str
    return f"SAP hatası ({code_str}).", code_str


def sap_error_from_response(response: httpx.Response) -> SAPError:
    """`httpx.Response`'tan `SAPError` üretir."""
    payload: dict[str, Any] | None = None
    try:
        payload = response.json()
    except Exception:
        payload = None
    message_tr, code = translate_sap_error(payload)
    if not payload and response.status_code in HTTP_STATUS_MAP:
        message_tr = HTTP_STATUS_MAP[response.status_code]
    return SAPError(
        message_tr,
        code=code,
        status_code=response.status_code,
        raw=payload or {"text": response.text[:500]},
    )
