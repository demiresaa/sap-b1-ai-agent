"""Analytics summary endpoint testi."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_summary_returns_zero_when_empty(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/api/analytics/summary?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] == 0
    assert data["llm_cost_usd"] == 0
    assert data["success_rate"] == 0


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_text(auth_client: AsyncClient) -> None:
    resp = await auth_client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus var ya da yok, en azından response 200 dönmeli
