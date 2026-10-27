"""Settings → Account: the counts, Download my data, and Delete account."""

from sqlalchemy import func, select, update

from app.models import AiUsage, ApiToken, Bookmark, BookmarkSource, Document, User
from app.services.usage import today
from tests.conftest import TestSession
from tests.test_sync import CHROME, feed, item, sync

EDGE = {"id": "edge-install-1", "browser": "edge"}


def delete_account(client, confirm="DELETE"):
    return client.request("DELETE", "/api/account", json={"confirm": confirm})


async def count(model, *where) -> int:
    async with TestSession() as session:
        return await session.scalar(select(func.count()).select_from(model).where(*where))


def test_counts_for_the_delete_dialog(client):
    sync(client, CHROME, [item("1", "https://a.com"), item("2", "https://b.com")], full=True)
    client.post("/api/tokens", json={"name": "Chrome"})
    client.post("/api/tokens", json={"name": "Edge"})
    assert client.get("/api/account").json() == {"bookmarks": 2, "browsers": 2}


async def test_download_my_data(client):
    sync(client, CHROME, [item("1", "https://a.com/post", "A post", folder="Reading")], full=True)
    sync(client, EDGE, [item("9", "https://a.com/post", "A post", folder="Later")], full=True)
    bookmark = feed(client)["items"][0]
    client.patch(f"/api/bookmarks/{bookmark['id']}", json={"read_state": "read"})
    async with TestSession() as session:
        await session.execute(
            update(Document).values(
                summary="It's a post.", key_points=["One point."], summary_status="done"
            )
        )
        await session.commit()
    client.post("/api/tokens", json={"name": "Chrome extension"})

    response = client.get("/api/account/export")
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="bookmark-brain-'
    )
    data = response.json()
    assert data["account"]["email"] == "ada@example.com"
    [exported] = data["bookmarks"]
    assert exported["url"] == "https://a.com/post"
    assert exported["read_state"] == "read"
    assert sorted((s["browser"], s["folder"]) for s in exported["saved_in"]) == [
        ("chrome", "Reading"),
        ("edge", "Later"),
    ]
    assert exported["summary"] == "It's a post."
    assert exported["key_points"] == ["One point."]
    [browser] = data["connected_browsers"]
    assert browser["name"] == "Chrome extension"
    assert "token" not in str(browser).lower()  # names and dates only, never the secret


def test_only_from_the_web_app_not_an_extension_token(client, anon_client):
    token = client.post("/api/tokens", json={}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert anon_client.get("/api/account/export", headers=headers).status_code == 401
    response = anon_client.request(
        "DELETE", "/api/account", headers=headers, json={"confirm": "DELETE"}
    )
    assert response.status_code == 401


async def test_delete_needs_the_typed_confirmation(client):
    response = delete_account(client, confirm="delete")
    assert response.status_code == 400
    assert await count(User) == 1


async def test_delete_removes_everything_personal_but_keeps_shared_pages(
    client, client_for, other_user
):
    sync(client, CHROME, [item("1", "https://a.com"), item("2", "https://b.com")], full=True)
    client.post("/api/tokens", json={})
    other = client_for(other_user)
    sync(other, CHROME, [item("1", "https://a.com")], full=True)
    async with TestSession() as session:
        session.add(AiUsage(user_id=1, day=today(), summaries=3))
        await session.commit()

    response = delete_account(client)
    assert response.status_code == 204
    assert "bb_session" in response.headers.get("set-cookie", "")  # signed out

    assert await count(User, User.email == "ada@example.com") == 0
    assert await count(Bookmark, Bookmark.user_id == 1) == 0
    assert await count(BookmarkSource, BookmarkSource.user_id == 1) == 0
    assert await count(ApiToken, ApiToken.user_id == 1) == 0
    assert await count(AiUsage, AiUsage.user_id == 1) == 0
    # Shared per-URL pages (and their summaries) stay; the other user is untouched.
    assert await count(Document) == 2
    assert len(feed(other)["items"]) == 1
    assert client.get("/api/me").status_code == 401
