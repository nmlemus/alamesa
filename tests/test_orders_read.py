"""Integration tests for GET /api/orders/{id} and GET /api/restaurants/{rid}/orders (ticket S3-02)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import Order, Restaurant, RestaurantUser, RestaurantUserRole
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


def _post_order(client: TestClient, token: str, table_id: str, items: list[dict]) -> dict:
    return client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"restaurant_slug": "demo", "table_id": table_id, "items": items},
    )


def _menu(client: TestClient) -> dict:
    return client.get("/api/restaurants/demo/menu").json()


def _create_order(client: TestClient, token: str) -> str:
    menu = _menu(client)
    r = _post_order(
        client,
        token,
        menu["tables"][0]["id"],
        [{"menu_item_id": menu["categories"][0]["items"][0]["id"], "quantity": 1}],
    )
    assert r.status_code == 201, r.json()
    return r.json()["id"]


def _setup_second_restaurant(db_engine: Engine) -> tuple[str, str]:
    """Creates a second restaurant + admin user. Returns (restaurant_id, email)."""
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
        return rest2.id, "admin@other.mesadigital.io"


# ── GET /api/orders/{id} ──────────────────────────────────────────────────────


def test_get_order_diner_can_read_own_order(seeded_client: TestClient) -> None:
    token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, token)

    r = seeded_client.get(f"/api/orders/{order_id}", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == order_id
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert "total_cents" in data
    assert "item_count" in data


def test_get_order_diner_cannot_read_another_diners_order(seeded_client: TestClient) -> None:
    token1 = _get_diner_token(seeded_client, phone="+34699000001")
    token2 = _get_diner_token(seeded_client, phone="+34699000002")
    order_id = _create_order(seeded_client, token1)

    r = seeded_client.get(f"/api/orders/{order_id}", headers={"Authorization": f"Bearer {token2}"})

    assert r.status_code == 403


def test_get_order_staff_can_read_order_in_their_restaurant(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.get(f"/api/orders/{order_id}", headers={"Authorization": f"Bearer {staff_token}"})

    assert r.status_code == 200
    assert r.json()["id"] == order_id


def test_get_order_staff_cross_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    _setup_second_restaurant(db_engine)
    r_login = seeded_client.post(
        "/api/auth/login",
        json={"email": "admin@other.mesadigital.io", "password": "demo1234"},
    )
    other_staff_token = r_login.json()["access_token"]

    r = seeded_client.get(
        f"/api/orders/{order_id}", headers={"Authorization": f"Bearer {other_staff_token}"}
    )

    assert r.status_code == 403


def test_get_order_not_found_returns_404(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)

    r = seeded_client.get("/api/orders/nonexistentid00000000000000000", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 404


def test_get_order_no_auth_returns_401(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    r = seeded_client.get(f"/api/orders/{order_id}")

    assert r.status_code == 401


# ── GET /api/restaurants/{rid}/orders ─────────────────────────────────────────


def _get_restaurant_id(client: TestClient) -> str:
    return client.get("/api/public/restaurants/demo").json()["id"]


def test_list_orders_staff_returns_orders(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    _create_order(seeded_client, diner_token)
    _create_order(seeded_client, diner_token)

    r = seeded_client.get(f"/api/restaurants/{rid}/orders", headers={"Authorization": f"Bearer {staff_token}"})

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    for order in data:
        assert order["restaurant_id"] == rid
        assert "id" in order
        assert "status" in order
        assert "created_at" in order


def test_list_orders_status_filter_single(seeded_client: TestClient, db_engine: Engine) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    order_id = _create_order(seeded_client, diner_token)

    # Confirm one order so we have both pending and confirmed
    with SASession(db_engine) as s:
        o = s.scalar(select(Order).where(Order.id == order_id))
        assert o is not None
        o.status = OrderStatus.CONFIRMED
        s.commit()

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders?status=pending",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 200
    assert all(o["status"] == "pending" for o in r.json())


def test_list_orders_status_filter_comma_separated(seeded_client: TestClient, db_engine: Engine) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    order_id1 = _create_order(seeded_client, diner_token)
    _create_order(seeded_client, diner_token)

    with SASession(db_engine) as s:
        o = s.scalar(select(Order).where(Order.id == order_id1))
        assert o is not None
        o.status = OrderStatus.CONFIRMED
        s.commit()

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders?status=pending,confirmed",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 200
    statuses = {o["status"] for o in r.json()}
    assert statuses <= {"pending", "confirmed"}
    assert "pending" in statuses
    assert "confirmed" in statuses


def test_list_orders_invalid_status_returns_422(seeded_client: TestClient) -> None:
    staff_token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders?status=notastatus",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 422


def test_list_orders_cross_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)
    _setup_second_restaurant(db_engine)
    r_login = seeded_client.post(
        "/api/auth/login",
        json={"email": "admin@other.mesadigital.io", "password": "demo1234"},
    )
    other_staff_token = r_login.json()["access_token"]

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders",
        headers={"Authorization": f"Bearer {other_staff_token}"},
    )
    assert r.status_code == 403


def test_list_orders_keyset_pagination(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    staff_token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    menu = _menu(seeded_client)
    table_id = menu["tables"][0]["id"]
    item_id = menu["categories"][0]["items"][0]["id"]

    created_ids = []
    for _ in range(5):
        r = _post_order(seeded_client, diner_token, table_id, [{"menu_item_id": item_id, "quantity": 1}])
        assert r.status_code == 201
        created_ids.append(r.json()["id"])

    # First page: limit=3
    r1 = seeded_client.get(
        f"/api/restaurants/{rid}/orders?limit=3",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r1.status_code == 200
    page1 = r1.json()
    assert len(page1) == 3

    # Second page: before=last item of page 1
    cursor = page1[-1]["id"]
    r2 = seeded_client.get(
        f"/api/restaurants/{rid}/orders?limit=3&before={cursor}",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r2.status_code == 200
    page2 = r2.json()

    # No overlap between pages
    page1_ids = {o["id"] for o in page1}
    page2_ids = {o["id"] for o in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_list_orders_invalid_cursor_returns_422(seeded_client: TestClient) -> None:
    staff_token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders?before=doesnotexist00000000000000000000",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 422


def test_list_orders_no_auth_returns_401(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(f"/api/restaurants/{rid}/orders")

    assert r.status_code == 401


def test_list_orders_diner_token_returns_401(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders",
        headers={"Authorization": f"Bearer {diner_token}"},
    )
    assert r.status_code == 401
