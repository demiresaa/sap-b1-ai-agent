"""JWT token üretimi/doğrulaması ve parola hashing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"

# bcrypt 72-bayt parola sınırı: aşan kısımları sessiz kesmek yerine SHA256 prehash ile uzun parolaları da güvenli destekleriz.
_BCRYPT_MAX = 72


def _prepare(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) <= _BCRYPT_MAX:
        return raw
    import hashlib

    return hashlib.sha256(raw).hexdigest().encode("utf-8")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(
    subject: str, token_type: str, expires_delta: timedelta, extra: dict[str, Any] | None = None
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    user_id: str, roles: list[str], tenant_slug: str | None = None
) -> str:
    extra: dict[str, Any] = {"roles": roles}
    if tenant_slug:
        extra["tenant"] = tenant_slug
    return _create_token(
        user_id,
        ACCESS_TYPE,
        timedelta(minutes=settings.jwt_expire_minutes),
        extra=extra,
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        user_id,
        REFRESH_TYPE,
        timedelta(days=settings.jwt_refresh_expire_days),
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    payload = jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
    if expected_type and payload.get("type") != expected_type:
        raise JWTError("Token tipi geçersiz")
    return payload
