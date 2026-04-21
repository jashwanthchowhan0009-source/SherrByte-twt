"""Application configuration.

Loads and validates environment variables. Import `settings` anywhere in the app
and trust that values exist and are of the right type. If a required variable is
missing or malformed, the process crashes at startup — by design.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_env: Literal["dev", "staging", "prod"] = "dev"
    app_name: str = "sherrbyte-api"
    app_version: str = "0.1.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    host: str = "0.0.0.0"
    port: int = 8000

    cors_origins: list[str] = Field(default_factory=list)

    # ---- Database ----
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 5
    database_echo: bool = False

    # ---- Sentry ----
    sentry_dsn: str = ""

    # ---- JWT (Phase B) ----
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7

    # ---- Redis (Phase C) ----
    redis_url: str = ""

    # ---- AI (Phase D) ----
    gemini_api_key: str = ""
    gemini_api_key_2: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""

    # ---- Services ----
    openweather_api_key: str = ""
    resend_api_key: str = ""
    resend_from_email: str = "noreply@sherrbyte.com"
    onesignal_app_id: str = ""
    onesignal_rest_key: str = ""

    # ---- Observability ----
    posthog_api_key: str = ""
    posthog_host: str = "https://eu.posthog.com"
    axiom_token: str = ""
    axiom_dataset: str = "sherrbyte-prod"

    # ---- Validators ----
    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("database_url")
    @classmethod
    def check_async_driver(cls, v: str) -> str:
        if v.startswith("postgres://"):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql+asyncpg://', "
                "not 'postgres://'. Edit your .env."
            )
        if "postgresql" in v and "+asyncpg" not in v:
            raise ValueError(
                "DATABASE_URL must use the asyncpg driver: "
                "'postgresql+asyncpg://...'"
            )
        return v

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"

    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Call this at module top-level or via Depends()."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
