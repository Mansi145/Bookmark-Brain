# Bookmark Brain

Collects browser bookmarks through an extension, shows them as an article feed, summarises them with AI, and supports hybrid search plus a chat agent ("ask your bookmarks"). Full plan and the reasons behind each decision: [docs/PLAN.md](docs/PLAN.md).

The owner is learning how to integrate AI agents. When you implement something, briefly explain the *why* (especially for AI/LLM concepts), and keep the code readable rather than clever.

## Stack
- **backend/**: FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, pydantic-settings, managed with `uv`. Python 3.12.
- **frontend/**: React + Vite + TypeScript, TanStack Query, Tailwind, React Router.
- **extension/**: WXT (Manifest V3); uses `chrome.bookmarks` and syncs to `POST /api/sync` with a personal access token (PAT).
- **DB**: Postgres + pgvector (local: docker-compose; prod: Neon). Full-text search via `tsvector`.
- **AI**: LangChain + LangGraph. Gemini Flash is primary, Groq is the fallback (`.with_fallbacks`). Gemini embeddings. LangSmith tracing.
- **Hosting**: Render (API, kept warm by a `/health` ping) + Neon + Vercel.

## Conventions
- All LLM/embedding access goes through `backend/app/ai/llm.py`. See the `llm-patterns` skill.
- Agent tools live in `backend/app/ai/agent/tools.py` and **must be scoped to the current user**. See the `langgraph-agent` skill.
- Slow work (fetching pages, summaries, embeddings, tagging, link checks) runs as rows in the `jobs` table, processed by `backend/app/worker.py`, never inside a request handler.
- `documents` are shared per normalised URL (AI output is cached there); `bookmarks` are per user.
- Schema changes go through Alembic only. See the `db-migrations` skill.
- Tests must not call real LLM APIs; use LangChain fake chat models.

## Skills
- `dev-setup`: run everything locally
- `llm-patterns`: how we call LLMs
- `langgraph-agent`: adding tools/nodes to the chat agent
- `db-migrations`: Alembic + pgvector workflow
- `deploy`: Render / Neon / Vercel
