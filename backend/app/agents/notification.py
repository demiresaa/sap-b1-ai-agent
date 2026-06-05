"""Notification — e-posta / Teams / Slack.

MVP: yapısal log + opsiyonel structlog/sentry kancası. Gerçek e-posta gönderimi
SMTP/Microsoft Graph bağlandığında doldurulur (Sprint 4-5).
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class NotificationAgent(BaseAgent):
    name = "notification"
    model = "n/a"

    async def _run(
        self,
        ctx: AgentContext,
        channel: str = "log",
        recipients: list[str] | None = None,
        subject: str | None = None,
        body: str | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        if channel == "log":
            logger.info(
                "[notification:%s] document=%s subject=%s recipients=%s body=%s",
                channel,
                ctx.document_id,
                subject,
                recipients,
                (body or "")[:200],
            )
            sent = True
        else:
            # TODO: SMTP / Microsoft Graph / Teams webhook
            logger.warning("[notification] kanal henüz desteklenmiyor: %s", channel)
            sent = False

        return AgentResult(
            agent_name=self.name,
            success=sent,
            confidence=1.0 if sent else 0.0,
            data={"channel": channel, "recipients": recipients or [], "subject": subject},
        )
