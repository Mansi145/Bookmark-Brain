"""Score the Ask agent on a set of questions about your own bookmarks (dev only).

An eval answers "is the agent getting better or worse?" with numbers instead of a feeling. Each
question lists the pages a good answer should cite, and the score is about citations only:

- recall: of the pages it should have cited, how many it did (expected pages only)
- precision: of the pages it cited, how many were expected (when it cited any)
- honest: for a question your bookmarks can't answer (`expect: []`), it cited nothing

Plain code does the scoring, so a run costs only the agent's own model calls, and the same answer
always gets the same score. Change something (the prompt, a tool, the search cutoff), run it
again and compare.

The questions live in eval/questions.json, which git ignores because it describes your bookmarks;
eval/questions.example.json shows the format. Each run is a LangSmith experiment: the questions
become the dataset "ask-eval", and every question links to the trace of its run, so you can see why
an answer went wrong. --local skips LangSmith and only prints the table.

    cd backend
    uv run python -m scripts.eval_agent
    uv run python -m scripts.eval_agent --local --email you@example.com

This calls the real models (free tier), one question at a time, and doesn't count towards the
daily AI limit. Never run by the tests.
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from sqlalchemy import select

from app.ai.agent.chat import CITATION
from app.ai.agent.graph import STOPPED, build_graph, run_config
from app.config import get_settings
from app.db import SessionLocal
from app.models import Bookmark, Document
from app.services import search
from app.services.urls import normalize_url
from scripts.explore_search import pick_user

QUESTIONS = Path(__file__).parent.parent / "eval" / "questions.json"
DATASET = "ask-eval"
FAILED = {"answer": "", "cited": [], "tool_calls": None}


def score(cited: list[str], expect: list[str]) -> dict[str, float]:
    """The scores that apply to one answer: citations against the expected pages (both URLs)."""
    hits = len(set(cited) & set(expect))
    if not expect:
        return {"honest": 0.0 if cited else 1.0}
    scores = {"recall": hits / len(expect)}
    if cited:
        scores["precision"] = hits / len(set(cited))
    return scores


async def urls_by_bookmark(user_id: int, sessions=SessionLocal) -> dict[int, str]:
    """Each of the user's bookmarks as its page's normalised URL, to compare with `expect`."""
    async with sessions() as session:
        rows = await session.execute(
            select(Bookmark.id, Document.normalized_url)
            .join(Document, Document.id == Bookmark.document_id)
            .where(Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None))
        )
    return dict(rows.all())


def load_questions(user_urls: set[str]) -> list[dict]:
    if not QUESTIONS.exists():
        raise SystemExit(f"No {QUESTIONS}. Copy eval/questions.example.json and write your own.")
    questions = json.loads(QUESTIONS.read_text())
    for q in questions:
        q["expect"] = [normalize_url(url) for url in q["expect"]]
        # A typo in a URL would quietly count as a miss on every run, so stop here instead.
        missing = [url for url in q["expect"] if url not in user_urls]
        if missing:
            raise SystemExit(f"Not in your bookmarks, for {q['question']!r}: {missing}")
    return questions


def make_agent(user_id: int, urls: dict[int, str], sessions=SessionLocal):
    """The thing being evaluated: one question in, the answer and the pages it cited out."""
    graph = build_graph()

    async def answer(inputs: dict) -> dict:
        try:
            state = await graph.ainvoke(
                {"messages": [HumanMessage(inputs["question"])]}, run_config(user_id, sessions)
            )
        except GraphRecursionError:
            return {"answer": STOPPED, "cited": [], "tool_calls": None}
        text = state["messages"][-1].text
        ids = dict.fromkeys(int(i) for i in CITATION.findall(text))
        tool_calls = sum(len(m.tool_calls) for m in state["messages"] if m.type == "ai")
        # An id that isn't one of the user's bookmarks (made up by the model) stays visible
        # as a wrong citation instead of disappearing.
        cited = [urls.get(i, f"unknown bookmark {i}") for i in ids]
        return {"answer": text, "cited": cited, "tool_calls": tool_calls}

    return answer


def citations(outputs: dict, reference_outputs: dict) -> dict:
    """LangSmith evaluator: hands score() the run's citations and the example's expected pages."""
    scores = score(outputs.get("cited", []), reference_outputs["expect"])
    return {"results": [{"key": key, "score": value} for key, value in scores.items()]}


def sync_dataset(client, questions: list[dict]) -> None:
    """Make the LangSmith dataset match questions.json, keeping examples that didn't change.

    Experiments are compared per example, so editing in place (rather than recreating the
    dataset) keeps earlier runs comparable with new ones.
    """
    if not client.has_dataset(dataset_name=DATASET):
        client.create_dataset(DATASET, description="Questions about my bookmarks for the Ask agent")
    existing = {e.inputs["question"]: e for e in client.list_examples(dataset_name=DATASET)}
    wanted = {q["question"]: {"expect": q["expect"]} for q in questions}
    new = [{"inputs": {"question": q}, "outputs": wanted[q]} for q in wanted.keys() - existing]
    if new:
        client.create_examples(dataset_name=DATASET, examples=new)
    for question, example in existing.items():
        if question not in wanted:
            client.delete_example(example.id)
        elif example.outputs != wanted[question]:
            client.update_example(example.id, outputs=wanted[question])


def print_table(rows: list[tuple[str, list[str], dict, dict]]) -> None:
    """One line per question (with what it missed or got wrong), then the average scores."""
    for question, expect, outputs, scores in rows:
        shown = "  ".join(f"{key} {value:.2f}" for key, value in scores.items())
        steps = outputs["tool_calls"] if outputs["tool_calls"] is not None else "-"
        print(f"{question[:60]:<62}{shown:<32}tools {steps}")
        if missed := [url for url in expect if url not in outputs["cited"]]:
            print(f"    missed: {', '.join(missed)}")
        if wrong := [url for url in outputs["cited"] if url not in expect]:
            print(f"    wrong:  {', '.join(wrong)}")
        if outputs["answer"].startswith("failed:"):
            print(f"    {outputs['answer'][:200]}")
    print()
    for key in ("recall", "precision", "honest"):
        values = [scores[key] for _, _, _, scores in rows if key in scores]
        if values:
            print(f"{key:<10} {sum(values) / len(values):.2f}  (over {len(values)} questions)")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", help="whose bookmarks (default: the user with the most)")
    parser.add_argument("--local", action="store_true", help="print the table, skip LangSmith")
    args = parser.parse_args()

    user = await pick_user(args.email)
    urls = await urls_by_bookmark(user.id)
    questions = load_questions(set(urls.values()))
    agent = make_agent(user.id, urls)
    print(f"Asking {len(questions)} questions about {user.email}'s bookmarks\n")

    rows = []
    if args.local:
        for n, q in enumerate(questions, 1):
            start = time.monotonic()
            try:
                outputs = await agent({"question": q["question"]})
            except Exception as error:  # every model failed: a miss, not the end of the run
                outputs = {**FAILED, "answer": f"failed: {error}"}
            rows.append((q["question"], q["expect"], outputs, score(outputs["cited"], q["expect"])))
            print(f"{n}/{len(questions)} in {time.monotonic() - start:.0f} s", flush=True)
        print()
    else:
        settings = get_settings()
        if not settings.langsmith_api_key:
            raise SystemExit("LANGSMITH_API_KEY isn't set in backend/.env. Use --local.")
        from langsmith import Client, aevaluate

        # The key goes in directly: it's only in the environment when everyday tracing is on.
        client = Client(api_key=settings.langsmith_api_key)
        sync_dataset(client, questions)
        results = await aevaluate(
            agent,
            data=DATASET,
            evaluators=[citations],
            experiment_prefix="ask",
            # Shown next to each experiment in LangSmith, to tell runs apart when comparing.
            metadata={"model": settings.gemini_model, "min_similarity": search.MIN_SIMILARITY},
            max_concurrency=1,  # one question at a time, gentle on the free quotas
            client=client,
        )
        async for row in results:
            outputs = row["run"].outputs or FAILED  # the run raised: LangSmith shows why
            scores = {r.key: r.score for r in row["evaluation_results"]["results"]}
            example = row["example"]
            rows.append((example.inputs["question"], example.outputs["expect"], outputs, scores))
        print(f"Experiment: {results.experiment_name} (open it in LangSmith to see each run)\n")
    print_table(rows)


if __name__ == "__main__":
    asyncio.run(main())
