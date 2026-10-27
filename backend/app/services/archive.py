"""Find a Wayback Machine (archive.org) copy of a page.

Used when the live page is gone (404), blocks us (403 bot protection) or has no
readable text. archive.org saved many public pages over the years, and serves them
without the bot checks, so it often has the article we couldn't get.

archive.org is a free public service with rate limits (it answers 429 when asked too
often, and keeps refusing for a while if you carry on). So:
- all requests go through `_polite()`: one at a time, spaced out;
- after a 429 *every* lookup pauses (a "circuit breaker"), for archive.org's Retry-After
  or a cool-down that doubles each time, up to 30 minutes, instead of each job
  hammering it again on its own;
- "busy" is reported as `ArchiveBusy(retry_in)` so the job tries again later instead of
  wrongly concluding there's no copy.

Privacy: asking archive.org sends it the bookmark's URL. We only ask for public-looking
pages, never sign-in, mail or account pages (see `worth_asking`).
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from app.services import fetch

AVAILABILITY_API = "https://archive.org/wayback/available"
WEB = "https://web.archive.org/web"
MIN_INTERVAL = 1.5  # seconds between our requests to archive.org, across all worker loops
FIRST_COOL_DOWN = 60.0  # seconds to pause everything after the first 429
MAX_COOL_DOWN = 30 * 60.0

# Hosts or host prefixes that are personal accounts, not public pages.
PRIVATE_HOST_PREFIXES = ("accounts.", "login.", "auth.", "mail.", "outlook.", "signin.", "sso.")
PRIVATE_HOSTS = {"localhost", "docs.google.com", "drive.google.com", "web.whatsapp.com"}


class ArchiveBusy(Exception):
    """archive.org is rate-limiting us or temporarily down: ask again in `retry_in` seconds."""

    def __init__(self, reason: str, retry_in: float = FIRST_COOL_DOWN) -> None:
        super().__init__(reason)
        self.retry_in = retry_in


@dataclass
class Snapshot:
    view_url: str  # for people: the archived page with the Wayback toolbar
    raw_url: str  # for us: the original HTML exactly as it was saved
    taken_at: datetime


def worth_asking(url: str) -> bool:
    """False for URLs that look like private/account pages (don't leak them to archive.org)."""
    host = (urlsplit(url).hostname or "").lower()
    if not host or host in PRIVATE_HOSTS or host.startswith(PRIVATE_HOST_PREFIXES):
        return False
    return "." in host  # intranet names like "wiki" or "nas" have no dot


# Shared by all worker loops in this process.
_lock: asyncio.Lock | None = None
_last_request = 0.0
_paused_until = 0.0  # circuit breaker: no requests before this (time.monotonic())
_cool_down = FIRST_COOL_DOWN


async def _polite() -> None:
    """Wait for our turn to call archive.org; raise ArchiveBusy while it's cooling down."""
    global _lock, _last_request
    remaining = _paused_until - time.monotonic()
    if remaining > 0:
        raise ArchiveBusy("cooling down after a rate limit", retry_in=remaining)
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        wait = _last_request + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request = time.monotonic()


def _rate_limited(response: httpx.Response) -> ArchiveBusy:
    """Open the circuit breaker: pause every lookup, longer each time it happens again."""
    global _paused_until, _cool_down
    try:
        pause = float(response.headers.get("retry-after", ""))
    except ValueError:
        pause = _cool_down
        _cool_down = min(_cool_down * 2, MAX_COOL_DOWN)
    _paused_until = time.monotonic() + pause
    return ArchiveBusy("archive.org rate limit (HTTP 429)", retry_in=pause)


def _answered() -> None:
    global _cool_down
    _cool_down = FIRST_COOL_DOWN  # archive.org is happy again


async def find_snapshot(url: str, http: httpx.AsyncClient) -> Snapshot | None:
    """The closest archived copy of `url`, or None if archive.org has none.

    Raises ArchiveBusy when archive.org can't answer right now.
    """
    if not worth_asking(url):
        return None
    await _polite()
    try:
        response = await http.get(AVAILABILITY_API, params={"url": url})
    except (httpx.TimeoutException, httpx.TransportError) as err:
        raise ArchiveBusy(str(err) or type(err).__name__) from err
    if response.status_code == 429:
        raise _rate_limited(response)
    if response.status_code >= 500:
        raise ArchiveBusy(f"HTTP {response.status_code}")
    _answered()
    try:
        closest = response.json().get("archived_snapshots", {}).get("closest") or {}
    except ValueError:
        return None
    if not closest.get("available") or str(closest.get("status")) != "200":
        return None
    # Note: closest["url"] is already the archive's own address for the snapshot
    # ("http://web.archive.org/web/<timestamp>/<original>"), so build ours from the
    # timestamp and the bookmark's URL instead of wrapping it again.
    timestamp = closest["timestamp"]  # e.g. "20160313081502"
    return Snapshot(
        view_url=f"{WEB}/{timestamp}/{url}",
        # The "id_" flag returns the saved HTML without archive.org's toolbar and rewriting.
        raw_url=f"{WEB}/{timestamp}id_/{url}",
        taken_at=datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=UTC),
    )


async def fetch_snapshot(snapshot: Snapshot, http: httpx.AsyncClient) -> str | None:
    """The archived HTML (None if it isn't HTML). Raises ArchiveBusy to try again later."""
    await _polite()
    try:
        page = await fetch.fetch_page(snapshot.raw_url, http)
    except fetch.TemporaryFetchError as err:
        raise ArchiveBusy(str(err)) from err
    except fetch.BlockedUrl:
        return None
    return page.html
