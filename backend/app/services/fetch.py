"""Download web pages that users have bookmarked, safely.

Used by background jobs (Phase 2 extracts article text from what this returns).

Safety: the server fetches URLs that users supply. Without a check, someone could
bookmark http://localhost:5432 or a cloud metadata address and make our server
probe its own private network (an "SSRF" attack). So every request, including each
redirect hop, must go to a public internet address.
"""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

MAX_BYTES = 3 * 1024 * 1024  # stop reading very large pages; articles fit easily
TIMEOUT = httpx.Timeout(10.0)
# Some sites refuse requests without a browser-like User-Agent.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BookmarkBrain/0.1; +https://github.com/Mansi145/Bookmark-Brain)",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
}


class BlockedUrl(Exception):
    """The URL points at a private/internal address, doesn't resolve, or isn't http(s)."""


class TemporaryFetchError(Exception):
    """Worth retrying later (timeouts, connection errors, 5xx, rate limits)."""


@dataclass
class FetchedPage:
    url: str  # after redirects
    status_code: int
    content_type: str
    html: str | None  # None unless the page is HTML with a 2xx status


async def ensure_public(url: str) -> None:
    """Raise BlockedUrl unless `url` is http(s) and its host resolves only to public IPs."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise BlockedUrl(url)
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            parts.hostname, parts.port or 443, type=socket.SOCK_STREAM
        )
    except socket.gaierror as err:  # the domain doesn't exist (any more)
        raise BlockedUrl(f"Can't resolve {parts.hostname}") from err
    for *_, sockaddr in infos:
        if not ipaddress.ip_address(sockaddr[0]).is_global:
            raise BlockedUrl(f"{parts.hostname} resolves to a private address")


async def _check_request(request: httpx.Request) -> None:
    await ensure_public(str(request.url))  # runs before the first request and every redirect


def make_client(**kwargs) -> httpx.AsyncClient:
    """An HTTP client that refuses private addresses. kwargs are for tests (e.g. transport)."""
    return httpx.AsyncClient(
        headers=HEADERS,
        timeout=TIMEOUT,
        follow_redirects=True,
        max_redirects=5,
        event_hooks={"request": [_check_request]},
        **kwargs,
    )


async def fetch_page(url: str, client: httpx.AsyncClient) -> FetchedPage:
    """GET `url` and return its HTML (if it is HTML).

    Raises TemporaryFetchError for problems worth retrying, BlockedUrl for unsafe URLs.
    A 404 or a PDF is not an error: it comes back with `html=None`.
    """
    try:
        async with client.stream("GET", url) as response:
            if response.status_code == 429 or response.status_code >= 500:
                raise TemporaryFetchError(f"HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "").lower()
            page = FetchedPage(str(response.url), response.status_code, content_type, None)
            if response.status_code >= 300 or "html" not in content_type:
                return page

            body = bytearray()
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) >= MAX_BYTES:
                    break
            page.html = body.decode(response.encoding or "utf-8", errors="replace")
            return page
    except httpx.TimeoutException as err:
        raise TemporaryFetchError("Timed out") from err
    except httpx.TooManyRedirects as err:
        raise BlockedUrl("Too many redirects") from err
    except httpx.TransportError as err:  # connection refused, TLS errors, ...
        raise TemporaryFetchError(str(err) or type(err).__name__) from err
