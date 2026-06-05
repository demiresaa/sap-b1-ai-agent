"""Orchestrator — state machine, hangi agent ne zaman çalışacak.

Plan: docs/SISTEM_ANALIZI.md §4.3

Akış (Sales Order için):
  1. DocumentReader → ExtractedDocument
  2. CustomerMatcher → CardCode
  3. ProductMatcher → her satır için ItemCode
  4. Pricing → fiyat doğrulama
  5. Stock → availability (Sales Order'da zorunlu)

Her adım `AgentRun` + `AgentStep` olarak DB'ye yazılır. Pipeline sonunda
belge READY durumuna geçer; operatör formda kontrol/düzeltme yaptıktan
sonra `submit` endpoint'i SAPWriter'ı çağırır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.customer_matcher import CustomerMatcherAgent
from app.agents.document_reader import DocumentReaderAgent
from app.agents.pricing import PricingAgent
from app.agents.product_matcher import ProductMatcherAgent
from app.agents.schemas import ExtractedDocument
from app.agents.stock import StockAgent
from app.db.base import utcnow
from app.db.models import AgentRun, AgentStep

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"
    model = "n/a"

    async def _run(
        self,
        ctx: AgentContext,
        file_path: str | None = None,
        db: AsyncSession | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if db is None:
            raise ValueError("db zorunlu")
        if not file_path:
            raise ValueError("file_path zorunlu")

        run = AgentRun(
            id=ctx.run_id,
            document_id=ctx.document_id,
            status="running",
            started_at=utcnow(),
        )
        db.add(run)
        await db.flush()

        steps_results: dict[str, AgentResult] = {}
        step_order = 0

        async def _step(agent: BaseAgent, **call_kwargs: Any) -> AgentResult:
            nonlocal step_order
            step_order += 1
            started = utcnow()
            result = await agent.run(ctx, **call_kwargs)
            db.add(
                AgentStep(
                    run_id=run.id,
                    step_order=step_order,
                    agent_name=agent.name,
                    input_payload=_safe_kwargs(call_kwargs),
                    output_payload=result.model_dump(mode="json"),
                    status="completed" if result.success else "failed",
                    duration_ms=result.duration_ms,
                    error_message=result.error,
                    started_at=started,
                )
            )
            await db.flush()
            return result

        # 1. DocumentReader
        reader_result = await _step(DocumentReaderAgent(), file_path=file_path)
        steps_results["document_reader"] = reader_result
        if not reader_result.success:
            return _finalize(db, run, "failed", reader_result.error, steps_results)

        extracted = ExtractedDocument.model_validate(reader_result.data["extracted"])

        # 2. CustomerMatcher
        customer_result = await _step(
            CustomerMatcherAgent(), customer=extracted.customer.model_dump(), db=db
        )
        steps_results["customer_matcher"] = customer_result
        card_code = customer_result.data.get("match", {}).get("card_code")

        # 3. ProductMatcher
        product_result = await _step(
            ProductMatcherAgent(),
            lines=[line.model_dump() for line in extracted.lines],
            customer_card_code=card_code,
            db=db,
        )
        steps_results["product_matcher"] = product_result

        # 4. Pricing
        pricing_result = await _step(
            PricingAgent(),
            lines=[line.model_dump() for line in extracted.lines],
            matches=product_result.data.get("matches", []),
            db=db,
        )
        steps_results["pricing"] = pricing_result

        # 5. Stock (sadece sales_order için zorunlu, quotation'da uyarı)
        stock_result = await _step(
            StockAgent(),
            lines=[line.model_dump() for line in extracted.lines],
            matches=product_result.data.get("matches", []),
        )
        steps_results["stock"] = stock_result

        any_human = any(r.needs_human for r in steps_results.values())
        overall_confidence = _aggregate_confidence(steps_results)

        return _finalize(
            db,
            run,
            "completed",
            None,
            steps_results,
            extra={
                "needs_human": any_human,
                "overall_confidence": overall_confidence,
                "card_code": card_code,
                "extracted": extracted.model_dump(mode="json"),
                "matches": product_result.data.get("matches", []),
                "pricing": pricing_result.data.get("checks", []),
                "stock": stock_result.data.get("checks", []),
            },
        )


def _finalize(
    db: AsyncSession,
    run: AgentRun,
    status: str,
    error: str | None,
    steps_results: dict[str, AgentResult],
    extra: dict[str, Any] | None = None,
) -> AgentResult:
    run.status = status
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = error
    run.summary = {**(extra or {}), "steps": {k: v.model_dump(mode="json") for k, v in steps_results.items()}}
    db.add(run)

    needs_human = (extra or {}).get("needs_human", False)
    confidence = (extra or {}).get("overall_confidence", 1.0)

    return AgentResult(
        agent_name="orchestrator",
        success=status == "completed",
        confidence=confidence,
        data=extra or {},
        needs_human=needs_human,
        human_reason=_first_human_reason(steps_results) if needs_human else None,
        error=error,
    )


def _first_human_reason(results: dict[str, AgentResult]) -> str | None:
    for r in results.values():
        if r.needs_human and r.human_reason:
            return r.human_reason
    return None


def _aggregate_confidence(results: dict[str, AgentResult]) -> float:
    # Başarısız agent'lar 0.0 ile dahil edilir — şişirilmiş confidence önlenir
    scores = [r.confidence if r.success else 0.0 for r in results.values()]
    return sum(scores) / len(scores) if scores else 0.0


def _safe_kwargs(call_kwargs: dict[str, Any]) -> dict[str, Any]:
    """DB session ve büyük blob'ları persistence'tan çıkarır."""
    return {k: v for k, v in call_kwargs.items() if not _is_unserializable(v)}


def _is_unserializable(value: Any) -> bool:
    if isinstance(value, AsyncSession):
        return True
    if hasattr(value, "redis"):
        return True
    return False
