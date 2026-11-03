"""The user's tags: starter tags, the limits, and adding / removing them on bookmarks.

Every change goes through here so the rules hold everywhere (the API now, the AI tagger in the
next step): names are 1–30 characters and unique per user whatever the case, a bookmark has at
most MAX_PER_BOOKMARK tags and an account at most MAX_PER_USER. A tag the user takes off a
bookmark is remembered (RemovedTag), so the AI never puts it back.

Checking a limit and then inserting is two statements, so two requests at once could both pass
the check. Locking the row the limit belongs to (the user for tags, the bookmark for its tags)
makes the second request wait until the first has committed.
"""

from sqlalchemy import delete, func, insert, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bookmark, BookmarkTag, RemovedTag, Tag, TagSource, User

# Copied to every new account as ordinary tags (owner, 2026-11-03): renamable and deletable.
STARTER_TAGS = (
    "Programming",
    "AI",
    "Design",
    "Data",
    "Business",
    "Science",
    "Health",
    "Cooking",
    "Travel",
    "News",
)
MAX_NAME = 30
MAX_PER_BOOKMARK = 5
MAX_PER_USER = 50  # the starter tags count


class TagError(Exception):
    """A rule a change would break. `code` is what the API sends, for the app to word."""

    code = "tag_error"


class NameTaken(TagError):
    code = "tag_name_taken"


class TooManyTags(TagError):
    code = "tag_limit"  # the account has MAX_PER_USER tags


class BookmarkFull(TagError):
    code = "bookmark_tag_limit"  # the bookmark has MAX_PER_BOOKMARK tags


class SameTag(TagError):
    code = "tag_merge_same"


def clean_name(name: str) -> str:
    """Trimmed, with runs of spaces made one ("  Web   design " → "Web design")."""
    return " ".join(name.split())


def add_starter_tags(session: AsyncSession, user: User) -> None:
    """For a new account, saved with it (migration 0012 did the same for older accounts)."""
    session.add_all(Tag(user=user, name=name) for name in STARTER_TAGS)


async def with_counts(session: AsyncSession, user_id: int) -> list[tuple[Tag, int]]:
    """Every tag the user has, with how many bookmarks have it, most used first."""
    in_use = (
        select(BookmarkTag.tag_id, func.count().label("n"))
        .join(Bookmark, Bookmark.id == BookmarkTag.bookmark_id)
        .where(Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None))
        .group_by(BookmarkTag.tag_id)
        .subquery()
    )
    count = func.coalesce(in_use.c.n, 0)
    rows = await session.execute(
        select(Tag, count)
        .outerjoin(in_use, in_use.c.tag_id == Tag.id)
        .where(Tag.user_id == user_id)
        .order_by(count.desc(), func.lower(Tag.name))
    )
    return [(tag, n) for tag, n in rows.all()]


async def own_tag(session: AsyncSession, user_id: int, tag_id: int) -> Tag | None:
    return await session.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))


async def _by_name(session: AsyncSession, user_id: int, name: str) -> Tag | None:
    return await session.scalar(
        select(Tag).where(Tag.user_id == user_id, func.lower(Tag.name) == name.lower())
    )


async def _lock_user(session: AsyncSession, user_id: int) -> None:
    await session.execute(select(User.id).where(User.id == user_id).with_for_update())


async def create(session: AsyncSession, user_id: int, name: str) -> Tag:
    """A new tag ("+ New tag"). NameTaken if one already has that name."""
    name = clean_name(name)
    await _lock_user(session, user_id)
    if await _by_name(session, user_id, name):
        raise NameTaken
    return await _insert(session, user_id, name)


async def find_or_create(session: AsyncSession, user_id: int, name: str) -> Tag:
    """The tag with this name, made if there isn't one (the detail panel's Add tag box)."""
    name = clean_name(name)
    await _lock_user(session, user_id)
    return await _by_name(session, user_id, name) or await _insert(session, user_id, name)


async def _insert(session: AsyncSession, user_id: int, name: str) -> Tag:
    total = await session.scalar(select(func.count()).where(Tag.user_id == user_id))
    if total >= MAX_PER_USER:
        raise TooManyTags
    tag = Tag(user_id=user_id, name=name)
    session.add(tag)
    await session.flush()  # gives the tag its id
    return tag


