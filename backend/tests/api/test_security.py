"""JWT ve parola hash birim testleri."""
from __future__ import annotations

import pytest
from jose import JWTError

from app.core.security import (
    ACCESS_TYPE,
    REFRESH_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify_round_trip() -> None:
    hashed = hash_password("Karpuz123!")
    assert hashed != "Karpuz123!"
    assert verify_password("Karpuz123!", hashed)
    assert not verify_password("yanlis", hashed)


def test_access_token_carries_roles() -> None:
    token = create_access_token("user-1", ["operator", "manager"])
    payload = decode_token(token, expected_type=ACCESS_TYPE)
    assert payload["sub"] == "user-1"
    assert payload["roles"] == ["operator", "manager"]


def test_refresh_token_type_mismatch_raises() -> None:
    token = create_refresh_token("user-2")
    with pytest.raises(JWTError):
        decode_token(token, expected_type=ACCESS_TYPE)
    # Doğru tipte sorunsuz
    data = decode_token(token, expected_type=REFRESH_TYPE)
    assert data["sub"] == "user-2"


def test_decode_invalid_token_raises() -> None:
    with pytest.raises(JWTError):
        decode_token("not-a-jwt")
