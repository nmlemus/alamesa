from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from mesadigital.api.db.session import get_db
from mesadigital.api.main import app


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_healthz_ok(client: TestClient) -> None:
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.json() == {"db": "ok"}


def test_healthz_db_down() -> None:
    def broken_db() -> Generator[MagicMock, None, None]:
        mock = MagicMock()
        mock.execute.side_effect = Exception("Connection refused")
        yield mock

    app.dependency_overrides[get_db] = broken_db
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/api/healthz")
        assert r.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_register_diner(seeded_client: TestClient) -> None:
    r = seeded_client.post(
        "/api/diners/register",
        json={
            "restaurant_slug": "demo",
            "phone": "+34600000001",
            "name": "Ana García",
            "password": "s3cr3t",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["phone"] == "+34600000001"
    assert data["name"] == "Ana García"
    assert isinstance(data["id"], str) and len(data["id"]) == 32


def test_register_diner_duplicate_phone(seeded_client: TestClient) -> None:
    payload = {
        "restaurant_slug": "demo",
        "phone": "+34600000002",
        "name": "User",
        "password": "pass",
    }
    seeded_client.post("/api/diners/register", json=payload)
    r = seeded_client.post("/api/diners/register", json=payload)
    assert r.status_code == 409


def test_register_diner_unknown_restaurant(client: TestClient) -> None:
    r = client.post(
        "/api/diners/register",
        json={
            "restaurant_slug": "does-not-exist",
            "phone": "+34600000003",
            "name": "Ghost",
            "password": "pass",
        },
    )
    assert r.status_code == 404


def test_get_menu_unknown_slug(client: TestClient) -> None:
    r = client.get("/api/restaurants/does-not-exist/menu")
    assert r.status_code == 404


def test_get_menu(seeded_client: TestClient) -> None:
    r = seeded_client.get("/api/restaurants/demo/menu")
    assert r.status_code == 200
    data = r.json()

    assert data["restaurant"]["slug"] == "demo"
    assert data["restaurant"]["name"] == "Restaurante Demo"
    assert len(data["categories"]) == 2
    assert len(data["tables"]) == 3

    all_items = [item for cat in data["categories"] for item in cat["items"]]
    assert len(all_items) == 5
    assert all(item["price_cents"] > 0 for item in all_items)


def test_create_order(seeded_client: TestClient) -> None:
    menu = seeded_client.get("/api/restaurants/demo/menu").json()
    table_id = menu["tables"][0]["id"]
    item_id = menu["categories"][0]["items"][0]["id"]

    r = seeded_client.post(
        "/api/orders",
        json={
            "restaurant_slug": "demo",
            "table_id": table_id,
            "items": [{"menu_item_id": item_id, "quantity": 2}],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["table_id"] == table_id


def test_order_full_lifecycle(seeded_client: TestClient) -> None:
    menu = seeded_client.get("/api/restaurants/demo/menu").json()
    table_id = menu["tables"][0]["id"]
    item_id = menu["categories"][0]["items"][0]["id"]

    order_id = seeded_client.post(
        "/api/orders",
        json={
            "restaurant_slug": "demo",
            "table_id": table_id,
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
    ).json()["id"]

    for status in ("confirmed", "preparing", "ready", "closed"):
        r = seeded_client.patch(
            f"/api/orders/{order_id}/status", json={"status": status}
        )
        assert r.status_code == 200, r.json()
        assert r.json()["status"] == status


def test_invalid_status_transition(seeded_client: TestClient) -> None:
    menu = seeded_client.get("/api/restaurants/demo/menu").json()
    table_id = menu["tables"][0]["id"]
    item_id = menu["categories"][0]["items"][0]["id"]

    order_id = seeded_client.post(
        "/api/orders",
        json={
            "restaurant_slug": "demo",
            "table_id": table_id,
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
    ).json()["id"]

    # Cannot jump pending → ready (skipping confirmed and preparing)
    r = seeded_client.patch(
        f"/api/orders/{order_id}/status", json={"status": "ready"}
    )
    assert r.status_code == 422


def test_invalid_status_value(seeded_client: TestClient) -> None:
    r = seeded_client.patch("/api/orders/nonexistent/status", json={"status": "cooking"})
    assert r.status_code == 400


def test_order_not_found(seeded_client: TestClient) -> None:
    r = seeded_client.patch("/api/orders/9999/status", json={"status": "confirmed"})
    assert r.status_code == 404
