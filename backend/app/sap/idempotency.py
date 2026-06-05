"""SAP POST'ları için idempotency anahtar yönetimi.

Aynı belgenin (PDF) iki kez yazılmasını önler. Anahtar:
  - frontend/agent tarafından üretilen UUID, veya
  - belge dosya hash'i + işlem tipi (`order:<sha256>`).

Redis'te `sap:idem:<key>` → {DocEntry, DocNum} TTL 24 saat saklanır.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from redis.asyncio import Redis

DEFAULT_TTL_SECONDS = 24 * 60 * 60
KEY_PREFIX = "sap:idem"


def make_key(operation: str, source: str) -> str:
    """`operation` (örn. 'order') + `source` (UUID veya hash) → namespaced key."""
    return f"{KEY_PREFIX}:{operation}:{source}"


def hash_payload(payload: dict[str, Any]) -> str:
    """Payload'tan deterministik SHA-256 hash üretir."""
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


class IdempotencyStore:
    """Redis tabanlı idempotency cache."""

    def __init__(self, redis: Redis, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl = ttl

    async def get(self, key: str) -> dict[str, Any] | None:
        raw = await self.redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def set(self, key: str, result: dict[str, Any]) -> None:
        await self.redis.set(key, json.dumps(result), ex=self.ttl)

    async def acquire(self, key: str) -> bool:
        """`SET NX` ile reserve eder. False dönerse başka biri işliyor."""
        return bool(await self.redis.set(key, "__pending__", nx=True, ex=self.ttl))
