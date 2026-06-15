import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from mesadigital.api.db.models import (
    Base,
    Diner,
    Order,
    OrderEvent,
    Restaurant,
    RestaurantTable,
    RestaurantUser,
)
from shared.contracts import OrderEventActorType, OrderStatus, RestaurantUserRole


@pytest.fixture()
def engine() -> Engine:
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def _restaurant(session: Session, slug: str = "r1") -> Restaurant:
    r = Restaurant(slug=slug, name="Test Restaurant")
    session.add(r)
    session.flush()
    return r


def test_all_nine_tables_exist(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    assert tables == {
        "restaurants",
        "restaurant_users",
        "categories",
        "menu_items",
        "tables",
        "diners",
        "orders",
        "order_items",
        "order_events",
    }


def test_ids_are_uuid_hex_strings(engine: Engine) -> None:
    with Session(engine) as s:
        r = _restaurant(s)
        s.commit()
        assert isinstance(r.id, str)
        assert len(r.id) == 32


def test_restaurant_user_unique_email_per_restaurant(engine: Engine) -> None:
    with Session(engine) as s:
        r = _restaurant(s)
        s.add(RestaurantUser(
            restaurant_id=r.id, email="staff@x.com",
            hashed_password="h", role=RestaurantUserRole.STAFF,
        ))
        s.flush()
        s.add(RestaurantUser(
            restaurant_id=r.id, email="staff@x.com",
            hashed_password="h", role=RestaurantUserRole.STAFF,
        ))
        with pytest.raises(IntegrityError):
            s.flush()


def test_restaurant_user_same_email_different_restaurant(engine: Engine) -> None:
    with Session(engine) as s:
        r1 = _restaurant(s, slug="r1")
        r2 = _restaurant(s, slug="r2")
        s.add(RestaurantUser(
            restaurant_id=r1.id, email="staff@x.com",
            hashed_password="h", role=RestaurantUserRole.STAFF,
        ))
        s.add(RestaurantUser(
            restaurant_id=r2.id, email="staff@x.com",
            hashed_password="h", role=RestaurantUserRole.STAFF,
        ))
        s.commit()  # no error — same email in different restaurants is OK


def test_diner_unique_phone_per_restaurant(engine: Engine) -> None:
    with Session(engine) as s:
        r = _restaurant(s)
        s.add(Diner(restaurant_id=r.id, phone="+1", name="A", hashed_password="h"))
        s.flush()
        s.add(Diner(restaurant_id=r.id, phone="+1", name="B", hashed_password="h"))
        with pytest.raises(IntegrityError):
            s.flush()


def test_diner_same_phone_different_restaurant(engine: Engine) -> None:
    with Session(engine) as s:
        r1 = _restaurant(s, slug="r1")
        r2 = _restaurant(s, slug="r2")
        s.add(Diner(restaurant_id=r1.id, phone="+1", name="A", hashed_password="h"))
        s.add(Diner(restaurant_id=r2.id, phone="+1", name="B", hashed_password="h"))
        s.commit()  # no error — same phone in different restaurants is OK


def test_table_unique_number_per_restaurant(engine: Engine) -> None:
    with Session(engine) as s:
        r = _restaurant(s)
        s.add(RestaurantTable(restaurant_id=r.id, number=1, label="T1"))
        s.flush()
        s.add(RestaurantTable(restaurant_id=r.id, number=1, label="T2"))
        with pytest.raises(IntegrityError):
            s.flush()


def test_table_same_number_different_restaurant(engine: Engine) -> None:
    with Session(engine) as s:
        r1 = _restaurant(s, slug="r1")
        r2 = _restaurant(s, slug="r2")
        s.add(RestaurantTable(restaurant_id=r1.id, number=1))
        s.add(RestaurantTable(restaurant_id=r2.id, number=1))
        s.commit()  # no error


def test_order_default_status_is_pending(engine: Engine) -> None:
    with Session(engine) as s:
        r = _restaurant(s)
        t = RestaurantTable(restaurant_id=r.id, number=1)
        s.add(t)
        s.flush()
        order = Order(restaurant_id=r.id, table_id=t.id)
        s.add(order)
        s.commit()
        s.refresh(order)
        assert order.status == OrderStatus.PENDING


def test_restaurant_user_has_hashed_password_column() -> None:
    cols = {c.key for c in RestaurantUser.__table__.columns}
    assert "hashed_password" in cols
    assert "password_hash" not in cols


def test_order_event_has_no_updated_at_column() -> None:
    cols = {c.key for c in OrderEvent.__table__.columns}
    assert "created_at" in cols
    assert "updated_at" not in cols


def test_order_events_are_insertable(engine: Engine) -> None:
    with Session(engine) as s:
        r = _restaurant(s)
        t = RestaurantTable(restaurant_id=r.id, number=1)
        s.add(t)
        s.flush()
        order = Order(restaurant_id=r.id, table_id=t.id)
        s.add(order)
        s.flush()
        event = OrderEvent(
            order_id=order.id,
            actor_type=OrderEventActorType.STAFF,
            from_status=OrderStatus.PENDING,
            to_status=OrderStatus.CONFIRMED,
        )
        s.add(event)
        s.commit()
        s.refresh(event)
        assert isinstance(event.id, str) and len(event.id) == 32
        assert event.created_at is not None
