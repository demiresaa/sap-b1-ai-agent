"""In-memory token-bucket rate limiter (tek instance için yeterli).

Faz 2 multi-tenant SaaS'ta Redis backed limit'e geçilecek.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    """Sliding window: `max_calls / window_seconds` başarılı çağrı."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, float]:
        """`(izin_var_mi, retry_after_seconds)`."""
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            bucket = self._calls[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_calls:
                retry_after = self.window - (now - bucket[0])
                return False, max(retry_after, 0.0)
            bucket.append(now)
            return True, 0.0
