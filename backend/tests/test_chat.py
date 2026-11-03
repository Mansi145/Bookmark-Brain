"""POST /api/chat and GET /api/chat/recent: the streamed answer, follow-ups in an open chat, the
first questions kept for Recent questions, the daily limit, and whose chats and bookmarks it sees.

The model is the scripted fake from conftest, so no test calls a real model.
"""

import json

import pytest
from langchain_core.messages import AIMessage

from app.ai import llm
from app.ai.agent import chat
from app.config import get_settings
from app.services import search
from tests.conftest import calls_tool, script
from tests.test_search import TopicEmbedder, save


@pytest.fixture(autouse=True)
def fresh(monkeypatch) -> None:
    """New open chats, query cache and topic embeddings for each test."""
    monkeypatch.setattr(chat, "open_chats", chat.OpenChats())
    monkeypatch.setattr(search, "query_embeddings", search.QueryEmbeddings())
    monkeypatch.setattr(llm, "get_embedder", lambda: TopicEmbedder())


def ask(client, message: str, chat_id: str | None = None) -> list[tuple[str, dict]]:
    """Ask, and read the Server-Sent Events: [(kind, data), …]."""
    response = client.post("/api/chat", json={"message": message, "chat_id": chat_id})
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for block in response.text.strip().split("\n\n"):
        kind, data = block.split("\n", 1)
        events.append((kind.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return events


def replies(text: str = "OK."):
    """A new reply for every call, for as long as the test asks."""
    while True:
        yield AIMessage(text)


async def test_streams_the_steps_the_answer_and_its_bookmarks(client, user, monkeypatch):
    indexes = await save(user, "Postgres indexes explained")
    await save(user, "Postgres for beginners")
    script(
        monkeypatch,
        calls_tool("search_bookmarks", query="postgres"),
        AIMessage(f"Indexes are covered here [bookmark: {indexes}]."),
    )

    events = ask(client, "what do I have on postgres?")

    kinds = [kind for kind, _ in events]
    assert (kinds[0], kinds[-1]) == ("chat", "done")
    steps = [data for kind, data in events if kind == "step"]
    assert steps == [
        {
            "id": "call-search_bookmarks",
            "status": "running",
            "tool": "search_bookmarks",
            "args": {"query": "postgres"},
        },
        {"id": "call-search_bookmarks", "status": "done", "found": 2},
    ]
    tokens = "".join(data["text"] for kind, data in events if kind == "token")
    assert tokens == f"Indexes are covered here [bookmark: {indexes}]."  # word by word
    done = events[-1][1]
    assert done["answer"] == f"Indexes are covered here [bookmark:{indexes}]."  # tidied
    assert [b["title"] for b in done["sources"]] == ["Postgres indexes explained"]
    assert [b["title"] for b in done["also_found"]] == ["Postgres for beginners"]


async def test_a_follow_up_continues_the_chat(client, user, monkeypatch):
    model = script(monkeypatch, AIMessage("Hello."), AIMessage("Still here."))

    chat_id = ask(client, "first question")[0][1]["chat_id"]
    ask(client, "and a follow-up", chat_id)

    conversation = [m.content for m in model.sent[1][1:]]  # after the system prompt
    assert conversation == ["first question", "Hello.", "and a follow-up"]


async def test_a_new_chat_starts_empty(client, user, monkeypatch):
    model = script(monkeypatch, AIMessage("Hello."), AIMessage("Hi again."))

    ask(client, "first question")
    ask(client, "another chat")
    assert [m.content for m in model.sent[1][1:]] == ["another chat"]


async def test_a_chat_id_never_opens_another_users_chat(
    client, client_for, other_user, monkeypatch
):
    model = script(monkeypatch, AIMessage("Ada's answer."), AIMessage("Fresh."))

    chat_id = ask(client, "Ada's question")[0][1]["chat_id"]
    ask(client_for(other_user), "follow-up", chat_id)
    assert [m.content for m in model.sent[1][1:]] == ["follow-up"]


async def test_idle_chats_are_forgotten(client, user, monkeypatch):
    model = script(monkeypatch, AIMessage("One."), AIMessage("Two."), AIMessage("Three."))
    chat.open_chats.MAX_CHATS = 1  # as if the first chat had been idle too long

    first = ask(client, "first chat")[0][1]["chat_id"]
    ask(client, "second chat")
    ask(client, "back to the first", first)
    assert [m.content for m in model.sent[2][1:]] == ["back to the first"]


async def test_cited_ids_that_arent_the_users_bookmarks_are_left_out(
    client, user, other_user, monkeypatch
):
    theirs = await save(other_user, "Grace's private notes")
    script(monkeypatch, AIMessage(f"See [bookmark:{theirs}] and [bookmark:999]."))

    done = ask(client, "anything?")[-1][1]
    assert (done["sources"], done["also_found"]) == ([], [])


async def test_only_each_new_chats_first_question_is_kept(client, user, monkeypatch):
    script(monkeypatch).messages = replies()

    first = ask(client, "Q1")[0][1]["chat_id"]
    ask(client, "a follow-up isn't kept", first)
    for question in ("Q2", "Q3", "Q4", "q2"):  # asking Q2 again moves it to the top
        ask(client, question)

    recent = client.get("/api/chat/recent").json()
    assert [q["question"] for q in recent] == ["q2", "Q4", "Q3"]
    exported = client.get("/api/account/export").json()["recent_questions"]
    assert [q["question"] for q in exported] == ["q2", "Q4", "Q3"]


async def test_each_question_counts_towards_the_daily_ai_limit(client, user, monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_daily_limit_per_user", 1)
    model = script(monkeypatch)
    model.messages = replies()

    ask(client, "first")
    response = client.post("/api/chat", json={"message": "second"})

    assert response.status_code == 429
    assert len(model.sent) == 1  # the second never reached the model
    assert client.get("/api/usage").json()["summaries_used"] == 1


async def test_says_ai_is_busy_and_gives_the_question_back_when_no_model_can_answer(
    client, user, monkeypatch
):
    def down():
        raise RuntimeError("every provider failed")
        yield

    script(monkeypatch).messages = down()

    events = ask(client, "hello?")
    assert events[-1] == ("error", {"reason": "busy", "message": "Couldn't answer right now"})
    assert client.get("/api/usage").json()["summaries_used"] == 0  # it didn't count


async def test_only_from_the_web_app(client, anon_client):
    token = client.post("/api/tokens", json={}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = anon_client.post("/api/chat", json={"message": "hi"}, headers=headers)
    assert response.status_code == 401
    assert anon_client.get("/api/chat/recent", headers=headers).status_code == 401


async def test_a_blank_question_is_refused(client):
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422
