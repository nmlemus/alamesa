from unittest.mock import patch

import pytest

from mesadigital.api.main import create_app
from mesadigital.api.settings import Settings


def test_factory_raises_runtime_error_postgresql_with_dev_secret() -> None:
    cfg = Settings(  # type: ignore[call-arg]
        DATABASE_URL="postgresql+psycopg2://user:pass@localhost/db",
        SECRET_KEY="dev-secret-change-in-prod",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(cfg)


def test_factory_ok_postgresql_with_real_secret() -> None:
    cfg = Settings(  # type: ignore[call-arg]
        DATABASE_URL="postgresql+psycopg2://user:pass@localhost/db",
        SECRET_KEY="super-real-prod-secret-123",
    )
    application = create_app(cfg)
    assert application is not None


def test_factory_raises_value_error_wildcard_cors_in_prod() -> None:
    cfg = Settings(CORS_ORIGINS="*", ENVIRONMENT="prod")  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="Wildcard"):
        create_app(cfg)


def test_factory_ok_wildcard_cors_in_dev() -> None:
    cfg = Settings(CORS_ORIGINS="*", ENVIRONMENT="dev")  # type: ignore[call-arg]
    application = create_app(cfg)
    assert application is not None


def test_factory_healthz_route_registered() -> None:
    cfg = Settings()
    application = create_app(cfg)
    # Robusto entre versiones de Starlette/FastAPI: el schema OpenAPI lista
    # las rutas registradas (application.routes trae wrappers internos sin .path).
    paths = application.openapi().get("paths", {})
    assert "/api/healthz" in paths


def test_factory_api_prefix_on_all_api_routes() -> None:
    _FRAMEWORK_PATHS = {"/health", "/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}
    cfg = Settings()
    application = create_app(cfg)
    api_paths = [
        route.path  # type: ignore[attr-defined]
        for route in application.routes
        if hasattr(route, "path") and route.path not in _FRAMEWORK_PATHS  # type: ignore[attr-defined]
    ]
    for path in api_paths:
        assert path.startswith("/api"), f"Route {path!r} lacks /api prefix"


def test_sentry_not_initialized_without_dsn() -> None:
    cfg = Settings(SENTRY_DSN=None)  # type: ignore[call-arg]
    with patch("mesadigital.api.main.sentry_sdk") as mock_sentry:
        create_app(cfg)
    mock_sentry.init.assert_not_called()


def test_sentry_initialized_with_dsn() -> None:
    cfg = Settings(SENTRY_DSN="https://key@sentry.io/1")  # type: ignore[call-arg]
    with patch("mesadigital.api.main.sentry_sdk") as mock_sentry:
        create_app(cfg)
    mock_sentry.init.assert_called_once_with(
        dsn="https://key@sentry.io/1",
        environment="dev",
    )
