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
The job worker starts automatically inside the FastAPI lifespan.

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
npm run dev                      # WXT opens a Chrome profile with the extension loaded
npm run dev:firefox              # Firefox build
```
Paste a PAT from the web app's Settings page into the extension popup.

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

Frontend: `VITE_API_URL`, `VITE_GOOGLE_CLIENT_ID`.
