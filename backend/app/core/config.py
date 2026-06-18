"""Application configuration.

Settings are loaded from environment variables (and an optional ``.env`` file)
using ``pydantic-settings``. Centralising configuration here keeps the rest of
the codebase free of ``os.environ`` lookups and makes the app trivially
configurable across environments (dev / staging / prod).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application -----------------------------------------------------
    PROJECT_NAME: str = "Forense"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # --- Database --------------------------------------------------------
    # Defaults to a local async SQLite file so the project runs with zero
    # infrastructure. Point at Postgres in production, e.g.:
    #   postgresql+asyncpg://user:pass@host:5432/forense
    DATABASE_URL: str = "sqlite+aiosqlite:///./forense.db"

    # --- Security --------------------------------------------------------
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-use-a-long-random-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- CORS ------------------------------------------------------------
    # Comma-separated list of allowed origins for the SPA frontend.
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the settings."""
    return Settings()


settings = get_settings()
