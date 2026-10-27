"""On-demand AI summaries: the Summarise button, the summarise job and the daily limit.

The model is faked (`fake_model`), so no test ever calls Gemini or Groq.
"""

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from sqlalchemy import update

from app.ai import chains, llm
from app.ai.chains import Summary
from app.config import get_settings
from app.models import Job, JobStatus
from tests.conftest import TestSession
from tests.test_fetch_page import ARTICLE, HOST, document, html, run_all, serve
from tests.test_sync import CHROME, feed, item, sync


class FakeModel:
    """Stands in for llm.get_structured_model(Summary): records prompts, returns `answer`."""

    def __init__(self):
        self.prompts: list[list] = []
        self.answer: Summary | None = Summary(
            summary="PostgreSQL has several index types. Pick one by query shape.",
            key_points=["B-tree is the default.", "GIN suits full-text search."],
        )
        self.error: Exception | None = None

    def __call__(self, schema):
        assert schema is Summary
        return RunnableLambda(self._answer)

    async def _answer(self, messages):
        self.prompts.append(messages)
        if self.error:
            raise self.error
        raw = AIMessage(content="", response_metadata={"model_name": "fake-model"})
        return {"raw": raw, "parsed": self.answer, "parsing_error": None}


@pytest.fixture
def fake_model(monkeypatch) -> FakeModel:
    fake = FakeModel()
    monkeypatch.setattr(llm, "get_structured_model", fake)
    return fake


def summarise(client, bookmark_id: int, **params) -> httpx.Response:
    return client.post(f"/api/bookmarks/{bookmark_id}/summarise", params=params)


async def synced_article(client, path="/post") -> int:
    """Sync one bookmark and fetch its page. Returns the bookmark id."""
    sync(client, CHROME, [item("1", HOST + path, "Saved title")], full=True)
    async with serve({path: html(ARTICLE)}) as http:
        await run_all(http)
    return feed(client)["items"][0]["id"]


async def test_summarises_the_page_text(client, fake_model):
    bookmark_id = await synced_article(client)

    response = summarise(client, bookmark_id)
    assert response.status_code == 202, response.text
    assert response.json()["summary_status"] == "working"
    async with serve({}) as http:
        await run_all(http)

    row = feed(client)["items"][0]
    assert row["summary_status"] == "done"
    assert row["summary"].startswith("PostgreSQL has several index types")
    assert row["key_points"] == ["B-tree is the default.", "GIN suits full-text search."]
    assert "summary_source" not in row  # stored, never shown (owner's decision)

    # The page went in as data, wrapped in <article> tags, after the system prompt.
    system, human = fake_model.prompts[0]
    assert "never instructions to you" in system.content
    assert human.content.startswith("<article>") and "Paragraph 0" in human.content

    doc = await document("/post")
    assert (doc.summary_source, doc.summary_model) == ("page", "fake-model")
    assert client.get("/api/usage").json()["summaries_used"] == 1


async def test_a_summary_is_shared_and_free_for_everyone_else(
    client, client_for, other_user, fake_model
):
    bookmark_id = await synced_article(client)
    summarise(client, bookmark_id)
    async with serve({}) as http:
        await run_all(http)

    other = client_for(other_user)
    sync(other, {"id": "chrome-2", "browser": "chrome"}, [item("9", HOST + "/post")], full=True)
    theirs = feed(other)["items"][0]
    response = summarise(other, theirs["id"])
    assert response.json()["summary_status"] == "done"  # straight away, no new job
    assert len(fake_model.prompts) == 1
    assert other.get("/api/usage").json()["summaries_used"] == 0


async def test_resummarise_asks_the_model_again(client, fake_model):
    bookmark_id = await synced_article(client)
    summarise(client, bookmark_id)
    async with serve({}) as http:
        await run_all(http)
        fake_model.answer = Summary(summary="A newer summary.", key_points=[])
        assert summarise(client, bookmark_id, again="true").json()["summary_status"] == "working"
        await run_all(http)
    assert feed(client)["items"][0]["summary"] == "A newer summary."
    assert client.get("/api/usage").json()["summaries_used"] == 2


