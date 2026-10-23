"""fetch_page: sync queues it for new documents; the worker stores article text.

No real network: a fake transport serves pages. URLs use a public IP literal so the
private-address guard passes without DNS.
"""

import httpx
import pytest
from sqlalchemy import func, select, update

from app import worker
from app.models import Document, DocumentStatus, Job, JobStatus
from app.services import archive
from app.services.extract import extract_article, reading_minutes
from app.services.fetch import make_client
from tests.conftest import TestSession
from tests.test_sync import CHROME, EDGE, feed, item, sync

HOST = "http://93.184.216.34"
ARCHIVE = "http://93.184.216.35"  # stands in for archive.org
SNAPSHOT_TS = "20160313081502"


@pytest.fixture(autouse=True)
def fake_archive_org(monkeypatch):
    """Never call the real archive.org from tests."""
    monkeypatch.setattr(archive, "AVAILABILITY_API", f"{ARCHIVE}/wayback/available")
    monkeypatch.setattr(archive, "WEB", f"{ARCHIVE}/web")
    monkeypatch.setattr(archive, "MIN_INTERVAL", 0)
    monkeypatch.setattr(archive, "_lock", None)  # a fresh lock per test event loop
    monkeypatch.setattr(archive, "_paused_until", 0.0)
    monkeypatch.setattr(archive, "_cool_down", archive.FIRST_COOL_DOWN)


ARTICLE = (
    "<html><head><title>Index Types | Blog</title>"
    '<meta name="description" content="A tour of index types."></head>'
    "<body><nav>Home · About · Contact</nav><article><h1>Index Types</h1>"
    # Varied paragraphs: trafilatura drops repeated text as boilerplate.
    + "".join(
        f"<p>Paragraph {i}: PostgreSQL ships several index types, and picking the right one "
        f"for query shape {i} matters a lot for performance.</p>"
        for i in range(30)
    )
    + "</article><footer>© 2026 Blog</footer></body></html>"
)


def serve(
    routes: dict[str, httpx.Response],
    archived: dict[str, str] | None = None,
    archive_calls: list | None = None,
) -> httpx.AsyncClient:
    """A fetch client whose 'internet' is `routes` (path -> response); anything else 404s.

    `archived` maps live paths to the HTML archive.org has saved for them; requests to the
    fake archive.org are appended to `archive_calls` if given.
    """
    archived = archived or {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "93.184.216.35":
            if archive_calls is not None:
                archive_calls.append(request)
            return fake_archive(request, archived)
        return routes.get(
            request.url.path, httpx.Response(404, headers={"content-type": "text/html"})
        )

    return make_client(transport=httpx.MockTransport(handler))


def fake_archive(request: httpx.Request, archived: dict[str, str]) -> httpx.Response:
    if request.url.path == "/wayback/available":
        wanted = request.url.params["url"]
        path = "/" + wanted.split("/", 3)[3]
        if path not in archived:
            return httpx.Response(200, json={"archived_snapshots": {}})
        # Like the real API: "url" is the archive's address for the snapshot, not the original.
        snapshot_url = f"http://web.archive.org/web/{SNAPSHOT_TS}/{wanted}"
        closest = {
            "available": True,
            "status": "200",
            "timestamp": SNAPSHOT_TS,
            "url": snapshot_url,
        }
        return httpx.Response(200, json={"archived_snapshots": {"closest": closest}})
    for path, body in archived.items():  # /web/<timestamp>id_/<original url>
        if str(request.url).endswith(f"id_/{HOST}{path}"):
            return html(body)
    return httpx.Response(404)


def html(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "text/html; charset=utf-8"}, text=body)


async def run_all(http: httpx.AsyncClient) -> None:
    while await worker.run_once(TestSession, http):
        pass


async def document(url_path: str) -> Document:
    async with TestSession() as session:
        return await session.scalar(select(Document).where(Document.url == HOST + url_path))


async def queued_fetch_jobs() -> int:
    async with TestSession() as session:
        return await session.scalar(
            select(func.count()).where(Job.kind == "fetch_page", Job.status == JobStatus.queued)
        )


# --- Extraction ---------------------------------------------------------------


def test_extracts_article_without_page_chrome():
    article = extract_article(ARTICLE, HOST + "/post")
    assert article.title == "Index Types"
    assert article.description == "A tour of index types."
    assert "several index types" in article.text
    assert "Contact" not in article.text and "© 2026" not in article.text
    assert article.word_count > 300


