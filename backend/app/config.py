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

    # Auth (Phase 1)
    jwt_secret: str = ""
    google_client_id: str = ""
    session_days: int = 30
    # Local dev: frontend and API are both on localhost, so Lax + non-secure works.
    # Production (vercel.app -> onrender.com is cross-site): set Secure=true, SameSite=none.
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"

    # Background job worker (app/worker.py). Tests turn it off and run jobs by hand.
    worker_enabled: bool = True

    # Filled in from later phases.
    google_api_key: str = ""
    groq_api_key: str = ""
    internal_cron_secret: str = ""
    ai_daily_limit_per_user: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
