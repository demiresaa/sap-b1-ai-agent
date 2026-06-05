"""Auth endpoint'leri — login, refresh, me."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from jose import JWTError
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
from app.db.models import Tenant, User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserOut

router = APIRouter(tags=["auth"])


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
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token geçersiz veya süresi dolmuş.")
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