def test_page_without_text_has_no_article():
    assert extract_article("<html><body><img src=x></body></html>", HOST).text is None


def test_app_page_keeps_title_and_description():
    # YouTube/Discord-style: everything is rendered by JavaScript, only <head> has content.
    app_page = (
        "<html><head><title>Lo-fi beats - YouTube</title>"
        '<meta name="description" content="Music to study to."></head>'
        '<body><div id="app"></div><script src="app.js"></script></body></html>'
    )
    article = extract_article(app_page, HOST)
    assert article.text is None
    assert article.title and "Lo-fi beats" in article.title
    assert article.description == "Music to study to."


def test_sign_in_wall_is_not_an_article_but_keeps_its_title():
    wall = "<html><head><title>Sign in · GitLab</title></head><body><main><h1>Sign in</h1>"
    wall += "<p>Username or email</p><p>Password</p></main></body></html>"
    article = extract_article(wall, HOST)
    assert article.text is None and article.word_count == 0
    assert article.title == "Sign in"  # trafilatura drops the " · Site" suffix


def test_reading_minutes_rounds_up():
    assert reading_minutes(None) is None
    assert reading_minutes(10) == 1
    assert reading_minutes(231) == 2


# --- Queueing from sync -------------------------------------------------------


async def test_sync_queues_one_job_per_new_document(client, client_for, other_user):
    sync(client, CHROME, [item("1", HOST + "/a"), item("2", HOST + "/b")], full=True)
    assert await queued_fetch_jobs() == 2

    # Re-syncing, the same URL from another browser, or from another user: nothing new.
    sync(client, CHROME, [item("1", HOST + "/a"), item("2", HOST + "/b")], full=True)
    sync(client, EDGE, [item("9", HOST + "/a")], full=True)
    sync(client_for(other_user), CHROME, [item("1", HOST + "/b")], full=True)
    assert await queued_fetch_jobs() == 2


# --- The handler --------------------------------------------------------------


async def test_fetch_stores_text_and_feed_shows_reading_time(client):
    sync(client, CHROME, [item("1", HOST + "/post")], full=True)
    assert feed(client)["items"][0]["status"] == "pending"
    assert feed(client)["items"][0]["reading_minutes"] is None

    async with serve({"/post": html(ARTICLE)}) as http:
        await run_all(http)

    doc = await document("/post")
    assert doc.status == DocumentStatus.fetched
    assert (doc.title, doc.http_status) == ("Index Types", 200)
    assert "several index types" in doc.content_text
    row = feed(client)["items"][0]
    assert row["status"] == "fetched"
    assert row["reading_minutes"] == reading_minutes(doc.word_count)


async def test_missing_page_is_dead(client):
    sync(client, CHROME, [item("1", HOST + "/gone")], full=True)
    async with serve({}) as http:
        await run_all(http)
    doc = await document("/gone")
    assert (doc.status, doc.http_status) == (DocumentStatus.dead, 404)


async def test_non_html_page_fails_without_retry(client):
    sync(client, CHROME, [item("1", HOST + "/paper.pdf")], full=True)
    pdf = httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.7")
    async with serve({"/paper.pdf": pdf}) as http:
        await run_all(http)
    assert (await document("/paper.pdf")).status == DocumentStatus.failed
    assert await queued_fetch_jobs() == 0


async def test_private_address_is_never_fetched(client):
    sync(client, CHROME, [item("1", "http://127.0.0.1:5432/")], full=True)
    requests = []

    def handler(request):
        requests.append(request)
        return html(ARTICLE)

    async with make_client(transport=httpx.MockTransport(handler)) as http:
        await run_all(http)
    assert requests == []
    assert feed(client)["items"][0]["status"] == "failed"


async def test_server_errors_retry_then_give_up(client):
    sync(client, CHROME, [item("1", HOST + "/flaky")], full=True)
    async with serve({"/flaky": httpx.Response(503)}) as http:
        for attempt in range(1, worker.MAX_ATTEMPTS + 1):
            assert await worker.run_once(TestSession, http)
            doc = await document("/flaky")
            if attempt < worker.MAX_ATTEMPTS:
                assert doc.status == DocumentStatus.pending  # still waiting for a retry
                async with TestSession() as session:  # skip the back-off delay
                    await session.execute(update(Job).values(run_after=func.now()))
                    await session.commit()

    assert doc.status == DocumentStatus.failed
    async with TestSession() as session:
        jobs = (await session.execute(select(Job.kind, Job.status))).all()
    assert jobs == [("fetch_page", JobStatus.done)]  # gave up cleanly; nothing sent to archive.org


