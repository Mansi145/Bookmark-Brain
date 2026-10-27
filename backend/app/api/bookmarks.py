"""The feed: the signed-in user's bookmarks, newest first."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select

from app.auth.deps import CurrentUser
from app.db import SessionDep
from app.models import Bookmark, BookmarkSource, Document, DocumentStatus, ReadState
from app.schemas import (
    ArrivedBookmark,
    BookmarkOut,
    BookmarkPage,
    BookmarkUpdate,
    FacetCount,
    FacetsOut,
    ReadStateCounts,
    SourceOut,
    SyncSummaryOut,
)
from app.services import usage
from app.services.extract import reading_minutes
from app.services.icons import default_icon
from app.worker import enqueue

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


class Section(StrEnum):
    main = "main"  # the feed: pages we can read today
    sign_in = "sign_in"  # pages that need an account or subscription
    dead = "dead"  # "Dead links": pages that no longer load (404/410)


# Each bookmark is in exactly one section: dead → dead, needs sign-in → sign_in, else main.
_dead_links = Document.status == DocumentStatus.dead
_needs_sign_in = and_(Document.access.is_not(None), ~_dead_links)


def _section_filter(section: Section):
    """SQL condition on the bookmark's document. EXISTS (`has`) keeps NULLs from leaking."""
    if section == Section.sign_in:
        return Bookmark.document.has(_needs_sign_in)
    if section == Section.dead:
        return Bookmark.document.has(_dead_links)
    return ~Bookmark.document.has(or_(_needs_sign_in, _dead_links))


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
    section: Section = Section.main,
    read_state: ReadState | None = None,  # the Feed's reading-state bar; None = all
):
    query = select(Bookmark).where(
        Bookmark.user_id == user.id,
        Bookmark.deleted_at.is_(None),
        _section_filter(section),  # dead links never show in the main feed
    )

    if read_state is not None:
        query = query.where(Bookmark.read_state == read_state)

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
async def facets(user: CurrentUser, session: SessionDep, section: Section = Section.main):
    """Folder and browser counts, for the feed's filter sidebar (per section).

    Every folder and browser the user has is listed, with 0 where this section has none,
    so the sidebar looks the same in every section.
    """
    active = and_(
        BookmarkSource.user_id == user.id,
        BookmarkSource.bookmark_id == Bookmark.id,
        Bookmark.deleted_at.is_(None),
    )

    async def count_by(column):
        everything = await session.scalars(
            select(column).where(active).group_by(column).order_by(column)
        )
        in_section = await session.execute(
            select(column, func.count(func.distinct(Bookmark.id)))
            .where(active, _section_filter(section))
            .group_by(column)
        )
        counts = dict(in_section.all())
        return [FacetCount(value=value, count=counts.get(value, 0)) for value in everything]

    in_section = and_(
        Bookmark.user_id == user.id, Bookmark.deleted_at.is_(None), _section_filter(section)
    )
    total = await session.scalar(select(func.count()).select_from(Bookmark).where(in_section))
    pending = await session.scalar(
        select(func.count())
        .select_from(Bookmark)
        .where(in_section, Bookmark.document.has(Document.status == DocumentStatus.pending))
    )
    by_state = dict(
        (
            await session.execute(
                select(Bookmark.read_state, func.count())
                .where(in_section)
                .group_by(Bookmark.read_state)
            )
        ).all()
    )
    return FacetsOut(
        total=total or 0,
        read_states=ReadStateCounts(**{s.value: by_state.get(s, 0) for s in ReadState}),
        pending=pending or 0,
        folders=await count_by(BookmarkSource.folder_path),
        browsers=await count_by(BookmarkSource.browser),
    )


@router.get("/sync-summary", response_model=SyncSummaryOut)
async def sync_summary(user: CurrentUser, session: SessionDep, browser: str):
    """What one browser has sent so far, for the Connect page.

    Counts every bookmark this browser has (all sections), the folders they're in, and the
    last few to arrive, by when we received them rather than when they were saved. A
    bookmark already synced from another browser counts as arrived when this one sends it.
    """
    live = and_(
        BookmarkSource.user_id == user.id,
        BookmarkSource.bookmark_id == Bookmark.id,
        Bookmark.deleted_at.is_(None),
    )
    from_browser = and_(live, BookmarkSource.browser == browser)

    bookmarks = await session.scalar(
        select(func.count(func.distinct(Bookmark.id))).where(from_browser)
    )
    folders = await session.scalar(
        select(func.count(func.distinct(BookmarkSource.folder_path))).where(
            from_browser, BookmarkSource.folder_path != ""
        )
    )
    newest = await session.scalars(
        select(Bookmark)
        .join(BookmarkSource, BookmarkSource.bookmark_id == Bookmark.id)
        .where(from_browser)
        .order_by(BookmarkSource.created_at.desc(), BookmarkSource.id.desc())
        .limit(4)
    )
    others = await session.scalars(
        select(BookmarkSource.browser)
        .where(live, BookmarkSource.browser != browser)
        .group_by(BookmarkSource.browser)
        .order_by(BookmarkSource.browser)
    )
    return SyncSummaryOut(
        bookmarks=bookmarks or 0,
        folders=folders or 0,
        just_arrived=[
            ArrivedBookmark(
                title=b.title,
                site=b.document.site,
                # Pages (and their logos) are fetched after the sync, so guess /favicon.ico
                # until then; the browser shows a letter tile if the guess is wrong.
                icon_url=b.document.icon_url or default_icon(b.document.url),
            )
            for b in newest.unique()
        ],
        other_browsers=list(others),
    )


