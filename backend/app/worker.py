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
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import and_, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import chains
from app.db import SessionLocal
from app.models import Document, DocumentStatus, Job, JobStatus
from app.services import archive, fetch
from app.services.access import PAYWALL, detect_access, is_paywalled
from app.services.extract import extract_article
from app.services.icons import default_icon, find_icon
from app.services.preview import find_preview_image

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
CONCURRENCY = 4  # jobs in flight at once; they mostly wait on the network
POLL_SECONDS = 2.0  # how long an idle loop sleeps before checking again
STALE_AFTER = timedelta(minutes=10)

Handler = Callable[[AsyncSession, Job, httpx.AsyncClient], Awaitable[None]]


class RetryLater(Exception):
    """Raise from a handler to run the job again after `seconds`, without using up an attempt.

    For "the other side is busy, nothing is wrong" (e.g. a rate limit). The handler is
    responsible for eventually giving up (e.g. by checking `job.created_at`).
    """

    def __init__(self, seconds: float, reason: str = "") -> None:
        super().__init__(reason or f"retry in {seconds:.0f}s")
        self.seconds = seconds


# --- Queueing ------------------------------------------------------------------


async def enqueue(session: AsyncSession, kind: str, payloads: list[dict]) -> None:
    """Add jobs in the caller's transaction (so they only exist if the caller commits)."""
    if payloads:
        await session.execute(insert(Job), [{"kind": kind, "payload": p} for p in payloads])


# --- Handlers ------------------------------------------------------------------

# A handler raises to have its job retried; anything it writes through `session` is
# committed together with the job being marked done.


async def fetch_page(session: AsyncSession, job: Job, http: httpx.AsyncClient) -> None:
    """Download a document's live page and store its title, description, text and logo.

    Queued by sync for every new document.
    - article text found → fetched (content_source "page")
    - 404/410 → dead ("Dead links"); the user can ask for a Wayback Machine copy
    - needs sign-in or a subscription (services/access.py) → `access` set
    - anything else (403 bot protection, no readable text, private address, gave up
      retrying) → failed ("Couldn't read this page")
    Nothing is sent to archive.org automatically: that only happens when a user clicks
    "Find archived copy" (see find_archive).
    """
    document = await session.get(Document, job.payload["document_id"])
    if document is None or document.status != DocumentStatus.pending:
        return  # deleted, or already done by an earlier run of this job

    try:
        page = await fetch.fetch_page(document.url, http)
    except fetch.BlockedUrl:
        # Private address / dead domain: never retry, and no logo guess either.
        _finish(document, DocumentStatus.failed, guess_icon=False)
        return
    except fetch.TemporaryFetchError:
        if job.attempts < MAX_ATTEMPTS:
            raise  # try again later
        _finish(document, DocumentStatus.failed)  # last try: give up so the feed stops waiting
        return

    document.http_status = page.status_code
    has_article = False
    if page.html is not None:
        document.icon_url = find_icon(page.html, page.url)
        document.image_url = find_preview_image(page.html, page.url)
        has_article = await _read_article(document, page.html, "page")
    document.access = detect_access(document.url, page, has_article)

    if has_article:
        _finish(document, DocumentStatus.fetched)  # (a paywalled teaser keeps access="paywall")
    elif page.status_code in (404, 410):
        _finish(document, DocumentStatus.dead)
    else:
        _finish(document, DocumentStatus.failed)


async def find_image(session: AsyncSession, job: Job, http: httpx.AsyncClient) -> None:
    """Look up the preview image of a page fetched before images were stored (migration 0007).

    Downloads the page again but only saves image_url, so the page's text, section and
    summary stay as they are. Gives up quietly: a missing image just means a text-only lead.
    """
    document = await session.get(Document, job.payload["document_id"])
    if document is None or document.image_url is not None:
        return
    try:
        page = await fetch.fetch_page(document.url, http)
    except (fetch.BlockedUrl, fetch.TemporaryFetchError):
        return
    if page.html is not None and page.status_code < 400:
        document.image_url = find_preview_image(page.html, page.url)


