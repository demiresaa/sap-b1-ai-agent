"""HashiCorp Vault istemci wrapper'ı.

Secret okuma: KV v2 engine. Cache TTL ile in-memory cache (varsayılan 5 dk).
Tenant başına path: `kv/data/tenants/<slug>/sap` → username/password/company_db/sl_base_url.
Global path: `kv/data/global/openrouter` → api_key.

Vault disabled (config'te) ise tüm `get_secret` çağrıları config.py'deki fallback env'lere
döner — yani tek-tenant MVP davranışı bozulmaz.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import hvac
from hvac.exceptions import InvalidPath, VaultError

from app.core.config import settings


class VaultUnavailable(RuntimeError):
    """Vault'a ulaşılamadı veya path yok."""


@dataclass(slots=True)
class _CacheEntry:
    data: dict[str, Any]
    expires_at: float


class VaultClient:
    """Senkron hvac istemcisi etrafında ince bir cache + fallback katmanı.

    hvac async değil; secret okuma seyrek olduğu için thread-safe bir cache yeterli.
    """

    def __init__(self) -> None:
        self._cache: dict[str, _CacheEntry] = {}
        self._client: hvac.Client | None = None

    def _get_client(self) -> hvac.Client:
        if self._client is None:
            self._client = hvac.Client(url=settings.vault_addr, token=settings.vault_token)
        return self._client

    def is_enabled(self) -> bool:
        return settings.vault_enabled and bool(settings.vault_token)

    def get_secret(self, path: str) -> dict[str, Any]:
        """KV v2 path'inden secret oku. Path örnek: `tenants/elekon/sap`.

        Cache miss durumunda Vault'a gider, hit durumunda cached değeri döner.
        Vault disabled ise VaultUnavailable atar — çağıran fallback yapar.
        """
        if not self.is_enabled():
            raise VaultUnavailable("Vault disabled — fallback'e düş")

        now = time.monotonic()
        entry = self._cache.get(path)
        if entry and entry.expires_at > now:
            return entry.data

        try:
            client = self._get_client()
            resp = client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=settings.vault_kv_mount,
                raise_on_deleted_version=True,
            )
        except InvalidPath as exc:
            raise VaultUnavailable(f"Vault path bulunamadı: {path}") from exc
        except VaultError as exc:
            raise VaultUnavailable(f"Vault hatası ({path}): {exc}") from exc

        data: dict[str, Any] = resp["data"]["data"]
        self._cache[path] = _CacheEntry(
            data=data,
            expires_at=now + settings.vault_secret_cache_ttl_seconds,
        )
        return data

    def invalidate(self, path: str | None = None) -> None:
        if path is None:
            self._cache.clear()
        else:
            self._cache.pop(path, None)


vault = VaultClient()


def get_tenant_sap_credentials(tenant_slug: str) -> dict[str, str]:
    """Tenant SAP credential'ını Vault'tan veya env fallback'ten oku."""
    try:
        return vault.get_secret(f"tenants/{tenant_slug}/sap")
    except VaultUnavailable:
        return {
            "username": settings.sap_username,
            "password": settings.sap_password,
            "company_db": settings.sap_company_db,
            "sl_base_url": settings.sap_service_layer_url,
        }


def get_openrouter_api_key() -> str:
    """OpenRouter API key Vault'tan veya env fallback."""
    try:
        data = vault.get_secret("global/openrouter")
        key = data.get("api_key", "")
        if key and key != "REPLACE_ME":
            return key
    except VaultUnavailable:
        pass
    return settings.openrouter_api_key
