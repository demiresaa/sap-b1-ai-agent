"""Auth endpoint'leri — login, refresh, me, OIDC SSO."""
from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse

import httpx
from fastapi import APIRouter, HTTPException, status
from jose import JWTError
from jose import jwt as jose_jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import (
    REFRESH_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.base import new_uuid, utcnow
from app.db.models import Tenant, User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserOut

router = APIRouter(tags=["auth"])

OIDC_STATE_TTL = 600  # 10 dakika


def _user_query(field, value):
    return select(User).options(selectinload(User.role_assignments)).where(field == value)


async def _resolve_tenant_slug(db, tenant_id: str | None) -> str | None:
    if not tenant_id:
        return None
    result = await db.execute(select(Tenant.slug).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    result = await db.execute(_user_query(User.email, payload.email))
    user = result.scalar_one_or_none()
    if (
        not user
        or not user.is_active
        or not user.hashed_password
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-posta veya şifre hatalı.")
    roles = [r.value for r in user.roles]
    tenant_slug = await _resolve_tenant_slug(db, user.tenant_id)
    return TokenResponse(
        access_token=create_access_token(user.id, roles, tenant_slug),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.jwt_expire_minutes * 60,
        tenant_slug=tenant_slug,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    try:
        data = decode_token(payload.refresh_token, expected_type=REFRESH_TYPE)
    except JWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Refresh token geçersiz veya süresi dolmuş."
        ) from exc
    user_id = data["sub"]
    result = await db.execute(_user_query(User.id, user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kullanıcı pasif.")
    roles = [r.value for r in user.roles]
    tenant_slug = await _resolve_tenant_slug(db, user.tenant_id)
    return TokenResponse(
        access_token=create_access_token(user.id, roles, tenant_slug),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.jwt_expire_minutes * 60,
        tenant_slug=tenant_slug,
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser, db: DbSession) -> UserOut:
    tenant_slug = await _resolve_tenant_slug(db, user.tenant_id)
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=[r.value for r in user.roles],
        is_active=user.is_active,
        tenant_slug=tenant_slug,
    )


# ------------------------------------------------------------------ #
# OIDC SSO — Azure AD / Google                                         #
# ------------------------------------------------------------------ #

class OIDCLoginOut(BaseModel):
    auth_url: str
    state: str


class OIDCCallbackIn(BaseModel):
    code: str
    state: str


def _make_oidc_state() -> str:
    """CSRF koruması için HMAC-SHA256 imzalı state üretir."""
    ts = str(int(time.time()))
    sig = hmac.new(
        settings.app_secret_key.encode(), ts.encode(), hashlib.sha256
    ).hexdigest()[:16]
    return f"{ts}.{sig}"


def _verify_oidc_state(state: str) -> None:
    parts = state.split(".", 1)
    if len(parts) != 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Geçersiz OIDC state")
    ts_str, sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Geçersiz OIDC state")  # noqa: B904
    expected = hmac.new(
        settings.app_secret_key.encode(), ts_str.encode(), hashlib.sha256
    ).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Geçersiz OIDC state imzası")
    if time.time() - ts > OIDC_STATE_TTL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OIDC state süresi dolmuş")


def _build_auth_url(state: str) -> str:
    params = {
        "client_id": settings.oidc_client_id,
        "response_type": "code",
        "redirect_uri": settings.oidc_redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "response_mode": "query",
    }
    if settings.oidc_provider == "azure":
        base = (
            f"https://login.microsoftonline.com/{settings.oidc_tenant_id}"
            "/oauth2/v2.0/authorize"
        )
    else:
        base = "https://accounts.google.com/o/oauth2/v2/auth"
        params.pop("response_mode", None)
    return f"{base}?{urllib.parse.urlencode(params)}"


async def _exchange_code(code: str) -> dict:
    """Authorization code → id_token + access_token."""
    if settings.oidc_provider == "azure":
        endpoint = (
            f"https://login.microsoftonline.com/{settings.oidc_tenant_id}"
            "/oauth2/v2.0/token"
        )
    else:
        endpoint = "https://oauth2.googleapis.com/token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            endpoint,
            data={
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
                "code": code,
                "redirect_uri": settings.oidc_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "OIDC token alınamadı")
    return resp.json()


def _extract_user_info(tokens: dict) -> tuple[str, str | None]:
    """id_token claim'lerinden email ve full_name döner."""
    id_token = tokens.get("id_token", "")
    try:
        claims = jose_jwt.get_unverified_claims(id_token)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "OIDC id_token okunamadı"
        ) from exc
    email = claims.get("email") or claims.get("preferred_username", "")
    if not email:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "OIDC: email claim bulunamadı")
    return email, claims.get("name") or claims.get("given_name")


@router.get("/oidc/login", response_model=OIDCLoginOut)
async def oidc_login() -> OIDCLoginOut:
    """SSO giriş URL'i üretir — frontend buraya yönlendirir."""
    if not settings.oidc_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SSO etkinleştirilmemiş")
    state = _make_oidc_state()
    return OIDCLoginOut(auth_url=_build_auth_url(state), state=state)


@router.post("/oidc/callback", response_model=TokenResponse)
async def oidc_callback(payload: OIDCCallbackIn, db: DbSession) -> TokenResponse:
    """OIDC callback — kodu token ile değiş tokuş eder, JWT döner."""
    if not settings.oidc_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SSO etkinleştirilmemiş")
    _verify_oidc_state(payload.state)
    tokens = await _exchange_code(payload.code)
    email, full_name = _extract_user_info(tokens)

    result = await db.execute(_user_query(User.email, email))
    user = result.scalar_one_or_none()
    if user is None:
        now = utcnow()
        user = User(
            id=new_uuid(),
            email=email,
            full_name=full_name,
            hashed_password=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()
    elif not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Hesap pasif.")

    roles = [r.value for r in user.roles]
    tenant_slug = await _resolve_tenant_slug(db, user.tenant_id)
    return TokenResponse(
        access_token=create_access_token(user.id, roles, tenant_slug),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.jwt_expire_minutes * 60,
        tenant_slug=tenant_slug,
    )