@router.post("/{bookmark_id}/find-archive", response_model=BookmarkOut, status_code=202)
async def find_archive_copy(bookmark_id: int, user: CurrentUser, session: SessionDep):
    """Look up a dead link on the Wayback Machine (the row's "Find archived copy" button).

    Queues a find_archive job and answers straight away with archive_status "checking";
    the feed polls until it changes. Only for dead links, and only when a user asks, so no
    URL is sent to archive.org without someone choosing to.
    """
    bookmark = await _own_bookmark(session, user.id, bookmark_id)
    document = bookmark.document
    if document.status != DocumentStatus.dead:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only dead links can be looked up")
    if document.archive_status != "checking":  # a lookup already queued is enough
        document.archive_status = "checking"
        await enqueue(session, "find_archive", [{"document_id": document.id}])
        await session.commit()
    return _to_out(bookmark)


@router.patch("/{bookmark_id}", response_model=BookmarkOut)
async def update_bookmark(
    bookmark_id: int, changes: BookmarkUpdate, user: CurrentUser, session: SessionDep
):
    """Mark a bookmark read or unread (the detail panel's Mark as read)."""
    bookmark = await _own_bookmark(session, user.id, bookmark_id)
    bookmark.read_state = changes.read_state
    await session.commit()
    return _to_out(bookmark)


@router.post("/{bookmark_id}/summarise", response_model=BookmarkOut, status_code=202)
async def summarise_bookmark(
    bookmark_id: int, user: CurrentUser, session: SessionDep, again: bool = False
):
    """The Summarise button (and Re-summarise with `again=true`).

    Summaries are cached per document, so if anyone already summarised this URL the answer
    comes back straight away and costs nothing. Otherwise this counts one summary towards
    the user's daily limit (429 once it's reached) and queues a summarise job; the feed polls
    while summary_status is "working".
    """
    bookmark = await _own_bookmark(session, user.id, bookmark_id)
    document = bookmark.document
    if document.status == DocumentStatus.dead and document.content_source != "archive":
        # A dead link can only be summarised from its Wayback copy (Find archived copy first).
        raise HTTPException(status.HTTP_409_CONFLICT, "Find an archived copy first")

    already = document.summary_status == "working" or (
        document.summary_status == "done" and not again
    )
    if not already:
        if not await usage.take_summary(session, user.id):
            # The app opens the Limit reached dialog; its email says when this happened.
            await usage.note_limit_reached(session, user.id)
            await session.commit()
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Daily summary limit reached")
        document.summary_status = "working"
        await enqueue(session, "summarise", [{"document_id": document.id, "title": bookmark.title}])
        await session.commit()
    return _to_out(bookmark)


# Declared after /facets and /sync-summary: routes match in order, and "facets" isn't an id.
@router.get("/{bookmark_id}", response_model=BookmarkOut)
async def get_bookmark(bookmark_id: int, user: CurrentUser, session: SessionDep):
    """One bookmark, for the detail panel (it may not be in the feed pages loaded so far)."""
    return _to_out(await _own_bookmark(session, user.id, bookmark_id))


async def _own_bookmark(session, user_id: int, bookmark_id: int) -> Bookmark:
    """The user's bookmark, or 404 (also for other users' bookmarks, so ids don't leak)."""
    bookmark = await session.scalar(
        select(Bookmark).where(
            Bookmark.id == bookmark_id, Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None)
        )
    )
    if bookmark is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bookmark not found")
    return bookmark


def _to_out(bookmark: Bookmark) -> BookmarkOut:
    return BookmarkOut(
        id=bookmark.id,
        title=bookmark.title,
        url=bookmark.document.url,
        site=bookmark.document.site,
        added_at=bookmark.added_at,
        read_state=bookmark.read_state,
        status=bookmark.document.status,
        http_status=bookmark.document.http_status,
        icon_url=bookmark.document.icon_url,
        image_url=bookmark.document.image_url,
        reading_minutes=reading_minutes(bookmark.document.word_count),
        content_source=bookmark.document.content_source,
        archive_status=bookmark.document.archive_status,
        archive_url=bookmark.document.archive_url,
        archived_on=bookmark.document.archived_on,
        access=bookmark.document.access,
        description=bookmark.document.description,
        summary=bookmark.document.summary,
        key_points=bookmark.document.key_points or [],
        summary_status=bookmark.document.summary_status,
        sources=[SourceOut.model_validate(s) for s in bookmark.sources],
    )
