"""Tags: starter tags, the limits, managing tags, tagging bookmarks one or many at a time, and
filtering the feed, its counts and search by several tags."""

from sqlalchemy import select

from app.api import auth as auth_api
from app.auth.security import GoogleIdentity
from app.models import RemovedTag, Tag, User
from app.services import tags
from tests.conftest import TestSession
from tests.test_search import TopicEmbedder, save  # noqa: F401  (save needs the embedder's vectors)


def make_tag(client, name: str) -> int:
    response = client.post("/api/tags", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def tag_bookmark(client, bookmark_id: int, name: str):
    return client.post(f"/api/bookmarks/{bookmark_id}/tags", json={"name": name})


def tag_names(client, bookmark_id: int) -> list[str]:
    return [t["name"] for t in client.get(f"/api/bookmarks/{bookmark_id}").json()["tags"]]


# --- Starter tags and names ----------------------------------------------------------------


def test_a_new_account_starts_with_the_starter_tags(anon_client, monkeypatch):
    async def fake_verify(credential):
        return GoogleIdentity(
            {"sub": "new-sub", "email": "new@example.com", "name": "New", "picture": None}
        )

    monkeypatch.setattr(auth_api, "verify_google_credential", fake_verify)
    assert anon_client.post("/api/auth/google", json={"credential": "x"}).status_code == 200

    listed = anon_client.get("/api/tags").json()
    assert sorted(t["name"] for t in listed) == sorted(tags.STARTER_TAGS)
    assert {t["count"] for t in listed} == {0}


def test_names_are_trimmed_and_unique_whatever_the_case(client):
    tag_id = make_tag(client, "  Web   performance ")
    assert client.get("/api/tags").json() == [{"id": tag_id, "name": "Web performance", "count": 0}]

    taken = client.post("/api/tags", json={"name": "web PERFORMANCE"})
    assert taken.status_code == 409
    assert taken.json()["detail"] == "tag_name_taken"


def test_names_must_be_1_to_30_characters(client):
    assert client.post("/api/tags", json={"name": "   "}).status_code == 422
    assert client.post("/api/tags", json={"name": "x" * 31}).status_code == 422
    assert client.post("/api/tags", json={"name": "x" * 30}).status_code == 201


async def test_an_account_has_at_most_50_tags(client, user):
    async with TestSession() as session:
        session.add_all(Tag(user_id=user.id, name=f"Tag {n}") for n in range(tags.MAX_PER_USER))
        await session.commit()

    response = client.post("/api/tags", json={"name": "One more"})
    assert response.status_code == 409
    assert response.json()["detail"] == "tag_limit"


# --- Tagging one bookmark ------------------------------------------------------------------


async def test_add_tag_uses_an_existing_tag_or_creates_one(client, user):
    bookmark = await save(user, "Postgres indexes")
    existing = make_tag(client, "Databases")

    assert tag_bookmark(client, bookmark, "databases").status_code == 200  # any case
    response = tag_bookmark(client, bookmark, "Indexing")  # "+ Create tag"
    assert [t["name"] for t in response.json()["tags"]] == ["Databases", "Indexing"]
    assert response.json()["tags"][0]["id"] == existing
    # Adding a tag it already has is fine and changes nothing.
    assert len(tag_bookmark(client, bookmark, "Indexing").json()["tags"]) == 2


async def test_a_bookmark_has_at_most_5_tags(client, user):
    bookmark = await save(user, "A well-tagged page")
    for n in range(tags.MAX_PER_BOOKMARK):
        assert tag_bookmark(client, bookmark, f"Tag {n}").status_code == 200

    response = tag_bookmark(client, bookmark, "Sixth")
    assert response.status_code == 409
    assert response.json()["detail"] == "bookmark_tag_limit"
    # Nothing from a refused request is kept, not even the new tag.
    assert "Sixth" not in [t["name"] for t in client.get("/api/tags").json()]


async def test_a_removed_tag_is_remembered_until_added_again_by_hand(client, user):
    bookmark = await save(user, "Sourdough starter guide")
    cooking = tag_bookmark(client, bookmark, "Cooking").json()["tags"][0]["id"]

    response = client.delete(f"/api/bookmarks/{bookmark}/tags/{cooking}")
    assert response.json()["tags"] == []
    async with TestSession() as session:
        assert await session.get(RemovedTag, (bookmark, cooking)) is not None

    tag_bookmark(client, bookmark, "Cooking")
    async with TestSession() as session:
        assert await session.get(RemovedTag, (bookmark, cooking)) is None


async def test_other_users_tags_and_bookmarks_are_not_found(client, client_for, user, other_user):
    mine = await save(user, "Mine")
    theirs = await save(other_user, "Theirs")
    their_tag = make_tag(client_for(other_user), "Private")

    assert tag_bookmark(client, theirs, "Mine now").status_code == 404
    assert client.patch(f"/api/tags/{their_tag}", json={"name": "Renamed"}).status_code == 404
    assert client.delete(f"/api/tags/{their_tag}").status_code == 404
    assert (
        client.post(f"/api/tags/{their_tag}/add", json={"bookmark_ids": [mine]}).status_code == 404
    )
    # Removing someone else's tag from your bookmark does nothing.
    assert client.delete(f"/api/bookmarks/{mine}/tags/{their_tag}").status_code == 200


# --- Managing tags -------------------------------------------------------------------------


async def test_rename_refuses_another_tags_name_but_allows_a_case_change(client):
    ai = make_tag(client, "ai")
    make_tag(client, "Machine learning")

    taken = client.patch(f"/api/tags/{ai}", json={"name": "machine learning"})
    assert (taken.status_code, taken.json()["detail"]) == (409, "tag_name_taken")
    assert client.patch(f"/api/tags/{ai}", json={"name": "AI"}).json()["name"] == "AI"


async def test_merge_moves_bookmarks_to_the_other_tag_and_deletes_it(client, user):
    both = await save(user, "Both tags")
    only_old = await save(user, "Old tag only")
    tag_bookmark(client, both, "Performance")
    tag_bookmark(client, both, "Web performance")
    old = tag_bookmark(client, only_old, "Performance").json()["tags"][0]["id"]
    new = next(t["id"] for t in client.get("/api/tags").json() if t["name"] == "Web performance")

    response = client.post(f"/api/tags/{old}/merge", json={"into": new})
    assert response.json() == {"id": new, "name": "Web performance"}
    assert tag_names(client, both) == ["Web performance"]
    assert tag_names(client, only_old) == ["Web performance"]
    assert [t["name"] for t in client.get("/api/tags").json()] == ["Web performance"]

    same = client.post(f"/api/tags/{new}/merge", json={"into": new})
    assert (same.status_code, same.json()["detail"]) == (409, "tag_merge_same")


async def test_deleting_a_tag_keeps_the_bookmarks_and_their_other_tags(client, user):
    bookmark = await save(user, "Design systems")
    design = tag_bookmark(client, bookmark, "Design").json()["tags"][0]["id"]
    tag_bookmark(client, bookmark, "Frontend")

    assert client.delete(f"/api/tags/{design}").status_code == 204
    assert tag_names(client, bookmark) == ["Frontend"]


# --- Select mode ---------------------------------------------------------------------------


async def test_add_to_many_skips_bookmarks_that_already_have_5_tags(client, user, other_user):
    plain, again, full = [await save(user, title) for title in ("Plain", "Again", "Full")]
    theirs = await save(other_user, "Not yours")
    programming = make_tag(client, "Programming")
    tag_bookmark(client, again, "Programming")
    for n in range(tags.MAX_PER_BOOKMARK):
        tag_bookmark(client, full, f"Tag {n}")

    response = client.post(
        f"/api/tags/{programming}/add", json={"bookmark_ids": [plain, again, full, theirs]}
    )
    # "Added Programming to 1 bookmark. 1 already had 5 tags…". `again` already had it, and
    # `theirs` isn't yours.
    assert response.json() == {"changed": 1, "skipped": 1}
    assert tag_names(client, plain) == ["Programming"]


async def test_remove_from_many(client, user):
    one, two, untagged = [await save(user, title) for title in ("One", "Two", "Untagged")]
    news = tag_bookmark(client, one, "News").json()["tags"][0]["id"]
    tag_bookmark(client, two, "News")

    response = client.post(f"/api/tags/{news}/remove", json={"bookmark_ids": [one, two, untagged]})
    assert response.json() == {"changed": 2, "skipped": 0}
    assert tag_names(client, one) == tag_names(client, two) == []


# --- Filtering -----------------------------------------------------------------------------


async def test_the_feed_shows_bookmarks_with_all_the_picked_tags(client, user):
    both = await save(user, "Postgres for data teams")
    data_only = await save(user, "Spreadsheets")
    await save(user, "Untagged")
    tag_bookmark(client, both, "Data")
    tag_bookmark(client, both, "Postgres")
    data = tag_bookmark(client, data_only, "Data").json()["tags"][0]["id"]
    postgres = next(t["id"] for t in client.get("/api/tags").json() if t["name"] == "Postgres")

    def titles(*tag_ids):
        params = [("tag", t) for t in tag_ids]
        return {b["title"] for b in client.get("/api/bookmarks", params=params).json()["items"]}

    assert titles(data) == {"Postgres for data teams", "Spreadsheets"}
    assert titles(data, postgres) == {"Postgres for data teams"}
    assert client.get("/api/bookmarks", params=[("tag", n) for n in range(6)]).status_code == 422


async def test_facets_count_tags_per_section_and_narrow_the_totals(client, user):
    from app.models import DocumentStatus

    readable = await save(user, "Readable page")
    dead = await save(user, "Gone page", status=DocumentStatus.dead)
    tag_bookmark(client, readable, "Science")
    science = tag_bookmark(client, dead, "Science").json()["tags"][0]["id"]
    make_tag(client, "Unused")  # not listed: the sidebar shows unused tags separately

    main = client.get("/api/bookmarks/facets").json()
    assert main["tags"] == [{"id": science, "name": "Science", "count": 1}]
    assert main["total"] == 1
    narrowed = client.get("/api/bookmarks/facets", params={"tag": science}).json()
    assert narrowed["total"] == 1  # the readable one; the dead link is in its own section
    dead_section = client.get("/api/bookmarks/facets", params={"section": "dead"}).json()
    assert dead_section["tags"][0]["count"] == 1


async def test_search_is_narrowed_by_tags(client, user, fake_embedder):
    tagged = await save(user, "Postgres indexes explained")
    await save(user, "Postgres replication")
    databases = tag_bookmark(client, tagged, "Databases").json()["tags"][0]["id"]

    response = client.get("/api/search", params={"q": "postgres", "tag": databases})
    assert [r["title"] for r in response.json()["items"]] == ["Postgres indexes explained"]
    assert response.json()["items"][0]["tags"] == [{"id": databases, "name": "Databases"}]


async def test_download_my_data_includes_tags(client, user):
    bookmark = await save(user, "Travel tips")
    tag_bookmark(client, bookmark, "Travel")
    make_tag(client, "Unused")

    data = client.get("/api/account/export").json()
    assert data["bookmarks"][0]["tags"] == ["Travel"]
    assert data["tags"] == [{"name": "Travel", "bookmarks": 1}, {"name": "Unused", "bookmarks": 0}]


async def test_deleting_the_account_deletes_its_tags(client, user):
    make_tag(client, "Gone soon")
    assert client.request("DELETE", "/api/account", json={"confirm": "DELETE"}).status_code == 204
    async with TestSession() as session:
        assert (await session.scalars(select(Tag))).all() == []
        assert await session.get(User, user.id) is None
