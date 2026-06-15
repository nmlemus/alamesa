from __future__ import annotations

from datetime import timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from mesadigital.api.dependencies import require_auth, require_restaurant_scope, require_role
from mesadigital.api.schemas import RestaurantUserRead
from mesadigital.api.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from mesadigital.api.settings import settings
from shared.contracts import RestaurantUserRole


# ── hash_password / verify_password ───────────────────────────────────────────


def test_hash_password_produces_bcrypt_hash() -> None:
    h = hash_password("secret")
    assert h.startswith("$2b$12$")


def test_verify_password_correct() -> None:
    h = hash_password("secret")
    assert verify_password("secret", h) is True


def test_verify_password_wrong_returns_false() -> None:
    h = hash_password("secret")
    assert verify_password("wrong", h) is False


# ── create_token / decode_token ───────────────────────────────────────────────


def test_create_and_decode_token_roundtrip() -> None:
    token = create_token({"sub": "user-abc", "type": "staff"}, timedelta(minutes=5))
    claims = decode_token(token)
    assert claims["sub"] == "user-abc"
    assert claims["type"] == "staff"


def test_expired_token_raises_401() -> None:
    token = create_token({"sub": "user-abc"}, timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


def test_invalid_signature_raises_401() -> None:
    token = jwt.encode({"sub": "user-abc"}, "wrong-key", algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


# ── require_role ──────────────────────────────────────────────────────────────


def _make_staff_user(
    role: RestaurantUserRole = RestaurantUserRole.STAFF,
    restaurant_id: str = "rest-1",
) -> RestaurantUserRead:
    return RestaurantUserRead(
        id="user-1",
        restaurant_id=restaurant_id,
        email="staff@example.com",
        role=role,
    )


def test_require_role_wrong_role_raises_403() -> None:
    app = FastAPI()
    user = _make_staff_user(role=RestaurantUserRole.STAFF)
    app.dependency_overrides[require_auth] = lambda: user

    @app.get("/test")
    def _handler(
        u: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
    ) -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/test")
    assert response.status_code == 403


def test_require_role_correct_role_passes() -> None:
    app = FastAPI()
    user = _make_staff_user(role=RestaurantUserRole.ADMIN)
    app.dependency_overrides[require_auth] = lambda: user

    @app.get("/test")
    def _handler(
        u: Annotated[RestaurantUserRead, Depends(require_role(["admin"]))],
    ) -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/test")
    assert response.status_code == 200


# ── require_restaurant_scope ──────────────────────────────────────────────────


def test_require_restaurant_scope_wrong_restaurant_raises_403() -> None:
    app = FastAPI()
    user = _make_staff_user(restaurant_id="rest-1")
    app.dependency_overrides[require_auth] = lambda: user

    @app.get("/test/{restaurant_id}")
    def _handler(
        u: Annotated[RestaurantUserRead, Depends(require_restaurant_scope)],
    ) -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/test/rest-2")
    assert response.status_code == 403


def test_require_restaurant_scope_correct_restaurant_passes() -> None:
    app = FastAPI()
    user = _make_staff_user(restaurant_id="rest-1")
    app.dependency_overrides[require_auth] = lambda: user

    @app.get("/test/{restaurant_id}")
    def _handler(
        u: Annotated[RestaurantUserRead, Depends(require_restaurant_scope)],
    ) -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/test/rest-1")
    assert response.status_code == 200
