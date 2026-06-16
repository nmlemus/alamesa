"""Integration tests for POST /api/orders (ticket S3-01)."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import MenuItem, Order, Restaurant, RestaurantTable


def _get_diner_token(client: TestClient, slug: str = "demo") -> str:
    restaurant = client.get(f"/api/public/restaurants/{slug}").json()
    r = client.post(
        f"/api/public/restaurants/{restaurant['id']}/diners/register",
        json={"name": "Test Diner", "phone": "+34699000001"},
    )
    assert r.status_code in (200, 201), r.json()
    return r.json()["access_token"]


def _post_order(client: TestClient, token: str, table_id: str, items: list[dict]) -> dict:
    return client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "restaurant_slug": "demo",
            "table_id": table_id,
            "items": items,
        },
    )


def test_create_order_valid_cart_returns_201(seeded_client: TestClient) -> None:
    menu = seeded_client.get("/api/restaurants/demo/menu").json()
    table_id = menu["tables"][0]["id"]
    item = menu["categories"][0]["items"][0]
    token = _get_diner_token(seeded_client)

    r = _post_order(seeded_client, token, table_id, [{"menu_item_id": item["id"], "quantity": 2}])

    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["table_id"] == table_id
    assert isinstance(data["id"], str) and len(data["id"]) == 32

    assert len(data["items"]) == 1
    line = data["items"][0]
    assert line["quantity"] == 2
    assert line["unit_price_cents"] == item["price_cents"]
    assert line["item_snapshot_name"] == item["name"]

    assert data["total_cents"] == item["price_cents"] * 2
    assert data["item_count"] == 2


def test_create_order_unavailable_item_returns_422(seeded_client: TestClient, db_engine: Engine) -> None:
    menu = seeded_client.get("/api/restaurants/demo/menu").json()
    table_id = menu["tables"][0]["id"]
    item = menu["categories"][0]["items"][0]
    token = _get_diner_token(seeded_client)

    # Mark the item as unavailable
    with SASession(db_engine) as s:
        mi = s.scalar(select(MenuItem).where(MenuItem.id == item["id"]))
        assert mi is not None
        mi.is_available = False
        s.commit()

    r = _post_order(seeded_client, token, table_id, [{"menu_item_id": item["id"], "quantity": 1}])

    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "unavailable_item_ids" in detail
    assert item["id"] in detail["unavailable_item_ids"]


def test_create_order_inactive_table_returns_422(seeded_client: TestClient, db_engine: Engine) -> None:
    menu = seeded_client.get("/api/restaurants/demo/menu").json()
    item = menu["categories"][0]["items"][0]
    token = _get_diner_token(seeded_client)

    # Create an inactive table for the demo restaurant
    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.slug == "demo"))
        assert restaurant is not None
        inactive_table = RestaurantTable(
            restaurant_id=restaurant.id,
            number=99,
            label="Inactive Table",
            is_active=False,
        )
        s.add(inactive_table)
        s.commit()
        inactive_table_id = inactive_table.id

    r = _post_order(seeded_client, token, inactive_table_id, [{"menu_item_id": item["id"], "quantity": 1}])

    assert r.status_code == 422
    assert "inactive" in r.json()["detail"].lower() or "not found" in r.json()["detail"].lower()


def test_create_order_transaction_rollback_on_db_error(seeded_client: TestClient, db_engine: Engine) -> None:
    """DB error during commit rolls back the entire transaction; no order persisted."""
    menu = seeded_client.get("/api/restaurants/demo/menu").json()
    table_id = menu["tables"][0]["id"]
    item = menu["categories"][0]["items"][0]
    # Register diner before patching commit to avoid affecting token creation
    token = _get_diner_token(seeded_client)
    orders_before = _count_orders(db_engine)

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OperationalError("simulated DB failure", None, None)

    with patch.object(SASession, "commit", boom):
        # TestClient with raise_server_exceptions=True will re-raise the OperationalError
        with pytest.raises(OperationalError):
            _post_order(seeded_client, token, table_id, [{"menu_item_id": item["id"], "quantity": 1}])

    # All inserts must have been rolled back — DB stays clean
    assert _count_orders(db_engine) == orders_before


def _count_orders(db_engine: Engine) -> int:
    with SASession(db_engine) as s:
        return s.scalar(select(func.count()).select_from(Order)) or 0
