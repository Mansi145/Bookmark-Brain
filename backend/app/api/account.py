"""The signed-in user's account: what it holds, a download of it, and deleting it.

Web app only (`WebUser`: the session cookie, never an extension token).

Deleting removes the user row; the database then removes everything personal with it
(`ondelete="CASCADE"`): bookmarks, which browser has each one (bookmark_sources), extension
tokens and AI usage. `documents` stay: they're shared per URL (the page text and its cached
summary aren't personal, and other users may have saved the same page).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select

from app.auth.deps import WebUser
from app.auth.security import SESSION_COOKIE
from app.config import get_settings
from app.db import SessionDep
from app.models import ApiToken, Bookmark, User
from app.schemas import AccountDeleteIn, AccountOut

router = APIRouter(prefix="/api/account", tags=["account"])


@router.get("", response_model=AccountOut)
async def account_summary(user: WebUser, session: SessionDep):
    """The counts the delete dialog shows ("248 bookmarks, 3 connected browsers")."""
    bookmarks = await session.scalar(
        select(func.count())
        .select_from(Bookmark)
        .where(Bookmark.user_id == user.id, Bookmark.deleted_at.is_(None))
    )
    browsers = await session.scalar(
        select(func.count()).select_from(ApiToken).where(ApiToken.user_id == user.id)
    )
    return AccountOut(bookmarks=bookmarks or 0, browsers=browsers or 0)


@router.get("/export")
async def export_data(user: WebUser, session: SessionDep):
    """Download my data: one JSON file with every bookmark, where it's saved, its read state
    and its summary, plus the connected browsers (names and dates only, never token secrets).
    """
    bookmarks = await session.scalars(
        select(Bookmark)
        .where(Bookmark.user_id == user.id, Bookmark.deleted_at.is_(None))
        .order_by(Bookmark.added_at.desc())
    )
    tokens = await session.scalars(
        select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at)
    )
    now = datetime.now(UTC)
    data = {
        "exported_at": now.isoformat(),
        "account": {"name": user.name, "email": user.email, "signed_in_with": "google"},
        "bookmarks": [
            {
                "title": b.title,
                "url": b.document.url,
                "site": b.document.site,
                "saved_at": b.added_at.isoformat(),
                "read_state": b.read_state.value,
                "saved_in": [{"browser": s.browser, "folder": s.folder_path} for s in b.sources],
                "summary": b.document.summary if b.document.summary_status == "done" else None,
                "key_points": b.document.key_points or [],
            }
            for b in bookmarks
        ],
        "connected_browsers": [
            {
                "name": t.name,
                "connected_at": t.created_at.isoformat(),
                "last_synced_at": t.last_used_at.isoformat() if t.last_used_at else None,
            }
            for t in tokens
        ],
    }
    filename = f"bookmark-brain-{now:%Y-%m-%d}.json"
    return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: AccountDeleteIn, user: WebUser, session: SessionDep, response: Response
):
    """Delete the account and everything personal in it. Can't be undone."""
    if body.confirm != "DELETE":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Type "DELETE" to confirm')
    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()
    # Sign them out too (the cookie would point at a user that no longer exists).
    settings = get_settings()
    response.delete_cookie(
        SESSION_COOKIE,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
