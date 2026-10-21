---
name: dev-setup
description: How to run Bookmark Brain locally (Postgres, FastAPI backend, React frontend, browser extension) and which env vars are needed. Use when starting, running, or debugging the local dev environment.
---

# Local development

## Prerequisites
- Python 3.12, `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node 24 + npm
- Docker (Docker Desktop with WSL integration on this machine)

## 1. Database
```bash
docker compose up -d db          # pgvector/pgvector:pg16 on localhost:5432
```

## 2. Backend
```bash
cd backend
cp .env.example .env             # fill in keys (see below)
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py   # http://localhost:8000, docs at /docs
uv run pytest                    # tests (no real LLM calls)
```
Tests use a separate `bookmark_brain_test` database in the same container (created
automatically by `tests/conftest.py`, wiped between tests). The DB container must be running.
(From Phase 2, the background job worker will start inside the FastAPI lifespan.)

## 3. Frontend
```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

## 4. Extension
```bash
cd extension
npm install
npm run build                    # -> .output/chrome-mv3/
npm run build:firefox            # -> .output/firefox-mv2/
npm run compile                  # type-check only
```
**On WSL** (Chrome runs on Windows): `wxt dev` can't launch Windows Chrome, so build and
load it unpacked: `chrome://extensions` → Developer mode → Load unpacked →
`\\wsl$\Ubuntu\home\mansi\personal_projects\bookmark_brain\extension\.output\chrome-mv3`.
After code changes, rebuild and click the reload icon on the extension card.
Edge: same steps at `edge://extensions`. Firefox: `about:debugging` → Load Temporary Add-on → pick
`.output/firefox-mv2/manifest.json`.

Then click the extension's **Connect this browser** (opens `/connect` in the web app, which hands the
token to the content script). Manual fallback: create a token in Settings and use *Advanced: paste a token*.
The API URL must match one of `host_permissions` in `wxt.config.ts`; the connect content script only
matches `http://localhost:5173/connect*`. For a deployed app add its `/connect` URL to `matches` in
`entrypoints/connect.content.ts` and build with `WXT_APP_URL` / `WXT_API_URL` set.

## Backend env vars (`backend/.env`)
| Var | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://bb:bb@localhost:5432/bookmark_brain` |
| `JWT_SECRET` | signs session JWTs |
| `GOOGLE_CLIENT_ID` | Google Sign-In (OAuth client, type "Web") |
| `GOOGLE_API_KEY` | Gemini chat + embeddings (from AI Studio) |
| `GROQ_API_KEY` | fallback LLM |
| `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true` | agent/chain traces |
| `FRONTEND_ORIGIN` | CORS, e.g. `http://localhost:5173` |
| `INTERNAL_CRON_SECRET` | protects `/internal/*` endpoints |
| `AI_DAILY_LIMIT_PER_USER` | quota guard |

Frontend (`frontend/.env.local`): `VITE_API_URL`, `VITE_GOOGLE_CLIENT_ID` (same OAuth client id as the backend).
