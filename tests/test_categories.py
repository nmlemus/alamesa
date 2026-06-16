from datetime import timedelta
from typing import NamedTuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from mesadigital.api.db.models import Category, MenuItem, Restaurant, RestaurantUser
from mesadigital.api.security import create_token, hash_password
from shared.contracts import RestaurantUserRole


def _staff_token(user: RestaurantUser) -> str:
    return create_token(
        {
            "sub": user.id,
            "restaurant_id": user.restaurant_id,
            "role": str(user.role),
            "type": "staff",
        },
        timedelta(days=1),
    )


class _Ctx(NamedTuple):
    restaurant_id: str
    admin_token: str
    staff_token: str
    cat1_id: str  # Starters, display_order=1
    cat2_id: str  # Mains, display_order=0


@pytest.fixture()
def ctx(client: TestClient, db_engine: Engine) -> _Ctx:
    with Session(db_engine) as session:
        rest = Restaurant(slug="cat-test", name="Category Test Restaurant")
        session.add(rest)
        session.flush()

        admin = RestaurantUser(
            restaurant_id=rest.id,
            email="admin@cat.test",
            hashed_password=hash_password("pass"),
            role=RestaurantUserRole.ADMIN,
            is_active=True,
        )
        staff = RestaurantUser(
            restaurant_id=rest.id,
            email="staff@cat.test",
            hashed_password=hash_password("pass"),
            role=RestaurantUserRole.STAFF,
            is_active=True,
        )
        session.add_all([admin, staff])
        session.flush()

        cat1 = Category(restaurant_id=rest.id, name="Starters", display_order=1)
        cat2 = Category(restaurant_id=rest.id, name="Mains", display_order=0)
        session.add_all([cat1, cat2])
        session.commit()

        return _Ctx(
            restaurant_id=rest.id,
            admin_token=_staff_token(admin),
            staff_token=_staff_token(staff),
            cat1_id=cat1.id,
            cat2_id=cat2.id,
        )