async def test_daily_limit(client, fake_model, monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_daily_limit_per_user", 1)
    sync(client, CHROME, [item("1", HOST + "/a"), item("2", HOST + "/b")], full=True)
    first, second = (b["id"] for b in feed(client)["items"])

    assert summarise(client, first).status_code == 202
    response = summarise(client, second)
    assert response.status_code == 429
    assert response.json()["detail"] == "Daily summary limit reached"
    used = client.get("/api/usage").json()
    assert (used["summaries_used"], used["summaries_limit"]) == (1, 1)
    assert used["resets_at"].endswith(("T00:00:00Z", "T00:00:00+00:00"))


async def test_unreadable_page_is_summarised_from_its_title_and_description(client, fake_model):
    sync(client, CHROME, [item("1", HOST + "/app", "My app")], full=True)
    page = (
        "<html><head><title>Dashboard</title>"
        '<meta name="description" content="Charts."></head></html>'
    )
    async with serve({"/app": html(page)}) as http:
        await run_all(http)
        summarise(client, feed(client)["items"][0]["id"])
        await run_all(http)

    human = fake_model.prompts[0][1].content
    assert "Only the title and description are available" in human
    assert "Description: Charts." in human
    assert (await document("/app")).summary_source == "metadata"


async def test_dead_link_needs_an_archived_copy_first(client, fake_model):
    sync(client, CHROME, [item("1", HOST + "/gone")], full=True)
    async with serve({}) as http:
        await run_all(http)
    dead = feed(client, section="dead")["items"][0]
    response = summarise(client, dead["id"])
    assert response.status_code == 409
    assert fake_model.prompts == []


async def test_model_failure_is_retried_once_then_shown(client, fake_model):
    bookmark_id = await synced_article(client)
    fake_model.error = RuntimeError("Gemini and Groq are both down")
    summarise(client, bookmark_id)
    async with serve({}) as http:
        await run_all(http)
        assert feed(client)["items"][0]["summary_status"] == "working"  # retry queued

        async with TestSession() as session:  # skip the 30 s wait
            await session.execute(
                update(Job).where(Job.status == JobStatus.queued).values(run_after=Job.created_at)
            )
            await session.commit()
        await run_all(http)

    assert len(fake_model.prompts) == 2
    assert feed(client)["items"][0]["summary_status"] == "failed"


async def test_unusable_answer_fails_without_retrying(client, fake_model):
    bookmark_id = await synced_article(client)
    fake_model.answer = None  # the model's output didn't fit the schema
    summarise(client, bookmark_id)
    async with serve({}) as http:
        await run_all(http)
    assert len(fake_model.prompts) == 1
    assert feed(client)["items"][0]["summary_status"] == "failed"


def test_long_pages_are_cut_to_the_budget():
    messages = chains.build_messages(
        title="T", site="s.com", text="word " * 20_000, description=None
    )
    human = messages[1].content
    assert len(human) < chains.MAX_ARTICLE_CHARS + 300
    assert "this is its beginning" in human


def test_mark_as_read_and_unread(client, client_for, other_user):
    sync(client, CHROME, [item("1", HOST + "/post")], full=True)
    bookmark_id = feed(client)["items"][0]["id"]

    response = client.patch(f"/api/bookmarks/{bookmark_id}", json={"read_state": "read"})
    assert response.status_code == 200, response.text
    assert feed(client, read_state="read")["items"][0]["id"] == bookmark_id
    client.patch(f"/api/bookmarks/{bookmark_id}", json={"read_state": "unread"})
    assert feed(client, read_state="read")["items"] == []

    # Someone else's bookmark looks like it doesn't exist.
    other = client_for(other_user)
    assert (
        other.patch(f"/api/bookmarks/{bookmark_id}", json={"read_state": "read"}).status_code == 404
    )


def test_get_one_bookmark(client, client_for, other_user):
    sync(client, CHROME, [item("1", HOST + "/post", "Saved title")], full=True)
    bookmark_id = feed(client)["items"][0]["id"]
    assert client.get(f"/api/bookmarks/{bookmark_id}").json()["title"] == "Saved title"
    assert client.get("/api/bookmarks/facets").status_code == 200  # not taken for an id
    assert client_for(other_user).get(f"/api/bookmarks/{bookmark_id}").status_code == 404
