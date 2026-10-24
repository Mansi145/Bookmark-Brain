"""The feed: the signed-in user's bookmarks, newest first."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select

from app.auth.deps import CurrentUser
from app.db import SessionDep
from app.models import Bookmark, BookmarkSource
from app.schemas import BookmarkOut, BookmarkPage, FacetCount, FacetsOut, SourceOut

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


def _encode_cursor(bookmark: Bookmark) -> str:
    return f"{bookmark.added_at.isoformat()}_{bookmark.id}"


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        added_at, _, bookmark_id = cursor.rpartition("_")
        return datetime.fromisoformat(added_at), int(bookmark_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid cursor") from None


@router.get("", response_model=BookmarkPage)
async def list_bookmarks(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    cursor: str | None = None,
    folder: str | None = None,
    browser: str | None = None,
):
    query = select(Bookmark).where(Bookmark.user_id == user.id, Bookmark.deleted_at.is_(None))

    if folder or browser:
        source_filter = [BookmarkSource.bookmark_id == Bookmark.id]
        if folder:  # the folder itself or any subfolder
            source_filter.append(
                or_(
                    BookmarkSource.folder_path == folder,
                    BookmarkSource.folder_path.startswith(folder + "/", autoescape=True),
                )
            )
        if browser:
            source_filter.append(BookmarkSource.browser == browser)
        query = query.where(select(BookmarkSource.id).where(*source_filter).exists())

    # Keyset pagination: "rows after this (added_at, id)". Unlike OFFSET, it stays
    # fast on page 100 and doesn't skip/duplicate rows when new bookmarks arrive.
    if cursor:
        added_at, bookmark_id = _decode_cursor(cursor)
        query = query.where(
            or_(
                Bookmark.added_at < added_at,
                and_(Bookmark.added_at == added_at, Bookmark.id < bookmark_id),
            )
        )

    query = query.order_by(Bookmark.added_at.desc(), Bookmark.id.desc()).limit(limit + 1)
    rows = (await session.scalars(query)).unique().all()
    page, has_more = rows[:limit], len(rows) > limit

    return BookmarkPage(
        items=[_to_out(b) for b in page],
        next_cursor=_encode_cursor(page[-1]) if has_more else None,
    )


@router.get("/facets", response_model=FacetsOut)
async def facets(user: CurrentUser, session: SessionDep):
    """Folder and browser counts, for the feed's filter sidebar."""
    active = and_(
        BookmarkSource.user_id == user.id,
        BookmarkSource.bookmark_id == Bookmark.id,
        Bookmark.deleted_at.is_(None),
    )

    async def count_by(column):
        result = await session.execute(
            select(column, func.count(func.distinct(Bookmark.id)))
            .where(active)
            .group_by(column)
            .order_by(column)
        )
        return [FacetCount(value=value, count=count) for value, count in result]

    return FacetsOut(
        folders=await count_by(BookmarkSource.folder_path),
        browsers=await count_by(BookmarkSource.browser),
    )


def _to_out(bookmark: Bookmark) -> BookmarkOut:
    return BookmarkOut(
        id=bookmark.id,
        title=bookmark.title,
        url=bookmark.document.url,
        site=bookmark.document.site,
        added_at=bookmark.added_at,
        read_state=bookmark.read_state,
        status=bookmark.document.status,
        sources=[SourceOut.model_validate(s) for s in bookmark.sources],
    )
