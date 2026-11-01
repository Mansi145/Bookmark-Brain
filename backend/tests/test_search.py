"""Search: keyword and meaning matches, the weighted merge, filters, the top 10, highlighting,
and the query cache and throttle.

The embedding model is faked: TopicEmbedder gives texts about the same topic the same direction,
so "meaning" is predictable without calling Gemini.
"""

import itertools
from datetime import UTC, datetime

import pytest

from app.ai import llm
from app.models import (
    EMBEDDING_DIMENSIONS,
    Bookmark,
    BookmarkSource,
    Document,
    DocumentStatus,
    ReadState,
)
from app.services import search
from tests.conftest import FakeEmbedder, TestSession

HOST = "http://93.184.216.34"
_ids = itertools.count()

# Words that mean the same thing share a topic (a direction in the fake vector space).
TOPICS = {"trousers": 0, "pants": 0, "guitar": 1, "music": 1, "postgres": 2, "database": 2}


class TopicEmbedder(FakeEmbedder):
    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for word, topic in TOPICS.items():
            if word in text.lower():
                vector[topic] += 1.0
        vector[-1] = 0.01  # never all zeros: a zero vector has no direction
        return vector


@pytest.fixture(autouse=True)
def fresh_query_embeddings(monkeypatch):
    """A cache and throttle per test."""
    monkeypatch.setattr(search, "query_embeddings", search.QueryEmbeddings())


@pytest.fixture
def topics(monkeypatch) -> TopicEmbedder:
    embedder = TopicEmbedder()
    monkeypatch.setattr(llm, "get_embedder", lambda: embedder)
    return embedder


async def save(
    user,
    title: str,
    *,
    saved_title: str | None = None,
    folder: str = "Bookmarks bar",
    browser: str = "chrome",
    read_state: ReadState = ReadState.unread,
    **document_fields,
) -> int:
    """A bookmark for `user`. Its embedding comes from TopicEmbedder's rules on the title."""
    now = datetime.now(UTC)
    url = f"{HOST}/page-{next(_ids)}"
    document_fields.setdefault("status", DocumentStatus.fetched)
    document = Document(
        url=url,
        normalized_url=url,
        site="example.com",
        title=title,
        embedding=TopicEmbedder()._vector(title),
        **document_fields,
    )
    bookmark = Bookmark(
        user_id=user.id,
        document=document,
        title=saved_title or title,
        added_at=now,
        read_state=read_state,
    )
    source = BookmarkSource(
        user_id=user.id,
        bookmark=bookmark,
        source_id="install-1",
        browser=browser,
        node_id=str(next(_ids)),
        title=bookmark.title,
        folder_path=folder,
        added_at=now,
    )
    async with TestSession() as session:
        session.add_all([document, bookmark, source])
        await session.commit()
        return bookmark.id


def titles(client, q: str, **params) -> list[str]:
    response = client.get("/api/search", params={"q": q, **params})
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()["items"]]


# --- Keyword matches ---------------------------------------------------------------


async def test_a_title_match_ranks_above_a_mention_in_the_text(client, user):
    await save(user, "Cooking at home", content_text="A side note about Django.")
    await save(user, "Django file uploads", content_text="Storing files.")

    assert titles(client, "django")[:2] == ["Django file uploads", "Cooking at home"]


async def test_finds_the_title_you_saved_and_your_folder_names(client, user):
    await save(user, "Sign in", saved_title="Team wiki")
    await save(user, "Banana bread", folder="Bookmarks bar/Recipes")

    assert titles(client, "wiki")[0] == "Team wiki"  # results show the title you saved
    assert titles(client, "recipes")[0] == "Banana bread"


async def test_the_browsers_root_folder_doesnt_match(client, user, fake_embedder):
    fake_embedder.error = llm.RateLimited("429")  # keyword matches only, to see them alone
    await save(user, "Banana bread", folder="Bookmarks bar/Recipes")

    assert titles(client, "bookmarks") == []


# --- Meaning matches and the merge -----------------------------------------------------


async def test_finds_pages_about_the_same_thing_in_other_words(client, user, topics):
    await save(user, "Hiking trousers")
    await save(user, "Learn the guitar")

    assert titles(client, "waterproof pants")[0] == "Hiking trousers"


