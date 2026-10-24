"""Background job worker: runs slow work queued in the `jobs` table.

How it works:
- Request handlers call `enqueue()` to insert job rows, then return immediately.
- A few worker loops run inside the API process (started from the FastAPI lifespan).
  Each loop claims one job at a time with `SELECT ... FOR UPDATE SKIP LOCKED`, so two
  loops (or two API instances) never take the same job, and nobody waits on a lock.
- A failed job is retried with a growing delay, then marked `failed` after MAX_ATTEMPTS.
- If the API restarts mid-job, the job stays `running`; once it's older than
  STALE_AFTER another loop takes it over.

Adding a kind of job: write `async def handler(session, job, http)` and add it to HANDLERS.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
from sqlalchemy import and_, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import SessionLocal
from app.models import Job, JobStatus
from app.services import fetch

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
CONCURRENCY = 4  # jobs in flight at once; they mostly wait on the network
POLL_SECONDS = 2.0  # how long an idle loop sleeps before checking again
STALE_AFTER = timedelta(minutes=10)

Handler = Callable[[AsyncSession, Job, httpx.AsyncClient], Awaitable[None]]


# --- Queueing ------------------------------------------------------------------


async def enqueue(session: AsyncSession, kind: str, payloads: list[dict]) -> None:
    """Add jobs in the caller's transaction (so they only exist if the caller commits)."""
    if payloads:
        await session.execute(insert(Job), [{"kind": kind, "payload": p} for p in payloads])


# --- Handlers ------------------------------------------------------------------

# kind -> handler. Phase 2 adds "fetch_page" (download + extract text) and "summarise".
# A handler raises to have its job retried; anything it writes through `session` is
# committed together with the job being marked done.
HANDLERS: dict[str, Handler] = {}


# --- Running jobs --------------------------------------------------------------


async def claim_job(sessions: async_sessionmaker[AsyncSession]) -> Job | None:
    """Mark the next due job as running and return it (None if there's nothing to do)."""
    due = or_(
        and_(Job.status == JobStatus.queued, Job.run_after <= func.now()),
        and_(Job.status == JobStatus.running, Job.locked_at < func.now() - STALE_AFTER),
    )
    next_id = (
        select(Job.id)
        .where(due)
        .order_by(Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    async with sessions() as session:
        job = await session.scalar(
            update(Job)
            .where(Job.id == next_id)
            .values(status=JobStatus.running, attempts=Job.attempts + 1, locked_at=func.now())
            .returning(Job)
        )
        await session.commit()
        return job


async def run_job(
    sessions: async_sessionmaker[AsyncSession], job: Job, http: httpx.AsyncClient
) -> None:
    handler = HANDLERS.get(job.kind)
    try:
        if handler is None:
            raise ValueError(f"No handler for job kind {job.kind!r}")
        async with sessions() as session:
            await handler(session, job, http)
            # The handler's writes and "done" are committed together.
            await session.execute(
                update(Job).where(Job.id == job.id).values(status=JobStatus.done, last_error=None)
            )
            await session.commit()
    except Exception as err:
        give_up = job.attempts >= MAX_ATTEMPTS or handler is None
        log.warning("Job %s (%s) failed, attempt %s: %s", job.id, job.kind, job.attempts, err)
        async with sessions() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job.id)
                .values(
                    status=JobStatus.failed if give_up else JobStatus.queued,
                    # 30 s, then 2 min, then 8 min...
                    run_after=func.now() + timedelta(seconds=30 * 4 ** (job.attempts - 1)),
                    last_error=str(err)[:2000] or type(err).__name__,
                )
            )
            await session.commit()


async def run_once(
    sessions: async_sessionmaker[AsyncSession] = SessionLocal,
    http: httpx.AsyncClient | None = None,
) -> bool:
    """Run one job if one is due. Returns True if it did (handy for tests)."""
    job = await claim_job(sessions)
    if job is None:
        return False
    if http is not None:
        await run_job(sessions, job, http)
    else:
        async with fetch.make_client() as client:
            await run_job(sessions, job, client)
    return True


async def _loop(stop: asyncio.Event, http: httpx.AsyncClient) -> None:
    while not stop.is_set():
        try:
            busy = await run_once(SessionLocal, http)
        except Exception:
            log.exception("Worker loop error (database down?)")
            busy = False
        if not busy:
            try:
                await asyncio.wait_for(stop.wait(), timeout=POLL_SECONDS)
            except TimeoutError:
                pass


@asynccontextmanager
async def running_workers():
    """Start the worker loops for as long as the `async with` block lasts."""
    stop = asyncio.Event()
    async with fetch.make_client() as http:
        tasks = [asyncio.create_task(_loop(stop, http)) for _ in range(CONCURRENCY)]
        log.info("Started %s job worker loops", CONCURRENCY)
        try:
            yield
        finally:
            stop.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
