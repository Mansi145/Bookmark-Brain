# Bookmark Brain: Implementation Plan

## Context
This is a learning project to understand how AI agents are integrated into real software. It will also go on a CV. The app collects your browser bookmarks (Chrome first, then other browsers), shows them as a feed of article cards, summarises them with AI, and lets you search them by keyword and by meaning. Later phases add a chat agent that answers questions from your saved articles, auto-tagging, dead-link and reading-status tracking, and a weekly digest. The app is deployed and supports multiple users, so it works without your PC running.

The directory `/home/mansi/personal_projects/bookmark_brain` is empty, so this is a new project. Installed: Python 3.12, Node 24. Still needed: `uv`, `git`, and Docker (for local Postgres).

## Decisions (and why)
| Area | Choice | Why |
|---|---|---|
| Bookmark source | **Browser extension** (Manifest V3, built with **WXT**) | Web pages can't read bookmarks; only extensions can, through `chrome.bookmarks`. WXT builds Chrome, Edge, Brave and Firefox versions from one codebase. |
| Backend | **FastAPI**, SQLAlchemy 2 (async) + asyncpg, Alembic, pydantic-settings, `uv` | Modern async Python; Pydantic models double as API schemas. |
| LLM | **Gemini Flash** (free tier) as primary, **Groq** (gpt-oss / Llama) as fallback, using LangChain's `.with_fallbacks()` | Both free. Gemini handles long input well and supports tool calling. A fallback keeps the app working when a quota runs out. |
| Embeddings | **Gemini embedding model** (free), stored in **pgvector** | Free, and stored in the same database as everything else (no separate vector DB). |
| Agent framework | **LangChain + LangGraph**, traced with **LangSmith** (free tier) | LangGraph shows the agent as nodes, edges and state. LangSmith lets you see every LLM and tool call, which helps a lot when learning. |
| Search | **Hybrid**: Postgres full-text (`tsvector`) + pgvector similarity, merged with Reciprocal Rank Fusion (RRF) | Keyword search finds exact terms; semantic search finds meaning. RRF is a simple, standard way to merge two ranked lists. |
| Frontend | **React + Vite + TypeScript**, TanStack Query, Tailwind, React Router | Industry standard; handles streaming chat UI well. |
| Auth | **Google Sign-In** (Google Identity Services); the backend verifies the ID token and issues its own JWT | Fits a Chrome-centric app. The extension uses a personal access token generated in the web app's settings page. |
| Hosting | **Render** (API) + **Neon** (Postgres + pgvector) + **Vercel** (frontend). Free tier; cron-job.org pings `/health` every 10 min to stop Render sleeping | $0. The ping avoids the 30–50s cold start and keeps the background worker running. |
| Background jobs | DB-backed `jobs` table + an in-process asyncio worker (`SELECT … FOR UPDATE SKIP LOCKED`) | No Redis or Celery needed (Render free tier has no free worker service). This is also a real production pattern. |
| Quota protection | Summaries/embeddings cached **per URL** (shared across users); per-user daily AI limits (`slowapi` + counters) | Free quotas are per API key, so every user shares the same daily limit. |

## Architecture
```
 Chrome/Edge/Firefox extension ──(PAT, POST /api/sync)──┐
                                                        ▼
 React app (Vercel) ──(JWT, REST + SSE)──► FastAPI (Render) ──► Neon Postgres (+pgvector, FTS)
                                              │   ▲
                                   asyncio job worker: fetch page → extract text (trafilatura)
                                              │       → summarise → embed → tag
                                              ▼
                               LangChain: Gemini ──fallback──► Groq      (traces → LangSmith)
```

