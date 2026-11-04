"""App settings, read from environment variables (and backend/.env in dev).

pydantic-settings validates types at startup, so a missing or malformed
variable fails loudly on boot instead of halfway through a request.
"""

import os
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Neon's connection string can be pasted as it is (see asyncpg_url).
    database_url: str = "postgresql+asyncpg://bb:bb@localhost:5432/bookmark_brain"
    frontend_origin: str = "http://localhost:5173"

    # Auth (Phase 1)
    jwt_secret: str = ""
    google_client_id: str = ""
    # GitHub sign-in (app/auth/github.py): an OAuth App from github.com/settings/developers.
    # Its "Authorization callback URL" must be API_ORIGIN + /api/auth/github/callback, and GitHub
    # allows one callback per app, so production needs an OAuth App of its own. Leave these empty
    # and the GitHub button says sign-in with GitHub isn't available.
    github_client_id: str = ""
    github_client_secret: str = ""
    # Where the browser reaches this API, for that callback URL.
    api_origin: str = "http://localhost:8000"
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
    # Ask tries this one first. Its answers are watched as they're written, and on the free tier
    # gemini-3.5-flash-lite took about 20 s per call (even for "hi") against about 1 s for
    # gemini-2.5-flash (2026-11-03), so an answer took a minute. Summaries run in the background,
    # where that doesn't matter, so they keep GEMINI_MODEL. Leave empty to use the usual order.
    ask_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3.5-super-vl:free"
    nvidia_api_key: str = ""
    nvidia_model: str = "deepseek-ai/deepseek-v4.1-flash"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    # Embeddings for search (llm.get_embedder): Gemini only, same key. There's no fallback
    # provider, because vectors from different models can't be compared: when this model is
    # down, search uses keywords alone. Changing it means re-embedding every page.
    gemini_embedding_model: str = "gemini-embedding-2"
    # Summaries a user may start per UTC day. The free quotas are per API key, so all users
    # share them; this stops one person from using up the day.
    ai_daily_limit_per_user: int = 50
    # After a sync, the newest this-many bookmarks are summarised without a click (owner,
    # 2026-11-04: the front page fills in by itself), within the daily limit above. 0 turns it
    # off, so every summary waits for its Summarise button.
    front_page_summaries: int = 30

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

    # Tracing (LangSmith): records every agent and chain run, step by step, at
    # smith.langchain.com. For local dev and the eval only (owner, 2026-11-03): leave these unset
    # in production, where traces would carry users' questions and the text of their pages.
    langsmith_api_key: str = ""
    langsmith_tracing: bool = False
    langsmith_project: str = "bookmark-brain"

    # Phase 7: cron endpoints.
    internal_cron_secret: str = ""

    @field_validator("database_url")
    @classmethod
    def asyncpg_url(cls, url: str) -> str:
        """Make a plain Postgres URL (what Neon gives you) work with the asyncpg driver.

        Neon's looks like postgresql://…/db?sslmode=require&channel_binding=require. SQLAlchemy
        needs "+asyncpg" in the scheme to use the async driver, and asyncpg doesn't know the libpq
        options sslmode / channel_binding: it takes ssl=require instead.
        """
        parts = urlsplit(url)
        scheme = (
            "postgresql+asyncpg" if parts.scheme in ("postgres", "postgresql") else parts.scheme
        )
        query = dict(parse_qsl(parts.query))
        if query.pop("sslmode", None) in ("require", "verify-ca", "verify-full"):
            query["ssl"] = "require"
        query.pop("channel_binding", None)
        return urlunsplit(parts._replace(scheme=scheme, query=urlencode(query)))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _share_tracing_settings(settings)
    return settings


def _share_tracing_settings(settings: Settings) -> None:
    """Hand the LangSmith settings to LangChain, which reads them from the environment only.

    pydantic-settings reads backend/.env into Settings without touching os.environ, so without
    this the keys in .env would never reach LangChain and nothing would be traced.
    """
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