async def find_archive(session: AsyncSession, job: Job, http: httpx.AsyncClient) -> None:
    """Look up the latest Wayback Machine copy of a dead link (the user clicked the button).

    Sets archive_status: found (archive_url / archived_on set, and the copy's text stored
    so it can be summarised) | none (no copy, or a private-looking URL we won't send) |
    failed (archive.org busy or unreachable; the user can try again).
    """
    document = await session.get(Document, job.payload["document_id"])
    if document is None:
        return
    try:
        snapshot = await archive.find_snapshot(document.url, http)
        if snapshot is None:
            document.archive_status = "none"
            return
        document.archive_url = snapshot.view_url
        document.archived_on = snapshot.taken_at
        html = await archive.fetch_snapshot(snapshot, http)
        if html is not None:
            document.icon_url = document.icon_url or find_icon(html, document.url)
            await _read_article(document, html, "archive")
            if is_paywalled(html):
                document.access = PAYWALL  # e.g. a Medium members-only teaser
        document.archive_status = "found"
    except archive.ArchiveBusy:
        # Someone is waiting for an answer, so report it rather than retrying for hours.
        document.archive_status = "failed"


async def _read_article(document: Document, html: str, source: str) -> bool:
    """Extract `html` into `document`. Returns True if it had article text."""
    # Parsing HTML is CPU work; a thread keeps the event loop free for other requests.
    article = await asyncio.to_thread(extract_article, html, document.url)
    # Title/description are kept even without text, and the live page's win over the archive's.
    document.title = document.title or article.title
    document.description = document.description or article.description
    if article.text is None:
        return False
    document.content_text = article.text
    document.word_count = article.word_count
    document.content_source = source
    return True


# Someone is watching "Summarising…", so a failing summary is retried once (after 30 s), not
# for 10 minutes. Waiting for the page itself to be fetched first is capped too.
SUMMARY_ATTEMPTS = 2
WAIT_FOR_PAGE = timedelta(minutes=2)


async def summarise(session: AsyncSession, job: Job, http: httpx.AsyncClient) -> None:
    """Write the AI summary for one document (a user clicked Summarise or Re-summarise).

    Uses the best text we have: the page's text, a Wayback copy's text for a dead link, or
    only the title and description (JavaScript apps, bot-protected pages). Sets
    summary_status to "done" or "failed"; summary_source records which text was used.
    """
    document = await session.get(Document, job.payload["document_id"])
    if document is None:
        return
    # The page's own title, else the one the user saved the bookmark under.
    title = document.title or job.payload.get("title") or document.url

    if document.status == DocumentStatus.pending:
        # The page is still being fetched; its text makes a much better summary.
        if datetime.now(UTC) - job.created_at < WAIT_FOR_PAGE:
            raise RetryLater(5, "waiting for the page to be fetched")

    text = document.content_text
    if document.status == DocumentStatus.dead and document.content_source != "archive":
        text = None  # the old live text (if any) isn't what the user is looking at now
    source = document.content_source if text else "metadata"

    try:
        result = await chains.summarise_document(
            title=title,
            site=document.site,
            text=text,
            description=document.description,
            trace={"document_id": document.id, "source": source},
        )
    except chains.BadAnswer as err:
        # A usable model gave an unusable answer; asking again rarely helps much.
        log.warning("Summary for document %s rejected: %s", document.id, err)
        document.summary_status = "failed"
        return
    except Exception:
        if job.attempts < SUMMARY_ATTEMPTS:
            raise  # both models failed (quota, outage): the queue retries in 30 s
        document.summary_status = "failed"
        return

    document.summary = result.summary
    document.key_points = result.key_points
    document.summary_source = source
    document.summary_model = result.model
    document.summarised_at = datetime.now(UTC)
    document.summary_status = "done"


def _finish(document: Document, status: DocumentStatus, guess_icon: bool = True) -> None:
    document.status = status
    document.fetched_at = datetime.now(UTC)
    if guess_icon and document.icon_url is None:
        # The page didn't name a logo (or we couldn't read it): most sites serve /favicon.ico.
        document.icon_url = default_icon(document.url)


# kind -> handler
HANDLERS: dict[str, Handler] = {
    "fetch_page": fetch_page,
    "find_archive": find_archive,
    "summarise": summarise,
    "find_image": find_image,
}


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
    except RetryLater as later:
        async with sessions() as session:
            await session.execute(
                update(Job)
                .where(Job.id == job.id)
                .values(
                    status=JobStatus.queued,
                    attempts=Job.attempts - 1,  # being told "later" isn't a failure
                    run_after=func.now() + timedelta(seconds=later.seconds),
                    last_error=str(later),
                )
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
