import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mesadigital.api.middleware import RequestLoggingMiddleware


@pytest.fixture()
def mini_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"pong": "true"}

    @app.get("/restaurants/{rid}/orders")
    def orders(rid: str) -> dict[str, str]:
        return {"rid": rid}

    @app.get("/public/restaurants/{restaurant_id}/diners/register")
    def register(restaurant_id: str) -> dict[str, str]:
        return {"restaurant_id": restaurant_id}

    return app


def test_x_request_id_present(mini_app: FastAPI) -> None:
    with TestClient(mini_app) as c:
        r = c.get("/ping")
    assert "X-Request-ID" in r.headers


def test_x_request_id_is_uuid4(mini_app: FastAPI) -> None:
    with TestClient(mini_app) as c:
        r = c.get("/ping")
    raw = r.headers["X-Request-ID"]
    parsed = uuid.UUID(raw, version=4)
    assert str(parsed) == raw


def test_each_request_unique_id(mini_app: FastAPI) -> None:
    with TestClient(mini_app) as c:
        ids = {c.get("/ping").headers["X-Request-ID"] for _ in range(5)}
    assert len(ids) == 5


def test_log_is_valid_json(
    mini_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO", logger="mesadigital.api.access"):
        with TestClient(mini_app) as c:
            c.get("/ping")
    assert len(caplog.records) == 1
    record = json.loads(caplog.records[0].message)
    assert isinstance(record, dict)


def test_log_contains_required_fields(
    mini_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    required = {"request_id", "method", "path", "status_code", "duration_ms", "restaurant_id"}
    with caplog.at_level("INFO", logger="mesadigital.api.access"):
        with TestClient(mini_app) as c:
            r = c.get("/ping")
    record = json.loads(caplog.records[0].message)
    assert required <= record.keys()
    assert record["method"] == "GET"
    assert record["path"] == "/ping"
    assert record["status_code"] == 200
    assert record["duration_ms"] >= 0
    assert record["restaurant_id"] is None
    assert record["request_id"] == r.headers["X-Request-ID"]


def test_log_no_pii_fields(
    mini_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO", logger="mesadigital.api.access"):
        with TestClient(mini_app) as c:
            c.get("/ping")
    record = json.loads(caplog.records[0].message)
    assert not {"name", "phone", "email", "password"} & record.keys()


def test_restaurant_id_from_rid_param(
    mini_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO", logger="mesadigital.api.access"):
        with TestClient(mini_app) as c:
            c.get("/restaurants/abc123/orders")
    record = json.loads(caplog.records[0].message)
    assert record["restaurant_id"] == "abc123"


def test_restaurant_id_from_restaurant_id_param(
    mini_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO", logger="mesadigital.api.access"):
        with TestClient(mini_app) as c:
            c.get("/public/restaurants/xyz789/diners/register")
    record = json.loads(caplog.records[0].message)
    assert record["restaurant_id"] == "xyz789"
