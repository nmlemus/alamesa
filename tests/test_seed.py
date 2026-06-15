import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from mesadigital.api.db.models import (
    Base,
    Category,
    MenuItem,
    Restaurant,
    RestaurantTable,
    RestaurantUser,
    RestaurantUserRole,
)

ROOT = Path(__file__).parent.parent


def _load_seed() -> object:
    spec = importlib.util.spec_from_file_location(
        "seed", ROOT / "scripts" / "seed.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture()
def engine() -> Engine:
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def test_seed_creates_restaurant(engine: Engine) -> None:
    seed_mod = _load_seed()
    with Session(engine) as session:
        seed_mod.seed(session)  # type: ignore[attr-defined]

    with Session(engine) as session:
        restaurants = session.scalars(select(Restaurant)).all()
        assert len(restaurants) == 1
        assert restaurants[0].slug == "demo"
        assert restaurants[0].name == "Restaurante Demo"


def test_seed_creates_admin_user(engine: Engine) -> None:
    seed_mod = _load_seed()
    with Session(engine) as session:
        seed_mod.seed(session)  # type: ignore[attr-defined]

    with Session(engine) as session:
        users = session.scalars(select(RestaurantUser)).all()
        assert len(users) == 1
        assert users[0].role == RestaurantUserRole.ADMIN
        assert users[0].email == "admin@demo.mesadigital.io"


def test_seed_creates_categories_and_items(engine: Engine) -> None:
    seed_mod = _load_seed()
    with Session(engine) as session:
        seed_mod.seed(session)  # type: ignore[attr-defined]

    with Session(engine) as session:
        categories = session.scalars(select(Category)).all()
        assert len(categories) == 2

        items = session.scalars(select(MenuItem)).all()
        assert len(items) == 5
        assert all(item.price_cents > 0 for item in items)


def test_seed_creates_tables(engine: Engine) -> None:
    seed_mod = _load_seed()
    with Session(engine) as session:
        seed_mod.seed(session)  # type: ignore[attr-defined]

    with Session(engine) as session:
        tables = session.scalars(select(RestaurantTable)).all()
        assert len(tables) == 3
        numbers = sorted(t.number for t in tables)
        assert numbers == [1, 2, 3]


def test_seed_is_idempotent(engine: Engine) -> None:
    seed_mod = _load_seed()

    with Session(engine) as session:
        seed_mod.seed(session)  # type: ignore[attr-defined]

    with Session(engine) as session:
        seed_mod.seed(session)  # type: ignore[attr-defined]

    with Session(engine) as session:
        assert len(session.scalars(select(Restaurant)).all()) == 1
        assert len(session.scalars(select(RestaurantUser)).all()) == 1
        assert len(session.scalars(select(Category)).all()) == 2
        assert len(session.scalars(select(MenuItem)).all()) == 5
        assert len(session.scalars(select(RestaurantTable)).all()) == 3
