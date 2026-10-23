"""Page fetching: the private-address guard and how responses are classified.

No real network: a fake transport answers requests. Hosts are public IP literals so
the guard can check them without DNS.
"""

import httpx
import pytest

from app.services.fetch import (
    BlockedUrl,
    TemporaryFetchError,
    ensure_public,
    fetch_page,
    make_client,
)

PUBLIC = "http://93.184.216.34"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:5432/",
        "http://localhost/",
        "http://10.0.0.5/",
        "http://192.168.1.1/admin",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata service
        "http://[::1]/",
        "file:///etc/passwd",
        "ftp://93.184.216.34/",
    ],
)
async def test_blocks_private_and_non_http_urls(url):
    with pytest.raises(BlockedUrl):
        await ensure_public(url)


async def test_allows_public_ip():
    await ensure_public(f"{PUBLIC}/post")


def client_for(handler) -> httpx.AsyncClient:
    return make_client(transport=httpx.MockTransport(handler))


async def test_returns_html():
    def handler(request):
        return httpx.Response(
            200, headers={"content-type": "text/html; charset=utf-8"}, text="<h1>Hi</h1>"
        )

    async with client_for(handler) as client:
        page = await fetch_page(f"{PUBLIC}/post", client)
    assert page.html == "<h1>Hi</h1>"
    assert page.status_code == 200


async def test_non_html_and_404_have_no_html():
    def handler(request):
        if request.url.path == "/doc.pdf":
            return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
        return httpx.Response(404, headers={"content-type": "text/html"}, text="Not found")

    async with client_for(handler) as client:
        assert (await fetch_page(f"{PUBLIC}/doc.pdf", client)).html is None
        missing = await fetch_page(f"{PUBLIC}/gone", client)
    assert (missing.status_code, missing.html) == (404, None)


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_server_errors_are_temporary(status):
    async with client_for(lambda request: httpx.Response(status)) as client:
        with pytest.raises(TemporaryFetchError):
            await fetch_page(f"{PUBLIC}/post", client)


async def test_redirect_to_private_address_is_blocked():
    def handler(request):
        return httpx.Response(302, headers={"location": "http://127.0.0.1:8000/internal"})

    async with client_for(handler) as client:
        with pytest.raises(BlockedUrl):
            await fetch_page(f"{PUBLIC}/innocent", client)


async def test_timeout_is_temporary():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    async with client_for(handler) as client:
        with pytest.raises(TemporaryFetchError):
            await fetch_page(f"{PUBLIC}/post", client)