## Repo layout (single repository for all three apps)
```
bookmark_brain/
├── CLAUDE.md
├── .claude/skills/…            # skill files (see below)
├── docker-compose.yml          # local pgvector/pgvector:pg16
├── backend/
│   ├── pyproject.toml          # uv-managed
│   ├── alembic/
│   └── app/
│       ├── main.py             # FastAPI app, routers, lifespan starts worker
│       ├── config.py           # pydantic-settings (env vars)
│       ├── db.py, models.py    # SQLAlchemy models
│       ├── auth/               # google token verify, JWT, PATs
│       ├── api/                # routers: bookmarks, sync, search, chat, digest, me
│       ├── services/           # extraction, search (RRF), dedupe, link_check
│       ├── ai/
│       │   ├── llm.py          # get_chat_model() with fallbacks, get_embedder()
│       │   ├── prompts/        # summarise.md, tag.md, digest.md …
│       │   ├── chains.py       # summarise / tag chains (structured output)
│       │   └── agent/          # LangGraph: state.py, tools.py, graph.py
│       └── worker.py           # job loop
│   └── tests/
├── frontend/                   # Vite React TS
│   └── src/{pages,components,api,hooks}
└── extension/                  # WXT project
    └── entrypoints/{background.ts, popup/}
```

## Data model (core tables)
- `users` (id, google_sub, email, name, avatar)
- `api_tokens` (user_id, hashed_token, name, last_used): PATs for the extension
- `documents` (id, **normalized_url** unique, title, site, content_text, summary, key_points jsonb, reading_minutes, embedding vector, tsv tsvector, status [pending/fetched/summarised/failed/dead], http_status, last_checked_at). **Shared across users**, so each URL is only summarised once.
- `bookmarks` (id, user_id, document_id, browser_source, browser_node_id, folder_path, title, added_at, read_state [unread/read/archived], deleted_at). Unique on (user_id, document_id).
- `tags`, `bookmark_tags` (user-scoped; `source` = ai|user)
- `jobs` (id, kind, payload jsonb, status, attempts, run_after, error)
- `chat_threads`, `chat_messages`; `digests`
- Indexes: GIN on `tsv`, HNSW on `embedding`.

## Phases (each ends with something working and deployable)

**Phase 0: Foundations.** `git init`, monorepo skeleton, docker-compose Postgres + pgvector, FastAPI `/health`, Alembic setup, Vite app, `CLAUDE.md` + initial skill files. *You'll learn:* project tooling and env config.

**Phase 1: Auth + extension sync (no AI yet).**
- Google Sign-In → `POST /api/auth/google` (verify with `google-auth`) → JWT in an httpOnly cookie.
- Settings page: generate a PAT. The extension popup stores the PAT, then on first run calls `chrome.bookmarks.getTree()` and does a full sync. After that, `onCreated/onChanged/onRemoved/onMoved` events send incremental updates to `POST /api/sync` (in batches, with retry).
- Backend normalises URLs (lowercase host, strip `utm_*`, trailing slash, fragment), upserts `documents` + `bookmarks`, and records `browser_source` so the same URL from several browsers is merged into one bookmark.
- Feed page: card list with infinite scroll, filter by folder or browser.

**Phase 2: Ingestion + summaries (first AI integration).**
- When a sync adds a new document, a `fetch` job is queued. The worker uses `httpx` + `trafilatura` to download the page and extract the article text, then queues a `summarise` job.
- `ai/llm.py`: `ChatGoogleGenerativeAI(...).with_fallbacks([ChatGroq(...)])`.
- Summarise chain uses `with_structured_output(SummarySchema)` to get back `{tldr, key_points[], reading_minutes}` as structured data. Long articles are cut to a token budget first.
- Cards show the TL;DR; a detail drawer shows key points. Includes a "re-summarise" button and the per-user daily limit.
- *You'll learn:* prompts, structured output, fallbacks, cost and quota control, async job processing.

**Phase 3: Hybrid search.**
- An embed job writes `documents.embedding` (title + summary + first part of content). A trigger or generated column keeps `tsv` updated.
- `GET /api/search?q=` runs an FTS query (`websearch_to_tsquery`) and a vector query (cosine distance) at the same time, each limited to the user's bookmarks, then merges them with RRF (`score = Σ 1/(60+rank)`).
- Search bar with debounce; matching words highlighted (`ts_headline`).
- *You'll learn:* embeddings, vector indexes, ranking.

