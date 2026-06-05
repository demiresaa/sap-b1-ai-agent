"""Debug endpoint'leri — sadece development.

Production'da `app_env=production` ile gizlenir.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.agents.llm_client import call_llm_text
from app.api.deps import CurrentUser
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["debug"])


@router.get("/llm")
async def test_llm(user: CurrentUser) -> dict[str, Any]:
    """OpenRouter'a kısa bir test isteği at, modelin cevap verdiğini doğrula."""
    if settings.app_env == "production":
        raise HTTPException(403, "Debug endpoint'leri production'da kapalı.")

    try:
        text = await call_llm_text(
            system="Sen Türkçe konuşan bir asistansın.",
            user_message="Merhaba de ve hangi modelsin söyle (kısa).",
            max_tokens=200,
        )
        return {
            "status": "ok",
            "model": settings.llm_model_fast,
            "base_url": settings.openrouter_base_url,
            "response_preview": text[:500],
        }
    except Exception as exc:
        logger.exception("LLM test başarısız")
        raise HTTPException(
            500,
            f"OpenRouter çağrısı başarısız: {type(exc).__name__}: {exc}",
        )


@router.get("/config")
async def show_config(user: CurrentUser) -> dict[str, Any]:
    """Yüklenen ayarları döner (sırlar maskeli)."""
    if settings.app_env == "production":
        raise HTTPException(403, "Debug endpoint'leri production'da kapalı.")

    def mask(value: str | None) -> str:
        if not value:
            return "(boş)"
        if len(value) < 8:
            return "***"
        return value[:4] + "***" + value[-2:]

    return {
        "app_env": settings.app_env,
        "celery_enabled": settings.celery_enabled,
        "openrouter": {
            "base_url": settings.openrouter_base_url,
            "api_key": mask(settings.openrouter_api_key),
            "model_default": settings.llm_model_default,
            "model_fast": settings.llm_model_fast,
            "model_hard": settings.llm_model_hard,
        },
        "sap": {
            "url": settings.sap_service_layer_url,
            "company_db": settings.sap_company_db,
            "username": settings.sap_username,
            "password": mask(settings.sap_password),
            "verify_ssl": settings.sap_verify_ssl,
        },
        "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "***",
    }
