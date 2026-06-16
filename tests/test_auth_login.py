
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from mesadigital.api.db.models import Restaurant, RestaurantUser
from mesadigital.api.security import hash_password
from mesadigital.api.settings import settings
from shared.contracts import RestaurantUserRole

_EMAIL = "staff@authtest.com"
_PASSWORD = "validpass123"


@pytest.fixture()
def auth_client(client: TestClient, db_engine: object) -> TestClient:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        restaurant = Restaurant(slug="auth-test", name="Auth Test Restaurant")
        session.add(restaurant)
        session.flush()
        user = RestaurantUser(
            restaurant_id=restaurant.id,
            email=_EMAIL,
            hashed_password=hash_password(_PASSWORD),
            role=RestaurantUserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        session.commit()
    return client


def test_login_valid_credentials(auth_client: TestClient) -> None:
    r = auth_client.post("/api/auth/login", json={"email": _EMAIL, "password": _PASSWORD})
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    token = data["access_token"]
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert claims["sub"]
    assert claims["restaurant_id"]
    assert claims["role"]
    assert claims["exp"]


def test_login_wrong_password(auth_client: TestClient) -> None:
    r = auth_client.post("/api/auth/login", json={"email": _EMAIL, "password": "wrongpass"})
    assert r.status_code == 401


def test_login_wrong_email(auth_client: TestClient) -> None:
    r = auth_client.post("/api/auth/login", json={"email": "ghost@authtest.com", "password": _PASSWORD})
    assert r.status_code == 401


def test_login_inactive_user(client: TestClient, db_engine: object) -> None:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        restaurant = Restaurant(slug="inactive-test", name="Inactive Test")
        session.add(restaurant)
        session.flush()
        session.add(
            RestaurantUser(
                restaurant_id=restaurant.id,
                email="inactive@authtest.com",
                hashed_password=hash_password("somepass"),
                role=RestaurantUserRole.STAFF,
                is_active=False,
            )
        )
        session.commit()

    r = client.post("/api/auth/login", json={"email": "inactive@authtest.com", "password": "somepass"})
    assert r.status_code == 401


def test_login_missing_password(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"email": "x@x.com"})
    assert r.status_code == 422


def test_login_missing_email(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"password": "pass"})
    assert r.status_code == 422


def test_login_empty_body(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={})
    assert r.status_code == 422
