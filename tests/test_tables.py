"""Integration tests for Table CRUD and slug immutability (ticket S4-03)."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import Restaurant, RestaurantTable, RestaurantUser
from mesadigital.api.security import create_token, hash_password
from shared.contracts import RestaurantUserRole


# ── helpers ───────────────────────────────────────────────────────────────────


def _get_admin_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.mesadigital.io", "password": "demo1234"},
    )
    assert r.status_code == 200, r.json()
    return r.json()["access_token"]


def _get_restaurant_id(client: TestClient) -> str:
    return client.get("/api/public/restaurants/demo").json()["id"]


def _setup_other_restaurant(db_engine: Engine) -> tuple[str, str]:
    """Creates a second restaurant + admin user. Returns (restaurant_id, admin_token)."""
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
        rid = rest2.id
        uid = user2.id

    token = create_token(
        {"sub": uid, "restaurant_id": rid, "role": "admin", "type": "staff"},
        __import__("datetime").timedelta(days=1),
    )
    return rid, token


# ── GET /api/restaurants/{rid}/tables ─────────────────────────────────────────


def test_list_tables_admin_returns_200(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 3  # seed creates 3 tables
    for t in data:
        assert "id" in t
        assert "number" in t
        assert "label" in t
        assert "is_active" in t
        assert "qr_url" in t
        assert t["is_active"] is True


def test_list_tables_ordered_by_number(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    numbers = [t["number"] for t in r.json()]
    assert numbers == sorted(numbers)


def test_list_tables_no_auth_returns_403(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(f"/api/restaurants/{rid}/tables")

    assert r.status_code == 403


def test_list_tables_wrong_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid2, _ = _setup_other_restaurant(db_engine)
    token = _get_admin_token(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid2}/tables",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 403


def test_list_tables_staff_role_returns_403(seeded_client: TestClient, db_engine: Engine) -> None:
    rid = _get_restaurant_id(seeded_client)
    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        staff_user = RestaurantUser(
            restaurant_id=rid,
            email="staff@demo.mesadigital.io",
            hashed_password=hash_password("demo1234"),
            role=RestaurantUserRole.STAFF,
        )
        s.add(staff_user)
        s.commit()
        staff_token = create_token(
            {"sub": staff_user.id, "restaurant_id": rid, "role": "staff", "type": "staff"},
            __import__("datetime").timedelta(days=1),
        )

    r = seeded_client.get(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert r.status_code == 403


# ── POST /api/restaurants/{rid}/tables ────────────────────────────────────────


def test_create_table_returns_201(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 99, "label": "VIP"},
    )

    assert r.status_code == 201
    data = r.json()
    assert data["number"] == 99
    assert data["label"] == "VIP"
    assert data["is_active"] is True
    assert data["restaurant_id"] == rid
    assert "qr_url" in data
    assert "id" in data


def test_create_table_without_label(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 50},
    )

    assert r.status_code == 201
    assert r.json()["label"] is None


def test_create_table_duplicate_number_returns_409(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    # Table 1 already created by seed
    r = seeded_client.post(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 1},
    )

    assert r.status_code == 409


def test_create_table_wrong_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid2, _ = _setup_other_restaurant(db_engine)
    token = _get_admin_token(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid2}/tables",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 1},
    )

    assert r.status_code == 403


def test_create_table_no_auth_returns_403(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/tables",
        json={"number": 99},
    )

    assert r.status_code == 403


def test_create_table_sets_first_qr_generated_at(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)

    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        assert restaurant.first_qr_generated_at is None

    token = _get_admin_token(seeded_client)
    r = seeded_client.post(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 99},
    )
    assert r.status_code == 201

    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        assert restaurant.first_qr_generated_at is not None


def test_create_table_second_creation_does_not_reset_first_qr_generated_at(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)
    token = _get_admin_token(seeded_client)

    seeded_client.post(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 88},
    )
    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        first_ts = restaurant.first_qr_generated_at

    seeded_client.post(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 89},
    )
    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        assert restaurant.first_qr_generated_at == first_ts


# ── PATCH /api/tables/{id} ────────────────────────────────────────────────────


def _get_first_table_id(client: TestClient, token: str, rid: str) -> str:
    tables_r = client.get(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tables_r.status_code == 200
    return tables_r.json()[0]["id"]


def test_patch_table_updates_label(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    table_id = _get_first_table_id(seeded_client, token, rid)

    r = seeded_client.patch(
        f"/api/tables/{table_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "Terraza"},
    )

    assert r.status_code == 200
    assert r.json()["label"] == "Terraza"
    assert r.json()["id"] == table_id


def test_patch_table_deactivates_table(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    table_id = _get_first_table_id(seeded_client, token, rid)

    r = seeded_client.patch(
        f"/api/tables/{table_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_patch_table_ignores_number_field(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    tables_r = seeded_client.get(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
    )
    first_table = tables_r.json()[0]
    original_number = first_table["number"]
    table_id = first_table["id"]

    r = seeded_client.patch(
        f"/api/tables/{table_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 9999, "label": "Modificada"},
    )

    assert r.status_code == 200
    assert r.json()["number"] == original_number
    assert r.json()["label"] == "Modificada"


def test_patch_table_not_found_returns_404(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)

    r = seeded_client.patch(
        "/api/tables/doesnotexist00000000000000000000",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "X"},
    )

    assert r.status_code == 404


def test_patch_table_wrong_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid2, other_token = _setup_other_restaurant(db_engine)
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    table_id = _get_first_table_id(seeded_client, token, rid)

    r = seeded_client.patch(
        f"/api/tables/{table_id}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"label": "Hack"},
    )

    assert r.status_code == 403


def test_patch_table_no_auth_returns_403(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    table_id = _get_first_table_id(seeded_client, token, rid)

    r = seeded_client.patch(f"/api/tables/{table_id}", json={"label": "X"})

    assert r.status_code == 403


# ── PATCH /api/restaurants/{rid} ──────────────────────────────────────────────


def test_patch_restaurant_updates_name(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.patch(
        f"/api/restaurants/{rid}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Nuevo Nombre"},
    )

    assert r.status_code == 200
    assert r.json()["name"] == "Nuevo Nombre"
    assert r.json()["id"] == rid


def test_patch_restaurant_updates_slug_when_qr_not_generated(
    seeded_client: TestClient,
) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.patch(
        f"/api/restaurants/{rid}",
        headers={"Authorization": f"Bearer {token}"},
        json={"slug": "nuevo-slug"},
    )

    assert r.status_code == 200
    assert r.json()["slug"] == "nuevo-slug"


def test_patch_restaurant_blocks_slug_when_qr_generated(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)

    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        restaurant.first_qr_generated_at = datetime.now(timezone.utc)
        s.commit()

    token = _get_admin_token(seeded_client)
    r = seeded_client.patch(
        f"/api/restaurants/{rid}",
        headers={"Authorization": f"Bearer {token}"},
        json={"slug": "new-slug"},
    )

    assert r.status_code == 409
    assert r.json()["detail"] == "Slug is immutable after first QR generation."


def test_patch_restaurant_allows_name_change_even_after_qr_generated(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)

    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        restaurant.first_qr_generated_at = datetime.now(timezone.utc)
        s.commit()

    token = _get_admin_token(seeded_client)
    r = seeded_client.patch(
        f"/api/restaurants/{rid}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Nuevo Nombre"},
    )

    assert r.status_code == 200
    assert r.json()["name"] == "Nuevo Nombre"


def test_patch_restaurant_wrong_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)
    _, other_token = _setup_other_restaurant(db_engine)

    r = seeded_client.patch(
        f"/api/restaurants/{rid}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"name": "Hack"},
    )

    assert r.status_code == 403


def test_patch_restaurant_no_auth_returns_403(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.patch(f"/api/restaurants/{rid}", json={"name": "X"})

    assert r.status_code == 403


# ── GET /api/tables/{id}/qr ───────────────────────────────────────────────────


def test_get_table_qr_returns_200(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    table_id = _get_first_table_id(seeded_client, token, rid)

    r = seeded_client.get(
        f"/api/tables/{table_id}/qr",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["table_id"] == table_id
    assert "qr_url" in data
    assert "/qr/" in data["qr_url"]


def test_get_table_qr_url_contains_slug_and_number(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    tables_r = seeded_client.get(
        f"/api/restaurants/{rid}/tables",
        headers={"Authorization": f"Bearer {token}"},
    )
    first_table = tables_r.json()[0]
    table_id = first_table["id"]
    table_number = first_table["number"]

    r = seeded_client.get(
        f"/api/tables/{table_id}/qr",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    assert f"demo/{table_number}" in r.json()["qr_url"]


def test_get_table_qr_sets_first_qr_generated_at(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)

    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        assert restaurant.first_qr_generated_at is None

    token = _get_admin_token(seeded_client)
    table_id = _get_first_table_id(seeded_client, token, rid)
    seeded_client.get(
        f"/api/tables/{table_id}/qr",
        headers={"Authorization": f"Bearer {token}"},
    )

    with SASession(db_engine) as s:
        restaurant = s.scalar(select(Restaurant).where(Restaurant.id == rid))
        assert restaurant is not None
        assert restaurant.first_qr_generated_at is not None


def test_get_table_qr_not_found_returns_404(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)

    r = seeded_client.get(
        "/api/tables/doesnotexist00000000000000000000/qr",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 404


def test_get_table_qr_wrong_restaurant_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    table_id = _get_first_table_id(seeded_client, token, rid)
    _, other_token = _setup_other_restaurant(db_engine)

    r = seeded_client.get(
        f"/api/tables/{table_id}/qr",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert r.status_code == 403


def test_get_table_qr_no_auth_returns_403(seeded_client: TestClient) -> None:
    token = _get_admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)
    table_id = _get_first_table_id(seeded_client, token, rid)

    r = seeded_client.get(f"/api/tables/{table_id}/qr")

    assert r.status_code == 403
