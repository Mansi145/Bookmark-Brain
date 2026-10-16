"""App settings, read from environment variables (and backend/.env in dev).

pydantic-settings validates types at startup, so a missing or malformed
variable fails loudly on boot instead of halfway through a request.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://bb:bb@localhost:5432/bookmark_brain"
    frontend_origin: str = "http://localhost:5173"

    # Filled in from Phase 1 onwards; empty defaults keep Phase 0 bootable.
    jwt_secret: str = ""
    google_client_id: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    internal_cron_secret: str = ""
    ai_daily_limit_per_user: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
