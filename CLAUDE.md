# Bookmark Brain

Collects browser bookmarks through an extension, shows them as a newspaper-style front page, summarises them with AI, and supports hybrid search plus a chat agent ("ask your bookmarks"). Full plan, status and the reasons behind each decision: [docs/PLAN.md](docs/PLAN.md).

The owner is learning how to integrate AI agents. When you implement something, briefly explain the *why* (especially for AI/LLM concepts), and keep the code readable rather than clever. Everything must work on free tiers.

## Stack
- **backend/**: FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, pydantic-settings, httpx, managed with `uv`. Python 3.12.
- **frontend/**: React + Vite + TypeScript, TanStack Query, Tailwind v4, React Router.
- **extension/**: WXT (Manifest V3); uses `chrome.bookmarks` and syncs to `POST /api/sync` with a personal access token (PAT), obtained through one-click connect.
- **DB**: Postgres + pgvector (local: docker-compose; prod: Neon). Full-text search via `tsvector`.
- **AI**: LangChain + LangGraph. Summaries use a fallback chain of free models (Gemini → a second Gemini model → OpenRouter → NVIDIA NIM → Groq, `.with_fallbacks`; a provider without a key is skipped). Gemini embeddings. LangSmith tracing.
- **Email**: Resend's free plan, one HTTPS call in `backend/app/services/mail.py` (the Limit reached dialog's "Notify the maintainer").
- **Hosting**: Render (API, kept warm by a `/health` ping) + Neon + Vercel.

## Conventions
- All LLM/embedding access goes through `backend/app/ai/llm.py`. See the `llm-patterns` skill.
- Agent tools live in `backend/app/ai/agent/tools.py` and **must be scoped to the current user**. See the `langgraph-agent` skill.
- Slow work (fetching pages, summaries, embeddings, tagging, link checks) runs as rows in the `jobs` table, processed by `backend/app/worker.py`, never inside a request handler. See the `background-jobs` skill.
- The server fetches user-supplied URLs **only** through `backend/app/services/fetch.py` (blocks private addresses, SSRF). Never use a bare `httpx` client for that.
- `documents` are shared per normalised URL (AI output is cached there); `bookmarks` are per user; `bookmark_sources` record which browser install has each bookmark.
- Schema changes go through Alembic only. See the `db-migrations` skill.
- Tests must not call real LLM APIs or the network; use LangChain fake chat models and `httpx.MockTransport`.
- `frontend/src/api/types.ts` mirrors `backend/app/schemas.py`; change both together.
- The extension keeps minimal permissions (no `<all_urls>`); see the `extension` skill before touching the connect flow.
- UI follows the design direction in the `ui-design` skill (dark Nude nebula texture with white text on it, off-white backgrounds (never pure white), dark Nude accents with white text, near-black text elsewhere, warm charcoal dark mode, Aleo + Geist, Masthead BB logo, a newspaper front-page feed with a preview image on the top story only). Design is done in a separate design session on the canvas; build only what has been designed there, and **ask the owner before designing or restyling anything new**.

## Git
- Commit, push or open PRs only when the owner asks.
- No AI attribution anywhere: no `Co-Authored-By` lines and no mention of an assistant in commits, PR descriptions or the changelog.
- Feature branch → PR into `development`; `development` → `main` for releases. Every change gets a `CHANGELOG.md` entry. See the `git-workflow` skill.

## Skills
- `dev-setup`: run everything locally
- `background-jobs`: the job queue and adding a job kind
- `extension`: sync, one-click connect, building and icons
- `ui-design`: design tokens and layout decisions
- `llm-patterns`: how we call LLMs
- `langgraph-agent`: adding tools/nodes to the chat agent
- `db-migrations`: Alembic + pgvector workflow
- `git-workflow`: branches, PRs, changelog
- `deploy`: Render / Neon / Vercel