async def rename(session: AsyncSession, tag: Tag, name: str) -> Tag:
    """Another tag already called that: NameTaken (the app suggests Merge instead).
    Changing only the case of a tag's own name ("ai" → "AI") is fine."""
    name = clean_name(name)
    other = await _by_name(session, tag.user_id, name)
    if other is not None and other.id != tag.id:
        raise NameTaken
    tag.name = name
    return tag


async def merge(session: AsyncSession, tag: Tag, into: Tag) -> Tag:
    """Every bookmark with `tag` gets `into` (if it hasn't already), then `tag` is deleted.

    A bookmark never ends up with more tags than before, so the 5-tag limit can't be broken.
    """
    if tag.id == into.id:
        raise SameTag
    has_into = select(BookmarkTag.bookmark_id).where(BookmarkTag.tag_id == into.id)
    await session.execute(
        insert(BookmarkTag).from_select(
            ["bookmark_id", "tag_id", "source"],
            select(BookmarkTag.bookmark_id, literal(into.id), BookmarkTag.source).where(
                BookmarkTag.tag_id == tag.id, BookmarkTag.bookmark_id.not_in(has_into)
            ),
        )
    )
    await session.delete(tag)  # its bookmark_tags and removed_tags rows go with it (CASCADE)
    return into


async def _lock_bookmark(session: AsyncSession, bookmark_id: int) -> None:
    await session.execute(select(Bookmark.id).where(Bookmark.id == bookmark_id).with_for_update())


async def _tag_ids(session: AsyncSession, bookmark_id: int) -> set[int]:
    rows = await session.scalars(
        select(BookmarkTag.tag_id).where(BookmarkTag.bookmark_id == bookmark_id)
    )
    return set(rows)


async def add(
    session: AsyncSession, bookmark: Bookmark, tag: Tag, source: TagSource = TagSource.user
) -> bool:
    """Put `tag` on `bookmark`: True if added, False if it was already there.

    BookmarkFull at MAX_PER_BOOKMARK. Adding by hand also forgets an earlier removal, so the
    user's own choice wins over the "never re-add" rule.
    """
    await _lock_bookmark(session, bookmark.id)
    current = await _tag_ids(session, bookmark.id)
    if tag.id in current:
        return False
    if len(current) >= MAX_PER_BOOKMARK:
        raise BookmarkFull
    session.add(BookmarkTag(bookmark_id=bookmark.id, tag_id=tag.id, source=source))
    if source == TagSource.user:
        await session.execute(
            delete(RemovedTag).where(
                RemovedTag.bookmark_id == bookmark.id, RemovedTag.tag_id == tag.id
            )
        )
    return True


async def remove(session: AsyncSession, bookmark_id: int, tag_id: int) -> bool:
    """Take a tag off a bookmark and remember it, so the AI doesn't add it again."""
    gone = await session.execute(
        delete(BookmarkTag).where(
            BookmarkTag.bookmark_id == bookmark_id, BookmarkTag.tag_id == tag_id
        )
    )
    if not gone.rowcount:
        return False
    already = await session.get(RemovedTag, (bookmark_id, tag_id))
    if already is None:
        session.add(RemovedTag(bookmark_id=bookmark_id, tag_id=tag_id))
    return True


async def add_to_many(
    session: AsyncSession, tag: Tag, bookmarks: list[Bookmark]
) -> tuple[int, int]:
    """Select mode's Add tag: (added, skipped because the bookmark already had 5 tags).
    Bookmarks that already have the tag count as neither."""
    added = skipped = 0
    for bookmark in bookmarks:
        try:
            added += await add(session, bookmark, tag)
        except BookmarkFull:
            skipped += 1
    return added, skipped


async def remove_from_many(session: AsyncSession, tag: Tag, bookmark_ids: list[int]) -> int:
    """Select mode's Remove tag: how many bookmarks had it."""
    removed = 0
    for bookmark_id in bookmark_ids:
        removed += await remove(session, bookmark_id, tag.id)
    return removed
