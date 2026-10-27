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

    # AI (app/ai/llm.py). Gemini is primary, Groq takes over when Gemini fails or is out of
    # quota. Model names live here so switching model is a config change, not a code change.
    # The fallback chain, in order: Gemini, a second Gemini model (its own free quota, same
    # key), OpenRouter's free models, NVIDIA NIM (hosts DeepSeek for free), then Groq. A
    # provider without a key is skipped. Free model line-ups change often: check them with
    # the commands in the llm-patterns skill.
    google_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_fallback_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3.5-super-vl:free"
    nvidia_api_key: str = ""
    nvidia_model: str = "deepseek-ai/deepseek-v4.1-flash"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    # Summaries a user may start per UTC day. The free quotas are per API key, so all users
    # share them; this stops one person from using up the day.
    ai_daily_limit_per_user: int = 50

    # Email (app/services/mail.py), for the Limit reached dialog's "Notify the maintainer".
    # Resend's free plan: 100 emails a day. Without your own domain, Resend only sends from its
    # test address, and only to the address you signed up with, so MAINTAINER_EMAIL must be
    # that address. Leave the key empty to switch the button off (it then answers 503).
    resend_api_key: str = ""
    maintainer_email: str = ""
    email_from: str = "Bookmark Brain <onboarding@resend.dev>"

    # Local testing only: turns on /api/usage/dev/* (use up or reset today's AI limit, for
    # trying the Limit reached dialog). Never set it in production.
    dev_tools: bool = False

    # Phase 7: cron endpoints.
    internal_cron_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
