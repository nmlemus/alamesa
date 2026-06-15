"""Integration tests for GET /api/public/restaurants/{slug} and
GET /api/public/restaurants/{slug}/menu."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from mesadigital.api.db.models import Category, MenuItem, Restaurant

_SLUG = "test-pub-rest"
_REST_URL = "/api/public/restaurants/{slug}"
_MENU_URL = "/api/public/restaurants/{slug}/menu"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def active_restaurant_id(client: TestClient, db_engine: object) -> str:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        r = Restaurant(slug=_SLUG, name="Pub Rest", is_active=True)
        session.add(r)
        session.commit()
        session.refresh(r)
        return r.id


@pytest.fixture()
def menu_restaurant_id(client: TestClient, db_engine: object) -> str:
    """Seed: 3 visible categories × 4 items each + 1 hidden category."""
    with Session(db_engine) as session:  # type: ignore[arg-type]
        r = Restaurant(slug=_SLUG, name="Menu Rest", is_active=True)
        session.add(r)
        session.flush()

        # Visible categories in reverse order to test display_order sort
        cat_c = Category(
            restaurant_id=r.id, name="Cat C", is_visible=True, display_order=3
        )
        cat_b = Category(
            restaurant_id=r.id, name="Cat B", is_visible=True, display_order=2
        )
        cat_a = Category(
            restaurant_id=r.id, name="Cat A", is_visible=True, display_order=1
        )
        cat_hidden = Category(
            restaurant_id=r.id, name="Hidden", is_visible=False, display_order=0
        )
        session.add_all([cat_a, cat_b, cat_c, cat_hidden])
        session.flush()

        for cat, prefix in [(cat_a, "A"), (cat_b, "B"), (cat_c, "C")]:
            for i in range(1, 5):
                # 4th item in each visible category is unavailable
                session.add(
                    MenuItem(
                        restaurant_id=r.id,
                        category_id=cat.id,
                        name=f"Item {prefix}{i}",
                        price_cents=1000 * i,
                        is_available=(i != 4),
                        display_order=i * 10,
                    )
                )

        # Item in hidden category (should never appear)
        session.add(
            MenuItem(
                restaurant_id=r.id,
                category_id=cat_hidden.id,
                name="Hidden Item",
                price_cents=500,
                is_available=True,
                display_order=1,
            )
        )

        session.commit()
        return r.id


# ── GET /api/public/restaurants/{slug} ────────────────────────────────────────


def test_get_restaurant_returns_200(
    client: TestClient, active_restaurant_id: str
) -> None:
    r = client.get(_REST_URL.format(slug=_SLUG))
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == active_restaurant_id
    assert data["slug"] == _SLUG
    assert data["name"] == "Pub Rest"


def test_get_restaurant_unknown_slug_returns_404(client: TestClient) -> None:
    r = client.get(_REST_URL.format(slug="does-not-exist"))
    assert r.status_code == 404


def test_get_restaurant_inactive_returns_404(
    client: TestClient, db_engine: object
) -> None:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        rest = Restaurant(slug="inactive-slug", name="Inactive", is_active=False)
        session.add(rest)
        session.commit()

    r = client.get(_REST_URL.format(slug="inactive-slug"))
    assert r.status_code == 404


# ── GET /api/public/restaurants/{slug}/menu ───────────────────────────────────


def test_get_menu_unknown_slug_returns_404(client: TestClient) -> None:
    r = client.get(_MENU_URL.format(slug="no-such-restaurant"))
    assert r.status_code == 404


def test_get_menu_inactive_restaurant_returns_404(
    client: TestClient, db_engine: object
) -> None:
    with Session(db_engine) as session:  # type: ignore[arg-type]
        rest = Restaurant(slug="inactive-menu", name="Inactive", is_active=False)
        session.add(rest)
        session.commit()

    r = client.get(_MENU_URL.format(slug="inactive-menu"))
    assert r.status_code == 404


def test_get_menu_3_categories_4_items_unavailable_excluded(
    client: TestClient, menu_restaurant_id: str
) -> None:
    """3 visible categories × 4 items each; 4th item in each cat is unavailable."""
    r = client.get(_MENU_URL.format(slug=_SLUG))
    assert r.status_code == 200
    data = r.json()

    assert len(data) == 3  # only visible categories

    for cat_data in data:
        assert len(cat_data["items"]) == 3  # unavailable 4th item excluded
        for item in cat_data["items"]:
            assert item["is_available"] is True


def test_get_menu_invisible_category_excluded(
    client: TestClient, menu_restaurant_id: str
) -> None:
    r = client.get(_MENU_URL.format(slug=_SLUG))
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert "Hidden" not in names


def test_get_menu_categories_sorted_by_display_order(
    client: TestClient, menu_restaurant_id: str
) -> None:
    r = client.get(_MENU_URL.format(slug=_SLUG))
    assert r.status_code == 200
    orders = [c["display_order"] for c in r.json()]
    assert orders == sorted(orders)
    assert [c["name"] for c in r.json()] == ["Cat A", "Cat B", "Cat C"]


def test_get_menu_items_sorted_by_display_order_within_category(
    client: TestClient, menu_restaurant_id: str
) -> None:
    r = client.get(_MENU_URL.format(slug=_SLUG))
    assert r.status_code == 200
    for cat_data in r.json():
        item_orders = [i["display_order"] for i in cat_data["items"]]
        assert item_orders == sorted(item_orders)


def test_get_menu_category_schema_fields(
    client: TestClient, menu_restaurant_id: str
) -> None:
    r = client.get(_MENU_URL.format(slug=_SLUG))
    assert r.status_code == 200
    cat = r.json()[0]
    assert "id" in cat
    assert "restaurant_id" in cat
    assert "name" in cat
    assert "is_visible" in cat
    assert "display_order" in cat
    assert "items" in cat

    item = cat["items"][0]
    assert "id" in item
    assert "restaurant_id" in item
    assert "category_id" in item
    assert "name" in item
    assert "price_cents" in item
    assert "is_available" in item
    assert "display_order" in item
