
from mesadigital.api.settings import Settings


def test_defaults() -> None:
    s = Settings()
    assert s.ENVIRONMENT == "dev"
    assert s.SENTRY_DSN is None
    assert s.SECRET_KEY == "dev-secret-change-in-prod"
    assert s.DATABASE_URL == "sqlite:///dev.db"


def test_cors_origins_parsed_from_comma_string() -> None:
    s = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:3001")  # type: ignore[call-arg]
    assert s.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:3001"]


def test_cors_origins_trims_whitespace() -> None:
    s = Settings(CORS_ORIGINS=" http://a.com , http://b.com ")  # type: ignore[call-arg]
    assert s.CORS_ORIGINS == ["http://a.com", "http://b.com"]


def test_cors_origins_list_passthrough() -> None:
    s = Settings(CORS_ORIGINS=["http://a.com"])  # type: ignore[call-arg]
    assert s.CORS_ORIGINS == ["http://a.com"]


def test_sentry_dsn_optional() -> None:
    s = Settings(SENTRY_DSN="https://key@sentry.io/1")  # type: ignore[call-arg]
    assert s.SENTRY_DSN == "https://key@sentry.io/1"
