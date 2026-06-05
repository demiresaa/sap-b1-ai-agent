"""Pricing agent — eşik aşımı testleri (DB mock)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentContext
from app.agents.pricing import PricingAgent
from app.agents.schemas import ExtractedLine, ProductMatch


def _make_db(item_price: float | None) -> MagicMock:
    """ItemCache lookup'ı için sahte AsyncSession."""
    item = MagicMock()
    item.raw = {"LastPurchasePrice": item_price} if item_price is not None else None

    scalars = MagicMock()
    scalars.first.return_value = item if item.raw is not None else None
    result = MagicMock()
    result.scalars.return_value = scalars

    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_pricing_flags_large_delta() -> None:
    line = ExtractedLine(line_no=1, description="Vana", quantity=2, unit_price=150)
    match = ProductMatch(line_no=1, item_code="A001", score=1.0)
    db = _make_db(item_price=100.0)

    result = await PricingAgent().run(
        AgentContext(document_id="doc-1"),
        lines=[line],
        matches=[match],
        db=db,
    )

    assert result.success
    assert result.needs_human is True
    check = result.data["checks"][0]
    assert check["breaches_threshold"] is True
    assert check["delta_pct"] is not None and abs(check["delta_pct"] - 50.0) < 0.1


@pytest.mark.asyncio
async def test_pricing_passes_within_threshold() -> None:
    line = ExtractedLine(line_no=1, description="X", quantity=1, unit_price=102)
    match = ProductMatch(line_no=1, item_code="A002", score=1.0)
    db = _make_db(item_price=100.0)

    result = await PricingAgent().run(
        AgentContext(document_id="doc-2"),
        lines=[line],
        matches=[match],
        db=db,
    )
    assert result.needs_human is False
    assert result.data["checks"][0]["breaches_threshold"] is False


@pytest.mark.asyncio
async def test_pricing_flags_high_discount() -> None:
    line = ExtractedLine(line_no=1, description="X", quantity=1, unit_price=100, discount_pct=20)
    match = ProductMatch(line_no=1, item_code="A003", score=1.0)
    db = _make_db(item_price=100.0)

    result = await PricingAgent().run(
        AgentContext(document_id="doc-3"), lines=[line], matches=[match], db=db
    )
    assert result.needs_human is True
    assert "İskonto" in (result.data["checks"][0]["note"] or "")
