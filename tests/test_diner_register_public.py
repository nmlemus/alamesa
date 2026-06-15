"""Integration tests for POST /api/public/restaurants/{restaurant_id}/diners/register."""
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from mesadigital.api.db.models import Diner, Restaurant
from mesadigital.api.settings import settings

_PHONE = "+34600000099"
_NAME = "Ana García"
_URL = "/api/public/restaurants/{restaurant_id}/diners/register"


@pytest.fixture()
def active_restaurant_id(client: TestClient, db_engine: object) -> str:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        restaurant = Restaurant(slug="pub-test", name="Public Test", is_active=True)
        session.add(restaurant)
        session.commit()
        session.refresh(restaurant)
        return restaurant.id


def test_new_phone_returns_201(client: TestClient, active_restaurant_id: str) -> None:
    r = client.post(
        _URL.format(restaurant_id=active_restaurant_id),
        json={"name": _NAME, "phone": _PHONE},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["token_type"] == "bearer"
    claims = jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert claims["sub"]
    assert claims["restaurant_id"] == active_restaurant_id
    assert claims["type"] == "diner"
    assert "exp" in claims


def test_same_phone_different_name_returns_200_and_updates_name(
    client: TestClient, active_restaurant_id: str, db_engine: object
) -> None:
    url = _URL.format(restaurant_id=active_restaurant_id)

    r1 = client.post(url, json={"name": _NAME, "phone": _PHONE})
    assert r1.status_code == 201
    diner_id = jwt.decode(r1.json()["access_token"], settings.SECRET_KEY, algorithms=["HS256"])["sub"]

    r2 = client.post(url, json={"name": "Nuevo Nombre", "phone": _PHONE})
    assert r2.status_code == 200
    assert jwt.decode(r2.json()["access_token"], settings.SECRET_KEY, algorithms=["HS256"])["sub"] == diner_id

    with Session(db_engine) as session:  # type: ignore[arg-type]
        diner = session.get(Diner, diner_id)
        assert diner is not None
        assert diner.name == "Nuevo Nombre"
        assert diner.last_seen_at is not None


def test_restaurant_not_found_returns_404(client: TestClient) -> None:
    r = client.post(
        _URL.format(restaurant_id="nonexistentid00000000000000000000"),
        json={"name": _NAME, "phone": _PHONE},
    )
    assert r.status_code == 404


def test_inactive_restaurant_returns_404(
    client: TestClient, db_engine: object
) -> None:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        restaurant = Restaurant(slug="inactive-pub", name="Inactive", is_active=False)
        session.add(restaurant)
        session.commit()
        session.refresh(restaurant)
        restaurant_id = restaurant.id

    r = client.post(
        _URL.format(restaurant_id=restaurant_id),
        json={"name": _NAME, "phone": _PHONE},
    )
    assert r.status_code == 404


def test_name_too_short_returns_422(client: TestClient, active_restaurant_id: str) -> None:
    r = client.post(
        _URL.format(restaurant_id=active_restaurant_id),
        json={"name": "A", "phone": _PHONE},
    )
    assert r.status_code == 422


def test_empty_phone_returns_422(client: TestClient, active_restaurant_id: str) -> None:
    r = client.post(
        _URL.format(restaurant_id=active_restaurant_id),
        json={"name": _NAME, "phone": ""},
    )
    assert r.status_code == 422


def test_token_expires_in_24h(client: TestClient, active_restaurant_id: str) -> None:
    from datetime import timezone as tz
    from datetime import datetime

    r = client.post(
        _URL.format(restaurant_id=active_restaurant_id),
        json={"name": _NAME, "phone": _PHONE},
    )
    assert r.status_code == 201
    claims = jwt.decode(r.json()["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    exp = datetime.fromtimestamp(claims["exp"], tz=tz.utc)
    now = datetime.now(tz.utc)
    delta_hours = (exp - now).total_seconds() / 3600
    assert 23 < delta_hours <= 24
