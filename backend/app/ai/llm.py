"""The one place that talks to language models (see the llm-patterns skill).

Every free tier has small limits, so we chain several providers. LangChain's
`.with_fallbacks()` wraps them: if a call raises (rate limit, used-up free quota, outage,
timeout), the same input goes to the next model straight away. Callers just see one model
that is much harder to break. The order:

1. Gemini (GEMINI_MODEL), the main model
2. a second Gemini model (GEMINI_FALLBACK_MODEL): its own free quota, same key
3. OpenRouter's free models (OPENROUTER_API_KEY)
4. NVIDIA NIM (NVIDIA_API_KEY), which hosts DeepSeek for free
5. Groq (GROQ_API_KEY)

A provider without a key is left out. Each client retries only once itself: waiting out a
long outage is the job queue's work (app/worker.py), and falling back fast matters more.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import get_settings

TIMEOUT_SECONDS = 45
TEMPERATURE = 0.2  # summaries should be faithful, not creative
OPENROUTER_URL = "https://openrouter.ai/api/v1"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1"


def _gemini(model: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=get_settings().google_api_key,
        # No temperature: the Gemini 3.x lite models use fixed sampling and ignore it.
        timeout=TIMEOUT_SECONDS,
        max_retries=1,
    )


def _openai_compatible(base_url: str, api_key: str, model: str) -> ChatOpenAI:
    """OpenRouter and NVIDIA NIM both speak the OpenAI API, so one client covers both."""
    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=TEMPERATURE,
        timeout=TIMEOUT_SECONDS,
        max_retries=1,
    )


def _models() -> list[BaseChatModel]:
    """The chain, first choice first, skipping providers that have no key."""
    s = get_settings()
    models: list[BaseChatModel] = []
    if s.google_api_key:
        models.append(_gemini(s.gemini_model))
        if s.gemini_fallback_model:
            models.append(_gemini(s.gemini_fallback_model))
    if s.openrouter_api_key:
        models.append(_openai_compatible(OPENROUTER_URL, s.openrouter_api_key, s.openrouter_model))
    if s.nvidia_api_key:
        models.append(_openai_compatible(NVIDIA_URL, s.nvidia_api_key, s.nvidia_model))
    if s.groq_api_key:
        models.append(
            ChatGroq(
                model=s.groq_model,
                api_key=s.groq_api_key,
                temperature=TEMPERATURE,
                timeout=TIMEOUT_SECONDS,
                max_retries=1,
            )
        )
    if not models:
        raise RuntimeError("No AI provider configured: set GOOGLE_API_KEY or another key")
    return models


def get_chat_model() -> Runnable:
    """A chat model that answers in free text (for the chat agent, later)."""
    first, *rest = _models()
    return first.with_fallbacks(rest) if rest else first


def get_structured_model(schema: type[BaseModel]) -> Runnable:
    """A model that answers with an instance of `schema` instead of free text.

    `with_structured_output` makes the model fill in the schema's fields (via the provider's
    JSON-schema or tool-calling support), so we never parse prose. It has to be applied to each
    model before `with_fallbacks`, because the fallback wrapper doesn't have that method.

    `include_raw=True` returns {"raw": the model's message, "parsed": the schema instance,
    "parsing_error": ...}; the raw message tells us which model actually answered.
    """
    first, *rest = [_structured(m, schema) for m in _models()]
    return first.with_fallbacks(rest) if rest else first


class UnparsedAnswer(Exception):
    """A model answered, but not in the schema's shape."""


def _structured(model: BaseChatModel, schema: type[BaseModel]) -> Runnable:
    if isinstance(model, ChatOpenAI):
        # Tool calling is the structured-output method most OpenAI-compatible hosts support;
        # the default (strict JSON schema) isn't available on every free model.
        structured = model.with_structured_output(
            schema, include_raw=True, method="function_calling"
        )
    else:
        structured = model.with_structured_output(schema, include_raw=True)
    # With include_raw, a bad answer comes back as parsed=None instead of an error, which
    # wouldn't trigger the fallback. Raising here lets the next model have a go.
    return structured | RunnableLambda(_require_parsed)


def _require_parsed(out: dict) -> dict:
    if out.get("parsed") is None:
        raise UnparsedAnswer(str(out.get("parsing_error") or "no structured answer"))
    return out
