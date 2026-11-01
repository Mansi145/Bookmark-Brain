"""GitHub sign-in: OAuth's "authorization code" flow, all on the server.

1. /api/auth/github sends the browser to GitHub with our app's id and a random `state`, which is
   also kept in a short-lived cookie.
2. The user approves on github.com, and GitHub sends the browser back to
   /api/auth/github/callback with a one-time `code` and the same `state`.
3. The state must match the cookie. That proves this browser started the sign-in, so another
   site can't sign someone in to an account of its choosing ("login CSRF").
4. The server swaps the code for an access token, using the app's secret (which never leaves the
   server), reads who the user is and their verified primary email, and forgets the token.

We ask GitHub only for read:user and user:email: no repositories, nothing else. These calls go to
fixed github.com addresses, never to a URL a user chose, so a plain httpx client is right here
(the SSRF-safe fetcher in services/fetch.py is for bookmarked pages).
"""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import get_settings

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"
SCOPES = "read:user user:email"


@dataclass
class GitHubIdentity:
    id: int  # GitHub's numeric user id: stays the same if the user renames their account
    name: str  # their display name, or their username when they haven't set one
    avatar_url: str | None
    email: str | None  # their primary email, only if GitHub has verified it


class GitHubError(Exception):
    """GitHub refused the code or couldn't be reached."""


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.github_client_id and settings.github_client_secret)


def callback_url() -> str:
    return f"{get_settings().api_origin}/api/auth/github/callback"


def authorize_url(state: str) -> str:
    """GitHub's "Authorize Bookmark Brain?" page (step 1)."""
    query = {
        "client_id": get_settings().github_client_id,
        "redirect_uri": callback_url(),
        "scope": SCOPES,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(query)}"


def make_client() -> httpx.AsyncClient:
    """Tests replace this with a client whose transport fakes GitHub."""
    return httpx.AsyncClient(timeout=10, headers={"User-Agent": "Bookmark-Brain"})


async def fetch_identity(code: str) -> GitHubIdentity:
    """Swap the one-time code for a token and read who signed in (step 4)."""
    settings = get_settings()
    try:
        async with make_client() as http:
            answer = await http.post(
                TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": callback_url(),
                },
            )
            # A bad or reused code still comes back 200, with an "error" field instead.
            token = answer.json().get("access_token") if answer.status_code == 200 else None
            if not token:
                raise GitHubError("GitHub didn't accept the sign-in code")
            auth = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
            profile = await http.get(f"{API_URL}/user", headers=auth)
            emails = await http.get(f"{API_URL}/user/emails", headers=auth)
    except httpx.HTTPError as err:
        raise GitHubError(f"Couldn't reach GitHub: {err}") from err
    if profile.status_code != 200 or emails.status_code != 200:
        raise GitHubError("GitHub didn't share the account's details")

    user = profile.json()
    primary = next(
        (e["email"] for e in emails.json() if e.get("primary") and e.get("verified")), None
    )
    return GitHubIdentity(
        id=user["id"],
        name=user.get("name") or user["login"],
        avatar_url=user.get("avatar_url"),
        email=primary,
    )
