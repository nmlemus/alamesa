"""Integration tests for POST /api/orders/{id}/confirm (ticket S3-03)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import OrderEvent, Restaurant, RestaurantUser
from mesadigital.api.security import create_token, hash_password
from shared.contracts import RestaurantUserRole


def _get_staff_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.mesadigital.io", "password": "demo1234"},
    )
    assert r.status_code == 200, r.json()
    return r.json()["access_token"]


def _get_diner_token(client: TestClient) -> str:
    restaurant = client.get("/api/public/restaurants/demo").json()
    r = client.post(
        f"/api/public/restaurants/{restaurant['id']}/diners/register",
        json={"name": "Test Diner", "phone": "+34699000001"},
    )
    assert r.status_code in (200, 201), r.json()
    return r.json()["access_token"]


def _create_order(client: TestClient, diner_token: str) -> dict:
    menu = client.get("/api/restaurants/demo/menu").json()
    table_id = menu["tables"][0]["id"]
    item = menu["categories"][0]["items"][0]
    r = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {diner_token}"},
        json={
            "restaurant_slug": "demo",
            "table_id": table_id,
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
    )
    assert r.status_code == 201, r.json()
    return r.json()


def test_confirm_happy_path(seeded_client: TestClient, db_engine: Engine) -> None:
    staff_token = _get_staff_token(seeded_client)
    diner_token = _get_diner_token(seeded_client)
    order = _create_order(seeded_client, diner_token)

    r = seeded_client.post(
        f"/api/orders/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 200, r.json()
    data = r.json()
    assert data["id"] == order["id"]
    assert data["status"] == "confirmed"
    assert data["confirmed_at"] is not None
    assert data["updated_at"] is not None

    with SASession(db_engine) as s:
        events = (
            s.query(OrderEvent)
            .filter_by(order_id=order["id"])
            .order_by(OrderEvent.created_at)
            .all()
        )
        confirm_events = [e for e in events if str(e.to_status) == "confirmed"]
        assert len(confirm_events) == 1
        evt = confirm_events[0]
        assert str(evt.from_status) == "pending"
        assert str(evt.actor_type) == "staff"
        assert evt.actor_id is not None


def test_confirm_requires_bearer_token(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    order = _create_order(seeded_client, diner_token)

    r = seeded_client.post(f"/api/orders/{order['id']}/confirm")
    assert r.status_code == 403


def test_confirm_rejects_diner_token(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    order = _create_order(seeded_client, diner_token)

    r = seeded_client.post(
        f"/api/orders/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {diner_token}"},
    )
    assert r.status_code == 401


def test_confirm_wrong_restaurant_scope(seeded_client: TestClient, db_engine: Engine) -> None:
    with SASession(db_engine) as s:
        other = Restaurant(slug="other-resto", name="Other Resto")
        s.add(other)
        s.flush()
        other_user = RestaurantUser(
            restaurant_id=other.id,
            email="staff@other.io",
            hashed_password=hash_password("pass123"),
            role=RestaurantUserRole.STAFF,
        )
        s.add(other_user)
        s.commit()
        other_user_id = other_user.id
        other_restaurant_id = other.id

    other_token = create_token(
        {
            "sub": other_user_id,
            "restaurant_id": other_restaurant_id,
            "role": "staff",
            "type": "staff",
        },
        timedelta(days=1),
    )

    diner_token = _get_diner_token(seeded_client)
    order = _create_order(seeded_client, diner_token)

    r = seeded_client.post(
        f"/api/orders/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403


def test_confirm_not_found_returns_404(seeded_client: TestClient) -> None:
    staff_token = _get_staff_token(seeded_client)
    r = seeded_client.post(
        "/api/orders/00000000000000000000000000000000/confirm",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 404


def test_concurrent_confirm_one_200_one_409(seeded_client: TestClient) -> None:
    """Only the first confirm succeeds; the second gets 409 (order not PENDING)."""
    staff_token = _get_staff_token(seeded_client)
    diner_token = _get_diner_token(seeded_client)
    order = _create_order(seeded_client, diner_token)

    r1 = seeded_client.post(
        f"/api/orders/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    r2 = seeded_client.post(
        f"/api/orders/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert sorted([r1.status_code, r2.status_code]) == [200, 409]
