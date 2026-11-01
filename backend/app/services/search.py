"""Hybrid search over one user's bookmarks: keyword matches and meaning matches, merged.

1. Keyword matches: Postgres full-text search over the page's words (documents.tsv: title,
   then description, summary and key points, then page text) plus the user's own words for it:
   the title they saved it under and their folder names. Words are stemmed ("uploads" finds
   "uploading"), and ts_rank puts a title match first.
2. Meaning matches: the query's embedding against each page's (cosine distance). Finds pages
   about the same thing in other words ("waterproof pants" finds "water repellent trousers").
3. Merge: weighted Reciprocal Rank Fusion (fuse). Only each page's place in each list counts,
   because the two lists' scores aren't on the same scale.

When the query can't be embedded (the model is down or rate limited, or this user searched a
lot in the last minute), the keyword matches come back alone. They look like any other results:
search never says how it matched (owner). Meaning matches have no cutoff yet (owner: later), so
they fill every slot.
"""

import asyncio
import logging
import time
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass

from sqlalchemy import ColumnElement, func, literal_column, select, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import llm
from app.models import Bookmark, BookmarkSource, Document

log = logging.getLogger(__name__)

RESULTS = 10  # shown (owner); the page says "Top 10 matches" when more matched
CANDIDATES = 50  # taken from each list before merging

# Reciprocal Rank Fusion: a page scores weight / (RRF_K + its place) in each list it's in.
# 60 is the original paper's constant. It flattens the gap between 1st and 2nd place, so being
# in both lists counts for more than topping one. Keyword matches weigh more (owner: a page
# with your words in it is a surer match than one that's only close in meaning).
RRF_K = 60
KEYWORD_WEIGHT = 1.5
MEANING_WEIGHT = 1.0

# Around matched words in a result's `highlighted` text. Control characters never occur in
# page text, so the frontend can split on them instead of rendering HTML from a web page.
MARK_START, MARK_END = "\x02", "\x03"


@dataclass
class Found:
    bookmark_ids: list[int]  # best first, at most RESULTS
    more: bool  # more than RESULTS matched
    highlighted: dict[int, str]  # bookmark id -> its summary (or description), words marked


async def search(
    session: AsyncSession, user_id: int, q: str, filters: list[ColumnElement[bool]]
) -> Found:
    """The user's bookmarks that best match `q`, narrowed by `filters` (conditions on Bookmark)."""
    vector = await query_embeddings.get(user_id, q)
    keyword_ids = await keyword_matches(session, user_id, q, filters)
    meaning_ids = [] if vector is None else await meaning_matches(session, user_id, vector, filters)
    ranked = fuse(keyword_ids, meaning_ids)
    top = ranked[:RESULTS]
    return Found(
        bookmark_ids=top,
        more=len(ranked) > RESULTS,
        highlighted=await highlights(session, top, q),
    )


def fuse(keyword_ids: list[int], meaning_ids: list[int]) -> list[int]:
    """Merge two ranked lists of bookmark ids (best first) into one, best first."""
    scores = fusion_scores(keyword_ids, meaning_ids)
    return sorted(scores, key=lambda bookmark_id: scores[bookmark_id], reverse=True)


def fusion_scores(keyword_ids: list[int], meaning_ids: list[int]) -> dict[int, float]:
    """Each page's merged score: 1.5 / (60 + keyword place) + 1 / (60 + meaning place).

    A page missing from a list gets nothing for it. E.g. 1st in both: 1.5/61 + 1/61 = 0.041;
    1st by keyword only: 0.025.
    """
    scores: dict[int, float] = defaultdict(float)
    for weight, ids in ((KEYWORD_WEIGHT, keyword_ids), (MEANING_WEIGHT, meaning_ids)):
        for place, bookmark_id in enumerate(ids, start=1):
            scores[bookmark_id] += weight / (RRF_K + place)
    return dict(scores)


def _mine(user_id: int) -> list[ColumnElement[bool]]:
    return [Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None)]


def _words():
    """The page's words plus the user's own words for it.

    The title they saved it under counts like the page's title (weight A); folder names count
    like a summary (B). The browser's root folder ("Bookmarks bar", "Other bookmarks") is left
    out, since it would match nearly every bookmark.
    """
    folders = (
        select(
            func.string_agg(func.regexp_replace(BookmarkSource.folder_path, "^[^/]*/?", ""), " ")
        )
        .where(BookmarkSource.bookmark_id == Bookmark.id)
        .scalar_subquery()
    )
    # setweight wants Postgres's one-byte "char" type, so the letters go into the SQL as is.
    weight_a, weight_b = literal_column("'A'"), literal_column("'B'")
    own = func.setweight(func.to_tsvector("english", Bookmark.title), weight_a).op(
        "||", return_type=TSVECTOR
    )(func.setweight(func.to_tsvector("english", func.coalesce(folders, "")), weight_b))
    return Document.tsv.op("||", return_type=TSVECTOR)(own)


