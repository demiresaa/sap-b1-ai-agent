"""CustomerMatcher — tax_id exact + fuzzy fallback."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentContext
from app.agents.customer_matcher import CustomerMatcherAgent
from app.agents.schemas import ExtractedCustomer


def _bp(card_code: str, name: str, tax_id: str | None = None, email: str | None = None) -> MagicMock:
    bp = MagicMock()
    bp.card_code = card_code
    bp.card_name = name
    bp.card_name_lower = name.lower()
    bp.federal_tax_id = tax_id
    bp.email_address = email
    return bp


def _scalar_result(items: list) -> MagicMock:
    scalars = MagicMock()
    scalars.first.return_value = items[0] if items else None
    scalars.all.return_value = items
    r = MagicMock()
    r.first.return_value = None  # `result.first()` (alias join'da kullanılan) → None
    r.scalars.return_value = scalars
    return r


@pytest.mark.asyncio
async def test_tax_id_exact_match_returns_score_1() -> None:
    bp = _bp("C100", "Acme A.Ş.", tax_id="1234567890")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result([bp]))

    result = await CustomerMatcherAgent().run(
        AgentContext(document_id="d"),
        customer=ExtractedCustomer(name="Acme", tax_id="1234567890"),
        db=db,
    )

    match = result.data["match"]
    assert match["card_code"] == "C100"
    assert match["strategy"] == "tax_id"
    assert match["score"] == 1.0
    assert result.needs_human is False


@pytest.mark.asyncio
async def test_fuzzy_name_falls_back_when_no_tax_match() -> None:
    # tax_id/email/alias kullanılmaz (customer'da yok). Tek db.execute fuzzy candidates için.
    bp1 = _bp("C200", "Karpuz Teknoloji Limited Şirketi")
    bp2 = _bp("C201", "Mavi Karpuz Sanayi A.Ş.")
    cand_result = _scalar_result([bp1, bp2])

    db = MagicMock()
    db.execute = AsyncMock(return_value=cand_result)

    result = await CustomerMatcherAgent().run(
        AgentContext(document_id="d"),
        customer=ExtractedCustomer(name="Karpuz Teknoloji"),
        db=db,
    )
    match = result.data["match"]
    assert match["strategy"] == "fuzzy_name"
    assert match["card_code"] == "C200"
    assert match["score"] >= 0.85


@pytest.mark.asyncio
async def test_unmatched_returns_candidates_and_needs_human() -> None:
    bp = _bp("C300", "Tamamen Farklı Şirket")
    cand_result = _scalar_result([bp])

    db = MagicMock()
    db.execute = AsyncMock(return_value=cand_result)

    result = await CustomerMatcherAgent().run(
        AgentContext(document_id="d"),
        customer=ExtractedCustomer(name="Asla Eşleşmeyecek İsim"),
        db=db,
    )
    match = result.data["match"]
    assert match["card_code"] is None
    assert result.needs_human is True
    assert len(match["candidates"]) >= 1
