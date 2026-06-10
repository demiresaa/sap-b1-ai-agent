"""Session pool — SAP lisans bazlı eş zamanlı session limitini yönetir."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.tenant_context import current_tenant
from app.core.vault import get_tenant_sap_credentials
from app.sap.client import SAPServiceLayerClient

logger = logging.getLogger(__name__)


class SessionPool:
    """Max N eş zamanlı oturum tutar; idle olanı tenant bazında yeniden kullanır.

    Multi-tenant: her tenant kendi kimlik bilgileriyle ayrı SAP oturumu açar.
    Vault disabled veya tenant yoksa settings env fallback'i kullanılır.
    """

    def __init__(self, max_sessions: int | None = None) -> None:
        self._max = max_sessions or settings.sap_max_concurrent_sessions
        self._semaphore = asyncio.Semaphore(self._max)
        # tenant_key → idle client listesi (None = single-tenant/fallback)
        self._idle: dict[str | None, list[SAPServiceLayerClient]] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[SAPServiceLayerClient]:
        tenant = current_tenant()
        tenant_key: str | None = tenant.slug if tenant else None

        # Vault'tan veya env'den kimlik bilgilerini al
        if tenant_key:
            try:
                credentials = get_tenant_sap_credentials(tenant_key)
                base_url = credentials.get("sl_base_url") or settings.sap_service_layer_url
            except Exception:
                credentials = None
                base_url = settings.sap_service_layer_url
        else:
            credentials = None
            base_url = settings.sap_service_layer_url

        await self._semaphore.acquire()
        client: SAPServiceLayerClient | None = None
        login_failed = False
        try:
            async with self._lock:
                idle = self._idle.get(tenant_key, [])
                if idle:
                    client = idle.pop()
                    self._idle[tenant_key] = idle
            if client is None:
                client = SAPServiceLayerClient(base_url=base_url, credentials=credentials)
                try:
                    await client.__aenter__()
                except Exception:
                    login_failed = True
                    try:
                        if client._client is not None:
                            await client._client.aclose()
                    except Exception as cleanup_exc:
                        logger.warning("client cleanup hatası: %s", cleanup_exc)
                    client = None
                    raise
            yield client
        finally:
            if client is not None and not login_failed:
                async with self._lock:
                    self._idle.setdefault(tenant_key, []).append(client)
            self._semaphore.release()

    async def close_all(self) -> None:
        async with self._lock:
            for idle_list in self._idle.values():
                while idle_list:
                    client = idle_list.pop()
                    await client.__aexit__(None, None, None)
            self._idle.clear()


pool = SessionPool()
