"""ApprovalAgent — kural bazlı onay talebi oluşturur.

Akış:
  1. Aktif `ApprovalRule` kayıtlarını DB'den okur (priority sıralı).
  2. Her kuralı pipeline çıktısına (extracted + confidence) karşı değerlendirir.
  3. Tetiklenen kural varsa `ApprovalRequest` oluşturur; needs_human=True döner.
  4. action=BLOCK → otomatik reddeder, SAP'a gönderilmez.
  5. action=WARN → approval_request oluşturulmaz, sadece uyarı notu döner.
  6. Multi-stage: ADMIN gerektiren kuralda parent=manager onayı zorunlu.

LLM kullanmaz — tamamen deterministik kural motoru.
"""
from __future__ import annotations

import logging
import operator as op_module
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.db.base import new_uuid, utcnow
from app.db.models.approval import ApprovalAction, ApprovalRequest, ApprovalRule, ApprovalStatus

logger = logging.getLogger(__name__)

OPERATORS: dict[str, Any] = {
    "gt": op_module.gt,
    "lt": op_module.lt,
    "gte": op_module.ge,
    "lte": op_module.le,
    "eq": op_module.eq,
    "neq": op_module.ne,
}

# Alanı pipeline çıktısından nasıl çıkaracağız
FIELD_EXTRACTORS: dict[str, Any] = {
    "discount_pct": lambda d: max(
        (float(ln.get("discount_pct") or 0) for ln in d.get("lines", [])), default=0.0
    ),
    "doc_total": lambda d: sum(
        float(ln.get("total") or (ln.get("quantity", 0) * (ln.get("unit_price") or 0)))
        for ln in d.get("lines", [])
    ),
    "confidence": lambda d: d.get("_confidence", 1.0),
    "item_count": lambda d: len(d.get("lines", [])),
    "new_customer": lambda d: float(not bool(d.get("customer", {}).get("card_code"))),
}


class ApprovalAgent(BaseAgent):
    name = "approval"
    model = "n/a"

    async def _run(
        self,
        ctx: AgentContext,
        extracted: dict[str, Any] | None = None,
        overall_confidence: float = 1.0,
        db: AsyncSession | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if db is None:
            raise ValueError("db session zorunlu")
        if extracted is None:
            extracted = {}

        # Confidence'ı extracted içine enjekte et (_confidence özel alan)
        extracted["_confidence"] = overall_confidence

        rules = await _load_rules(db)
        triggered: list[dict[str, Any]] = []
        warnings: list[str] = []
        blocked = False

        for rule in rules:
            value = _extract_field(extracted, rule.field)
            if value is None:
                continue
            compare = OPERATORS.get(rule.operator)
            if compare is None:
                continue
            if not compare(value, rule.threshold):
                continue

            ctx_data = {
                "rule_name": rule.name,
                "field": rule.field,
                "operator": rule.operator,
                "threshold": rule.threshold,
                "actual_value": value,
            }

            if rule.action == ApprovalAction.BLOCK:
                blocked = True
                triggered.append({"action": "block", **ctx_data})
                logger.warning("[approval] BLOCK kuralı tetiklendi: %s", rule.name)
                break

            if rule.action == ApprovalAction.WARN:
                warnings.append(f"{rule.name}: {rule.field}={value:.2f}")
                continue

            # require_approval → ApprovalRequest oluştur
            deadline = (
                datetime.now(UTC) + timedelta(hours=rule.sla_hours)
                if rule.sla_hours > 0 else None
            )
            req = ApprovalRequest(
                id=new_uuid(),
                document_id=ctx.document_id,
                rule_id=rule.id,
                status=ApprovalStatus.PENDING,
                approver_role=rule.required_role,
                deadline_at=deadline,
                rule_context=ctx_data,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(req)
            triggered.append({"action": "require_approval", "request_id": req.id, **ctx_data})
            logger.info(
                "[approval] Onay talebi oluşturuldu: %s (kural=%s)", req.id, rule.name
            )

        await db.flush()

        if blocked:
            return AgentResult(
                agent_name=self.name,
                success=False,
                confidence=0.0,
                data={"triggered": triggered, "warnings": warnings, "blocked": True},
                needs_human=True,
                human_reason="İşlem kural tarafından engellendi — yetkili onayı gerekli",
                error="Belge bloklandı",
            )

        needs_human = bool(triggered)
        reason: str | None = None
        if needs_human:
            reason = f"{len(triggered)} kural tetiklendi, onay bekleniyor"
        elif warnings:
            reason = f"Uyarı: {'; '.join(warnings)}"

        return AgentResult(
            agent_name=self.name,
            success=True,
            confidence=1.0 if not needs_human else 0.5,
            data={"triggered": triggered, "warnings": warnings, "blocked": False},
            needs_human=needs_human,
            human_reason=reason,
        )


async def _load_rules(db: AsyncSession) -> list[ApprovalRule]:
    result = await db.execute(
        select(ApprovalRule)
        .where(ApprovalRule.is_active.is_(True))
        .order_by(ApprovalRule.priority)
    )
    return list(result.scalars().all())


def _extract_field(extracted: dict[str, Any], field: str) -> float | None:
    extractor = FIELD_EXTRACTORS.get(field)
    if extractor is None:
        return None
    try:
        return float(extractor(extracted))
    except (TypeError, ValueError, AttributeError):
        return None
