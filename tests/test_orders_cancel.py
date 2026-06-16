"""Integration tests for POST /api/orders/{id}/cancel (ticket S3-05)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import OrderEvent, Restaurant, RestaurantUser, RestaurantUserRole
from mesadigital.api.security import hash_password
from shared.contracts import OrderStatus



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


def _confirm_order(client: TestClient, order_id: str, staff_token: str) -> None:
    r = client.post(
        f"/api/orders/{order_id}/confirm",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 200, r.json()


def _setup_second_restaurant(db_engine: Engine) -> str:
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
    return "admin@other.mesadigital.io"


# ── POST /api/orders/{id}/cancel ──────────────────────────────────────────────


def test_diner_cancels_pending_order_returns_200(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {diner_token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == order_id
    assert data["status"] == "cancelled"
    assert data["cancelled_at"] is not None


def test_diner_cancels_confirmed_order_returns_403(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)
    _confirm_order(seeded_client, order_id, staff_token)

    r = seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {diner_token}"},
    )

    assert r.status_code == 403


def test_staff_cancels_confirmed_order_returns_200(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)
    _confirm_order(seeded_client, order_id, staff_token)

    r = seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_at"] is not None


def test_cancel_already_cancelled_order_returns_409(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r1 = seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r1.status_code == 200

    r2 = seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r2.status_code == 409


def test_cancel_order_event_recorded_diner(seeded_client: TestClient, db_engine: Engine) -> None:
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {diner_token}"},
    )

    with SASession(db_engine) as s:
        events = s.scalars(
            select(OrderEvent).where(
                OrderEvent.order_id == order_id,
                OrderEvent.from_status == OrderStatus.PENDING,
                OrderEvent.to_status == OrderStatus.CANCELLED,
            )
        ).all()

    assert len(events) == 1
    assert events[0].actor_type == "diner"
    assert events[0].actor_id is not None


def test_cancel_order_event_recorded_staff(seeded_client: TestClient, db_engine: Engine) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)
    _confirm_order(seeded_client, order_id, staff_token)

    seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    with SASession(db_engine) as s:
        events = s.scalars(
            select(OrderEvent).where(
                OrderEvent.order_id == order_id,
                OrderEvent.from_status == OrderStatus.CONFIRMED,
                OrderEvent.to_status == OrderStatus.CANCELLED,
            )
        ).all()

    assert len(events) == 1
    assert events[0].actor_type == "staff"
    assert events[0].actor_id is not None


def test_staff_cancels_pending_order_returns_200(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_at"] is not None


def test_cancel_order_not_found_returns_404(seeded_client: TestClient) -> None:
    staff_token = _get_staff_token(seeded_client)

    r = seeded_client.post(
        "/api/orders/nonexistentid00000000000000000/cancel",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 404


def test_cancel_order_no_auth_returns_403(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.post(f"/api/orders/{order_id}/cancel")
    assert r.status_code == 403


def test_cancel_order_cross_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    other_email = _setup_second_restaurant(db_engine)
    r_login = seeded_client.post(
        "/api/auth/login",
        json={"email": other_email, "password": "demo1234"},
    )
    other_staff_token = r_login.json()["access_token"]

    r = seeded_client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {other_staff_token}"},
    )
    assert r.status_code == 403
