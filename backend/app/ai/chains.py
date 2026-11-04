"""Chains: a prompt + a model + an output schema, for one task each.

summarise_document() builds the prompt from what we stored about a page, asks the model for a
`Summary` (structured output, so no text parsing), and checks the answer before anyone sees it.
pick_tags() does the same for choosing a bookmark's tags from the user's own list.
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.ai import llm

PROMPTS = Path(__file__).parent / "prompts"

# About 3,000 tokens. Gemini could take far more, but Groq's free tier (the fallback) allows
# only 8,000 tokens a minute, and the opening of an article is what a summary needs anyway.
MAX_ARTICLE_CHARS = 12_000
MAX_SUMMARY_CHARS = 1_200  # the prompt asks for about 800; allow some slack before rejecting
MAX_KEY_POINTS = 5


class Summary(BaseModel):
    """What the model must return. Field descriptions are sent to the model as guidance."""

    summary: str = Field(
        description="A short paragraph: 5 to 6 sentences, about 800 characters, plain text."
    )
    key_points: list[str] = Field(
        default_factory=list, description="3 to 5 short points, one sentence each."
    )


@dataclass
class SummaryResult:
    summary: str
    key_points: list[str]
    model: str  # which model answered, e.g. "gemini-3.5-flash-lite" or the Groq fallback


class BadAnswer(Exception):
    """The model answered, but not with a usable summary (empty, unparseable, far too long)."""


@cache
def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text()


def build_messages(*, title: str, site: str, text: str | None, description: str | None) -> list:
    """The system prompt plus the page, wrapped in <article> tags (it's untrusted input)."""
    if text:
        body = text[:MAX_ARTICLE_CHARS]
        cut = (
            " (the page is longer; this is its beginning)" if len(text) > MAX_ARTICLE_CHARS else ""
        )
        page = f"Title: {title}\nSite: {site}\nPage text{cut}:\n{body}"
    else:
        page = (
            f"Title: {title}\nSite: {site}\n"
            f"Description: {description or '(none)'}\n"
            "(Only the title and description are available, not the page text.)"
        )
    return [
        SystemMessage(load_prompt("summarise")),
        HumanMessage(f"<article>\n{page}\n</article>"),
    ]


async def summarise_document(
    *,
    title: str,
    site: str,
    text: str | None,
    description: str | None,
    trace: dict | None = None,
) -> SummaryResult:
    """Ask the model (Gemini, falling back to Groq) for a summary of one page.

    Raises whatever the models raise when both fail (the job retries), or BadAnswer when the
    answer isn't usable.
    """
    model = llm.get_structured_model(Summary)
    out = await model.ainvoke(
        build_messages(title=title, site=site, text=text, description=description),
        # Shows up in LangSmith as "summarise", with the document id to find it by.
        config={"run_name": "summarise", "metadata": trace or {}},
    )
    parsed: Summary | None = out.get("parsed")
    if parsed is None:  # every model in the chain gave an unparseable answer
        raise BadAnswer(f"Unparseable answer: {out.get('parsing_error')}")
    return SummaryResult(
        summary=_clean_summary(parsed.summary),
        key_points=[p.strip() for p in parsed.key_points if p.strip()][:MAX_KEY_POINTS],
        model=_model_name(out.get("raw")),
    )


def _clean_summary(summary: str) -> str:
    summary = " ".join(summary.split())
    if not summary:
        raise BadAnswer("Empty summary")
    if len(summary) > MAX_SUMMARY_CHARS:
        raise BadAnswer(f"Summary too long ({len(summary)} characters)")
    return summary


def _model_name(raw) -> str:
    metadata = getattr(raw, "response_metadata", None) or {}
    return str(metadata.get("model_name") or metadata.get("model") or "unknown")[:64]


MAX_AI_TAGS = 2  # the most the AI adds to one bookmark (owner, 2026-11-03)


class TagChoice(BaseModel):
    tags: list[str] = Field(
        default_factory=list,
        description="Up to 2 names copied exactly from the list, best first. Empty if none fit.",
    )


async def pick_tags(
    *, title: str, summary: str, key_points: list[str], tags: list[str], trace: dict | None = None
) -> list[str]:
    """Up to MAX_AI_TAGS of `tags` (the user's own) that fit a summarised page.

    The model may only choose, never invent: any name that isn't in `tags` is dropped, so the
    AI can't create tags (owner). Raises BadAnswer for an unparseable answer.
    """
    listed = "\n".join(f"- {tag}" for tag in tags)
    points = "\n".join(f"- {point}" for point in key_points)
    page = f"Title: {title}\nSummary: {summary}\nKey points:\n{points}"
    out = await llm.get_structured_model(TagChoice).ainvoke(
        [
            SystemMessage(load_prompt("tag")),
            HumanMessage(f"Tags to choose from:\n{listed}\n\n<article>\n{page}\n</article>"),
        ],
        config={"run_name": "tag", "metadata": trace or {}},
    )
    parsed: TagChoice | None = out.get("parsed")
    if parsed is None:
        raise BadAnswer(f"Unparseable answer: {out.get('parsing_error')}")
    by_name = {tag.lower(): tag for tag in tags}
    picked: list[str] = []
    for name in parsed.tags:
        tag = by_name.get(" ".join(name.split()).lower())
        if tag and tag not in picked:
            picked.append(tag)
    return picked[:MAX_AI_TAGS]
