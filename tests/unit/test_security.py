from __future__ import annotations

from datetime import timedelta
from typing import Any

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from mesadigital.api.dependencies import require_restaurant_scope, require_role
from mesadigital.api.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from mesadigital.api.settings import settings


def _token(**claims: Any) -> str:
    return create_token(claims, timedelta(hours=1))


# ── hash_password / verify_password ──────────────────────────────────────────


def test_hash_password_returns_bcrypt_hash() -> None:
    h = hash_password("secret")
    assert h.startswith("$2b$")


def test_verify_password_correct() -> None:
    h = hash_password("hunter2")
    assert verify_password("hunter2", h) is True


def test_verify_password_wrong() -> None:
    h = hash_password("hunter2")
    assert verify_password("wrong", h) is False


# ── create_token / decode_token ───────────────────────────────────────────────


def test_create_and_decode_roundtrip() -> None:
    token = _token(sub="u1", role="admin")
    claims = decode_token(token)
    assert claims["sub"] == "u1"
    assert claims["role"] == "admin"


def test_expired_token_raises_401() -> None:
    token = create_token({"sub": "u1"}, timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc:
        decode_token(token)
    assert exc.value.status_code == 401


def test_invalid_signature_raises_401() -> None:
    bad_token = pyjwt.encode({"sub": "u1"}, "wrong-key", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        decode_token(bad_token)
    assert exc.value.status_code == 401


def test_garbage_token_raises_401() -> None:
    with pytest.raises(HTTPException) as exc:
        decode_token("not.a.token")
    assert exc.value.status_code == 401


# ── require_role ──────────────────────────────────────────────────────────────


def test_require_role_passes_when_role_matches() -> None:
    guard = require_role(["admin"])
    # calling the returned closure directly bypasses FastAPI DI
    guard({"role": "admin"})  # must not raise


def test_require_role_wrong_role_raises_403() -> None:
    guard = require_role(["admin"])
    with pytest.raises(HTTPException) as exc:
        guard({"role": "staff"})
    assert exc.value.status_code == 403


def test_require_role_missing_role_raises_403() -> None:
    guard = require_role(["admin"])
    with pytest.raises(HTTPException) as exc:
        guard({})
    assert exc.value.status_code == 403


def test_require_role_multiple_allowed_roles() -> None:
    guard = require_role(["admin", "staff"])
    guard({"role": "staff"})  # must not raise
    guard({"role": "admin"})  # must not raise


# ── require_restaurant_scope ──────────────────────────────────────────────────


def test_require_restaurant_scope_passes_when_matches() -> None:
    guard = require_restaurant_scope("rest-abc")
    guard({"restaurant_id": "rest-abc"})  # must not raise


def test_require_restaurant_scope_wrong_restaurant_raises_403() -> None:
    guard = require_restaurant_scope("rest-abc")
    with pytest.raises(HTTPException) as exc:
        guard({"restaurant_id": "rest-xyz"})
    assert exc.value.status_code == 403


def test_require_restaurant_scope_missing_claim_raises_403() -> None:
    guard = require_restaurant_scope("rest-abc")
    with pytest.raises(HTTPException) as exc:
        guard({})
    assert exc.value.status_code == 403
