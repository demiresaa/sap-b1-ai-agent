"""Prometheus metric tanımları.

`/metrics` endpoint'inden expose edilir (basic auth Faz 2'de).
"""
from __future__ import annotations

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    CONTENT_TYPE_LATEST = "text/plain"

    class _Noop:
        def labels(self, *a, **kw):
            return self

        def inc(self, *a, **kw):
            return None

        def observe(self, *a, **kw):
            return None

        def set(self, *a, **kw):
            return None

    Counter = Histogram = Gauge = lambda *a, **kw: _Noop()  # type: ignore[assignment]

    def generate_latest() -> bytes:  # type: ignore[misc]
        return b""


DOCUMENTS_PROCESSED = Counter(
    "documents_processed_total",
    "İşlenen belge sayısı.",
    labelnames=("status",),
)
SAP_SUBMISSIONS = Counter(
    "sap_submissions_total",
    "SAP submission denemesi.",
    labelnames=("kind", "outcome"),
)
LLM_CALLS = Counter(
    "llm_calls_total",
    "Anthropic API çağrısı.",
    labelnames=("agent", "model"),
)
LLM_COST_USD = Counter(
    "llm_cost_usd_total",
    "Toplam Anthropic maliyeti (USD).",
    labelnames=("model",),
)
AGENT_DURATION = Histogram(
    "agent_duration_seconds",
    "Agent süresi.",
    labelnames=("agent",),
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
)
SAP_API_LATENCY = Histogram(
    "sap_api_seconds",
    "SAP Service Layer çağrı süresi.",
    labelnames=("endpoint", "method"),
    buckets=(0.1, 0.5, 1, 2, 5, 10),
)
SAP_SESSIONS_IN_USE = Gauge(
    "sap_sessions_in_use",
    "Anlık SAP Service Layer session sayısı.",
)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
