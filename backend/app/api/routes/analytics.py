"""Analitik endpoint'leri — no-touch ratio, throughput, LLM maliyet."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.db.models import Document, DocumentStatus, LLMCall, SAPSubmission

router = APIRouter(tags=["analytics"])


@router.get("/summary")
async def summary(user: CurrentUser, db: DbSession, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

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
