"""Search: the user's bookmarks that best match a query (app/services/search.py finds them)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.bookmarks import bookmark_out, in_folder_or_browser
from app.auth.deps import CurrentUser
from app.db import SessionDep
from app.models import Bookmark
from app.schemas import SearchOut, SearchResult
from app.services import search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchOut)
async def search_bookmarks(
    user: CurrentUser,
    session: SessionDep,
    q: Annotated[str, Query(max_length=200)],
    folder: str | None = None,
    browser: str | None = None,
):
    """Everything the user saved is searched (read stories, Needs sign-in and Dead links too),
    narrowed by the sidebar's folder and browser filters. Searches don't count toward the daily
    AI limit, and going over the search throttle never answers with an error (owner)."""
    q = q.strip()
    if not q:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Type something to search for")

    found = await search.search(session, user.id, q, in_folder_or_browser(folder, browser))
    rows = await session.scalars(select(Bookmark).where(Bookmark.id.in_(found.bookmark_ids)))
    bookmarks = {bookmark.id: bookmark for bookmark in rows.unique()}
    return SearchOut(
        items=[
            SearchResult(
                **bookmark_out(bookmarks[bookmark_id]).model_dump(),
                highlighted=found.highlighted.get(bookmark_id),
            )
            for bookmark_id in found.bookmark_ids
        ],
        more=found.more,
    )
