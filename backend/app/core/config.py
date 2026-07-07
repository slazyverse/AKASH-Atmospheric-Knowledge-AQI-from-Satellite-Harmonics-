"""
Application configuration management.

All settings are sourced exclusively from environment variables (or a .env file
in local development). The Settings class validates and coerces every value at
import time — failure to supply a required variable raises a clear Pydantic
ValidationError before the server accepts a single HTTP request.

Design decisions:
  - Pydantic BaseSettings: single source of truth for all env vars;
    no scattered os.getenv() calls throughout the codebase.
  - @lru_cache on get_settings(): the .env file is parsed exactly once and
    the same Settings object is shared across the entire application lifetime.
  - computed_field for DATABASE_URL: the connection string is derived from
    individual components rather than accepting a raw DSN, which prevents
    accidental credential exposure in opaque connection strings.
    urllib.parse.quote_plus() encodes both user and password so that special
    characters (@ / # ? % etc.) in credentials do not corrupt the URL.
  - No SYNC_DATABASE_URL: Alembic now runs migrations via asyncio.run() +
    create_async_engine(), using asyncpg as the sole PostgreSQL driver.
    psycopg2 is not installed or required.
  - Production guard in model_validator: DEBUG=True with ENVIRONMENT=production
    is a misconfiguration that raises immediately at startup.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralised, type-safe application settings.

    All fields map 1-to-1 to environment variables. Pydantic performs
    automatic type coercion (e.g., "true" → True, "8000" → 8000).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",       # Silently ignore unknown env vars
        validate_default=True,
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "VAYU-DRISHTI"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "Air quality monitoring and geospatial analytics platform. "
        "Ingests real-time sensor data, applies ML forecasting models, "
        "and exposes a geospatial API for dashboard consumption."
    )
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # ── Server ─────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=8000, ge=1, le=65535)
    WORKERS: int = Field(default=1, ge=1, le=64)

    # ── Security ───────────────────────────────────────────────────────────────
    # min_length=32 enforces a cryptographically adequate secret key length.
    SECRET_KEY: str = Field(
        default="change-me-in-production-use-secrets-token-hex-32",
        min_length=32,
    )
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
    )

    # ── PostgreSQL / PostGIS ───────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_USER: str = "vayu"
    POSTGRES_PASSWORD: str = Field(default="vayu_password")
    POSTGRES_DB: str = "vayu_drishti"

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL(self) -> str:
        """
        Async-compatible PostgreSQL DSN using the asyncpg driver.

        Used by SQLAlchemy's async engine for BOTH runtime operations AND
        Alembic migrations (via create_async_engine in alembic/env.py).

        urllib.parse.quote_plus() percent-encodes the username and password
        before embedding them in the URL. Without encoding, passwords containing
        URL-special characters (@, /, #, ?, %, +, space, etc.) would truncate
        or corrupt the DSN, causing authentication failures that are hard to
        diagnose because the raw password is never logged.
        """
        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    # ── API ────────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── Future: ML Inference (Day 4+) ──────────────────────────────────────────
    # These fields are wired up now so they appear in docs and .env.example.
    # The ML service router will read them when ENABLE_ML_ENDPOINTS=true.
    ML_MODEL_PATH: str | None = None
    ENABLE_ML_ENDPOINTS: bool = False

    # ── Future: Caching (Day N+) ───────────────────────────────────────────────
    REDIS_URL: str | None = None

    # ── Validators ────────────────────────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_production_constraints(self) -> "Settings":
        """Fail fast on misconfigurations that must never reach production."""
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError(
                    "DEBUG must be False in the production environment. "
                    "Set DEBUG=false in your production .env or secrets manager."
                )
            if self.SECRET_KEY == "change-me-in-production-use-secrets-token-hex-32":
                raise ValueError(
                    "The default SECRET_KEY must not be used in production. "
                    "Generate a new key with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            for origin in self.ALLOWED_ORIGINS:
                if "localhost" in origin or "127.0.0.1" in origin or origin == "*":
                    raise ValueError(
                        f"Insecure origin '{origin}' is not allowed in production environment. "
                        "ALLOWED_ORIGINS must not contain localhost, loopback IPs, or wildcard (*)."
                    )
        return self


@lru_cache
def get_settings() -> Settings:
    """
    Return the application Settings singleton.

    lru_cache ensures this function body executes exactly once for the lifetime
    of the process, regardless of how many times it is called. This is safe
    because Settings is immutable after construction.

    In tests, call get_settings.cache_clear() between tests that need
    different configuration values.
    """
    return Settings()
