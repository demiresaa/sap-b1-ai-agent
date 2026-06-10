"""CustomerMatcher — çıkarılan müşteri bilgisini SAP BusinessPartner ile eşler.

Stratejiler (sırayla, ilki bulduğunda durur):
  1. Vergi no (FederalTaxID) exact
  2. E-posta exact
  3. Müşteri alias tablosu (öğrenilmiş)
  4. Fuzzy ad (rapidfuzz token_set_ratio) > 85

Skor < 0.85 → human-in-the-loop.
"""
from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz, process
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.schemas import CustomerMatch, ExtractedCustomer
from app.db.models import BusinessPartnerCache, CustomerAlias

FUZZY_THRESHOLD = 85
HIGH_CONFIDENCE = 0.85
MAX_CANDIDATES = 5

# SAP CardType değerleri
CARD_TYPE_CUSTOMER = "cCustomer"
CARD_TYPE_SUPPLIER = "cSupplier"


class CustomerMatcherAgent(BaseAgent):
    name = "customer_matcher"

    async def _run(
        self,
        ctx: AgentContext,
        customer: ExtractedCustomer | dict[str, Any] | None = None,
        db: AsyncSession | None = None,
        mode: str = "customer",  # "customer" | "supplier"
        **kwargs: Any,
    ) -> AgentResult:
        if db is None:
            raise ValueError("db session zorunlu")
        if customer is None:
            raise ValueError("customer zorunlu")
        if isinstance(customer, dict):
            customer = ExtractedCustomer.model_validate(customer)

        card_type = CARD_TYPE_SUPPLIER if mode == "supplier" else CARD_TYPE_CUSTOMER
        match = CustomerMatch()

        if customer.tax_id:
            bp = await _by_tax_id(db, customer.tax_id, card_type=card_type)
            if bp:
                match = _exact(bp, "tax_id")

        if not match.card_code and customer.email:
            bp = await _by_email(db, customer.email, card_type=card_type)
            if bp:
                match = _exact(bp, "email")

        if not match.card_code and customer.name:
            alias_hit = await _by_alias(db, customer.name)
            if alias_hit:
                match = alias_hit

        if not match.card_code and customer.name:
            match = await _fuzzy_name(db, customer.name, card_type=card_type)

        if not match.card_code:
            cands = await _name_candidates(
                db, customer.name or "", limit=MAX_CANDIDATES, card_type=card_type
            )
            match.candidates = [_bp_summary(bp) for bp in cands]

        needs_human = match.score < HIGH_CONFIDENCE or not match.card_code
        reason: str | None = None
        if needs_human:
            reason = (
                "Müşteri eşleşmedi — manuel seçim gerekli"
                if not match.card_code
                else f"Düşük güven ({match.score:.2f}) — onay gerekli"
            )

        return AgentResult(
            agent_name=self.name,
            success=True,
            confidence=match.score,
            data={"match": match.model_dump()},
            needs_human=needs_human,
            human_reason=reason,
        )


async def _by_tax_id(
    db: AsyncSession, tax_id: str, *, card_type: str = CARD_TYPE_CUSTOMER
) -> BusinessPartnerCache | None:
    result = await db.execute(
        select(BusinessPartnerCache)
        .where(BusinessPartnerCache.federal_tax_id == tax_id)
        .where(BusinessPartnerCache.card_type == card_type)
    )
    return result.scalars().first()


async def _by_email(
    db: AsyncSession, email: str, *, card_type: str = CARD_TYPE_CUSTOMER
) -> BusinessPartnerCache | None:
    result = await db.execute(
        select(BusinessPartnerCache)
        .where(BusinessPartnerCache.email_address == email)
        .where(BusinessPartnerCache.card_type == card_type)
    )
    return result.scalars().first()


async def _by_alias(db: AsyncSession, alias_text: str) -> CustomerMatch | None:
    lower = alias_text.lower()
    result = await db.execute(
        select(CustomerAlias, BusinessPartnerCache)
        .join(BusinessPartnerCache, BusinessPartnerCache.card_code == CustomerAlias.target_code)
        .where(CustomerAlias.alias_lower == lower)
        .where(CustomerAlias.target_kind == "bp")
        .limit(1)
    )
    row = result.first()
    if not row:
        return None
    alias, bp = row
    return CustomerMatch(
        card_code=bp.card_code,
        card_name=bp.card_name,
        score=float(alias.confidence),
        strategy="alias",
    )


async def _fuzzy_name(
    db: AsyncSession, name: str, top: int = 200, *, card_type: str = CARD_TYPE_CUSTOMER
) -> CustomerMatch:
    candidates = await _name_candidates(db, name, limit=top, card_type=card_type)
    if not candidates:
        return CustomerMatch()
    names = [bp.card_name for bp in candidates]
    best = process.extractOne(name, names, scorer=fuzz.token_set_ratio)
    if not best:
        return CustomerMatch()
    _, score, index = best
    if score < FUZZY_THRESHOLD:
        return CustomerMatch(
            candidates=[_bp_summary(bp) for bp in candidates[:MAX_CANDIDATES]],
        )
    bp = candidates[index]
    others = [_bp_summary(b) for b in candidates[:MAX_CANDIDATES] if b.card_code != bp.card_code]
    return CustomerMatch(
        card_code=bp.card_code,
        card_name=bp.card_name,
        score=score / 100,
        strategy="fuzzy_name",
        candidates=others,
    )


async def _name_candidates(
    db: AsyncSession, name: str, limit: int, *, card_type: str = CARD_TYPE_CUSTOMER
) -> list[BusinessPartnerCache]:
    if not name:
        return []
    tokens = name.lower().split()[:2]
    conditions = [
        BusinessPartnerCache.card_name_lower.like(f"%{tok}%") for tok in tokens
    ]
    name_filter = or_(*conditions) if len(conditions) > 1 else conditions[0]
    stmt = (
        select(BusinessPartnerCache)
        .where(name_filter)
        .where(BusinessPartnerCache.card_type == card_type)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _exact(bp: BusinessPartnerCache, strategy: str) -> CustomerMatch:
    return CustomerMatch(
        card_code=bp.card_code,
        card_name=bp.card_name,
        score=1.0,
        strategy=strategy,
    )


def _bp_summary(bp: BusinessPartnerCache) -> dict[str, Any]:
    return {
        "card_code": bp.card_code,
        "card_name": bp.card_name,
        "federal_tax_id": bp.federal_tax_id,
        "email_address": bp.email_address,
    }
