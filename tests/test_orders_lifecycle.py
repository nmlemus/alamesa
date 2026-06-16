"""Integration tests for the full order lifecycle (ticket S3-04).

Covers: PENDING→CONFIRMED→PREPARING→READY→CLOSED and terminal state enforcement.
"""
from fastapi.testclient import TestClient


# ── helpers ───────────────────────────────────────────────────────────────────


def _get_diner_token(client: TestClient, phone: str = "+34699000001") -> str:
    restaurant = client.get("/api/public/restaurants/demo").json()
    r = client.post(
        f"/api/public/restaurants/{restaurant['id']}/diners/register",
        json={"name": "Test Diner", "phone": phone},
    )
    assert r.status_code in (200, 201), r.json()
    return r.json()["access_token"]


def _get_staff_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.mesadigital.io", "password": "demo1234"},
    )
    assert r.status_code == 200, r.json()
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


# ── lifecycle tests ───────────────────────────────────────────────────────────


def test_full_order_lifecycle(seeded_client: TestClient) -> None:
    """Full happy-path: PENDING → CONFIRMED → PREPARING → READY → CLOSED."""
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.post(
        f"/api/orders/{order_id}/confirm",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"
    assert data["confirmed_at"] is not None

    r = seeded_client.post(
        f"/api/orders/{order_id}/start-preparing",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "preparing"
    assert data["preparing_at"] is not None

    r = seeded_client.post(
        f"/api/orders/{order_id}/mark-ready",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ready"
    assert data["ready_at"] is not None

    r = seeded_client.post(
        f"/api/orders/{order_id}/close",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "closed"
    assert data["closed_at"] is not None


def test_closed_order_rejects_all_transitions(seeded_client: TestClient) -> None:
    """CLOSED is a terminal state: every transition endpoint must return 409."""
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    for endpoint in ["confirm", "start-preparing", "mark-ready", "close"]:
        seeded_client.post(
            f"/api/orders/{order_id}/{endpoint}",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

    for endpoint in ["confirm", "start-preparing", "mark-ready", "close"]:
        r = seeded_client.post(
            f"/api/orders/{order_id}/{endpoint}",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert r.status_code == 409, f"Expected 409 for {endpoint} on CLOSED order, got {r.status_code}"
