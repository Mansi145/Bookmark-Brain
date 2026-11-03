"""The chat agent: its tools (only ever the signed-in user's bookmarks), the hand-written loop
that runs them, and the LangGraph graph that does the same.

The model is LangChain's fake chat model answering from a script, so no test calls a real model.
"""

import itertools
import json

import pytest
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from app.ai import llm
from app.ai.agent import graph, manual_loop
from app.ai.agent.tools import PAGE_CHARS, read_bookmark, search_bookmarks
from app.services import search
from tests.conftest import TestSession, calls_tool, script
from tests.test_search import TopicEmbedder, save


@pytest.fixture(autouse=True)
def topics(monkeypatch) -> None:
    monkeypatch.setattr(search, "query_embeddings", search.QueryEmbeddings())
    monkeypatch.setattr(llm, "get_embedder", lambda: TopicEmbedder())


def config(user) -> dict:
    return {"configurable": {"user_id": user.id, "sessions": TestSession}}


async def test_search_finds_only_the_users_own_bookmarks(user, other_user):
    await save(user, "Postgres indexes explained", summary="B-tree and GIN indexes, compared.")
    await save(other_user, "Postgres for beginners")

    found = json.loads(await search_bookmarks.ainvoke({"query": "postgres"}, config(user)))
    assert [(b["title"], b["summary"]) for b in found] == [
        ("Postgres indexes explained", "B-tree and GIN indexes, compared.")
    ]
    assert found[0]["read"] is False


async def test_reading_another_users_bookmark_finds_nothing(user, other_user):
    theirs = await save(other_user, "Grace's private notes", content_text="Secret plans.")

    result = json.loads(await read_bookmark.ainvoke({"bookmark_id": theirs}, config(user)))
    assert result == {"error": "No bookmark with that id."}


async def test_reading_a_bookmark_sends_only_the_start_of_a_long_page(user):
    mine = await save(user, "A very long essay", content_text="word " * 5_000)

    result = json.loads(await read_bookmark.ainvoke({"bookmark_id": mine}, config(user)))
    assert result["title"] == "A very long essay"
    assert len(result["text"]) == PAGE_CHARS


def test_the_model_never_sees_or_sets_the_user_id():
    # The schema sent to the model has only the arguments it may fill in.
    assert set(search_bookmarks.args) == {"query"}
    assert set(read_bookmark.args) == {"bookmark_id"}


async def test_the_loop_runs_the_tool_and_sends_back_its_result(user, monkeypatch):
    mine = await save(user, "Postgres indexes explained")
    model = script(
        monkeypatch,
        calls_tool("search_bookmarks", query="postgres"),
        AIMessage(f"You saved one page about indexes [bookmark:{mine}]."),
    )

    answer = await manual_loop.ask("postgres?", user.id, sessions=TestSession, show=lambda _: None)

    assert answer == f"You saved one page about indexes [bookmark:{mine}]."
    second_call = model.sent[1]
    assert isinstance(second_call[-1], ToolMessage)
    assert second_call[-1].tool_call_id == "call-search_bookmarks"
    assert "Postgres indexes explained" in second_call[-1].content


async def test_the_loop_tells_the_model_about_a_tool_that_doesnt_exist(user, monkeypatch):
    model = script(monkeypatch, calls_tool("delete_everything"), AIMessage("Sorry."))

    await manual_loop.ask("hi", user.id, sessions=TestSession, show=lambda _: None)
    assert "no tool called delete_everything" in model.sent[1][-1].content


async def test_the_loop_gives_up_after_too_many_steps(user, monkeypatch):
    model = script(monkeypatch)
    model.messages = itertools.repeat(calls_tool("search_bookmarks", query="x"))

    answer = await manual_loop.ask("x", user.id, sessions=TestSession, show=lambda _: None)
    assert answer == "I stopped after too many steps without an answer."
    assert len(model.sent) == manual_loop.MAX_STEPS


# --- The LangGraph version (graph.py) ---------------------------------------------------


async def test_the_graph_runs_the_tool_and_answers(user, monkeypatch):
    mine = await save(user, "Postgres indexes explained")
    model = script(
        monkeypatch,
        calls_tool("search_bookmarks", query="postgres"),
        AIMessage(f"One page about indexes [bookmark:{mine}]."),
    )

    answer = await graph.ask("postgres?", user.id, sessions=TestSession)

    assert answer == f"One page about indexes [bookmark:{mine}]."
    second_call = model.sent[1]
    assert isinstance(second_call[0], SystemMessage)  # the prompt goes with every call
    assert isinstance(second_call[-1], ToolMessage)
    assert "Postgres indexes explained" in second_call[-1].content


async def test_the_graph_runs_every_tool_call_in_a_reply(user, monkeypatch):
    first = await save(user, "Postgres indexes explained")
    second = await save(user, "Learn the guitar")
    both = AIMessage(
        "",
        tool_calls=[
            {"name": "read_bookmark", "args": {"bookmark_id": first}, "id": "call-a"},
            {"name": "read_bookmark", "args": {"bookmark_id": second}, "id": "call-b"},
        ],
    )
    model = script(monkeypatch, both, AIMessage("Done."))

    await graph.ask("compare them", user.id, sessions=TestSession)
    results = {m.tool_call_id: m.content for m in model.sent[1] if isinstance(m, ToolMessage)}
    assert "Postgres" in results["call-a"]
    assert "guitar" in results["call-b"]


async def test_the_graph_keeps_other_users_bookmarks_out(user, other_user, monkeypatch):
    theirs = await save(other_user, "Grace's private notes")
    model = script(monkeypatch, calls_tool("read_bookmark", bookmark_id=theirs), AIMessage("No."))

    await graph.ask("read it", user.id, sessions=TestSession)
    assert "No bookmark with that id" in model.sent[1][-1].content


async def test_the_graph_tells_the_model_about_a_tool_that_doesnt_exist(user, monkeypatch):
    model = script(monkeypatch, calls_tool("delete_everything"), AIMessage("Sorry."))

    await graph.ask("hi", user.id, sessions=TestSession)
    assert "delete_everything is not a valid tool" in model.sent[1][-1].content


async def test_the_graph_gives_up_after_too_many_steps(user, monkeypatch):
    model = script(monkeypatch)
    # A new message each time, as from a real model: add_messages treats a message it has seen
    # before (same id) as a replacement, not a new one.
    model.messages = (calls_tool("search_bookmarks", query="x") for _ in itertools.count())

    assert await graph.ask("x", user.id, sessions=TestSession) == graph.STOPPED
    assert len(model.sent) == 6  # model calls, as in the hand-written loop
