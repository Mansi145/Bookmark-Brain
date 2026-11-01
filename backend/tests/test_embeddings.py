"""Meaning and keyword search data: which text each page is embedded from, the embed_pages job
(batches, rate limits, re-embedding after a summary) and the keyword-search column.

The embedding model is faked (conftest's FakeEmbedder), so no test calls Gemini.
"""

import itertools

from sqlalchemy import func, select
from sqlalchemy.orm import undefer

from app import worker
from app.ai import llm
from app.ai.embedding import MAX_PAGE_CHARS, embedding_text
from app.models import EMBEDDING_DIMENSIONS, Document, DocumentStatus, Job, JobStatus
from tests.conftest import TestSession
from tests.test_fetch_page import ARTICLE, HOST, html, run_all, serve
from tests.test_summaries import FakeModel, summarise, synced_article
from tests.test_sync import CHROME, item, sync

_urls = itertools.count()


def page(**fields) -> Document:
    """A document in memory, for the embedding_text rules."""
    defaults = {"url": f"{HOST}/p", "site": "example.com", "status": DocumentStatus.fetched}
    return Document(**(defaults | fields))


async def add_pages(*pages: dict) -> None:
    """Store documents waiting to be embedded, and queue the job, as fetch_page would."""
    async with TestSession() as session:
        for fields in pages:
            url = f"{HOST}/page-{next(_urls)}"
            session.add(page(url=url, normalized_url=url, **fields))
        await worker.queue_embedding(session)
        await session.commit()


async def documents() -> list[Document]:
    async with TestSession() as session:
        query = select(Document).options(undefer(Document.embedding)).order_by(Document.id)
        return list((await session.scalars(query)).all())


# --- Which text --------------------------------------------------------------------


def test_title_description_and_the_opening_of_the_page():
    text = embedding_text(
        page(title="Index Types", description="A tour.", content_text="q" * 20_000)
    )
    assert text.source == "page"
    assert text.text.startswith("title: Index Types | text: A tour.\nqqq")
    assert text.text.count("q") == MAX_PAGE_CHARS  # only the opening: more text blurs the vector


def test_the_summary_once_there_is_one():
    text = embedding_text(
        page(
            title="Index Types",
            content_text="The whole long page.",
            summary="PostgreSQL has several index types.",
            key_points=["B-tree is the default."],
            summary_status="done",
        )
    )
    assert text.source == "summary"
    assert text.text == (
        "title: Index Types | text: PostgreSQL has several index types.\nB-tree is the default."
    )


def test_sign_in_pages_get_no_embedding():
    sign_in = page(title="Sign in", access="login", status=DocumentStatus.failed)
    assert embedding_text(sign_in, saved_title="Gmail") is None


def test_the_saved_title_beats_a_fetched_placeholder():
    parked = page(title="Site en construction", status=DocumentStatus.failed)
    text = embedding_text(parked, saved_title="The Hacker Playbook 2")
    assert text.text == "title: The Hacker Playbook 2 | text: example.com"


def test_a_dead_page_forgets_what_the_live_page_said():
    dead = page(title="Old post", content_text="Stale words.", status=DocumentStatus.dead)
    text = embedding_text(dead)
    assert "Stale" not in text.text
    assert text.source == "metadata"


# --- The embed_pages job --------------------------------------------------------------


async def test_a_fetched_page_gets_embedded(client, fake_embedder):
    sync(client, CHROME, [item("1", HOST + "/post", "Saved title")], full=True)
    async with serve({"/post": html(ARTICLE)}) as http:
        await run_all(http)

    [doc] = await documents()
    assert len(doc.embedding) == EMBEDDING_DIMENSIONS
    assert doc.embedding_model == "fake-embedding"
    [[text]] = fake_embedder.calls
    assert text.startswith("title: ") and "A tour of index types." in text


async def test_many_pages_take_one_request_per_batch(fake_embedder):
    await add_pages(*({"title": f"Page {i}"} for i in range(worker.EMBED_BATCH + 10)))
    async with serve({}) as http:
        await run_all(http)

    assert [len(texts) for texts in fake_embedder.calls] == [worker.EMBED_BATCH, 10]
    assert all(doc.embedding is not None for doc in await documents())


async def test_one_queued_job_is_enough():
    async with TestSession() as session:
        for _ in range(3):
            await worker.queue_embedding(session)
        await session.commit()
        jobs = await session.scalar(select(func.count()).where(Job.kind == "embed_pages"))
    assert jobs == 1


async def test_sign_in_pages_are_skipped_not_left_waiting(fake_embedder):
    await add_pages({"title": "Sign in", "access": "login", "status": DocumentStatus.failed})
    async with serve({}) as http:
        await run_all(http)

    [doc] = await documents()
    assert doc.embedding is None
    assert doc.embedded_at is not None  # decided: it won't be picked up again
    assert fake_embedder.calls == []


async def test_a_rate_limit_waits_without_using_up_attempts(fake_embedder):
    await add_pages({"title": "Index Types"})
    fake_embedder.error = llm.RateLimited("429 RESOURCE_EXHAUSTED")
    async with serve({}) as http:
        assert await worker.run_once(TestSession, http)

    async with TestSession() as session:
        job = await session.scalar(select(Job).where(Job.kind == "embed_pages"))
        waited = await session.scalar(select(Job.run_after > func.now()).where(Job.id == job.id))
    assert job.status == JobStatus.queued
    assert job.attempts == 0
    assert waited
    [doc] = await documents()
    assert doc.embedded_at is None  # still waiting


async def test_a_new_summary_is_embedded_again(client, monkeypatch, fake_embedder):
    monkeypatch.setattr(llm, "get_structured_model", FakeModel())
    bookmark_id = await synced_article(client)
    summarise(client, bookmark_id)
    async with serve({}) as http:
        await run_all(http)

    assert len(fake_embedder.calls) == 2  # the page, then its summary
    assert fake_embedder.calls[1][0].endswith("B-tree is the default.\nGIN suits full-text search.")


# --- Keyword search ----------------------------------------------------------------


async def test_the_keyword_column_ranks_a_title_match_first():
    await add_pages(
        {"title": "Cooking at home", "content_text": "A side note about Django."},
        {"title": "Django file uploads", "content_text": "Storing files."},
    )
    query = func.websearch_to_tsquery("english", "django")
    async with TestSession() as session:
        titles = await session.scalars(
            select(Document.title)
            .where(Document.tsv.op("@@")(query))
            .order_by(func.ts_rank(Document.tsv, query).desc())
        )
        assert list(titles) == ["Django file uploads", "Cooking at home"]
