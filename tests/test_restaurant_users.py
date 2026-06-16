"""Integration tests for restaurant user management (ticket S4-04)."""
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

from mesadigital.api.db.models import Restaurant, RestaurantUser, RestaurantUserRole
from mesadigital.api.security import hash_password


def _admin_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.mesadigital.io", "password": "demo1234"},
    )
    assert r.status_code == 200, r.json()
    return r.json()["access_token"]


def _get_restaurant_id(client: TestClient) -> str:
    return client.get("/api/public/restaurants/demo").json()["id"]


def _create_staff(db_engine: Engine, restaurant_id: str, email: str) -> str:
    with SASession(db_engine) as s:
        user = RestaurantUser(
            restaurant_id=restaurant_id,
            email=email,
            hashed_password=hash_password("temp1234"),
            role=RestaurantUserRole.STAFF,
        )
        s.add(user)
        s.commit()
        return user.id


# ── GET /api/restaurants/{rid}/users ─────────────────────────────────────────


def test_list_users_admin_sees_all_users_without_hashed_password(seeded_client: TestClient) -> None:
    token = _admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.get(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for user in data:
        assert "hashed_password" not in user
        assert "id" in user
        assert "email" in user
        assert "role" in user
        assert "is_active" in user


def test_list_users_staff_role_returns_403(seeded_client: TestClient, db_engine: Engine) -> None:
    rid = _get_restaurant_id(seeded_client)
    _create_staff(db_engine, rid, "staff_lister@demo.io")

    r = seeded_client.post(
        "/api/auth/login",
        json={"email": "staff_lister@demo.io", "password": "temp1234"},
    )
    staff_token = r.json()["access_token"]

    r = seeded_client.get(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 403


def test_list_users_no_auth_returns_401(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)
    r = seeded_client.get(f"/api/restaurants/{rid}/users")
    assert r.status_code == 401


def test_list_users_cross_restaurant_admin_returns_403(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    rid = _get_restaurant_id(seeded_client)
    with SASession(db_engine) as s:
        rest2 = Restaurant(slug="other", name="Other")
        s.add(rest2)
        s.flush()
        admin2 = RestaurantUser(
            restaurant_id=rest2.id,
            email="admin@other.io",
            hashed_password=hash_password("other1234"),
            role=RestaurantUserRole.ADMIN,
        )
        s.add(admin2)
        s.commit()

    r = seeded_client.post("/api/auth/login", json={"email": "admin@other.io", "password": "other1234"})
    other_token = r.json()["access_token"]

    r = seeded_client.get(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403


# ── POST /api/restaurants/{rid}/users ────────────────────────────────────────


def test_create_user_returns_201_without_hashed_password(seeded_client: TestClient) -> None:
    token = _admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "new_staff@demo.io", "password": "temp1234", "role": "staff"},
    )

    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new_staff@demo.io"
    assert data["role"] == "staff"
    assert data["restaurant_id"] == rid
    assert "hashed_password" not in data


def test_create_user_duplicate_email_returns_409(seeded_client: TestClient) -> None:
    token = _admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    payload = {"email": "dup@demo.io", "password": "temp1234", "role": "staff"}
    r1 = seeded_client.post(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r1.status_code == 201

    r2 = seeded_client.post(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r2.status_code == 409


def test_create_user_invalid_role_returns_422(seeded_client: TestClient) -> None:
    token = _admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    r = seeded_client.post(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "bad_role@demo.io", "password": "temp1234", "role": "superadmin"},
    )
    assert r.status_code == 422


def test_create_user_non_admin_returns_403(seeded_client: TestClient, db_engine: Engine) -> None:
    rid = _get_restaurant_id(seeded_client)
    _create_staff(db_engine, rid, "staff_creator@demo.io")

    r = seeded_client.post(
        "/api/auth/login",
        json={"email": "staff_creator@demo.io", "password": "temp1234"},
    )
    staff_token = r.json()["access_token"]

    r = seeded_client.post(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"email": "another@demo.io", "password": "temp1234", "role": "staff"},
    )
    assert r.status_code == 403


# ── PATCH /api/users/{id} ────────────────────────────────────────────────────


def test_patch_user_admin_can_change_role(seeded_client: TestClient, db_engine: Engine) -> None:
    rid = _get_restaurant_id(seeded_client)
    token = _admin_token(seeded_client)
    user_id = _create_staff(db_engine, rid, "patch_role@demo.io")

    r = seeded_client.patch(
        f"/api/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "admin"},
    )

    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_patch_user_admin_can_deactivate_other_user(seeded_client: TestClient, db_engine: Engine) -> None:
    rid = _get_restaurant_id(seeded_client)
    token = _admin_token(seeded_client)
    user_id = _create_staff(db_engine, rid, "deactivate_staff@demo.io")

    r = seeded_client.patch(
        f"/api/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_patch_user_admin_cannot_deactivate_own_account(seeded_client: TestClient) -> None:
    token = _admin_token(seeded_client)
    rid = _get_restaurant_id(seeded_client)

    users_r = seeded_client.get(
        f"/api/restaurants/{rid}/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    admin_user = next(u for u in users_r.json() if u["role"] == "admin")

    r = seeded_client.patch(
        f"/api/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert r.status_code == 403


def test_patch_user_invalid_role_returns_422(seeded_client: TestClient, db_engine: Engine) -> None:
    rid = _get_restaurant_id(seeded_client)
    token = _admin_token(seeded_client)
    user_id = _create_staff(db_engine, rid, "inv_role@demo.io")

    r = seeded_client.patch(
        f"/api/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "superadmin"},
    )
    assert r.status_code == 422


def test_patch_user_not_found_returns_404(seeded_client: TestClient) -> None:
    token = _admin_token(seeded_client)

    r = seeded_client.patch(
        "/api/users/nonexistentid00000000000000000",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "staff"},
    )
    assert r.status_code == 404


def test_patch_user_cross_restaurant_returns_403(seeded_client: TestClient, db_engine: Engine) -> None:
    rid = _get_restaurant_id(seeded_client)
    target_user_id = _create_staff(db_engine, rid, "cross_target@demo.io")

    with SASession(db_engine) as s:
        rest2 = Restaurant(slug="crossother", name="CrossOther")
        s.add(rest2)
        s.flush()
        admin2 = RestaurantUser(
            restaurant_id=rest2.id,
            email="admin@crossother.io",
            hashed_password=hash_password("other1234"),
            role=RestaurantUserRole.ADMIN,
        )
        s.add(admin2)
        s.commit()

    r = seeded_client.post(
        "/api/auth/login", json={"email": "admin@crossother.io", "password": "other1234"}
    )
    other_token = r.json()["access_token"]

    r = seeded_client.patch(
        f"/api/users/{target_user_id}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"role": "admin"},
    )
    assert r.status_code == 403
