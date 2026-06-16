from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///dev.db"
    SECRET_KEY: str = "dev-secret-change-in-prod"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    SENTRY_DSN: str | None = None
    ENVIRONMENT: str = "dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(o) for o in v]
        return []


settings = Settings()
