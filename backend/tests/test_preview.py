"""Preview images (og:image) for the newspaper feed's top story."""

from app.services.preview import find_preview_image
from app.worker import enqueue
from tests.conftest import TestSession
from tests.test_fetch_page import ARTICLE, HOST, document, html, run_all, serve
from tests.test_sync import CHROME, feed, item, sync

PAGE = "https://example.com/blog/post"


def head(*tags: str) -> str:
    return f"<html><head>{''.join(tags)}</head><body><p>hi</p></body></html>"


def test_prefers_the_secure_og_image_and_resolves_relative_urls():
    page = head(
        '<meta name="twitter:image" content="/twitter.png">',
        '<meta property="og:image" content="http://example.com/og.png">',
        '<meta property="og:image:secure_url" content="https://cdn.example.com/og.png">',
    )
    assert find_preview_image(page, PAGE) == "https://cdn.example.com/og.png"
    assert find_preview_image(head('<meta name="twitter:image" content="/t.png">'), PAGE) == (
        "https://example.com/t.png"
    )


def test_ignores_missing_inline_and_body_images():
    assert find_preview_image(head(), PAGE) is None
    assert (
        find_preview_image(
            head('<meta property="og:image" content="data:image/png;base64,AA">'), PAGE
        )
        is None
    )
    in_body = '<html><head></head><body><meta property="og:image" content="/x.png"></body></html>'
    assert find_preview_image(in_body, PAGE) is None
    assert (
        find_preview_image(head('<meta property="og:image" content="javascript:alert(1)">'), PAGE)
        is None
    )


async def test_fetch_stores_the_image_and_the_feed_returns_it(client):
    page = ARTICLE.replace("<head>", '<head><meta property="og:image" content="/cover.jpg">')
    sync(client, CHROME, [item("1", HOST + "/post")], full=True)
    async with serve({"/post": html(page)}) as http:
        await run_all(http)
    assert feed(client)["items"][0]["image_url"] == HOST + "/cover.jpg"


async def test_find_image_only_adds_the_image(client):
    sync(client, CHROME, [item("1", HOST + "/post")], full=True)
    async with serve({"/post": html(ARTICLE)}) as http:
        await run_all(http)
    before = await document("/post")
    assert before.image_url is None

    async with TestSession() as session:
        await enqueue(session, "find_image", [{"document_id": before.id}])
        await session.commit()
    page = ARTICLE.replace("<head>", '<head><meta property="og:image" content="/new.jpg">')
    async with serve({"/post": html(page)}) as http:
        await run_all(http)

    after = await document("/post")
    assert after.image_url == HOST + "/new.jpg"
    assert (after.status, after.content_text, after.fetched_at) == (
        before.status,
        before.content_text,
        before.fetched_at,
    )
