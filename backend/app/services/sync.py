"""Merge bookmarks from one browser install into the user's library.

Steps (all in one transaction):
1. upsert `documents` by normalised URL (shared across users)
2. upsert the user's `bookmarks` (one per document)
3. upsert `bookmark_sources` (one per browser node)
4. delete sources the browser no longer has
5. soft-delete bookmarks that no browser has any more

Uses Postgres `INSERT ... ON CONFLICT` so re-sending the same data is harmless
(idempotent). That matters because the extension retries after failures.
"""

from datetime import UTC, datetime
from itertools import batched

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bookmark, BookmarkSource, Document
from app.schemas import SyncIn, SyncItem, SyncOut
from app.services.urls import is_supported, normalize_url, site_of

# Postgres caps a statement at 32,767 parameters; stay well below it.
BATCH = 500


async def apply_sync(session: AsyncSession, user_id: int, payload: SyncIn) -> SyncOut:
    items = [item for item in payload.upserts if is_supported(item.url)]
    skipped = len(payload.upserts) - len(items)
    by_url: dict[str, list[SyncItem]] = {}
    for item in items:
        by_url.setdefault(normalize_url(item.url), []).append(item)

    doc_ids = await _upsert_documents(session, by_url)
    bookmark_ids = await _upsert_bookmarks(session, user_id, by_url, doc_ids)
    await _upsert_sources(session, user_id, payload, by_url, bookmark_ids)
    removed = await _remove_sources(session, user_id, payload, items)
    await _soft_delete_orphans(session, user_id)
    await session.commit()

    active = await session.scalar(
        select(func.count()).where(Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None))
    )
    return SyncOut(
        received=len(payload.upserts),
        skipped_unsupported=skipped,
        upserted=len(items),
        removed_sources=removed,
        active_bookmarks=active or 0,
    )


async def _upsert_documents(session, by_url: dict[str, list[SyncItem]]) -> dict[str, int]:
    """Return {normalized_url: document_id}."""
    ids: dict[str, int] = {}
    for chunk in batched(by_url.items(), BATCH):
        rows = [
            {"normalized_url": norm, "url": items[0].url.strip(), "site": site_of(norm)}
            for norm, items in chunk
        ]
        await session.execute(
            insert(Document).values(rows).on_conflict_do_nothing(index_elements=["normalized_url"])
        )
        result = await session.execute(
            select(Document.normalized_url, Document.id).where(
                Document.normalized_url.in_([norm for norm, _ in chunk])
            )
        )
        ids.update(dict(result.all()))
    return ids


async def _upsert_bookmarks(session, user_id, by_url, doc_ids) -> dict[str, int]:
    """Return {normalized_url: bookmark_id}. Revives soft-deleted bookmarks."""
    ids: dict[str, int] = {}
    for chunk in batched(by_url.items(), BATCH):
        rows = [
            {
                "user_id": user_id,
                "document_id": doc_ids[norm],
                "title": next((i.title for i in items if i.title), norm),
                "added_at": min(i.added_at for i in items),
            }
            for norm, items in chunk
        ]
        stmt = insert(Bookmark).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "document_id"],
            set_={
                "deleted_at": None,
                "added_at": func.least(Bookmark.added_at, stmt.excluded.added_at),
            },
        ).returning(Bookmark.document_id, Bookmark.id)
        by_doc = dict((await session.execute(stmt)).all())
        ids.update({norm: by_doc[doc_ids[norm]] for norm, _ in chunk})
    return ids


async def _upsert_sources(session, user_id, payload: SyncIn, by_url, bookmark_ids) -> None:
    rows = [
        {
            "user_id": user_id,
            "bookmark_id": bookmark_ids[norm],
            "source_id": payload.source.id,
            "browser": payload.source.browser,
            "node_id": item.node_id,
            "title": item.title,
            "folder_path": item.folder_path,
            "added_at": item.added_at,
        }
        for norm, items in by_url.items()
        for item in items
    ]
    for chunk in batched(rows, BATCH):
        stmt = insert(BookmarkSource).values(list(chunk))
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "source_id", "node_id"],
            # The URL of a node can be edited, which moves it to another bookmark.
            set_={
                col: stmt.excluded[col]
                for col in ("bookmark_id", "browser", "title", "folder_path")
            },
        )
        await session.execute(stmt)


async def _remove_sources(session, user_id, payload: SyncIn, kept: list[SyncItem]) -> int:
    where = [BookmarkSource.user_id == user_id, BookmarkSource.source_id == payload.source.id]
    if payload.full:
        # Everything this browser didn't mention is gone from it.
        where.append(BookmarkSource.node_id.not_in([i.node_id for i in kept]))
    elif payload.removed_node_ids:
        where.append(BookmarkSource.node_id.in_(payload.removed_node_ids))
    else:
        return 0
    result = await session.execute(delete(BookmarkSource).where(*where))
    return result.rowcount or 0


async def _soft_delete_orphans(session, user_id) -> None:
    has_source = exists().where(BookmarkSource.bookmark_id == Bookmark.id)
    await session.execute(
        update(Bookmark)
        .where(Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None), ~has_source)
        .values(deleted_at=datetime.now(UTC))
    )
