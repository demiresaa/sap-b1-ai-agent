"""FastAPI middleware'leri — rate limit, request id, structured access log.

Not: `BaseHTTPMiddleware` async SQLAlchemy session'larını boz(uy)or (greenlet
context kayboluyor). Bu yüzden saf ASGI middleware kullanıyoruz.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from app.core.rate_limit import RateLimiter

logger = logging.getLogger("access")

_AUTH_LIMITER = RateLimiter(max_calls=10, window_seconds=60)
_GENERAL_LIMITER = RateLimiter(max_calls=300, window_seconds=60)


def reset_rate_limiters() -> None:
    """Test fixture'ları için bucket'ları temizler."""
    _AUTH_LIMITER._calls.clear()
    _GENERAL_LIMITER._calls.clear()


def _client_key(scope: dict[str, Any]) -> str:
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-for":
            return value.decode().split(",")[0].strip()
    client = scope.get("client")
    if client:
        return client[0]
    return "anonymous"


class RateLimitMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith("/api/auth/login"):
            limiter = _AUTH_LIMITER
        elif path.startswith("/api/"):
            limiter = _GENERAL_LIMITER
        else:
            await self.app(scope, receive, send)
            return

        ok, retry = limiter.allow(_client_key(scope))
        if not ok:
            payload = json.dumps(
                {"detail": "Çok fazla istek, lütfen biraz bekleyin."}, ensure_ascii=False
            ).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json; charset=utf-8"),
                        (b"retry-after", str(int(retry) + 1).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": payload})
            return

        await self.app(scope, receive, send)


class RequestContextMiddleware:
    """Her isteğe `X-Request-Id` ekler ve access log basar."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                request_id = value.decode()
                break

        started = time.monotonic()
        status_holder: dict[str, int] = {"status": 500}

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "%s %s → %s in %dms (rid=%s)",
                scope.get("method", ""),
                scope.get("path", ""),
                status_holder["status"],
                duration_ms,
                request_id,
            )