@pytest.fixture()
def other_ctx(client: TestClient, db_engine: Engine) -> _Ctx:
    """A second restaurant with its own admin and one category."""
    with Session(db_engine) as session:
        rest = Restaurant(slug="other-rest", name="Other Restaurant")
        session.add(rest)
        session.flush()

        admin = RestaurantUser(
            restaurant_id=rest.id,
            email="admin@other.test",
            hashed_password=hash_password("pass"),
            role=RestaurantUserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        session.flush()

        cat = Category(restaurant_id=rest.id, name="Soups", display_order=0)
        session.add(cat)
        session.commit()

        return _Ctx(
            restaurant_id=rest.id,
            admin_token=_staff_token(admin),
            staff_token=_staff_token(admin),
            cat1_id=cat.id,
            cat2_id=cat.id,
        )


# ── GET /api/restaurants/{rid}/categories ─────────────────────────────────


def test_list_categories_sorted(client: TestClient, ctx: _Ctx) -> None:
    r = client.get(
        f"/api/restaurants/{ctx.restaurant_id}/categories",
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    # sorted by display_order: Mains (0) before Starters (1)
    assert data[0]["name"] == "Mains"
    assert data[1]["name"] == "Starters"


def test_list_categories_response_shape(client: TestClient, ctx: _Ctx) -> None:
    r = client.get(
        f"/api/restaurants/{ctx.restaurant_id}/categories",
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 200
    cat = r.json()[0]
    assert "id" in cat
    assert "restaurant_id" in cat
    assert "name" in cat
    assert "is_visible" in cat
    assert "display_order" in cat
    assert cat["items"] == []


def test_list_categories_requires_auth(client: TestClient, ctx: _Ctx) -> None:
    r = client.get(f"/api/restaurants/{ctx.restaurant_id}/categories")
    assert r.status_code == 403


def test_list_categories_requires_admin_role(client: TestClient, ctx: _Ctx) -> None:
    r = client.get(
        f"/api/restaurants/{ctx.restaurant_id}/categories",
        headers={"Authorization": f"Bearer {ctx.staff_token}"},
    )
    assert r.status_code == 403


# ── POST /api/restaurants/{rid}/categories ────────────────────────────────


def test_create_category(client: TestClient, ctx: _Ctx) -> None:
    r = client.post(
        f"/api/restaurants/{ctx.restaurant_id}/categories",
        json={"name": "Desserts", "display_order": 2, "is_visible": True},
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Desserts"
    assert data["display_order"] == 2
    assert data["is_visible"] is True
    assert data["restaurant_id"] == ctx.restaurant_id
    assert isinstance(data["id"], str) and len(data["id"]) == 32
    assert data["items"] == []


def test_create_category_defaults(client: TestClient, ctx: _Ctx) -> None:
    r = client.post(
        f"/api/restaurants/{ctx.restaurant_id}/categories",
        json={"name": "Drinks"},
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["display_order"] == 0
    assert data["is_visible"] is True


def test_create_category_requires_auth(client: TestClient, ctx: _Ctx) -> None:
    r = client.post(
        f"/api/restaurants/{ctx.restaurant_id}/categories",
        json={"name": "NoAuth"},
    )
    assert r.status_code == 403


def test_create_category_requires_admin_role(client: TestClient, ctx: _Ctx) -> None:
    r = client.post(
        f"/api/restaurants/{ctx.restaurant_id}/categories",
        json={"name": "StaffAttempt"},
        headers={"Authorization": f"Bearer {ctx.staff_token}"},
    )
    assert r.status_code == 403


# ── PATCH /api/categories/{id} ────────────────────────────────────────────


def test_patch_category_name(client: TestClient, ctx: _Ctx) -> None:
    r = client.patch(
        f"/api/categories/{ctx.cat1_id}",
        json={"name": "Appetizers"},
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Appetizers"
    assert data["display_order"] == 1  # unchanged
    assert data["is_visible"] is True  # unchanged


def test_patch_category_all_fields(client: TestClient, ctx: _Ctx) -> None:
    r = client.patch(
        f"/api/categories/{ctx.cat1_id}",
        json={"name": "Hidden", "display_order": 99, "is_visible": False},
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Hidden"
    assert data["display_order"] == 99
    assert data["is_visible"] is False


def test_patch_category_display_order(client: TestClient, ctx: _Ctx) -> None:
    r = client.patch(
        f"/api/categories/{ctx.cat2_id}",
        json={"display_order": 5},
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["display_order"] == 5


def test_patch_category_not_found(client: TestClient, ctx: _Ctx) -> None:
    r = client.patch(
        "/api/categories/nonexistent",
        json={"name": "X"},
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 404


def test_patch_category_requires_auth(client: TestClient, ctx: _Ctx) -> None:
    r = client.patch(f"/api/categories/{ctx.cat1_id}", json={"name": "X"})
    assert r.status_code == 403


# ── DELETE /api/categories/{id} ───────────────────────────────────────────


def test_delete_category(client: TestClient, ctx: _Ctx) -> None:
    r = client.delete(
        f"/api/categories/{ctx.cat2_id}",
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 204


def test_delete_category_with_items_returns_409(
    client: TestClient, ctx: _Ctx, db_engine: Engine
) -> None:
    with Session(db_engine) as session:
        session.add(
            MenuItem(
                restaurant_id=ctx.restaurant_id,
                category_id=ctx.cat1_id,
                name="Test Item",
                price_cents=100,
            )
        )
        session.commit()

    r = client.delete(
        f"/api/categories/{ctx.cat1_id}",
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 409


def test_delete_category_not_found(client: TestClient, ctx: _Ctx) -> None:
    r = client.delete(
        "/api/categories/nonexistent",
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 404


def test_delete_category_requires_auth(client: TestClient, ctx: _Ctx) -> None:
    r = client.delete(f"/api/categories/{ctx.cat1_id}")
    assert r.status_code == 403


# ── Cross-tenant isolation ────────────────────────────────────────────────


def test_cross_tenant_list(
    client: TestClient, ctx: _Ctx, other_ctx: _Ctx
) -> None:
    r = client.get(
        f"/api/restaurants/{other_ctx.restaurant_id}/categories",
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 403


def test_cross_tenant_create(
    client: TestClient, ctx: _Ctx, other_ctx: _Ctx
) -> None:
    r = client.post(
        f"/api/restaurants/{other_ctx.restaurant_id}/categories",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 403


def test_cross_tenant_patch(
    client: TestClient, ctx: _Ctx, other_ctx: _Ctx
) -> None:
    r = client.patch(
        f"/api/categories/{other_ctx.cat1_id}",
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 403


def test_cross_tenant_delete(
    client: TestClient, ctx: _Ctx, other_ctx: _Ctx
) -> None:
    r = client.delete(
        f"/api/categories/{other_ctx.cat1_id}",
        headers={"Authorization": f"Bearer {ctx.admin_token}"},
    )
    assert r.status_code == 403
