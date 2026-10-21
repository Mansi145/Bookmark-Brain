"""Token helpers: our session JWTs, extension access tokens, and Google ID token checks."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.concurrency import run_in_threadpool
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import get_settings

SESSION_COOKIE = "bb_session"
PAT_PREFIX = "bb_pat_"
_ALGORITHM = "HS256"


# --- Session JWTs (web app) -------------------------------------------------


def create_session_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=settings.session_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def read_session_token(token: str) -> int | None:
    """Return the user id, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


# --- Personal access tokens (extension) -------------------------------------


def generate_pat() -> str:
    # The prefix makes leaked tokens easy to recognise (and to scan for in git).
    return PAT_PREFIX + secrets.token_urlsafe(32)


def hash_pat(token: str) -> str:
    # A fast hash is fine here: unlike passwords, the token is long and random,
    # so it can't be brute-forced from the hash.
    return hashlib.sha256(token.encode()).hexdigest()


# --- Google Sign-In ---------------------------------------------------------


class GoogleIdentity:
    def __init__(self, claims: dict):
        self.sub: str = claims["sub"]
        self.email: str = claims["email"]
        self.name: str | None = claims.get("name")
        self.picture: str | None = claims.get("picture")


async def verify_google_credential(credential: str) -> GoogleIdentity:
    """Check the ID token's signature, expiry and audience (our client id).

    Raises ValueError if the token is invalid. google-auth is synchronous (it
    fetches Google's public keys over HTTP), so run it in a worker thread.
    """
    claims = await run_in_threadpool(
        id_token.verify_oauth2_token,
        credential,
        google_requests.Request(),
        get_settings().google_client_id,
    )
    if not claims.get("email_verified"):
        raise ValueError("Google account email is not verified")
    return GoogleIdentity(claims)
