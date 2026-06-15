"""Verify Alembic migration: upgrade head creates all 9 tables + 5 indexes,
downgrade base drops them all, and alembic check detects no drift."""
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

_PROJECT_ROOT = Path(__file__).parent.parent

_EXPECTED_TABLES = {
    "restaurants",
    "restaurant_users",
    "diners",
    "categories",
    "menu_items",
    "tables",
    "orders",
    "order_items",
    "order_events",
}

_EXPECTED_INDEXES = {
    "orders": {"ix_orders_restaurant_status_created", "ix_orders_restaurant_updated"},
    "categories": {"ix_categories_restaurant_visible_order"},
    "menu_items": {"ix_menu_items_restaurant_available_cat_order"},
    "order_events": {"ix_order_events_order_created"},
}


def _make_config(db_url: str) -> Config:
    cfg = Config(str(_PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
    return cfg


@pytest.fixture()
def sqlite_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'migration_test.db'}"


def test_upgrade_creates_all_nine_tables(sqlite_url: str) -> None:
    command.upgrade(_make_config(sqlite_url), "head")
    engine = create_engine(sqlite_url)
    try:
        tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        assert tables == _EXPECTED_TABLES
    finally:
        engine.dispose()


def test_upgrade_creates_all_indexes(sqlite_url: str) -> None:
    command.upgrade(_make_config(sqlite_url), "head")
    engine = create_engine(sqlite_url)
    try:
        insp = inspect(engine)
        for table, expected in _EXPECTED_INDEXES.items():
            actual = {idx["name"] for idx in insp.get_indexes(table)}
            assert expected <= actual, (
                f"Table {table!r} missing indexes: {expected - actual}"
            )
    finally:
        engine.dispose()


def test_downgrade_drops_all_tables(sqlite_url: str) -> None:
    cfg = _make_config(sqlite_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    engine = create_engine(sqlite_url)
    try:
        tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        assert tables == set()
    finally:
        engine.dispose()


def test_alembic_check_no_drift(sqlite_url: str) -> None:
    from mesadigital.api.db.models import target_metadata

    cfg = _make_config(sqlite_url)
    command.upgrade(cfg, "head")
    engine = create_engine(sqlite_url)
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            diff = compare_metadata(ctx, target_metadata)
        assert diff == [], f"alembic check detected drift: {diff}"
    finally:
        engine.dispose()
