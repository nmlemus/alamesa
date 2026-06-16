"""Integration tests for POST /api/orders/{id}/close (ticket S3-04)."""
import threading

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import Order, OrderEvent, Restaurant, RestaurantUser, RestaurantUserRole
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


def _advance_to_ready(client: TestClient, order_id: str, staff_token: str) -> None:
    for endpoint in ["confirm", "start-preparing", "mark-ready"]:
        r = client.post(
            f"/api/orders/{order_id}/{endpoint}",
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


# ── POST /api/orders/{id}/close ───────────────────────────────────────────────


def test_close_ready_order_returns_200(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)
    _advance_to_ready(seeded_client, order_id, staff_token)

    r = seeded_client.post(
        f"/api/orders/{order_id}/close",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == order_id
    assert data["status"] == "closed"
    assert data["closed_at"] is not None


def test_close_event_recorded(seeded_client: TestClient, db_engine: Engine) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)
    _advance_to_ready(seeded_client, order_id, staff_token)

    seeded_client.post(
        f"/api/orders/{order_id}/close",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    with SASession(db_engine) as s:
        events = s.scalars(
            select(OrderEvent).where(
                OrderEvent.order_id == order_id,
                OrderEvent.from_status == OrderStatus.READY,
                OrderEvent.to_status == OrderStatus.CLOSED,
            )
        ).all()

    assert len(events) == 1
    event = events[0]
    assert event.actor_type == "staff"
    assert event.actor_id is not None


def test_close_already_closed_returns_409(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)
    _advance_to_ready(seeded_client, order_id, staff_token)

    r1 = seeded_client.post(
        f"/api/orders/{order_id}/close",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r1.status_code == 200

    r2 = seeded_client.post(
        f"/api/orders/{order_id}/close",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r2.status_code == 409


def test_close_order_not_ready_returns_409(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    with SASession(db_engine) as s:
        order = s.scalar(select(Order).where(Order.id == order_id))
        assert order is not None
        order.status = OrderStatus.CANCELLED
        s.commit()

    r = seeded_client.post(
        f"/api/orders/{order_id}/close",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 409


def test_close_order_not_found_returns_404(seeded_client: TestClient) -> None:
    staff_token = _get_staff_token(seeded_client)

    r = seeded_client.post(
        "/api/orders/nonexistentid00000000000000000/close",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 404


def test_close_cross_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)
    _advance_to_ready(seeded_client, order_id, staff_token)

    other_email = _setup_second_restaurant(db_engine)
    r_login = seeded_client.post(
        "/api/auth/login",
        json={"email": other_email, "password": "demo1234"},
    )
    other_staff_token = r_login.json()["access_token"]

    r = seeded_client.post(
        f"/api/orders/{order_id}/close",
        headers={"Authorization": f"Bearer {other_staff_token}"},
    )
    assert r.status_code == 403


def test_close_no_auth_returns_401(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.post(f"/api/orders/{order_id}/close")
    assert r.status_code == 401


def test_close_diner_token_returns_401(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.post(
        f"/api/orders/{order_id}/close",
        headers={"Authorization": f"Bearer {diner_token}"},
    )
    assert r.status_code == 401


def test_concurrent_close_one_200_one_409(seeded_client: TestClient) -> None:
    """Two close requests on the same READY order: exactly one 200, one 409."""
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)
    _advance_to_ready(seeded_client, order_id, staff_token)

    results: list[int] = []
    first_committed = threading.Event()

    def close_first() -> None:
        r = seeded_client.post(
            f"/api/orders/{order_id}/close",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        results.append(r.status_code)
        first_committed.set()

    def close_second() -> None:
        first_committed.wait(timeout=5)
        r = seeded_client.post(
            f"/api/orders/{order_id}/close",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        results.append(r.status_code)

    t1 = threading.Thread(target=close_first)
    t2 = threading.Thread(target=close_second)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert sorted(results) == [200, 409]
