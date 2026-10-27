"""Who is making this request?

`CurrentUser` accepts either the web app's session cookie or the extension's bearer token.
`WebUser` accepts only the cookie, for account actions an extension must never do.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select

from app.auth.security import PAT_PREFIX, SESSION_COOKIE, hash_pat, read_session_token
from app.db import SessionDep
from app.models import ApiToken, User


async def get_current_user(request: Request, session: SessionDep) -> User:
    user: User | None = None

    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token.startswith(PAT_PREFIX):
            api_token = await session.scalar(
                select(ApiToken).where(ApiToken.token_hash == hash_pat(token))
            )
            if api_token:
                api_token.last_used_at = datetime.now(UTC)
                await session.commit()
                user = await session.get(User, api_token.user_id)
    elif cookie := request.cookies.get(SESSION_COOKIE):
        if (user_id := read_session_token(cookie)) is not None:
            user = await session.get(User, user_id)

    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_web_user(request: Request, session: SessionDep) -> User:
    """Like get_current_user, but only the web app's session cookie, never an extension token.

    For account actions (download my data, delete account): a token pasted into a browser
    extension shouldn't be able to export or wipe the whole account if it leaks.
    """
    cookie = request.cookies.get(SESSION_COOKIE)
    user_id = read_session_token(cookie) if cookie else None
    user = await session.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


WebUser = Annotated[User, Depends(get_web_user)]
