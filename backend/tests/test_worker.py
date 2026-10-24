"""The job queue: claiming, success, retries with back-off, giving up, stale jobs."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select, update

from app import worker
from app.models import Job, JobStatus
from tests.conftest import TestSession

HTTP = httpx.AsyncClient()  # handlers here never use it


@pytest.fixture
def handlers(monkeypatch):
    """Swap in test handlers: {"kind": async handler}."""
    registry: dict = {}
    monkeypatch.setattr(worker, "HANDLERS", registry)
    return registry


async def add_job(kind="test", payload=None) -> int:
    async with TestSession() as session:
        await worker.enqueue(session, kind, [payload or {"n": 1}])
        await session.commit()
        return await session.scalar(select(Job.id).order_by(Job.id.desc()).limit(1))


async def get_job(job_id: int) -> Job:
    async with TestSession() as session:
        return await session.get(Job, job_id)


async def run_once() -> bool:
    return await worker.run_once(TestSession, HTTP)


async def test_nothing_to_do():
    assert await run_once() is False


async def test_successful_job_is_done(handlers):
    seen = []

    async def handler(session, job, http):
        seen.append(job.payload)

    handlers["test"] = handler
    job_id = await add_job(payload={"document_id": 7})

    assert await run_once() is True
    job = await get_job(job_id)
    assert seen == [{"document_id": 7}]
    assert (job.status, job.attempts) == (JobStatus.done, 1)
    assert await run_once() is False  # done jobs aren't picked up again


async def test_failure_is_retried_later_then_given_up(handlers):
    async def handler(session, job, http):
        raise RuntimeError("site is down")

    handlers["test"] = handler
    job_id = await add_job()

    for attempt in range(1, worker.MAX_ATTEMPTS + 1):
        assert await run_once() is True
        job = await get_job(job_id)
        assert job.attempts == attempt
        assert job.last_error == "site is down"
        if attempt < worker.MAX_ATTEMPTS:
            assert job.status == JobStatus.queued
            assert job.run_after > datetime.now(UTC)  # backed off
            assert await run_once() is False  # not due yet
            async with TestSession() as session:  # pretend the delay has passed
                await session.execute(
                    update(Job).where(Job.id == job_id).values(run_after=datetime.now(UTC))
                )
                await session.commit()

    assert job.status == JobStatus.failed


async def test_unknown_kind_fails_immediately(handlers):
    job_id = await add_job(kind="no-such-kind")
    await run_once()
    job = await get_job(job_id)
    assert job.status == JobStatus.failed
    assert "no-such-kind" in job.last_error


async def test_handler_writes_roll_back_on_failure(handlers):
    async def handler(session, job, http):
        await worker.enqueue(session, "follow-up", [{}])  # a write...
        raise RuntimeError("boom")  # ...then a failure

    handlers["test"] = handler
    await add_job()
    await run_once()
    async with TestSession() as session:
        kinds = (await session.scalars(select(Job.kind))).all()
    assert kinds == ["test"]  # the follow-up job was not committed


async def test_stale_running_job_is_taken_over(handlers):
    async def handler(session, job, http):
        pass

    handlers["test"] = handler
    job_id = await add_job()
    async with TestSession() as session:  # a worker took it and then the API died
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.running,
                attempts=1,
                locked_at=datetime.now(UTC) - worker.STALE_AFTER - timedelta(minutes=1),
            )
        )
        await session.commit()

    assert await run_once() is True
    job = await get_job(job_id)
    assert (job.status, job.attempts) == (JobStatus.done, 2)


async def test_recently_claimed_job_is_left_alone(handlers):
    job_id = await add_job()
    async with TestSession() as session:
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.running, locked_at=datetime.now(UTC))
        )
        await session.commit()
    assert await run_once() is False
