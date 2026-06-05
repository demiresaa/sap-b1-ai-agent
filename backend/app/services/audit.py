"""Audit log servisi — append-only.

`audit_log` tablosu Postgres trigger ile UPDATE/DELETE engellenir; service katmanı
sadece INSERT yapar.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models import AuditLog


async def record(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None,
    actor_id: str | None = None,
    actor_email: str | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        actor_email=actor_email,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=utcnow(),
    )
    db.add(entry)
    return entry
