"""Integration tests for GET /api/restaurants/{rid}/orders/stream (ticket S6-03)."""
import json

import pytest
import mesadigital.api.main as _main_module
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import Restaurant, RestaurantUser, RestaurantUserRole
from mesadigital.api.security import hash_password


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def fast_finite_poll(monkeypatch):
    """Single poll iteration with near-zero sleep so tests complete quickly."""
    monkeypatch.setattr(_main_module, "_SSE_POLL_INTERVAL", 0.001)
    monkeypatch.setattr(_main_module, "_SSE_MAX_ITERATIONS", 1)


# ── helpers ───────────────────────────────────────────────────────────────────


def _get_staff_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.mesadigital.io", "password": "demo1234"},
    )
    assert r.status_code == 200, r.json()
    return r.json()["access_token"]


def _get_restaurant_id(client: TestClient) -> str:
    r = client.get("/api/public/restaurants/demo")
    assert r.status_code == 200
    return r.json()["id"]


def _get_diner_token(client: TestClient) -> str:
    restaurant = client.get("/api/public/restaurants/demo").json()
    r = client.post(
        f"/api/public/restaurants/{restaurant['id']}/diners/register",
        json={"name": "Test Diner", "phone": "+34699000001"},
    )
    assert r.status_code in (200, 201), r.json()
    return r.json()["access_token"]


def _create_order(client: TestClient, diner_token: str) -> str:
    menu = client.get("/api/restaurants/demo/menu").json()
    r = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {diner_token}"},
        json={
            "restaurant_slug": "demo",
            "table_id": menu["tables"][0]["id"],
            "items": [{"menu_item_id": menu["categories"][0]["items"][0]["id"], "quantity": 1}],
        },
    )
    assert r.status_code == 201, r.json()
    return r.json()["id"]


def _setup_other_restaurant(db_engine: Engine) -> str:
    with SASession(db_engine) as s:
        rest2 = Restaurant(slug="other", name="Other Restaurant")
        s.add(rest2)
        s.flush()
        user2 = RestaurantUser(
            restaurant_id=rest2.id,
            email="admin@other.mesadigital.io",
            hashed_password=hash_password("demo1234"),
            role=RestaurantUserRole.ADMIN,
        )
        s.add(user2)
        s.commit()
        return str(rest2.id)


def _parse_sse_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


# ── tests ─────────────────────────────────────────────────────────────────────


def test_sse_requires_bearer_token(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)
    r = seeded_client.get(f"/api/restaurants/{rid}/orders/stream")
    assert r.status_code == 403


def test_sse_rejects_staff_from_wrong_restaurant(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)
    _setup_other_restaurant(db_engine)
    r = seeded_client.post(
        "/api/auth/login",
        json={"email": "admin@other.mesadigital.io", "password": "demo1234"},
    )
    other_token = r.json()["access_token"]
    r2 = seeded_client.get(
        f"/api/restaurants/{rid}/orders/stream",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r2.status_code == 403


def test_sse_content_type_and_retry_directive(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)
    staff_token = _get_staff_token(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders/stream",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    lines = _parse_sse_lines(r.text)
    assert any("retry" in ln and "3000" in ln for ln in lines)


def test_sse_sends_order_updated_for_existing_orders(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders/stream",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 200
    lines = _parse_sse_lines(r.text)
    assert any("order_updated" in ln for ln in lines), f"No order_updated in: {lines}"
    assert any(order_id in ln for ln in lines), f"Order {order_id} not in: {lines}"


def test_sse_data_is_valid_json_with_order_fields(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders/stream",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 200
    data_payloads = [
        line[6:]
        for line in r.text.splitlines()
        if line.startswith("data: ")
    ]
    assert data_payloads, "No data lines received"

    target = next((p for p in data_payloads if order_id in p), None)
    assert target is not None, f"Order {order_id} not found in payloads: {data_payloads}"

    payload = json.loads(target)
    assert payload["id"] == order_id
    assert payload["status"] == "pending"
    assert "restaurant_id" in payload
    assert "table_id" in payload
    assert "created_at" in payload


def test_sse_only_sends_delta_on_status_change(seeded_client: TestClient, monkeypatch) -> None:
    """Subsequent polls only emit events for orders whose status changed."""
    monkeypatch.setattr(_main_module, "_SSE_MAX_ITERATIONS", 2)
    rid = _get_restaurant_id(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders/stream",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 200
    # The order appears only once across both iterations (no duplicate events)
    occurrences = r.text.count(order_id)
    assert occurrences == 1, f"Expected 1 occurrence, got {occurrences}"