**Phase 4: "Ask your bookmarks" agent (LangGraph).**
- Tools: `search_bookmarks(query)`, `get_article(doc_id)`, `list_by_tag(tag)`, `summarise_many(doc_ids)`. Every tool is limited to the current user's bookmarks.
- Before using LangGraph, write a ~50-line plain-Python tool-calling loop in `ai/agent/manual_loop.py` (for learning only) so you can see what LangGraph does for you.
- Graph: `agent` node (LLM with tools bound) ↔ `tools` node (ToolNode), with a conditional edge on whether the model requested tool calls. Conversation memory is saved with a Postgres checkpointer. Answers must cite doc ids, which the UI renders as links.
- `POST /api/chat` streams tokens and tool steps over SSE. The chat UI shows "🔎 searching…" steps as they happen.
- *You'll learn:* tool calling, agent loops, state, memory, streaming, tracing in LangSmith.

**Phase 5: Auto-tags & smart collections.** A tag chain picks tags from the user's existing tags and suggests new ones (structured output). Collections are built by clustering embeddings (k-means, using the LLM to name each cluster). Near-duplicates are detected by cosine similarity above about 0.95.

**Phase 6: Dead links & reading status.** A periodic `link_check` job sends HEAD/GET requests and records status: 404/410 is marked dead, and the UI offers the Wayback Machine copy instead. Reading states are unread/read/archived, with a "mark read" action when you open a bookmark. The feed can filter by state and sort by reading time.

**Phase 7: Weekly digest.** A GitHub Actions cron calls `POST /internal/digest` (protected by a shared secret). It picks unread bookmarks older than 30 days, a digest chain writes a short themed overview, and the result is saved to `digests` and shown on a Digest page. Sending it by email (Resend free tier) is optional.

**Phase 8: Deploy & polish.** Neon DB + migrations, Render web service (`uvicorn`, env vars), Vercel frontend, CORS and cookie settings for cross-site use, cron-job.org keep-warm ping, publish the extension (Chrome Web Store unlisted, or load-unpacked). README with architecture diagram + demo GIF for the CV. Basic CI: ruff + pytest + tsc on GitHub Actions.

*(In practice, a deploy is also done at the end of Phase 1 so problems surface early.)*

## Skill files (written in Phase 0, updated as each phase is finalised)
Stored in `.claude/skills/<name>/SKILL.md`:
- **dev-setup**: how to start Postgres, backend (`uv run fastapi dev`), frontend, and the extension (`wxt dev`); env vars list.
- **llm-patterns**: always go through `ai/llm.py`, prompts live in `ai/prompts/`, use structured output, respect quotas, cache per document, never call the LLM inside a request handler when a background job will do.
- **langgraph-agent**: how to add a tool (user-scoped, docstring = tool description, return compact JSON), how to add a node, how to test with a fake LLM.
- **db-migrations**: Alembic autogenerate workflow + pgvector/tsvector caveats.
- **deploy**: Render/Neon/Vercel steps, env vars, keep-warm ping, rollback.
- Plus a root `CLAUDE.md` summarising stack, layout, and conventions.

## Verification
- **Backend:** `pytest` with a test Postgres (docker). Unit tests for URL normalisation, RRF fusion, and sync upsert/merge. Chains and agent are tested with LangChain's `FakeListChatModel` so tests make no API calls.
- **Agent:** an eval script with about 10 questions about a fixture set of bookmarks, checking that answers cite the right documents. Inspect traces in LangSmith.
- **End-to-end (manual):** load the extension unpacked in Chrome → sign in on the web app → paste PAT → bookmarks appear in the feed → summaries fill in within about a minute → search "that article about X" finds it → ask the chat a question and get a cited answer. Repeat in Edge/Firefox to confirm the same URL merges into one bookmark.
- **Deployed:** the same flow against the Vercel URL. Check that `/health` responds in under 1s after a long idle period, which confirms the keep-warm ping works.
