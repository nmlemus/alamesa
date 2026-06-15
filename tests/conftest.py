import importlib.util
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from mesadigital.api.db.models import Base
from mesadigital.api.main import app, get_db

ROOT = Path(__file__).parent.parent


def load_seed_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "seed", ROOT / "scripts" / "seed.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture()
def db_engine() -> Generator[Engine, None, None]:
    # StaticPool shares the same in-memory SQLite connection across all
    # sessions, so tables created by create_all remain visible to the app.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_engine: Engine) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_client(client: TestClient, db_engine: Engine) -> TestClient:
    seed_mod = load_seed_module()
    with Session(db_engine) as session:
        seed_mod.seed(session)  # type: ignore[attr-defined]
    return client
