"""Rate limit unit test."""
from __future__ import annotations

from app.core.rate_limit import RateLimiter


def test_allows_under_limit() -> None:
    limiter = RateLimiter(max_calls=3, window_seconds=60)
    for _ in range(3):
        ok, retry = limiter.allow("ip-1")
        assert ok
        assert retry == 0


def test_blocks_over_limit() -> None:
    limiter = RateLimiter(max_calls=2, window_seconds=60)
    limiter.allow("k")
    limiter.allow("k")
    ok, retry = limiter.allow("k")
    assert not ok
    assert retry > 0


def test_per_key_buckets_are_isolated() -> None:
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    assert limiter.allow("a")[0]
    assert not limiter.allow("a")[0]
    assert limiter.allow("b")[0]
