"""Try embeddings on your local bookmarks, to pick the similarity cutoff for search.

Embeds every bookmarked page in the local database (the same text the embed_page job will use,
see app/ai/embedding.py), then for each query prints the pages ranked by cosine similarity:
1.0 means the same direction (same meaning), around 0 means unrelated. Meaning search always
has a "nearest" page, even for a query nothing matches, so each row is marked with whether the
cutoff rule below would show it.

One fixed score can't be the cutoff: unrelated pages score anywhere from 0.45 to 0.64
depending on the query. What marks a real match is how far it stands above the rest, so the
rule needs both: a floor, and being close to that search's best match.

Vectors are cached in backend/.cache/embeddings.json (git-ignored), keyed by model and text, so
running it again only embeds pages that are new or changed. It calls the real Gemini API (free
tier), so it's a tool for us, never run by the tests.

    cd backend
    uv run python -m scripts.explore_embeddings "postgres indexes" "learning react"
    uv run python -m scripts.explore_embeddings          # asks for queries one at a time
"""

import argparse
import asyncio
import hashlib
import json
import math
import statistics
from pathlib import Path

from sqlalchemy import select

from app.ai import llm
from app.ai.embedding import embedding_text, saved_title
from app.config import get_settings
from app.db import SessionLocal
from app.models import EMBEDDING_DIMENSIONS, Bookmark, Document, DocumentStatus

CACHE = Path(__file__).resolve().parent.parent / ".cache" / "embeddings.json"
BATCH = 50  # texts per request (the API takes up to 100)
RETRY_WAIT_SECONDS = 60  # free tier: a rate limit counts per minute

# The cutoff rule being tried: a page is shown if it scores at least MIN_SIMILARITY and is
# within MAX_GAP_FROM_BEST of the search's best page.
MIN_SIMILARITY = 0.65
MAX_GAP_FROM_BEST = 0.07


async def load_pages() -> list[dict]:
    """Every page someone has bookmarked, with the text the embed_pages job would embed."""
    bookmarked = (
        select(Bookmark.id)
        .where(Bookmark.document_id == Document.id, Bookmark.deleted_at.is_(None))
        .exists()
    )
    query = (
        select(Document)
        .where(Document.status != DocumentStatus.pending, bookmarked)
        .order_by(Document.id)
    )
    pages = []
    async with SessionLocal() as session:
        for document in (await session.scalars(query)).all():
            title = await saved_title(session, document.id)
            text = embedding_text(document, saved_title=title)
            if text is None:
                print(f"Not embedded (sign-in page): {title}")
                continue
            shown = text.text.split(" | text: ")[0].removeprefix("title: ")  # what was embedded
            pages.append({"title": shown, "text": text.text, "source": text.source})
    return pages


def cache_key(text: str) -> str:
    model = f"{get_settings().gemini_embedding_model}/{EMBEDDING_DIMENSIONS}"
    return hashlib.sha256(f"{model}\n{text}".encode()).hexdigest()


def load_cache() -> dict[str, list[float]]:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def save_cache(cache: dict[str, list[float]]) -> None:
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache))


async def embed_missing(texts: list[str], cache: dict[str, list[float]]) -> None:
    """Embed the texts that aren't cached yet, a batch per request."""
    missing = [text for text in texts if cache_key(text) not in cache]
    if not missing:
        return
    embedder = llm.get_embedder()
    print(f"Embedding {len(missing)} new text(s) with {embedder.model}…")
    for start in range(0, len(missing), BATCH):
        batch = missing[start : start + BATCH]
        for attempt in range(3):
            try:
                vectors = await embedder.aembed_documents(batch)
                break
            except Exception as err:
                if attempt == 2:
                    raise
                print(f"  {err}\n  trying again in {RETRY_WAIT_SECONDS} s")
                await asyncio.sleep(RETRY_WAIT_SECONDS)
        for text, vector in zip(batch, vectors, strict=True):
            cache[cache_key(text)] = vector
        save_cache(cache)  # keep what we have if a later batch fails


async def embed_query(query: str, cache: dict[str, list[float]]) -> list[float]:
    """Queries are cached too, so trying the same one again is free."""
    key = cache_key("query: " + query)
    if key not in cache:
        cache[key] = await llm.get_embedder().aembed_query(query)
        save_cache(cache)
    return cache[key]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """How closely two vectors point the same way: the dot product divided by their lengths.

    gemini-embedding-2 returns vectors of length 1, so this is just the dot product, but
    dividing keeps it right for any model.
    """
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def show(query: str, query_vector: list[float], pages: list[dict], cache: dict, top: int):
    scored = sorted(
        ((cosine_similarity(query_vector, cache[cache_key(p["text"])]), p) for p in pages),
        key=lambda pair: pair[0],
        reverse=True,
    )
    best = scored[0][0]
    shown = [s >= MIN_SIMILARITY and s >= best - MAX_GAP_FROM_BEST for s, _ in scored]
    print(f"\n“{query}”  ({sum(shown)} shown)")
    for (score, page), is_shown in zip(scored[:top], shown, strict=False):
        mark = "shown " if is_shown else "hidden"
        print(f"  {score:.3f}  {mark}  {page['title'][:64]:<64}  ({page['source']})")
    scores = [score for score, _ in scored]
    print(
        f"  scores: best {scores[0]:.3f} · median {statistics.median(scores):.3f}"
        f" · worst {scores[-1]:.3f} over {len(scores)} pages"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("queries", nargs="*", help="queries to try (none: ask one at a time)")
    parser.add_argument("--top", type=int, default=15, help="pages to show per query")
    args = parser.parse_args()

    pages = await load_pages()
    if not pages:
        print("No fetched pages in the local database. Sync some bookmarks first.")
        return
    cache = load_cache()
    await embed_missing([page["text"] for page in pages], cache)
    sources = {s: sum(p["source"] == s for p in pages) for s in ("summary", "page", "metadata")}
    made_from = ", ".join(f"{n} {s}" for s, n in sources.items())
    print(f"{len(pages)} pages, embedded from: {made_from}")

    queries = iter(args.queries) if args.queries else iter(lambda: input("\nQuery: ").strip(), "")
    for query in queries:
        show(query, await embed_query(query, cache), pages, cache, args.top)


if __name__ == "__main__":
    asyncio.run(main())
