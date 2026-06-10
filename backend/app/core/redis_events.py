"""Redis pub/sub — belge işleme olaylarını WebSocket'e iletmek için.

Yayıncı (Celery worker / orchestrator): publish_document_event()
Abone (FastAPI WS handler): subscribe_document_events()

Kanal adı: doc:{document_id}
"""
from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: aioredis.ConnectionPool | None = None


def _get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
    return _pool


def _channel(document_id: str) -> str:
    return f"doc:{document_id}"


async def publish_document_event(document_id: str, event: dict[str, Any]) -> None:
    """Belge kanalına olay yayınlar. Hata durumunda log yazar, raise etmez."""
    try:
        r = aioredis.Redis(connection_pool=_get_pool())
        await r.publish(_channel(document_id), json.dumps(event))
    except Exception:
        logger.exception("[redis_events] publish başarısız doc=%s", document_id)


async def subscribe_document_events(document_id: str) -> AsyncIterator[dict[str, Any]]:
    """Belge kanalını dinler, gelen her JSON mesajı dict olarak yield eder.

    Kullanım: async for event in subscribe_document_events(doc_id): ...
    Çıkış: bağlantı kesildiğinde veya channel silindiğinde generator biter.
    """
    r = aioredis.Redis(connection_pool=_get_pool())
    async with r.pubsub() as pubsub:
        await pubsub.subscribe(_channel(document_id))
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                yield json.loads(message["data"])
