"""The chat agent's tools: how it looks things up in the user's bookmarks.

A tool is an async function with LangChain's @tool decorator. Its name, typed arguments and
docstring become a schema that's sent to the model with every request (llm.get_tool_model), so
**the docstring is what the model reads** to decide when and how to use it.

Every tool is scoped to one user. The user id comes from the run's config, which our code sets
from the session cookie, never from a tool argument: arguments are written by the model, and a
page it has read could talk it into asking for someone else's bookmarks. A parameter typed
`RunnableConfig` is filled in by LangChain and left out of the schema the model sees.

Results are compact JSON with capped sizes: whatever a tool returns is sent back to the model on
every later call, and free tiers count each token.
"""

import json
from collections.abc import Sequence

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import SessionLocal
from app.models import Bookmark, ReadState
from app.services import search

SNIPPET_CHARS = 300  # of each search result's summary
PAGE_CHARS = 4_000  # of a page's text in read_bookmark: about 1,000 tokens


@tool
async def search_bookmarks(query: str, config: RunnableConfig) -> str:
    """Search the user's saved bookmarks by keywords and by meaning.

    Returns up to 10 bookmarks, best match first, each with its id, title, site, the day it was
    saved, whether the user has read it, and a short summary. Use it first for any question
    about what the user saved.

    Keep queries short: a keyword match needs every word of the query to be in the page, so
    search one topic at a time with one or two distinctive words ("python", "react hooks"), not
    a sentence, and search again for each other topic.
    """
    user_id, sessions = _context(config)
    async with sessions() as session:
        found = await search.search(session, user_id, query, [])
        bookmarks = await _bookmarks(session, user_id, found.bookmark_ids)
    return _json([{**_card(b), "summary": _snippet(b)} for b in bookmarks])


@tool
async def read_bookmark(bookmark_id: int, config: RunnableConfig) -> str:
    """Read one of the user's bookmarks: its address, summary, key points and the start of the
    page's text.

    Use it when a search result's summary isn't enough to answer. `bookmark_id` is an id that
    search_bookmarks returned.
    """
    user_id, sessions = _context(config)
    async with sessions() as session:
        bookmarks = await _bookmarks(session, user_id, [bookmark_id])
    if not bookmarks:
        return _json({"error": "No bookmark with that id."})
    bookmark = bookmarks[0]
    document = bookmark.document
    return _json(
        {
            **_card(bookmark),
            "url": document.url,
            "description": document.description,
            "summary": document.summary,
            "key_points": document.key_points or [],
            "text": (document.content_text or "")[:PAGE_CHARS],
        }
    )


TOOLS = [search_bookmarks, read_bookmark]


def _context(config: RunnableConfig) -> tuple[int, async_sessionmaker[AsyncSession]]:
    """Who is asking, and how to reach the database (tests pass their own sessions).

    Each tool call opens its own session: an agent can run several calls at once, and one
    session can't be shared between them.
    """
    configurable = config.get("configurable") or {}
    return configurable["user_id"], configurable.get("sessions", SessionLocal)


async def _bookmarks(session: AsyncSession, user_id: int, ids: Sequence[int]) -> list[Bookmark]:
    """The user's bookmarks with these ids, in the same order; others' ids are skipped."""
    rows = await session.scalars(
        select(Bookmark).where(
            Bookmark.id.in_(ids), Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None)
        )
    )
    by_id = {bookmark.id: bookmark for bookmark in rows}
    return [by_id[i] for i in ids if i in by_id]


def _card(bookmark: Bookmark) -> dict:
    return {
        "id": bookmark.id,
        "title": bookmark.title,
        "site": bookmark.document.site,
        "saved": bookmark.added_at.date().isoformat(),
        "read": bookmark.read_state == ReadState.read,
    }


def _snippet(bookmark: Bookmark) -> str:
    text = bookmark.document.summary or bookmark.document.description or ""
    return text if len(text) <= SNIPPET_CHARS else text[:SNIPPET_CHARS].rstrip() + "…"


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)
