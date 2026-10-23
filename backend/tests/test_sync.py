import asyncio

from sqlalchemy import update

from app.models import Bookmark, ReadState
from tests.conftest import TestSession

CHROME = {"id": "chrome-install-1", "browser": "chrome"}
EDGE = {"id": "edge-install-1", "browser": "edge"}


def item(node_id, url, title="", folder="Bookmarks bar", added="2026-01-01T10:00:00Z"):
    return {
        "node_id": node_id,
        "url": url,
        "title": title or url,
        "folder_path": folder,
        "added_at": added,
    }


def sync(client, source, upserts=(), removed=(), full=False):
    response = client.post(
        "/api/sync",
        json={
            "source": source,
            "full": full,
            "upserts": list(upserts),
            "removed_node_ids": list(removed),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def feed(client, **params):
    response = client.get("/api/bookmarks", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_full_sync_creates_bookmarks(client):
    result = sync(
        client,
        CHROME,
        [item("1", "https://a.com/post"), item("2", "https://b.com/")],
        full=True,
    )
    assert result["upserted"] == 2
    assert result["active_bookmarks"] == 2
    assert {b["site"] for b in feed(client)["items"]} == {"a.com", "b.com"}


def test_skips_non_web_urls(client):
    result = sync(
        client, CHROME, [item("1", "chrome://settings"), item("2", "https://a.com")], full=True
    )
    assert result["skipped_unsupported"] == 1
    assert result["active_bookmarks"] == 1


def test_same_article_with_tracking_params_is_one_bookmark(client):
    sync(
        client,
        CHROME,
        [item("1", "https://a.com/post?utm_source=x"), item("2", "https://A.com/post/#top")],
        full=True,
    )
    items = feed(client)["items"]
    assert len(items) == 1
    assert len(items[0]["sources"]) == 2


def test_resending_is_idempotent(client):
    payload = [item("1", "https://a.com/post")]
    sync(client, CHROME, payload, full=True)
    result = sync(client, CHROME, payload, full=True)
    assert result["active_bookmarks"] == 1
    assert len(feed(client)["items"][0]["sources"]) == 1


def test_two_browsers_merge_and_removal_needs_both(client):
    sync(client, CHROME, [item("c1", "https://a.com/post")], full=True)
    sync(client, EDGE, [item("e9", "https://a.com/post", folder="Favorites")], full=True)

    [bookmark] = feed(client)["items"]
    assert {s["browser"] for s in bookmark["sources"]} == {"chrome", "edge"}

    # Removed from Chrome only: still in Edge, so it stays.
    sync(client, CHROME, removed=["c1"])
    [bookmark] = feed(client)["items"]
    assert [s["browser"] for s in bookmark["sources"]] == ["edge"]

    # Removed from Edge too: gone from the feed.
    result = sync(client, EDGE, removed=["e9"])
    assert result["active_bookmarks"] == 0
    assert feed(client)["items"] == []


def test_full_sync_removes_missing_and_rebookmark_revives(client):
    sync(client, CHROME, [item("1", "https://a.com"), item("2", "https://b.com")], full=True)
    result = sync(client, CHROME, [item("1", "https://a.com")], full=True)
    assert result["removed_sources"] == 1
    assert result["active_bookmarks"] == 1

    sync(client, CHROME, [item("3", "https://b.com")])
    assert feed(client)["items"].__len__() == 2


def test_editing_a_bookmark_url_moves_it(client):
    sync(client, CHROME, [item("1", "https://old.com")], full=True)
    sync(client, CHROME, [item("1", "https://new.com")])
    assert [b["site"] for b in feed(client)["items"]] == ["new.com"]


def test_users_are_isolated(client, client_for, other_user):
    sync(client, CHROME, [item("1", "https://a.com")], full=True)
    other = client_for(other_user)
    assert feed(other)["items"] == []
    # Same URL for another user shares the document but is a separate bookmark.
    sync(other, {"id": "chrome-install-2", "browser": "chrome"}, [item("1", "https://a.com")])
    assert len(feed(other)["items"]) == 1
    assert len(feed(client)["items"]) == 1


def test_pagination_and_filters(client):
    items = [
        item(str(i), f"https://site{i}.com", folder="Reading/AI" if i % 2 else "Recipes",
             added=f"2026-01-{i + 1:02d}T00:00:00Z")
        for i in range(5)
    ]  # fmt: skip
    sync(client, CHROME, items, full=True)
    sync(client, EDGE, [item("e1", "https://site0.com", folder="Favorites")])

    first = feed(client, limit=2)
    assert [b["site"] for b in first["items"]] == ["site4.com", "site3.com"]  # newest first
    second = feed(client, limit=2, cursor=first["next_cursor"])
    assert [b["site"] for b in second["items"]] == ["site2.com", "site1.com"]
    third = feed(client, limit=2, cursor=second["next_cursor"])
    assert [b["site"] for b in third["items"]] == ["site0.com"]
    assert third["next_cursor"] is None

    # Folder filter includes subfolders.
    assert {b["site"] for b in feed(client, folder="Reading")["items"]} == {
        "site1.com",
        "site3.com",
    }
    assert [b["site"] for b in feed(client, browser="edge")["items"]] == ["site0.com"]

    facets = client.get("/api/bookmarks/facets").json()
    assert {f["value"]: f["count"] for f in facets["browsers"]} == {"chrome": 5, "edge": 1}
    assert {f["value"]: f["count"] for f in facets["folders"]} == {
        "Favorites": 1,
        "Reading/AI": 2,
        "Recipes": 3,
    }


def test_sync_with_extension_token(client, anon_client):
    token = client.post("/api/tokens", json={}).json()["token"]
    response = anon_client.post(
        "/api/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={"source": CHROME, "full": True, "upserts": [item("1", "https://a.com")]},
    )
    assert response.status_code == 200
    assert response.json()["active_bookmarks"] == 1


def test_sync_requires_auth(anon_client):
    response = anon_client.post("/api/sync", json={"source": CHROME, "upserts": []})
    assert response.status_code == 401


def test_feed_filters_by_reading_state(client):
    sync(client, CHROME, [item("1", "https://a.com/x"), item("2", "https://b.com/y")], full=True)

    async def mark_read():
        async with TestSession() as session:
            await session.execute(
                update(Bookmark)
                .where(Bookmark.title == "https://a.com/x")
                .values(read_state=ReadState.read)
            )
            await session.commit()

    asyncio.run(mark_read())
    assert [b["url"] for b in feed(client, read_state="read")["items"]] == ["https://a.com/x"]
    assert [b["url"] for b in feed(client, read_state="unread")["items"]] == ["https://b.com/y"]
    assert len(feed(client)["items"]) == 2
    counts = client.get("/api/bookmarks/facets").json()["read_states"]
    assert counts == {"unread": 1, "read": 1}
