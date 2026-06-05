"""Session pool — SAP lisans bazlı eş zamanlı session limitini yönetir."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.core.config import settings
from app.sap.client import SAPServiceLayerClient

logger = logging.getLogger(__name__)


class SessionPool:
    """Max N eş zamanlı oturum tutar; idle olanı yeniden kullanır.

    Login fail eden client'i pool'a geri koymaz — bir sonraki acquire'ı
    bozuk session ile beklemeyelim.
    """

    def __init__(self, max_sessions: int | None = None) -> None:
        self._max = max_sessions or settings.sap_max_concurrent_sessions
        self._semaphore = asyncio.Semaphore(self._max)
        self._idle: list[SAPServiceLayerClient] = []
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[SAPServiceLayerClient]:
        await self._semaphore.acquire()
        client: SAPServiceLayerClient | None = None
        login_failed = False
        try:
            async with self._lock:
                if self._idle:
                    client = self._idle.pop()
            if client is None:
                client = SAPServiceLayerClient()
                try:
                    await client.__aenter__()
                except Exception:
                    login_failed = True
                    # Yarı açılmış httpx client'i kapat
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
                    self._idle.append(client)
            self._semaphore.release()

    async def close_all(self) -> None:
        async with self._lock:
            while self._idle:
                client = self._idle.pop()
                await client.__aexit__(None, None, None)


pool = SessionPool()
