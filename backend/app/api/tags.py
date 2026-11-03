"""Tags: the sidebar's Tags group (list, new, rename, merge, delete), the detail panel's tags and
Select mode's Add tag / Remove tag. The rules live in app/services/tags.py.

A rule a change would break answers 409 with a code as its detail, which the app words:
tag_name_taken, tag_limit (50 per account), bookmark_tag_limit (5 per bookmark), tag_merge_same.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.bookmarks import bookmark_out, own_bookmark
from app.auth.deps import CurrentUser
from app.db import SessionDep
from app.models import Bookmark
from app.schemas import BookmarkOut, TagBulkIn, TagBulkOut, TagCount, TagIn, TagMergeIn, TagOut
from app.services import tags
from app.services.tags import TagError

router = APIRouter(tags=["tags"])


def _conflict(error: TagError) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, error.code)


async def _own_tag(session, user_id: int, tag_id: int):
    """The user's tag, or 404 (also for other users' tags, so ids don't leak)."""
    tag = await tags.own_tag(session, user_id, tag_id)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not found")
    return tag


@router.get("/api/tags", response_model=list[TagCount])
async def list_tags(user: CurrentUser, session: SessionDep):
    """Every tag, unused ones too (count 0), most used first."""
    return [
        TagCount(id=tag.id, name=tag.name, count=n)
        for tag, n in await tags.with_counts(session, user.id)
    ]


@router.post("/api/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(body: TagIn, user: CurrentUser, session: SessionDep):
    """+ New tag: a tag that isn't on any bookmark yet."""
    try:
        tag = await tags.create(session, user.id, body.name)
    except TagError as error:
        raise _conflict(error) from None
    await session.commit()
    return tag


@router.patch("/api/tags/{tag_id}", response_model=TagOut)
async def rename_tag(tag_id: int, body: TagIn, user: CurrentUser, session: SessionDep):
    tag = await _own_tag(session, user.id, tag_id)
    try:
        await tags.rename(session, tag, body.name)
    except TagError as error:
        raise _conflict(error) from None
    await session.commit()
    return tag


@router.post("/api/tags/{tag_id}/merge", response_model=TagOut)
async def merge_tag(tag_id: int, body: TagMergeIn, user: CurrentUser, session: SessionDep):
    """Merge into another tag: its bookmarks get `into`, then this tag is deleted."""
    tag = await _own_tag(session, user.id, tag_id)
    into = await _own_tag(session, user.id, body.into)
    try:
        await tags.merge(session, tag, into)
    except TagError as error:
        raise _conflict(error) from None
    await session.commit()
    return into


@router.delete("/api/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int, user: CurrentUser, session: SessionDep):
    """The tag comes off every bookmark; the bookmarks and their other tags stay."""
    await session.delete(await _own_tag(session, user.id, tag_id))
    await session.commit()


@router.post("/api/bookmarks/{bookmark_id}/tags", response_model=BookmarkOut)
async def add_tag(bookmark_id: int, body: TagIn, user: CurrentUser, session: SessionDep):
    """The detail panel's Add tag: an existing tag by name, or a new one ("+ Create tag")."""
    bookmark = await own_bookmark(session, user.id, bookmark_id)
    try:
        tag = await tags.find_or_create(session, user.id, body.name)
        await tags.add(session, bookmark, tag)
    except TagError as error:
        raise _conflict(error) from None
    await session.commit()
    await session.refresh(bookmark, ["tags"])
    return bookmark_out(bookmark)


@router.delete("/api/bookmarks/{bookmark_id}/tags/{tag_id}", response_model=BookmarkOut)
async def remove_tag(bookmark_id: int, tag_id: int, user: CurrentUser, session: SessionDep):
    bookmark = await own_bookmark(session, user.id, bookmark_id)
    await tags.remove(session, bookmark.id, tag_id)
    await session.commit()
    await session.refresh(bookmark, ["tags"])
    return bookmark_out(bookmark)


async def _own_bookmarks(session, user_id: int, ids: list[int]) -> list[Bookmark]:
    """The ones among `ids` that are the user's (others' ids are quietly left out)."""
    rows = await session.scalars(
        select(Bookmark)
        .where(Bookmark.id.in_(ids), Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None))
        .order_by(Bookmark.id)  # a fixed order, so two requests lock rows in the same order
    )
    return list(rows.unique())


@router.post("/api/tags/{tag_id}/add", response_model=TagBulkOut)
async def add_to_many(tag_id: int, body: TagBulkIn, user: CurrentUser, session: SessionDep):
    """Select mode's Add tag: "Added Programming to 2 bookmarks. 1 already had 5 tags…"."""
    tag = await _own_tag(session, user.id, tag_id)
    bookmarks = await _own_bookmarks(session, user.id, body.bookmark_ids)
    added, skipped = await tags.add_to_many(session, tag, bookmarks)
    await session.commit()
    return TagBulkOut(changed=added, skipped=skipped)


@router.post("/api/tags/{tag_id}/remove", response_model=TagBulkOut)
async def remove_from_many(tag_id: int, body: TagBulkIn, user: CurrentUser, session: SessionDep):
    """Select mode's Remove tag."""
    tag = await _own_tag(session, user.id, tag_id)
    bookmarks = await _own_bookmarks(session, user.id, body.bookmark_ids)
    removed = await tags.remove_from_many(session, tag, [b.id for b in bookmarks])
    await session.commit()
    return TagBulkOut(changed=removed)