async def test_pages_both_halves_find_rank_first(client, user, topics):
    await save(user, "Postgres tuning")  # meaning only: a postgres page without the word "database"
    await save(user, "Database indexes for Postgres")  # keyword and meaning

    assert titles(client, "database")[:2] == ["Database indexes for Postgres", "Postgres tuning"]


async def test_keyword_matches_alone_when_meaning_search_is_down(client, user, topics):
    await save(user, "Hiking trousers")  # would only match by meaning
    await save(user, "Waterproof jackets")
    topics.error = llm.RateLimited("429 RESOURCE_EXHAUSTED")

    response = client.get("/api/search", params={"q": "waterproof pants"})
    assert response.status_code == 200  # never an error: it looks like any other search
    assert [item["title"] for item in response.json()["items"]] == []  # all words must match

    assert titles(client, "waterproof") == ["Waterproof jackets"]


def test_fuse_weights_keyword_matches_and_rewards_agreement():
    # 1 is first by keyword only, 2 first by meaning only, 3 second in both lists.
    assert search.fuse([1, 3], [2, 3]) == [3, 1, 2]
    # Keyword priority: first by keyword (1.5/61) beats first by meaning (1/61).
    assert search.fuse([1], [2]) == [1, 2]


# --- Who and what is searched ----------------------------------------------------------


async def test_only_your_own_bookmarks(client, user, other_user):
    await save(other_user, "Django file uploads")
    assert titles(client, "django") == []


async def test_everything_you_saved_is_searched(client, user):
    await save(user, "Django read", read_state=ReadState.read)
    await save(user, "Django dead", status=DocumentStatus.dead)
    await save(user, "Django sign in", access="login", status=DocumentStatus.failed)

    assert sorted(titles(client, "django")) == ["Django dead", "Django read", "Django sign in"]


async def test_sidebar_filters_narrow_the_search(client, user):
    await save(user, "Django in Chrome", folder="Bookmarks bar/Work", browser="chrome")
    await save(user, "Django in Edge", folder="Favorites bar/Home", browser="edge")

    assert titles(client, "django", browser="edge") == ["Django in Edge"]
    assert titles(client, "django", folder="Bookmarks bar/Work") == ["Django in Chrome"]


async def test_shows_the_best_10(client, user):
    for i in range(12):
        await save(user, f"Django tip {i}")

    response = client.get("/api/search", params={"q": "django"})
    body = response.json()
    assert len(body["items"]) == 10
    assert body["more"] is True  # "Top 10 matches"


async def test_says_when_everything_fits(client, user, fake_embedder):
    fake_embedder.error = llm.RateLimited("429")  # keyword only: meaning would fill every slot
    await save(user, "Django tip")

    assert client.get("/api/search", params={"q": "django"}).json()["more"] is False


async def test_marks_the_matched_words(client, user):
    await save(user, "Index types", summary="Indexes speed up queries. Pick the right index.")

    [result] = client.get("/api/search", params={"q": "index"}).json()["items"]
    marked = "\x02Indexes\x03 speed up queries. Pick the right \x02index\x03."
    assert result["highlighted"] == marked


async def test_an_empty_query_is_rejected(client):
    assert client.get("/api/search", params={"q": "   "}).status_code == 422


async def test_needs_sign_in(anon_client):
    assert anon_client.get("/api/search", params={"q": "django"}).status_code == 401


# --- Query cache and throttle --------------------------------------------------------


async def test_the_same_query_is_embedded_once(fake_embedder):
    embeddings = search.QueryEmbeddings()
    first = await embeddings.get(1, "Django uploads")
    again = await embeddings.get(1, "  django   UPLOADS ")

    assert first == again
    assert fake_embedder.queries == ["django uploads"]


async def test_over_the_throttle_searches_by_keyword_without_waiting_long(fake_embedder):
    embeddings = search.QueryEmbeddings()
    embeddings.PER_MINUTE = 2
    assert await embeddings.get(1, "one") is not None
    assert await embeddings.get(1, "two") is not None

    assert await embeddings.get(1, "three") is None  # a slot frees in ~60 s: too long to wait
    assert await embeddings.get(2, "three") is not None  # other users aren't affected
    assert await embeddings.get(1, "one") is not None  # cached queries cost nothing
    assert fake_embedder.queries == ["one", "two", "three"]
