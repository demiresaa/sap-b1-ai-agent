"""SAP B1 Service Layer HTTP istemcisi.

Tüm SAP modülleri bu sınıfı kullanır. Sorumlulukları:
  - Login/Logout (B1SESSION + ROUTEID cookies)
  - Otomatik re-login on 401 + bir kez retry
  - Transient hata (502/503/504/network) için exponential backoff retry
  - Hata yanıtlarını `SAPError`'a (Türkçe mesaj) çevirme
  - OData parametrelerini query string'e çevirme

Session pool tarafından sahiplenilir, doğrudan `__aenter__` yerine pool kullan.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.sap.errors import HTTP_STATUS_MAP, SAPError, sap_error_from_response

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10.0
CONNECT_TIMEOUT_SECONDS = 5.0
TRANSIENT_STATUS_CODES = {502, 503, 504}
MAX_RETRIES = 2  # Bağlanamıyorsa 30sn değil ~10sn'de pes et
BACKOFF_BASE_SECONDS = 1.0


class SAPServiceLayerClient:
    """Service Layer base client. Session pool tarafından yönetilir."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.sap_service_layer_url
        self._client: httpx.AsyncClient | None = None
        self._session_id: str | None = None
        self._route_id: str | None = None

    async def __aenter__(self) -> "SAPServiceLayerClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            verify=settings.sap_verify_ssl,
            timeout=httpx.Timeout(DEFAULT_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        await self.login()
        return self

    async def __aexit__(self, *_: Any) -> None:
        try:
            await self.logout()
        finally:
            if self._client:
                await self._client.aclose()

    @property
    def is_authenticated(self) -> bool:
        return self._session_id is not None

    async def login(self) -> None:
        """POST /Login → B1SESSION + ROUTEID cookies set edilir."""
        assert self._client is not None
        try:
            resp = await self._client.post(
                "/Login",
                json={
                    "CompanyDB": settings.sap_company_db,
                    "UserName": settings.sap_username,
                    "Password": settings.sap_password,
                },
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            raise SAPError(
                f"SAP Service Layer'a bağlanılamıyor ({self.base_url}). "
                "VPN bağlı mı, IP/port doğru mu kontrol edin.",
                status_code=503,
                raw={"error": str(exc), "url": self.base_url},
            ) from exc
        if resp.status_code != 200:
            raise sap_error_from_response(resp)
        self._session_id = resp.cookies.get("B1SESSION")
        self._route_id = resp.cookies.get("ROUTEID")
        logger.info(
            "SAP Service Layer login başarılı (session=%s)",
            self._session_id[:8] if self._session_id else None,
        )

    async def logout(self) -> None:
        if self._client and self._session_id:
            try:
                await self._client.post("/Logout")
            except Exception as exc:
                logger.warning("Logout sırasında hata yutuldu: %s", exc)
            self._session_id = None
            self._route_id = None

    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        return await self._request("GET", path, params=_clean_params(params))

    async def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=payload)

    async def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PATCH", path, json=payload)

    async def delete(self, path: str) -> None:
        await self._request("DELETE", path)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert self._client is not None
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._client.request(method, path, **kwargs)
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as exc:
                last_exc = exc
                logger.warning(
                    "SAP bağlantı hatası (%s) attempt=%s/%s",
                    type(exc).__name__,
                    attempt + 1,
                    MAX_RETRIES,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))
                continue

            if resp.status_code == 401:
                # Oturum düştü → bir kez re-login + retry
                await self.login()
                resp = await self._client.request(method, path, **kwargs)

            if resp.status_code in TRANSIENT_STATUS_CODES and attempt < MAX_RETRIES - 1:
                logger.warning(
                    "SAP transient hata %s, yeniden denenecek (attempt=%s)",
                    resp.status_code,
                    attempt + 1,
                )
                await asyncio.sleep(BACKOFF_BASE_SECONDS * (4 ** attempt))
                continue

            if resp.status_code >= 400:
                raise sap_error_from_response(resp)

            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()

        message = (
            f"SAP Service Layer'a ulaşılamıyor ({self.base_url}). "
            f"VPN bağlantınızı veya sunucu adresini kontrol edin."
        )
        raise SAPError(
            message,
            status_code=503,
            raw={"error": str(last_exc) if last_exc else "unknown", "url": self.base_url},
        )


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    """None değerli parametreleri ayıklar."""
    return {k: v for k, v in params.items() if v is not None}
