"""See how search ranks your local bookmarks, and why (dev only).

For each query it runs the real search (app/services/search.py) on the local database and
prints the top results with, for each one:
- its place in the keyword list ("-" when not all the query's words are in it),
- its place in the meaning list and its cosine similarity (1.0 = same direction, 0 = unrelated),
- its merged score: 1.5 / (60 + keyword place) + 1 / (60 + meaning place).
Use it to judge the keyword weight and, later, a similarity cutoff. With gemini-embedding-2,
unrelated pages scored 0.45-0.64 on our bookmarks and real matches 0.68 and up.

Pages are embedded by the embed_pages job (the dev server's worker), so only the queries are
embedded here. That calls the real Gemini API (free tier), so it's a tool for us, never run by
the tests.

    cd backend
    uv run python -m scripts.explore_search "postgres indexes" "learning react"
    uv run python -m scripts.explore_search          # asks for queries one at a time
    uv run python -m scripts.explore_search --email you@example.com "react"
"""

import argparse
import asyncio

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Bookmark, Document, DocumentStatus, User
from app.services import search


async def pick_user(email: str | None) -> User:
    """The user with that email, else the one with the most bookmarks."""
    async with SessionLocal() as session:
        if email:
            user = await session.scalar(select(User).where(User.email == email))
        else:
            most = (
                select(Bookmark.user_id)
                .where(Bookmark.deleted_at.is_(None))
                .group_by(Bookmark.user_id)
                .order_by(func.count().desc())
                .limit(1)
                .scalar_subquery()
            )
            user = await session.scalar(select(User).where(User.id == most))
    if user is None:
        raise SystemExit("No such user in the local database. Sync some bookmarks first.")
    return user


async def coverage(user_id: int) -> str:
    """How many of the user's pages meaning search can see."""
    async with SessionLocal() as session:
        decided = Document.embedded_at.is_not(None)
        rows = await session.execute(
            select(
                func.count().filter(Document.embedding.is_not(None)),
                func.count().filter(decided, Document.embedding.is_(None)),
                func.count().filter(
                    Document.embedded_at.is_(None), Document.status != DocumentStatus.pending
                ),
            )
            .select_from(Bookmark)
            .join(Document, Document.id == Bookmark.document_id)
            .where(Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None))
        )
        embedded, skipped, waiting = rows.one()
    return (
        f"{embedded} pages embedded, {skipped} without one (sign-in pages), "
        f"{waiting} waiting for the embed_pages job"
    )


async def explain(user_id: int, q: str, top: int) -> None:
    async with SessionLocal() as session:
        vector = await search.query_embeddings.get(user_id, q)
        keyword_ids = await search.keyword_matches(session, user_id, q, [])
        meaning_ids = (
            [] if vector is None else await search.meaning_matches(session, user_id, vector, [])
        )
        scores = search.fusion_scores(keyword_ids, meaning_ids)
        ranked = search.fuse(keyword_ids, meaning_ids)[:top]
        similarity = {}
        if vector is not None:
            rows = await session.execute(
                select(Bookmark.id, 1 - Document.embedding.cosine_distance(vector))
                .join(Document, Document.id == Bookmark.document_id)
                .where(Bookmark.id.in_(ranked))
            )
            similarity = dict(rows.all())
        rows = await session.execute(
            select(Bookmark.id, Bookmark.title).where(Bookmark.id.in_(ranked))
        )
        titles = dict(rows.all())

    print(f"\n“{q}”  {len(keyword_ids)} keyword matches, {len(meaning_ids)} meaning candidates")
    if vector is None:
        print("  (couldn't embed the query: keyword matches only)")
    print("   #  keyword  meaning (similarity)  score   title")
    for place, bookmark_id in enumerate(ranked, start=1):
        keyword = str(keyword_ids.index(bookmark_id) + 1) if bookmark_id in keyword_ids else "-"
        meaning = "-"
        if bookmark_id in meaning_ids:
            meaning = f"{meaning_ids.index(bookmark_id) + 1} ({similarity[bookmark_id]:.3f})"
        print(
            f"  {place:>2}  {keyword:>7}  {meaning:>20}  {scores[bookmark_id]:.4f}"
            f"  {titles[bookmark_id][:60]}"
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("queries", nargs="*", help="queries to try (none: ask one at a time)")
    parser.add_argument("--email", help="whose bookmarks (default: the user with the most)")
    parser.add_argument("--top", type=int, default=search.RESULTS, help="results to show")
    args = parser.parse_args()

    user = await pick_user(args.email)
    print(f"Searching {user.email}'s bookmarks: {await coverage(user.id)}")
    queries = iter(args.queries) if args.queries else iter(lambda: input("\nQuery: ").strip(), "")
    for q in queries:
        await explain(user.id, q, args.top)


if __name__ == "__main__":
    asyncio.run(main())
