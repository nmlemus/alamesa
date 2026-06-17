"""Integration tests for GET /api/public/restaurants/{slug}/tables/{number}."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from mesadigital.api.db.models import Restaurant, RestaurantTable

_SLUG = "test-pub-table"
_URL = "/api/public/restaurants/{slug}/tables/{number}"


@pytest.fixture()
def restaurant_with_table(client: TestClient, db_engine: object) -> dict:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        r = Restaurant(slug=_SLUG, name="Table Test Restaurant", is_active=True)
        session.add(r)
        session.flush()
        t = RestaurantTable(restaurant_id=r.id, number=5, label="Terraza", is_active=True)
        session.add(t)
        session.commit()
        session.refresh(t)
        return {"restaurant_id": r.id, "table_id": t.id, "table_number": t.number}


@pytest.fixture()
def inactive_table(client: TestClient, db_engine: object, restaurant_with_table: dict) -> str:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        t = RestaurantTable(
            restaurant_id=restaurant_with_table["restaurant_id"],
            number=99,
            is_active=False,
        )
        session.add(t)
        session.commit()
        session.refresh(t)
        return t.id


def test_returns_200_with_table_data(client: TestClient, restaurant_with_table: dict) -> None:
    r = client.get(_URL.format(slug=_SLUG, number=5))
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == restaurant_with_table["table_id"]
    assert data["number"] == 5
    assert data["label"] == "Terraza"
    assert data["is_active"] is True
    assert "qr_url" in data


def test_returns_404_for_unknown_slug(client: TestClient, restaurant_with_table: dict) -> None:
    r = client.get(_URL.format(slug="nonexistent-slug", number=5))
    assert r.status_code == 404


def test_returns_404_for_unknown_table_number(client: TestClient, restaurant_with_table: dict) -> None:
    r = client.get(_URL.format(slug=_SLUG, number=999))
    assert r.status_code == 404


def test_returns_404_for_inactive_table(
    client: TestClient, restaurant_with_table: dict, inactive_table: str
) -> None:
    r = client.get(_URL.format(slug=_SLUG, number=99))
    assert r.status_code == 404


def test_returns_404_for_inactive_restaurant(client: TestClient, db_engine: object) -> None:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        r = Restaurant(slug="inactive-rest", name="Inactive", is_active=False)
        session.add(r)
        session.flush()
        t = RestaurantTable(restaurant_id=r.id, number=1, is_active=True)
        session.add(t)
        session.commit()

    r2 = client.get(_URL.format(slug="inactive-rest", number=1))
    assert r2.status_code == 404
