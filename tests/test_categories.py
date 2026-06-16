"""Integration tests for Category CRUD (ticket S4-01)."""
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
        json={"name": "Test Diner", "phone": "+34699000001"},
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


def _create_category(
    client: TestClient, token: str, rid: str, name: str = "Test Category", **kwargs: object
) -> dict:
    r = client.post(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, **kwargs},
    )
    assert r.status_code == 201, r.json()
    return r.json()


# ── GET /api/restaurants/{rid}/categories ─────────────────────────────────────


def test_list_categories_staff_returns_list(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    for cat in data:
        assert cat["restaurant_id"] == rid
        assert "id" in cat
        assert "name" in cat
        assert "is_visible" in cat
        assert "display_order" in cat


def test_list_categories_sorted_by_display_order(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    orders = [cat["display_order"] for cat in r.json()]
    assert orders == sorted(orders)


def test_list_categories_no_auth_returns_401(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(f"/api/restaurants/{rid}/categories")

    assert r.status_code == 401


def test_list_categories_diner_token_returns_401(seeded_client: TestClient) -> None:
    diner_token = _get_diner_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {diner_token}"},
    )

    assert r.status_code == 401


def test_list_categories_cross_tenant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)
    _setup_second_restaurant(db_engine)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {_other_staff_token(seeded_client)}"},
    )

    assert r.status_code == 403


# ── POST /api/restaurants/{rid}/categories ────────────────────────────────────


def test_create_category_returns_201_with_category_read(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Postres", "is_visible": True, "display_order": 10},
    )

    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Postres"
    assert data["is_visible"] is True
    assert data["display_order"] == 10
    assert data["restaurant_id"] == rid
    assert "id" in data


def test_create_category_default_fields(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Sin Gluten"},
    )

    assert r.status_code == 201
    data = r.json()
    assert data["is_visible"] is True
    assert data["display_order"] == 0


def test_create_category_missing_name_returns_422(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_visible": True},
    )

    assert r.status_code == 422


def test_create_category_no_auth_returns_401(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/categories",
        json={"name": "Intruder"},
    )

    assert r.status_code == 401


def test_create_category_cross_tenant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)
    _setup_second_restaurant(db_engine)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/categories",
        headers={"Authorization": f"Bearer {_other_staff_token(seeded_client)}"},
        json={"name": "Intrusion"},
    )

    assert r.status_code == 403


# ── PATCH /api/categories/{id} ────────────────────────────────────────────────


def test_patch_category_name(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    cat = _create_category(seeded_client, token, rid, name="Original")

    r = seeded_client.patch(
        f"/api/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Updated"},
    )

    assert r.status_code == 200
    assert r.json()["name"] == "Updated"


def test_patch_category_is_visible(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    cat = _create_category(seeded_client, token, rid, name="Visible Cat", is_visible=True)

    r = seeded_client.patch(
        f"/api/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_visible": False},
    )

    assert r.status_code == 200
    assert r.json()["is_visible"] is False


def test_patch_category_display_order(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    cat = _create_category(seeded_client, token, rid, name="Order Cat", display_order=5)

    r = seeded_client.patch(
        f"/api/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_order": 99},
    )

    assert r.status_code == 200
    assert r.json()["display_order"] == 99


def test_patch_category_not_found_returns_404(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)

    r = seeded_client.patch(
        "/api/categories/nonexistentid0000000000000000000",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Ghost"},
    )

    assert r.status_code == 404


def test_patch_category_cross_tenant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    cat = _create_category(seeded_client, token, rid, name="Owned Cat")

    _setup_second_restaurant(db_engine)

    r = seeded_client.patch(
        f"/api/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {_other_staff_token(seeded_client)}"},
        json={"name": "Hacked"},
    )

    assert r.status_code == 403


def test_patch_category_no_auth_returns_401(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    cat = _create_category(seeded_client, token, rid, name="No Auth Cat")

    r = seeded_client.patch(
        f"/api/categories/{cat['id']}",
        json={"name": "No Auth"},
    )

    assert r.status_code == 401


# ── DELETE /api/categories/{id} ───────────────────────────────────────────────


def test_delete_empty_category_returns_204(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    cat = _create_category(seeded_client, token, rid, name="To Delete")

    r = seeded_client.delete(
        f"/api/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 204


def test_delete_category_with_items_returns_409(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    with SASession(db_engine) as s:
        cat = Category(restaurant_id=rid, name="Has Items", display_order=99)
        s.add(cat)
        s.flush()
        s.add(MenuItem(
            restaurant_id=rid,
            category_id=cat.id,
            name="Blocking Item",
            price_cents=500,
        ))
        s.commit()
        cat_id = cat.id

    r = seeded_client.delete(
        f"/api/categories/{cat_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 409


def test_delete_category_not_found_returns_404(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)

    r = seeded_client.delete(
        "/api/categories/nonexistentid0000000000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 404


def test_delete_category_cross_tenant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    cat = _create_category(seeded_client, token, rid, name="Target Cat")

    _setup_second_restaurant(db_engine)

    r = seeded_client.delete(
        f"/api/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {_other_staff_token(seeded_client)}"},
    )

    assert r.status_code == 403


def test_delete_category_no_auth_returns_401(seeded_client: TestClient) -> None:
    token = _get_staff_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    cat = _create_category(seeded_client, token, rid, name="No Auth Delete")

    r = seeded_client.delete(f"/api/categories/{cat['id']}")

    assert r.status_code == 401
