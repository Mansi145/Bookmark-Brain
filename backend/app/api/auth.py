import secrets
from typing import Literal
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import github
from app.auth.deps import CurrentUser, WebUser, find_web_user
from app.auth.security import SESSION_COOKIE, create_session_token, verify_google_credential
from app.config import get_settings
from app.db import SessionDep
from app.models import User
from app.schemas import GoogleLoginIn, UserOut
from app.services import tags

router = APIRouter(prefix="/api", tags=["auth"])

# Holds the sign-in's random state (and where to go afterwards) while the user is on GitHub.
GITHUB_STATE_COOKIE = "bb_github_state"
GITHUB_STATE_SECONDS = 600
GITHUB_COOKIE_PATH = "/api/auth/github"
# Why the trip to GitHub started: to sign in, or to link GitHub to the signed-in account.
SIGN_IN, LINK = "signin", "link"


@router.post("/auth/google", response_model=UserOut)
async def login_with_google(body: GoogleLoginIn, response: Response, session: SessionDep):
    """Exchange a Google ID token for our own session cookie."""
    try:
        identity = await verify_google_credential(body.credential)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, f"Invalid Google credential: {exc}"
        ) from exc

    user = await session.scalar(select(User).where(User.google_sub == identity.sub))
    if user is None:
        user = await _account_to_link(session, identity.email, User.google_sub)
        user.google_sub = identity.sub
    # Refresh profile details on every login.
    user.email, user.name, user.avatar_url = identity.email, identity.name, identity.picture
    await session.commit()

    _set_session_cookie(response, user.id)
    return user


@router.post("/auth/google/link", response_model=UserOut)
async def link_google(body: GoogleLoginIn, user: WebUser, session: SessionDep):
    """Settings → Sign-in methods → Link: add a Google account to the signed-in account.

    Unlike signing in, the emails needn't match: being signed in here and then approving on
    Google proves one person has both.
    """
    try:
        identity = await verify_google_credential(body.credential)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, f"Invalid Google credential: {exc}"
        ) from exc
    owner = await session.scalar(select(User).where(User.google_sub == identity.sub))
    if owner is not None and owner.id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "That Google account has its own account")
    user.google_sub = identity.sub
    await session.commit()
    return user


@router.get("/auth/github")
async def start_github_login(next: str = "/"):
    """Send the browser to GitHub to approve signing in (app/auth/github.py, step 1).

    `next` is where to come back to in the web app, e.g. /connect?nonce=… mid one-click connect.
    """
    return _go_to_github(_safe_next(next), SIGN_IN)


@router.get("/auth/github/link")
async def start_github_link(
    request: Request, session: SessionDep, next: str = "/settings?section=account"
):
    """Settings → Sign-in methods → Link: the same trip to GitHub, but coming back adds GitHub
    to the signed-in account instead of signing in (see link_google)."""
    target = _safe_next(next)
    if await find_web_user(request, session) is None:
        return _back_to_app(target, error="failed")
    return _go_to_github(target, LINK)


