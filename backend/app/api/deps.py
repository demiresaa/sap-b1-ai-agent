"""FastAPI dependency'leri: DB session, current user, RBAC."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import ACCESS_TYPE, decode_token
from app.db.models import User, UserRole
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]
TokenStr = Annotated[str | None, Depends(oauth2_scheme)]


async def get_current_user(token: TokenStr, db: DbSession) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Oturum gerekli.")
    try:
        payload = decode_token(token, expected_type=ACCESS_TYPE)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Geçersiz veya süresi dolmuş oturum.")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Geçersiz oturum.")
    result = await db.execute(
        select(User).options(selectinload(User.role_assignments)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kullanıcı bulunamadı veya pasif.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: UserRole):
    """Belirli rollere sahip kullanıcı dışını engelleyen dependency factory."""

    async def _checker(user: CurrentUser) -> User:
        if not set(allowed).intersection(user.roles):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Bu işlem için gerekli yetki yok ({', '.join(r.value for r in allowed)}).",
            )
        return user

    return _checker