async def keyword_matches(
    session: AsyncSession, user_id: int, q: str, filters: list[ColumnElement[bool]]
) -> list[int]:
    """Bookmark ids whose words contain every word of `q`, best first.

    websearch_to_tsquery reads `q` like a search engine: all words must appear (stemmed),
    "quoted phrases" stay together and -word excludes. Joining the user's own words means the
    GIN index on documents.tsv isn't used, which is fine: a user has hundreds or thousands of
    bookmarks, not millions.
    """
    words = _words()
    query = func.websearch_to_tsquery("english", q)
    rows = await session.scalars(
        select(Bookmark.id)
        .join(Document, Document.id == Bookmark.document_id)
        .where(*_mine(user_id), *filters, words.op("@@")(query))
        .order_by(func.ts_rank(words, query).desc(), Bookmark.id.desc())
        .limit(CANDIDATES)
    )
    return list(rows)


async def meaning_matches(
    session: AsyncSession, user_id: int, vector: list[float], filters: list[ColumnElement[bool]]
) -> list[int]:
    """Bookmark ids whose page embedding is closest to the query's, closest first."""
    # The HNSW index walks towards the nearest pages of *all* users, keeping only this user's
    # afterwards, and by default stops after 40 candidates (hnsw.ef_search): a user whose pages
    # aren't among them would get nothing. Iterative scans (pgvector 0.8) keep walking, in
    # order, until there are enough. SET LOCAL lasts until this request's transaction ends.
    await session.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
    rows = await session.scalars(
        select(Bookmark.id)
        .join(Document, Document.id == Bookmark.document_id)
        .where(*_mine(user_id), *filters, Document.embedding.is_not(None))
        .order_by(Document.embedding.cosine_distance(vector))
        .limit(CANDIDATES)
    )
    return list(rows)


async def highlights(session: AsyncSession, bookmark_ids: list[int], q: str) -> dict[int, str]:
    """For each result whose shown text (summary, else description) contains query words: that
    text with each matched word between MARK_START and MARK_END (ts_headline knows the stems)."""
    if not bookmark_ids:
        return {}
    shown = func.coalesce(Document.summary, Document.description)
    marked = func.ts_headline(
        "english",
        shown,
        func.websearch_to_tsquery("english", q),
        f"StartSel={MARK_START}, StopSel={MARK_END}, HighlightAll=true",
    )
    rows = await session.execute(
        select(Bookmark.id, marked)
        .join(Document, Document.id == Bookmark.document_id)
        .where(Bookmark.id.in_(bookmark_ids), shown.is_not(None))
    )
    return {bookmark_id: text for bookmark_id, text in rows if MARK_START in text}


class QueryEmbeddings:
    """Embeds search queries, with a short-lived cache and a per-user throttle.

    Searching as you type sends a query after every pause, so the same words come back often
    (typing, deleting, typing again), and the cache answers those for free. The throttle keeps
    one person from using up the shared free quota: over PER_MINUTE new queries, a search waits
    up to MAX_WAIT_SECONDS for a free slot, then gets keyword matches only. Nobody sees an error
    for it (owner). Kept in memory, which is enough for the free tier's single API instance.
    """

    TTL_SECONDS = 300
    MAX_CACHED = 1_000
    PER_MINUTE = 20
    MAX_WAIT_SECONDS = 2.0

    def __init__(self) -> None:
        self._cache: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()
        self._calls: dict[int, deque[float]] = defaultdict(deque)  # user -> recent call times

    async def get(self, user_id: int, q: str) -> list[float] | None:
        """The query's vector, or None when it can't be had right now (search by keyword)."""
        key = " ".join(q.lower().split())
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < self.TTL_SECONDS:
            self._cache.move_to_end(key)
            return cached[1]
        if not await self._take_slot(user_id):
            return None
        try:
            vector = await llm.get_embedder().aembed_query(key)
        except Exception as err:  # down, rate limited, no key: search still works by keyword
            log.warning("Couldn't embed a search query: %s", err)
            return None
        self._cache[key] = (time.monotonic(), vector)
        self._cache.move_to_end(key)
        if len(self._cache) > self.MAX_CACHED:
            self._cache.popitem(last=False)  # the least recently used
        return vector

    async def _take_slot(self, user_id: int) -> bool:
        calls = self._calls[user_id]
        now = time.monotonic()
        while calls and now - calls[0] >= 60:
            calls.popleft()
        if len(calls) >= self.PER_MINUTE:
            wait = 60 - (now - calls[0])
            if wait > self.MAX_WAIT_SECONDS:
                return False
            await asyncio.sleep(wait)
            calls.popleft()
        calls.append(time.monotonic())
        return True


query_embeddings = QueryEmbeddings()
