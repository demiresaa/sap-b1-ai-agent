"""Tüm agent'lar için ortak temel sınıf + telemetry."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.db.base import new_uuid

logger = logging.getLogger(__name__)


class AgentContext(BaseModel):
    """Bir agent çağrısı için context — document, run, kullanıcı."""

    run_id: str = Field(default_factory=new_uuid)
    document_id: str
    user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Bir agent çağrısının standart çıktısı."""

    agent_name: str
    success: bool
    confidence: float = 1.0
    data: dict[str, Any] = Field(default_factory=dict)
    needs_human: bool = False
    human_reason: str | None = None
    error: str | None = None
    duration_ms: int = 0


class BaseAgent(ABC):
    """Tüm agent'ların türediği temel sınıf.

    Alt sınıflar `_run` implementeder; `run` zamanlama + hata yakalama + log sarmalını yapar.
    """

    name: str = "base"
    # Agent override etmezse `settings.llm_model_default` kullanılır
    model: str = ""

    async def run(self, ctx: AgentContext, **kwargs: Any) -> AgentResult:
        started = time.monotonic()
        try:
            result = await self._run(ctx, **kwargs)
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.exception("[%s] hata", self.name)
            return AgentResult(
                agent_name=self.name,
                success=False,
                confidence=0.0,
                needs_human=True,
                human_reason=f"{self.name} agent hatası",
                error=str(exc),
                duration_ms=duration_ms,
            )
        duration_ms = int((time.monotonic() - started) * 1000)
        result.duration_ms = duration_ms
        if not result.agent_name:
            result.agent_name = self.name
        logger.info(
            "[%s] tamamlandı (success=%s confidence=%.2f duration=%dms)",
            self.name,
            result.success,
            result.confidence,
            duration_ms,
        )
        return result

    @abstractmethod
    async def _run(self, ctx: AgentContext, **kwargs: Any) -> AgentResult: ...
