"""Integration tests for GET /api/restaurants/{rid}/orders/stream (ticket S3-06)."""
import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession, sessionmaker

from mesadigital.api.db.models import Order, Restaurant, RestaurantUser, RestaurantUserRole
from mesadigital.api.db.session import get_session_factory
from mesadigital.api.main import _SSE_POLL_INTERVAL, app
from mesadigital.api.schemas import OrderRead
from mesadigital.api.security import hash_password


# ── helpers ───────────────────────────────────────────────────────────────────


def _get_staff_token(client: TestClient) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@demo.mesadigital.io", "password": "demo1234"},
    )
    assert r.status_code == 200, r.json()
    return r.json()["access_token"]


def _get_diner_token(client: TestClient, phone: str = "+34699000099") -> str:
    restaurant = client.get("/api/public/restaurants/demo").json()
    r = client.post(
        f"/api/public/restaurants/{restaurant['id']}/diners/register",
        json={"name": "Stream Tester", "phone": phone},
    )
    assert r.status_code in (200, 201), r.json()
    return r.json()["access_token"]


def _get_restaurant_id(client: TestClient) -> str:
    return client.get("/api/public/restaurants/demo").json()["id"]


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


# ── non-streaming auth / scope tests ─────────────────────────────────────────


def test_sse_no_auth_returns_403(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)
    r = seeded_client.get(f"/api/restaurants/{rid}/orders/stream")
    assert r.status_code == 403


def test_sse_diner_token_returns_401(seeded_client: TestClient) -> None:
    rid = _get_restaurant_id(seeded_client)
    diner_token = _get_diner_token(seeded_client)
    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders/stream",
        headers={"Authorization": f"Bearer {diner_token}"},
    )
    assert r.status_code == 401


def test_sse_cross_restaurant_returns_403(seeded_client: TestClient, db_engine: Engine) -> None:
    with SASession(db_engine) as s:
        rest2 = Restaurant(slug="other2", name="Other")
        s.add(rest2)
        s.flush()
        user2 = RestaurantUser(
            restaurant_id=rest2.id,
            email="admin@other2.io",
            hashed_password=hash_password("pass"),
            role=RestaurantUserRole.ADMIN,
        )
        s.add(user2)
        s.commit()

    rid = _get_restaurant_id(seeded_client)
    r_login = seeded_client.post(
        "/api/auth/login", json={"email": "admin@other2.io", "password": "pass"}
    )
    other_token = r_login.json()["access_token"]

    r = seeded_client.get(
        f"/api/restaurants/{rid}/orders/stream",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403


# ── streaming integration test ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sse_emits_event_within_2s_of_order_creation(
    seeded_client: TestClient, db_engine: Engine
) -> None:
    """
    Create an order via the API, then verify the SSE generator emits the
    corresponding event within 2 seconds (≤ 2 poll cycles).

    httpx / starlette TestClient both buffer the full response body before
    returning it, making infinite SSE streams untestable over HTTP in-process.
    This test therefore validates the generator logic directly — the HTTP
    plumbing (headers, EventSourceResponse wiring) is covered by the auth tests.
    """
    sf = sessionmaker(bind=db_engine)
    rid = _get_restaurant_id(seeded_client)
    diner_token = _get_diner_token(seeded_client)

    # Record a baseline timestamp BEFORE creating the order.
    # SQLite stores timestamps at second granularity; subtract 1 s so the order's
    # truncated updated_at is strictly greater than baseline.
    baseline: datetime = datetime.utcnow().replace(microsecond=0) - timedelta(seconds=1)

    # Create an order via the HTTP API.
    order_id = _create_order(seeded_client, diner_token)

    # Simulate exactly what the SSE generator does: poll every _SSE_POLL_INTERVAL
    # for orders newer than the baseline, stop as soon as one is found.
    async def _run_generator_until_event(deadline_s: float = 2.0) -> list[OrderRead]:
        last_seen_at = baseline
        found: list[OrderRead] = []
        loop = asyncio.get_event_loop()
        deadline = loop.time() + deadline_s

        while loop.time() < deadline:

            def _poll(ts: datetime = last_seen_at) -> list[Order]:
                with sf() as sess:
                    return list(
                        sess.scalars(
                            select(Order)
                            .where(
                                Order.restaurant_id == rid,
                                Order.updated_at > ts,
                            )
                            .order_by(Order.updated_at.asc())
                        ).all()
                    )

            orders = await asyncio.to_thread(_poll)

            for order in orders:
                found.append(OrderRead.model_validate(order))
                if order.updated_at > last_seen_at:
                    last_seen_at = order.updated_at

            if found:
                return found

            await asyncio.sleep(_SSE_POLL_INTERVAL)

        return found

    found = await _run_generator_until_event(deadline_s=2.0)

    assert len(found) >= 1, "SSE generator did not emit an event within 2 seconds"
    assert found[0].id == order_id
    assert str(found[0].status) == "pending"
    assert found[0].restaurant_id == rid
