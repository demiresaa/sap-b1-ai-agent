"""Analitik endpoint'leri — no-touch ratio, throughput, LLM maliyet."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import Date, cast, func, select

from app.api.deps import CurrentUser, DbSession
from app.db.models import AgentStep, Document, DocumentEvent, DocumentStatus, LLMCall, SAPSubmission

router = APIRouter(tags=["analytics"])


@router.get("/summary")
async def summary(user: CurrentUser, db: DbSession, days: int = 30) -> dict:
    since = datetime.now(UTC) - timedelta(days=days)

    by_status_q = (
        select(Document.status, func.count(Document.id))
        .where(Document.created_at >= since)
        .group_by(Document.status)
    )
    by_status_raw = (await db.execute(by_status_q)).all()
    by_status = {status.value: count for status, count in by_status_raw}
    total = sum(by_status.values())
    submitted = by_status.get(DocumentStatus.SUBMITTED.value, 0)
    errors = by_status.get(DocumentStatus.ERROR.value, 0) + by_status.get(
        DocumentStatus.REJECTED.value, 0
    )
    success_rate = submitted / total if total else 0.0
    error_rate = errors / total if total else 0.0

    llm_cost_q = (
        select(func.coalesce(func.sum(LLMCall.cost_usd), 0)).where(LLMCall.created_at >= since)
    )
    llm_cost = float((await db.execute(llm_cost_q)).scalar() or 0)

    llm_tokens_q = (
        select(
            func.coalesce(func.sum(LLMCall.request_tokens), 0),
            func.coalesce(func.sum(LLMCall.response_tokens), 0),
        ).where(LLMCall.created_at >= since)
    )
    in_tok, out_tok = (await db.execute(llm_tokens_q)).one()

    submissions_q = (
        select(func.count(SAPSubmission.id)).where(SAPSubmission.created_at >= since)
    )
    submissions = int((await db.execute(submissions_q)).scalar() or 0)

    return {
        "period_days": days,
        "total_documents": total,
        "by_status": by_status,
        "submitted_count": submitted,
        "error_count": errors,
        "success_rate": round(success_rate, 4),
        "error_rate": round(error_rate, 4),
        "sap_submissions": submissions,
        "llm_cost_usd": round(llm_cost, 4),
        "llm_input_tokens": int(in_tok or 0),
        "llm_output_tokens": int(out_tok or 0),
    }


@router.get("/agents")
async def agents_stats(user: CurrentUser, db: DbSession, days: int = 30) -> list[dict]:
    """Her agent için ortalama süre ve adım sayısı (son N gün)."""
    since = datetime.now(UTC) - timedelta(days=days)
    q = (
        select(
            AgentStep.agent_name,
            func.count(AgentStep.id).label("step_count"),
            func.avg(AgentStep.duration_ms).label("avg_duration_ms"),
        )
        .where(AgentStep.created_at >= since)
        .group_by(AgentStep.agent_name)
        .order_by(func.count(AgentStep.id).desc())
    )
    rows = (await db.execute(q)).all()
    return [
        {
            "agent_name": r.agent_name,
            "step_count": r.step_count,
            "avg_duration_ms": round(float(r.avg_duration_ms or 0), 1),
        }
        for r in rows
    ]


@router.get("/costs")
async def costs_breakdown(user: CurrentUser, db: DbSession, days: int = 30) -> list[dict]:
    """Model bazlı LLM maliyet + token dökümü (son N gün)."""
    since = datetime.now(UTC) - timedelta(days=days)
    q = (
        select(
            LLMCall.model,
            func.count(LLMCall.id).label("call_count"),
            func.coalesce(func.sum(LLMCall.request_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(LLMCall.response_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(LLMCall.cost_usd), 0).label("total_cost_usd"),
        )
        .where(LLMCall.created_at >= since)
        .group_by(LLMCall.model)
        .order_by(func.sum(LLMCall.cost_usd).desc())
    )
    rows = (await db.execute(q)).all()
    return [
        {
            "model": r.model,
            "call_count": r.call_count,
            "input_tokens": int(r.input_tokens),
            "output_tokens": int(r.output_tokens),
            "total_cost_usd": round(float(r.total_cost_usd), 4),
        }
        for r in rows
    ]


@router.get("/trends")
async def document_trends(user: CurrentUser, db: DbSession, days: int = 30) -> list[dict]:
    """Günlük belge sayısı — son N gün (grafik için zaman serisi)."""
    since = datetime.now(UTC) - timedelta(days=days)
    q = (
        select(
            cast(DocumentEvent.created_at, Date).label("day"),
            func.count(DocumentEvent.id).label("event_count"),
        )
        .where(
            DocumentEvent.event_type == "received",
            DocumentEvent.created_at >= since,
        )
        .group_by(cast(DocumentEvent.created_at, Date))
        .order_by(cast(DocumentEvent.created_at, Date))
    )
    rows = (await db.execute(q)).all()
    return [{"day": str(r.day), "count": r.event_count} for r in rows]
