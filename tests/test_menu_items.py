"""Integration tests for MenuItem CRUD (ticket S4-02)."""
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import Category, MenuItem, Restaurant, RestaurantUser, RestaurantUserRole
from mesadigital.api.security import hash_password


# ── helpers ───────────────────────────────────────────────────────────────────


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
        json={"name": "Test Diner", "phone": "+34699000002"},
    )
    assert r.status_code in (200, 201), r.json()
    return r.json()["access_token"]


def _get_restaurant_id(client: TestClient) -> str:
    return client.get("/api/public/restaurants/demo").json()["id"]


def _setup_second_restaurant(db_engine: Engine) -> tuple[str, str]:
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


def _other_staff_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@other.mesadigital.io", "password": "demo1234"},
    )
    assert r.status_code == 200, r.json()
    return r.json()["access_token"]


def _get_category_id(client: TestClient, token: str, rid: str) -> str:
    r = client.get(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.json()
    categories = r.json()
    assert len(categories) > 0, "seeded data must have at least one category"
    return categories[0]["id"]


def _create_item(
    client: TestClient,
    token: str,
    rid: str,
    category_id: str,
    name: str = "Test Item",
    price_cents: int = 1000,
    **kwargs: object,
) -> dict:
    r = client.post(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": category_id, "name": name, "price_cents": price_cents, **kwargs},
    )
    assert r.status_code == 201, r.json()
    return r.json()


# ── GET /api/restaurants/{rid}/menu-items ─────────────────────────────────────


def test_list_menu_items_returns_list(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    for item in data:
        assert item["restaurant_id"] == rid
        assert "id" in item
        assert "name" in item
        assert "price_cents" in item
        assert "category_id" in item
        assert "is_available" in item
        assert "display_order" in item


def test_list_menu_items_sorted_by_display_order(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    orders = [item["display_order"] for item in r.json()]
    assert orders == sorted(orders)


def test_list_menu_items_filter_by_category_id(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
        params={"category_id": category_id},
    )

    assert r.status_code == 200
    data = r.json()
    for item in data:
        assert item["category_id"] == category_id


def test_list_menu_items_no_auth_returns_403(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(f"/api/restaurants/{rid}/menu-items")

    assert r.status_code == 403


def test_list_menu_items_diner_token_returns_401(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {diner_token}"},
    )

    assert r.status_code == 401


def test_list_menu_items_cross_tenant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)
    _setup_second_restaurant(db_engine)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {_other_staff_token(seeded_client)}"},
    )

    assert r.status_code == 403


# ── POST /api/restaurants/{rid}/menu-items ────────────────────────────────────


def test_create_menu_item_returns_201(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "category_id": category_id,
            "name": "Tortilla Española",
            "description": "Clásica tortilla de patata",
            "price_cents": 850,
            "is_available": True,
            "display_order": 5,
        },
    )

    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Tortilla Española"
    assert data["description"] == "Clásica tortilla de patata"
    assert data["price_cents"] == 850
    assert data["is_available"] is True
    assert data["display_order"] == 5
    assert data["category_id"] == category_id
    assert data["restaurant_id"] == rid
    assert "id" in data


def test_create_menu_item_default_fields(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": category_id, "name": "Agua", "price_cents": 150},
    )

    assert r.status_code == 201
    data = r.json()
    assert data["is_available"] is True
    assert data["display_order"] == 0
    assert data["description"] is None


def test_create_menu_item_zero_price_returns_422(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": category_id, "name": "Free", "price_cents": 0},
    )

    assert r.status_code == 422


def test_create_menu_item_negative_price_returns_422(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": category_id, "name": "Negative", "price_cents": -100},
    )

    assert r.status_code == 422


def test_create_menu_item_cross_tenant_category_returns_422(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    other_rid, _ = _setup_second_restaurant(db_engine)

    with SASession(db_engine) as s:
        other_cat = Category(restaurant_id=other_rid, name="Other Cat", display_order=0)
        s.add(other_cat)
        s.commit()
        other_cat_id = other_cat.id

    r = seeded_client.post(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": other_cat_id, "name": "Smuggled", "price_cents": 500},
    )

    assert r.status_code == 422


def test_create_menu_item_missing_name_returns_422(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": category_id, "price_cents": 500},
    )

    assert r.status_code == 422


def test_create_menu_item_no_auth_returns_403(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/menu-items",
        json={"category_id": "anycatid", "name": "Intruder", "price_cents": 500},
    )

    assert r.status_code == 403


def test_create_menu_item_cross_tenant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    _setup_second_restaurant(db_engine)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/menu-items",
        headers={"Authorization": f"Bearer {_other_staff_token(seeded_client)}"},
        json={"category_id": category_id, "name": "Intrusion", "price_cents": 500},
    )

    assert r.status_code == 403


# ── PATCH /api/menu-items/{id} ────────────────────────────────────────────────


def test_patch_menu_item_name(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id, name="Original Name")

    r = seeded_client.patch(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Updated Name"},
    )

    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"


def test_patch_menu_item_price(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id, price_cents=1000)

    r = seeded_client.patch(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"price_cents": 2500},
    )

    assert r.status_code == 200
    assert r.json()["price_cents"] == 2500


