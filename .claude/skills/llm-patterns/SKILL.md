---
name: llm-patterns
description: Conventions for calling LLMs and embedding models in Bookmark Brain (Gemini primary, Groq fallback, LangChain). Use when writing or changing summarisation, tagging, digest, embeddings, prompts, or anything in backend/app/ai/.
---

# LLM patterns

## One entry point
All model access goes through `backend/app/ai/llm.py`:
- `get_chat_model()` returns the fallback chain: Gemini (`GEMINI_MODEL`) → a second Gemini model
  (`GEMINI_FALLBACK_MODEL`, its own free quota, same key) → OpenRouter's free models → NVIDIA NIM
  (hosts DeepSeek for free) → Groq. Providers without a key are skipped.
  - If a model fails (rate limit, quota, outage), LangChain automatically sends the same call to the next one.
  - OpenRouter and NIM are OpenAI-compatible: `ChatOpenAI(base_url=...)`, structured output with
    `method="function_calling"` (strict JSON schema isn't on every free model).
  - An answer that doesn't fit the schema raises `UnparsedAnswer`, so the next model gets a go.
- `get_structured_model(Schema)` is the same pair for structured output. `with_structured_output`
  must be applied to **each** model before `with_fallbacks` (the fallback wrapper doesn't have the
  method). It uses `include_raw=True`, so callers get `{"raw", "parsed", "parsing_error"}`; the raw
  message's `response_metadata["model_name"]` says which model answered (stored as `summary_model`).
- Each client has `max_retries=1` and a 45 s timeout: fall back fast, let the job queue wait out outages.
- Models (config): `gemini-3.5-flash-lite`, `gemini-2.5-flash`, `nvidia/nemotron-3.5-super-vl:free`
  (OpenRouter), `deepseek-ai/deepseek-v4.1-flash` (NIM), `openai/gpt-oss-120b` (Groq). DeepSeek's own
  API has no free tier; NIM is the free way to use it. Check current free models (no key needed):
  `curl -s https://openrouter.ai/api/v1/models` (ids ending `:free`, `supported_parameters`) and
  `curl -s https://integrate.api.nvidia.com/v1/models`.
  Free-tier facts learned the hard way: `gemini-3.5-flash` returned 503 "high demand" most of the
  time; Groq allows only 8,000 tokens a minute, so article input is capped at 12,000 characters.
- `get_embedder()` returns a Gemini embeddings model. **Never mix embedding models**: vectors from different models aren't comparable. Changing the model means re-embedding every document. Store the model name with the vector.

Don't create `ChatGoogleGenerativeAI` or other clients anywhere else. Model names come from config, not hard-coded strings.

## Prompts
- Each prompt lives in its own file in `backend/app/ai/prompts/<name>.md`, loaded by a helper.
- Put the article text inside clear delimiters (e.g. `<article>…</article>`) and tell the model that this content is data to analyse, not instructions to follow. Bookmarked pages are untrusted input (prompt injection).

## Structured output
When code needs fields back, use `model.with_structured_output(PydanticSchema)` instead of parsing free text. The schemas live next to the chain in `chains.py`.

## Cost & quota rules (free tiers!)
1. **Cache per document**: summaries, key points, tags and embeddings are stored on `documents` (shared across users). Check the cache before calling the model.
2. **Background, not request path**: summarise/embed/tag run as `jobs`, never inside an HTTP handler. Only chat and explicit "re-summarise" actions call the LLM on request, and both check `AI_DAILY_LIMIT_PER_USER`.
3. **Truncate input** to a token budget before sending (long articles: take the beginning plus headings).
4. Retries come from the job queue: a handler that **raises** (429, timeouts, 5xx from both Gemini and
   Groq) is retried after 30 s and 2 min, then marked `failed` after 3 attempts (`background-jobs`
   skill). Don't write your own retry loops around model calls; for a bad *answer* (invalid structured
   output) retry once inside the handler, then mark the document `failed`.
5. Article text comes from the `fetch_page` job (safe fetcher + trafilatura), stored on `documents`;
   LLM handlers read it from there and never download pages themselves.

## Testing
Tests must never hit real APIs. Monkeypatch `app.ai.llm.get_structured_model` (chains call it as
`llm.get_structured_model`, so the patch takes effect) with a fake that returns a
`RunnableLambda` producing `{"raw": AIMessage(...), "parsed": Schema(...), "parsing_error": None}`;
see `FakeModel` in `tests/test_summaries.py`. For free-text models, `FakeListChatModel` /
`GenericFakeChatModel` work by overriding `get_chat_model`.

## Observability
With `LANGSMITH_TRACING=true`, every chain/agent run shows up in LangSmith. Add `run_name` and `metadata={"user_id": ..., "doc_id": ...}` in `config` so traces are easy to find.