@router.get("/auth/github/callback")
async def github_callback(
    request: Request,
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """GitHub sends the browser back here (steps 2-4); then on to the web app, signed in (or,
    when linking, with GitHub added to the account).

    Problems go back to the app as ?github_error=…: cancelled (the user said no on GitHub),
    no_email (no verified primary email), in_use (linking a GitHub account that has its own
    account), failed (anything else).
    """
    saved_state, _, rest = request.cookies.get(GITHUB_STATE_COOKIE, "").partition(".")
    purpose, _, saved_next = rest.partition(".")
    target = _safe_next(unquote(saved_next) or "/")

    def back(error: str | None = None) -> RedirectResponse:
        response = _back_to_app(target, error)
        response.delete_cookie(GITHUB_STATE_COOKIE, path=GITHUB_COOKIE_PATH)
        return response

    if not (saved_state and state and secrets.compare_digest(saved_state, state)):
        return back("failed")  # not started from this browser, or the 10 minutes ran out
    if error or not code:
        return back("cancelled")
    try:
        identity = await github.fetch_identity(code)
    except github.GitHubError:
        return back("failed")
    if identity.email is None:
        return back("no_email")

    user = await session.scalar(select(User).where(User.github_id == identity.id))
    if purpose == LINK:
        # Add GitHub to whoever is signed in here; the emails needn't match (see link_google).
        # The profile stays as it is: linking isn't signing in.
        signed_in = await find_web_user(request, session)
        if signed_in is None:
            return back("failed")  # signed out meanwhile
        if user is not None and user.id != signed_in.id:
            return back("in_use")
        signed_in.github_id = identity.id
        await session.commit()
        return back()

    if user is None:
        user = await _account_to_link(session, identity.email, User.github_id)
        user.github_id = identity.id
    user.email, user.name, user.avatar_url = identity.email, identity.name, identity.avatar_url
    await session.commit()

    response = back()
    _set_session_cookie(response, user.id)
    return response


@router.delete("/auth/{provider}/link", response_model=UserOut)
async def unlink(provider: Literal["google", "github"], user: WebUser, session: SessionDep):
    """Settings → Sign-in methods → Unlink, e.g. after linking the wrong GitHub account.

    Never the last one, so the account can always be signed in to (the database checks this
    too: ck_users_has_provider). Signing in with it again later links it again if its email is
    the account's (the same verified email is one account).
    """
    if user.providers == [provider]:
        raise HTTPException(status.HTTP_409_CONFLICT, "That's the only way to sign in")
    if provider == "google":
        user.google_sub = None
    else:
        user.github_id = None
    await session.commit()
    return user


def _go_to_github(target: str, purpose: str) -> RedirectResponse:
    """Off to GitHub (step 1), remembering the state, why we went and where to come back to."""
    if not github.is_configured():
        return _back_to_app(target, error="unavailable")
    state = secrets.token_urlsafe(24)
    response = RedirectResponse(github.authorize_url(state), status.HTTP_302_FOUND)
    settings = get_settings()
    response.set_cookie(
        GITHUB_STATE_COOKIE,
        f"{state}.{purpose}.{quote(target, safe='')}",  # the state and purpose have no "."
        max_age=GITHUB_STATE_SECONDS,
        path=GITHUB_COOKIE_PATH,
        httponly=True,
        secure=settings.session_cookie_secure,
        # Lax is enough: GitHub's redirect back is a top-level navigation, which sends it.
        samesite="lax",
    )
    return response


async def _account_to_link(session: AsyncSession, email: str, provider_column) -> User:
    """The account a first sign-in with a provider belongs to.

    An account with the same email is the same person (owner's decision), as long as it isn't
    already linked to another account of this provider. That's safe because both emails are
    verified: Google signs in only verified emails, and for GitHub we take only the verified
    primary one, so nobody can claim an account just by typing its address somewhere.
    Otherwise it's a new account.
    """
    user = await session.scalar(
        select(User)
        .where(func.lower(User.email) == email.lower(), provider_column.is_(None))
        .order_by(User.id)
        .limit(1)
    )
    if user is None:
        user = User(email=email)
        session.add(user)
        tags.add_starter_tags(session, user)  # saved with the user, once a provider is set
    return user


def _safe_next(next: str) -> str:
    """Only a path in our own web app, never another site (that would be an "open redirect")."""
    if not next.startswith("/") or next.startswith("//") or "\\" in next:
        return "/"
    return next


def _back_to_app(target: str, error: str | None = None) -> RedirectResponse:
    """A redirect to `target` in the web app, with ?github_error=… added when sign-in failed."""
    _, _, path, query, fragment = urlsplit(target)
    params = parse_qsl(query, keep_blank_values=True)
    if error:
        params.append(("github_error", error))
    url = urlunsplit(("", "", path, urlencode(params), fragment))
    return RedirectResponse(get_settings().frontend_origin + url, status.HTTP_302_FOUND)


def _set_session_cookie(response: Response, user_id: int) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id),
        max_age=settings.session_days * 24 * 3600,
        httponly=True,  # page JavaScript can't read it, so XSS can't steal it
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    settings = get_settings()
    response.delete_cookie(
        SESSION_COOKIE,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
