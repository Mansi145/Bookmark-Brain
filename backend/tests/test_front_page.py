"""Front-page summaries: a sync queues summaries for the newest bookmarks, within the daily limit
(owner, 2026-11-04)."""

import httpx
import pytest
from sqlalchemy import delete, select

from app.config import get_settings
from app.models import AiUsage, Document, DocumentStatus, Job
from app.services.usage import today
from tests.conftest import TestSession
from tests.test_fetch_page import run_all
from tests.test_summaries import fake_model  # noqa: F401  (the summary model, faked)
from tests.test_sync import CHROME, item, sync


@pytest.fixture(autouse=True)
def front_page(monkeypatch):
    monkeypatch.setattr(get_settings(), "front_page_summaries", 3)


def items(n: int) -> list[dict]:
    # Saved a day apart, so item 0 is the oldest and the last is the newest.
    return [
        item(str(i), f"http://93.184.216.34/page-{i}", added=f"2026-01-{i + 1:02d}T10:00:00Z")
        for i in range(n)
    ]


async def summary_jobs() -> list[dict]:
    async with TestSession() as session:
        jobs = await session.scalars(select(Job).where(Job.kind == "summarise").order_by(Job.id))
        return [j.payload for j in jobs]


async def used_today(user_id: int) -> int:
    async with TestSession() as session:
        usage = await session.get(AiUsage, (user_id, today()))
        return usage.summaries if usage else 0


async def test_a_sync_summarises_the_newest_bookmarks_and_counts_them(client, user):
    sync(client, CHROME, items(5), full=True)

    jobs = await summary_jobs()
    assert len(jobs) == 3
    async with TestSession() as session:
        working = await session.scalars(
            select(Document.url).where(Document.summary_status == "working").order_by(Document.url)
        )
        assert list(working) == [f"http://93.184.216.34/page-{i}" for i in (2, 3, 4)]
    assert await used_today(user.id) == 3
    assert all(j["auto"] and j["user_id"] == user.id for j in jobs)


async def test_the_next_sync_only_adds_what_is_new(client, user):
    sync(client, CHROME, items(3), full=True)
    sync(client, CHROME, items(4), full=True)  # one new bookmark, now the newest

    assert len(await summary_jobs()) == 4
    assert await used_today(user.id) == 4


async def test_at_the_daily_limit_the_rest_keep_their_button(client, user, monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_daily_limit_per_user", 2)
    sync(client, CHROME, items(3), full=True)

    assert len(await summary_jobs()) == 2  # no error, no dialog: the third just isn't queued


async def test_a_page_that_turns_out_dead_gives_its_use_back(client, user, fake_model):  # noqa: F811
    sync(client, CHROME, items(1), full=True)
    assert await used_today(user.id) == 1
    async with TestSession() as session:
        (await session.scalar(select(Document))).status = DocumentStatus.dead  # fetch found a 404
        await session.execute(delete(Job).where(Job.kind == "fetch_page"))
        await session.commit()

    async with httpx.AsyncClient() as http:
        await run_all(http)

    async with TestSession() as session:
        assert (await session.scalar(select(Document))).summary_status is None
    assert await used_today(user.id) == 0
    assert fake_model.prompts == []  # no summary was made
