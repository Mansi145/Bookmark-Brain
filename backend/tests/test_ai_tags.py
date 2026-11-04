"""AI tags: when a summary is made, the AI adds up to 2 of the user's own tags (Phase 5).

The model is a fake that returns a fixed TagChoice, so no test calls a real model.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from sqlalchemy import select

from app import worker
from app.ai import llm
from app.ai.chains import TagChoice
from app.models import Bookmark, BookmarkTag, Job, JobStatus, RemovedTag, Tag, TagSource
from tests.conftest import TestSession
from tests.test_search import save
from tests.test_sync import CHROME, item, sync

NOW = datetime.now(UTC)


class FakeTagger:
    """Stands in for llm.get_structured_model(TagChoice): answers `picks`, records prompts."""

    def __init__(self):
        self.picks: list[str] = []
        self.prompts: list[str] = []
        self.error: Exception | None = None

    def __call__(self, schema):
        assert schema is TagChoice
        return RunnableLambda(self._answer)

    async def _answer(self, messages):
        self.prompts.append(messages[-1].content)
        if self.error:
            raise self.error
        raw = AIMessage(content="", response_metadata={"model_name": "fake"})
        return {"raw": raw, "parsed": TagChoice(tags=self.picks), "parsing_error": None}


@pytest.fixture
def tagger(monkeypatch) -> FakeTagger:
    fake = FakeTagger()
    monkeypatch.setattr(llm, "get_structured_model", fake)
    return fake


async def summarised(user, title="Postgres indexes", **fields) -> int:
    return await save(
        user,
        title,
        summary="How B-tree and GIN indexes speed up queries.",
        summary_status="done",
        summarised_at=NOW,
        key_points=["B-tree is the default."],
        **fields,
    )


async def make_tags(user, *names) -> dict[str, int]:
    async with TestSession() as session:
        tags = [Tag(user_id=user.id, name=name) for name in names]
        session.add_all(tags)
        await session.commit()
        return {t.name: t.id for t in tags}


async def tag_job(bookmark_id: int) -> None:
    async with TestSession() as session:
        await worker.enqueue(session, "tag_bookmark", [{"bookmark_id": bookmark_id}])
        await session.commit()


async def run_jobs() -> None:
    async with httpx.AsyncClient() as http:
        while await worker.run_once(TestSession, http):
            pass


async def tags_on(bookmark_id: int) -> dict[str, TagSource]:
    async with TestSession() as session:
        rows = await session.execute(
            select(Tag.name, BookmarkTag.source)
            .join(BookmarkTag, BookmarkTag.tag_id == Tag.id)
            .where(BookmarkTag.bookmark_id == bookmark_id)
        )
        return dict(rows.all())


async def test_the_ai_adds_up_to_2_of_the_users_own_tags(user, tagger):
    bookmark = await summarised(user)
    await make_tags(user, "Databases", "Performance", "Cooking")
    tagger.picks = ["databases", "Performance", "Made up", "Cooking"]  # any case; never invents

    await tag_job(bookmark)
    await run_jobs()

    assert await tags_on(bookmark) == {"Databases": TagSource.ai, "Performance": TagSource.ai}
    # The model saw the user's tags and the summary, not the page.
    assert "- Cooking" in tagger.prompts[0] and "<article>" in tagger.prompts[0]


async def test_it_runs_once_per_summary(user, tagger):
    bookmark = await summarised(user)
    await make_tags(user, "Databases")
    tagger.picks = ["Databases"]
    await tag_job(bookmark)
    await run_jobs()

    await tag_job(bookmark)  # e.g. a second sync
    await run_jobs()
    assert len(tagger.prompts) == 1

    # A new summary (Re-summarise) is a new chance, for the tags not on it yet.
    await make_tags(user, "Indexing")
    async with TestSession() as session:
        (await session.get(Bookmark, bookmark)).document.summarised_at = NOW + timedelta(hours=1)
        await session.commit()
    await tag_job(bookmark)
    await run_jobs()
    assert len(tagger.prompts) == 2 and "- Indexing" in tagger.prompts[1]


async def test_it_never_re_adds_a_removed_tag_or_goes_past_the_limits(user, tagger):
    bookmark = await summarised(user)
    ids = await make_tags(user, "Removed", "One", "Two", "Three", "Four", "Fifth")
    async with TestSession() as session:
        session.add(RemovedTag(bookmark_id=bookmark, tag_id=ids["Removed"]))
        for name in ("One", "Two", "Three", "Four"):
            session.add(BookmarkTag(bookmark_id=bookmark, tag_id=ids[name], source=TagSource.user))
        await session.commit()
    tagger.picks = ["Removed", "Fifth"]

    await tag_job(bookmark)
    await run_jobs()

    assert "Removed" not in tagger.prompts[0]  # it isn't even offered
    tags = await tags_on(bookmark)
    assert len(tags) == 5 and tags["Fifth"] == TagSource.ai


async def test_a_bookmark_at_5_tags_costs_no_model_call(user, tagger):
    bookmark = await summarised(user)
    ids = await make_tags(user, "A", "B", "C", "D", "E", "F")
    async with TestSession() as session:
        for name in "ABCDE":
            session.add(BookmarkTag(bookmark_id=bookmark, tag_id=ids[name], source=TagSource.user))
        await session.commit()

    await tag_job(bookmark)
    await run_jobs()
    assert tagger.prompts == []


async def test_model_failures_are_retried_by_the_queue(user, tagger):
    bookmark = await summarised(user)
    await make_tags(user, "Databases")
    tagger.error = RuntimeError("every model is busy")

    await tag_job(bookmark)
    await run_jobs()

    async with TestSession() as session:
        job = await session.scalar(select(Job).where(Job.kind == "tag_bookmark"))
        assert job.status == JobStatus.queued and job.attempts == 1  # back in 30 s
        assert (await session.get(Bookmark, bookmark)).ai_tagged_at is None


async def test_syncing_a_page_someone_already_summarised_queues_tags(client, user, tagger):
    sync(client, CHROME, [item("1", "http://93.184.216.34/post", "Saved")], full=True)
    async with TestSession() as session:
        bookmark = await session.scalar(select(Bookmark))
        bookmark.document.summary_status = "done"
        bookmark.document.summary = "A summary someone made."
        await session.commit()

    sync(client, CHROME, [item("1", "http://93.184.216.34/post", "Saved")], full=True)

    async with TestSession() as session:
        kinds = (await session.scalars(select(Job.kind))).all()
    assert kinds.count("tag_bookmark") == 1
