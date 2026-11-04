"""The one place that talks to language models (see the llm-patterns skill).

Every free tier has small limits, so we chain several providers. LangChain's
`.with_fallbacks()` wraps them: if a call raises (rate limit, used-up free quota, outage,
timeout), the same input goes to the next model straight away. Callers just see one model
that is much harder to break. The order:

1. Gemini (GEMINI_MODEL), the main model; Ask tries ASK_MODEL before it
2. a second Gemini model (GEMINI_FALLBACK_MODEL): its own free quota, same key
3. OpenRouter's free models (OPENROUTER_API_KEY)
4. NVIDIA NIM (NVIDIA_API_KEY), which hosts DeepSeek for free
5. Groq (GROQ_API_KEY)

A provider without a key is left out. Each client retries only once itself: waiting out a
long outage is the job queue's work (app/worker.py), and falling back fast matters more.

Embeddings (get_embedder) are Gemini only, with no fallback: see GeminiEmbeddings.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.models import EMBEDDING_DIMENSIONS

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


def _models(first: str | None = None) -> list[BaseChatModel]:
    """The chain, first choice first, skipping providers that have no key.

    `first` moves one Gemini model to the front (Ask uses ASK_MODEL); the rest keep their order.
    """
    s = get_settings()
    models: list[BaseChatModel] = []
    if s.google_api_key:
        names = [first, s.gemini_model, s.gemini_fallback_model]
        models += [_gemini(name) for name in dict.fromkeys(n for n in names if n)]
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


def get_tool_model(tools: Sequence[BaseTool]) -> Runnable:
    """A chat model that may ask to call `tools` (the chat agent, app/ai/agent/).

    `bind_tools` sends each tool's name, argument schema and docstring with every request. The
    model then answers either with text or with "tool calls": a tool name and arguments for us
    to run. It never runs anything itself. Like structured output, tools have to be bound to
    each model before `with_fallbacks`.

    Someone watches every answer as it's written, so ASK_MODEL (a fast model) goes first; see
    config.py.
    """
    first, *rest = [m.bind_tools(tools) for m in _models(first=get_settings().ask_model)]
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


# --- Embeddings ----------------------------------------------------------------


def get_embedder() -> "GeminiEmbeddings":
    """The embedding model for search (GEMINI_EMBEDDING_MODEL)."""
    s = get_settings()
    if not s.google_api_key:
        raise RuntimeError("Embeddings need GOOGLE_API_KEY")
    return GeminiEmbeddings(s.gemini_embedding_model, s.google_api_key)


class RateLimited(Exception):
    """The provider said "too many requests" (HTTP 429): nothing is wrong, try again later."""


def document_for_embedding(title: str | None, text: str) -> str:
    """A page in the form gemini-embedding-2 expects for search: "title: … | text: …"."""
    return f"title: {title or 'none'} | text: {text}"


class GeminiEmbeddings(Embeddings):
    """gemini-embedding-2 behind LangChain's `Embeddings` interface.

    An embedding turns a text into a list of numbers (a vector), placed so that texts with
    similar meaning get vectors pointing in similar directions. Search embeds the query and
    compares it with every page's stored vector.

    LangChain's own GoogleGenerativeAIEmbeddings always sends a `task_type`
    (RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY), which gemini-embedding-2 doesn't accept. This
    model wants the task written into the text instead, so we call Google's SDK ourselves:
    - a page is sent as "title: … | text: …" (format it with document_for_embedding)
    - a query is sent as "task: search result | query: …" (embed_query adds that)
    Each text goes in its own `Content`; a plain list would come back as one combined vector.
    """

    QUERY_PREFIX = "task: search result | query: "

    def __init__(self, model: str, api_key: str):
        self.model = model
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000)
        )
        self._config = types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Pages formatted with document_for_embedding(); one vector each (100 at most)."""
        with _rate_limit_as_ours():
            result = self._client.models.embed_content(
                model=self.model, contents=_contents(texts), config=self._config
            )
        return [list(e.values) for e in result.embeddings]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([self.QUERY_PREFIX + text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        with _rate_limit_as_ours():
            result = await self._client.aio.models.embed_content(
                model=self.model, contents=_contents(texts), config=self._config
            )
        return [list(e.values) for e in result.embeddings]

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([self.QUERY_PREFIX + text]))[0]


def _contents(texts: list[str]) -> list[types.Content]:
    return [types.Content(parts=[types.Part(text=text)]) for text in texts]


@contextmanager
def _rate_limit_as_ours() -> Iterator[None]:
    """Turn Google's 429 into RateLimited, so callers needn't know the SDK's error types."""
    try:
        yield
    except genai_errors.APIError as err:
        if err.code == 429:
            raise RateLimited(str(err)) from err
        raise
