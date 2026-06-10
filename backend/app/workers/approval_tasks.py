"""Onay SLA kontrolü — süresi dolan talepleri eskalasyon veya expire eder.

Her 30 dakikada bir çalışır. `deadline_at` geçmiş ve hâlâ `pending` olan
ApprovalRequest kayıtları `expired` durumuna getirilir.
Eskalasyon mantığı: escalation_level=0 → 1 (manager → admin) seçeneği için
yeni bir ApprovalRequest oluşturulabilir (is_escalation_enabled konfigürasyonu).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select

from app.db.base import utcnow
from app.db.models.approval import ApprovalRequest, ApprovalStatus
from app.db.session import SessionFactory
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.approval_tasks.check_approval_sla")
def check_approval_sla() -> dict[str, Any]:
    """Süresi dolan onay taleplerini expire eder."""
    return asyncio.run(_check_sla_async())


async def _check_sla_async() -> dict[str, Any]:
    expired_count = 0
    now = utcnow()

    async with SessionFactory() as db:
        result = await db.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.status == ApprovalStatus.PENDING)
            .where(ApprovalRequest.deadline_at.isnot(None))
            .where(ApprovalRequest.deadline_at <= now)
        )
        overdue = list(result.scalars().all())

        for req in overdue:
            req.status = ApprovalStatus.EXPIRED
            req.updated_at = now
            expired_count += 1
            logger.warning(
                "[approval_sla] Süre doldu: request=%s doc=%s role=%s",
                req.id,
                req.document_id,
                req.approver_role,
            )

        await db.commit()

    logger.info("[approval_sla] %d talep expire edildi", expired_count)
    return {"expired": expired_count, "checked_at": now.isoformat()}