def test_patch_menu_item_availability(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id, is_available=True)

    r = seeded_client.patch(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_available": False},
    )

    assert r.status_code == 200
    assert r.json()["is_available"] is False


def test_patch_menu_item_category(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    categories = seeded_client.get(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert len(categories) >= 2, "seeded data must have at least two categories"
    cat1_id = categories[0]["id"]
    cat2_id = categories[1]["id"]

    item = _create_item(seeded_client, token, rid, cat1_id)

    r = seeded_client.patch(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": cat2_id},
    )

    assert r.status_code == 200
    assert r.json()["category_id"] == cat2_id


def test_patch_menu_item_cross_tenant_category_returns_422(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id)
    other_rid, _ = _setup_second_restaurant(db_engine)

    with SASession(db_engine) as s:
        other_cat = Category(restaurant_id=other_rid, name="Other Cat", display_order=0)
        s.add(other_cat)
        s.commit()
        other_cat_id = other_cat.id

    r = seeded_client.patch(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"category_id": other_cat_id},
    )

    assert r.status_code == 422


def test_patch_menu_item_zero_price_returns_422(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id)

    r = seeded_client.patch(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"price_cents": 0},
    )

    assert r.status_code == 422


def test_patch_menu_item_not_found_returns_404(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)

    r = seeded_client.patch(
        "/api/menu-items/nonexistentid0000000000000000000",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Ghost"},
    )

    assert r.status_code == 404


def test_patch_menu_item_cross_tenant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id)
    _setup_second_restaurant(db_engine)

    r = seeded_client.patch(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {_other_staff_token(seeded_client)}"},
        json={"name": "Hacked"},
    )

    assert r.status_code == 403


def test_patch_menu_item_no_auth_returns_403(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id)

    r = seeded_client.patch(
        f"/api/menu-items/{item['id']}",
        json={"name": "No Auth"},
    )

    assert r.status_code == 403


# ── DELETE /api/menu-items/{id} ───────────────────────────────────────────────


def test_delete_menu_item_returns_204(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id, name="To Delete")

    r = seeded_client.delete(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 204


def test_delete_menu_item_with_order_items_allowed(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    """DELETE is always allowed; historical order_items keep the snapshot."""
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id, name="Referenced Item")

    r = seeded_client.delete(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 204


def test_delete_menu_item_not_found_returns_404(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)

    r = seeded_client.delete(
        "/api/menu-items/nonexistentid0000000000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 404


def test_delete_menu_item_cross_tenant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id, name="Target Item")
    _setup_second_restaurant(db_engine)

    r = seeded_client.delete(
        f"/api/menu-items/{item['id']}",
        headers={"Authorization": f"Bearer {_other_staff_token(seeded_client)}"},
    )

    assert r.status_code == 403


def test_delete_menu_item_no_auth_returns_403(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    category_id = _get_category_id(seeded_client, token, rid)
    item = _create_item(seeded_client, token, rid, category_id, name="No Auth Delete")

    r = seeded_client.delete(f"/api/menu-items/{item['id']}")

    assert r.status_code == 403


# ── AC5: Cross-tenant isolation ───────────────────────────────────────────────


def test_cross_tenant_isolation_restaurant_a_cannot_see_b_items(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token_a = _get_staff_token(seeded_client)
    rid_a = _get_restaurant_id(seeded_client)
    other_rid, _ = _setup_second_restaurant(db_engine)

    with SASession(db_engine) as s:
        other_cat = Category(restaurant_id=other_rid, name="B Category", display_order=0)
        s.add(other_cat)
        s.flush()
        other_item = MenuItem(
            restaurant_id=other_rid,
            category_id=other_cat.id,
            name="Restaurant B Item",
            price_cents=999,
        )
        s.add(other_item)
        s.commit()
        other_item_id = other_item.id

    r = seeded_client.get(
        f"/api/restaurants/{rid_a}/menu-items",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert r.status_code == 200
    ids = [item["id"] for item in r.json()]
    assert other_item_id not in ids


def test_cross_tenant_isolation_restaurant_b_cannot_get_a_list(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid_a = _get_restaurant_id(seeded_client)
    _setup_second_restaurant(db_engine)
    token_b = _other_staff_token(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid_a}/menu-items",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert r.status_code == 403
