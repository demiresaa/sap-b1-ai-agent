"""Tenant resolution middleware — JWT veya X-Tenant-Slug header'dan tenant'ı çözer.

Çözüm sırası:
  1. `X-Tenant-Slug` HTTP header — admin override veya cross-tenant ops için.
  2. Authorization Bearer JWT'sindeki `tenant` claim.

Bulunamazsa tenant context boş kalır; tenant-scoped endpoint'ler `get_current_tenant`
ile 401 atar. Public endpoint'ler (login, health) etkilenmez.
"""
from __future__ import annotations

from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import ACCESS_TYPE, decode_token
from app.core.tenant_context import TenantContext, set_current_tenant


class TenantResolverMiddleware(BaseHTTPMiddleware):
    """JWT/header'dan tenant slug çıkarıp request.state.tenant_slug'a yazar.

    Asıl Tenant satırı `get_current_tenant` dependency'sinde DB'den çekilir; bu
    middleware sadece slug seviyesinde resolution yapar (DB hit'ten kaçınmak için).
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        slug = _resolve_slug(request)
        request.state.tenant_slug = slug

        # ContextVar'a hafif bir placeholder bırak — get_current_tenant tazeler
        if slug:
            set_current_tenant(
                TenantContext(
                    id="",
                    slug=slug,
                    schema_name=f"tenant_{slug}",
                    sap_dry_run=True,
                    sl_base_url="",
                    company_db="",
                    vault_secret_path=f"tenants/{slug}/sap",
                    default_warehouse=None,
                    default_sales_person_id=None,
                    default_currency=None,
                    default_pdf_template="default",
                )
            )
        else:
            set_current_tenant(None)

        try:
            response: Response = await call_next(request)
        finally:
            set_current_tenant(None)
        return response


def _resolve_slug(request: Request) -> str | None:
    header_slug = request.headers.get("x-tenant-slug")
    if header_slug:
        return header_slug.strip().lower()

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = decode_token(token, expected_type=ACCESS_TYPE)
        except JWTError:
            return None
        claim = payload.get("tenant")
        if isinstance(claim, str) and claim:
            return claim.lower()
    return None