# --- Dead links and the Wayback Machine (only when the user asks) --------------

BLOCKED = httpx.Response(403, headers={"content-type": "text/html"}, text="Just a moment...")


def section(client, name):  # main | sign_in | dead
    return [b["url"] for b in feed(client, section=name)["items"]]


async def find_archive(client, url_path: str, http) -> dict:
    bookmark = next(b for b in feed(client, section="dead")["items"] if b["url"] == HOST + url_path)
    response = client.post(f"/api/bookmarks/{bookmark['id']}/find-archive")
    assert response.status_code == 202, response.text
    assert response.json()["archive_status"] == "checking"
    await run_all(http)
    return next(b for b in feed(client, section="dead")["items"] if b["id"] == bookmark["id"])


async def test_nothing_goes_to_archive_org_automatically(client):
    sync(client, CHROME, [item("1", HOST + "/gone"), item("2", HOST + "/blocked")], full=True)
    calls = []
    archived = {"/gone": ARTICLE, "/blocked": ARTICLE}
    async with serve({"/blocked": BLOCKED}, archived, calls) as http:
        await run_all(http)
    assert calls == []
    assert (await document("/gone")).status == DocumentStatus.dead
    assert (await document("/blocked")).status == DocumentStatus.failed  # "Couldn't read this page"
    assert section(client, "dead") == [HOST + "/gone"]
    assert section(client, "main") == [HOST + "/blocked"]


async def test_find_archived_copy_of_a_dead_link(client):
    sync(client, CHROME, [item("1", HOST + "/gone")], full=True)
    async with serve({}, archived={"/gone": ARTICLE}) as http:
        await run_all(http)
        row = await find_archive(client, "/gone", http)

    assert row["archive_status"] == "found"
    assert row["archive_url"].endswith(f"{SNAPSHOT_TS}/{HOST}/gone")
    assert row["archived_on"].startswith("2016-03-13")
    doc = await document("/gone")
    assert (doc.status, doc.content_source) == (DocumentStatus.dead, "archive")
    assert "several index types" in doc.content_text  # ready to be summarised
    assert section(client, "dead") == [HOST + "/gone"]  # still a dead link


async def test_no_archived_copy(client):
    sync(client, CHROME, [item("1", HOST + "/gone")], full=True)
    async with serve({}) as http:
        await run_all(http)
        row = await find_archive(client, "/gone", http)
    assert (row["archive_status"], row["archive_url"]) == ("none", None)


async def test_unreachable_archive_can_be_retried(client):
    sync(client, CHROME, [item("1", HOST + "/gone")], full=True)
    busy = True

    def handler(request):
        if request.url.host == "93.184.216.35":
            return httpx.Response(429) if busy else fake_archive(request, {"/gone": ARTICLE})
        return httpx.Response(404, headers={"content-type": "text/html"})

    async with make_client(transport=httpx.MockTransport(handler)) as http:
        await run_all(http)
        assert (await find_archive(client, "/gone", http))["archive_status"] == "failed"
        busy = False
        archive._paused_until = 0.0  # the shared cool-down is over
        assert (await find_archive(client, "/gone", http))["archive_status"] == "found"


async def test_only_dead_links_of_your_own_can_be_looked_up(client, client_for, other_user):
    sync(client, CHROME, [item("1", HOST + "/gone"), item("2", HOST + "/post")], full=True)
    async with serve({"/post": html(ARTICLE)}) as http:
        await run_all(http)
    rows = {
        b["url"]: b["id"] for b in feed(client, section="dead")["items"] + feed(client)["items"]
    }
    assert client.post(f"/api/bookmarks/{rows[HOST + '/post']}/find-archive").status_code == 409
    stranger = client_for(other_user)
    assert stranger.post(f"/api/bookmarks/{rows[HOST + '/gone']}/find-archive").status_code == 404


