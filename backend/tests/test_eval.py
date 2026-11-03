"""The Ask eval's scoring (scripts/eval_agent.py): citations against the expected pages.

The agent runs on the scripted fake model, so no test calls a real model or LangSmith.
"""

import pytest

from app.ai.agent import graph
from scripts import eval_agent
from scripts.eval_agent import citations, make_agent, score, urls_by_bookmark
from tests.conftest import TestSession, calls_tool, script
from tests.test_agent import topics  # noqa: F401  (search with the topic embedder)
from tests.test_search import save

A, B, C = "https://a.example/", "https://b.example/", "https://c.example/"


def test_an_answer_citing_every_expected_page_scores_full_marks():
    assert score([A, B], [A, B]) == {"recall": 1.0, "precision": 1.0}


def test_a_missed_page_lowers_recall_and_a_wrong_one_lowers_precision():
    assert score([A, C], [A, B]) == {"recall": 0.5, "precision": 0.5}


def test_citing_nothing_when_pages_were_expected_has_no_precision_to_score():
    assert score([], [A]) == {"recall": 0.0}


def test_a_question_with_no_answer_is_scored_on_citing_nothing():
    assert score([], []) == {"honest": 1.0}
    assert score([A], []) == {"honest": 0.0}


def test_the_langsmith_evaluator_reports_each_score():
    result = citations({"cited": [A]}, {"expect": [A, B]})
    assert result == {
        "results": [{"key": "recall", "score": 0.5}, {"key": "precision", "score": 1.0}]
    }


async def test_the_agent_under_test_returns_the_pages_it_cited(monkeypatch, user):
    mine = await save(user, "Postgres indexes explained")
    urls = await urls_by_bookmark(user.id, TestSession)
    script(
        monkeypatch,
        calls_tool("search_bookmarks", query="postgres"),
        f"Use a B-tree index [bookmark:{mine}] [bookmark:999].",
    )

    outputs = await make_agent(user.id, urls, TestSession)({"question": "postgres?"})
    assert outputs["cited"] == [urls[mine], "unknown bookmark 999"]
    assert outputs["tool_calls"] == 1


async def test_a_run_that_never_answers_counts_as_stopped(monkeypatch, user):
    monkeypatch.setattr(graph, "RECURSION_LIMIT", 2)
    script(monkeypatch, *[calls_tool("search_bookmarks", query="x")] * 3)

    outputs = await make_agent(user.id, {}, TestSession)({"question": "loop forever"})
    assert outputs == {"answer": graph.STOPPED, "cited": [], "tool_calls": None}


def test_a_url_missing_from_your_bookmarks_stops_before_any_question(tmp_path, monkeypatch):
    questions = tmp_path / "questions.json"
    questions.write_text('[{"question": "q", "expect": ["https://typo.example/"]}]')
    monkeypatch.setattr(eval_agent, "QUESTIONS", questions)

    with pytest.raises(SystemExit, match="Not in your bookmarks"):
        eval_agent.load_questions({A})