async def test_facets_follow_the_section(client):
    sync(
        client,
        CHROME,
        [item("1", HOST + "/gone", folder="Old"), item("2", HOST + "/alive", folder="Reading")],
        full=True,
    )
    async with serve({"/alive": html(ARTICLE)}) as http:
        await run_all(http)
    main = client.get("/api/bookmarks/facets").json()
    old = client.get("/api/bookmarks/facets", params={"section": "dead"}).json()
    assert (main["total"], main["pending"], old["total"]) == (1, 0, 1)
    assert main["read_states"] == {"unread": 1, "read": 0}
    # Every folder is listed in every section, with 0 where the section has none.
    assert [(f["value"], f["count"]) for f in main["folders"]] == [("Old", 0), ("Reading", 1)]
    assert [(f["value"], f["count"]) for f in old["folders"]] == [("Old", 1), ("Reading", 0)]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://stackoverflow.com/questions/1", True),
        ("https://accounts.google.com/signin", False),
        ("https://outlook.office.com/mail/", False),
        ("https://docs.google.com/document/d/abc", False),
        ("http://wiki/page", False),
    ],
)
def test_private_looking_pages_are_never_sent_to_archive_org(url, expected):
    assert archive.worth_asking(url) is expected


async def test_rate_limit_pauses_all_lookups():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429)

    async with make_client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(archive.ArchiveBusy) as first:
            await archive.find_snapshot(HOST + "/a", http)
        with pytest.raises(archive.ArchiveBusy) as second:
            await archive.find_snapshot(HOST + "/b", http)  # no request: still cooling down
    assert len(calls) == 1
    assert first.value.retry_in == archive.FIRST_COOL_DOWN
    assert 0 < second.value.retry_in <= archive.FIRST_COOL_DOWN
    assert archive._cool_down == archive.FIRST_COOL_DOWN * 2  # longer next time


# --- Needs sign-in -------------------------------------------------------------

SIGN_IN = (
    "<html><head><title>Sign in</title></head><body><form>"
    '<input name="login"><input type="password" name="password"></form></body></html>'
)


async def test_sign_in_page_gets_its_own_section(client):
    archive_calls = []

    def handler(request):
        if request.url.host == "93.184.216.35":
            archive_calls.append(request)
            return httpx.Response(404)
        if request.url.path == "/private":
            return httpx.Response(302, headers={"location": f"{HOST}/users/sign_in"})
        if request.url.path == "/users/sign_in":
            return html(SIGN_IN)
        return html(ARTICLE)

    sync(client, CHROME, [item("1", HOST + "/private"), item("2", HOST + "/post")], full=True)
    async with make_client(transport=httpx.MockTransport(handler)) as http:
        await run_all(http)

    doc = await document("/private")
    assert (doc.status, doc.access, doc.title) == (DocumentStatus.failed, "login", "Sign in")
    assert archive_calls == []  # possibly private: never sent to archive.org
    assert section(client, "sign_in") == [HOST + "/private"]
    assert section(client, "main") == [HOST + "/post"]
    assert section(client, "dead") == []


async def test_paywalled_article_keeps_teaser_in_sign_in_section(client):
    paywalled = ARTICLE.replace(
        "</head>",
        '<script type="application/ld+json">{"isAccessibleForFree": false}</script></head>',
    )
    sync(client, CHROME, [item("1", HOST + "/news")], full=True)
    async with serve({"/news": html(paywalled)}) as http:
        await run_all(http)
    doc = await document("/news")
    assert (doc.status, doc.access, doc.content_source) == (
        DocumentStatus.fetched,
        "paywall",
        "page",
    )
    assert section(client, "sign_in") == [HOST + "/news"]


async def test_logo_is_taken_from_the_page_or_guessed(client):
    with_icon = ARTICLE.replace("</head>", '<link rel="icon" href="/static/logo.png"></head>')
    sync(client, CHROME, [item("1", HOST + "/a"), item("2", HOST + "/b")], full=True)
    async with serve({"/a": html(with_icon), "/b": html(ARTICLE)}) as http:
        await run_all(http)
    icons = {b["url"]: b["icon_url"] for b in feed(client)["items"]}
    assert icons[HOST + "/a"] == HOST + "/static/logo.png"
    assert icons[HOST + "/b"] == HOST + "/favicon.ico"  # nothing declared: the usual guess


async def test_private_address_gets_no_logo(client):
    sync(client, CHROME, [item("1", "http://127.0.0.1:5432/")], full=True)
    async with serve({}) as http:
        await run_all(http)
    assert feed(client)["items"][0]["icon_url"] is None
