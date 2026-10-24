---
name: dev-setup
description: How to run Bookmark Brain locally (Postgres, FastAPI backend with its job worker, React frontend, browser extension), which env vars are needed, and how to check everything works. Use when starting, running, or debugging the local dev environment.
---

# Local development

## Prerequisites
- Python 3.12, `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node 24 + npm
- Docker (Docker Desktop on Windows with WSL integration on this machine). If
  `docker compose` says it can't connect, Docker Desktop isn't running: it can't be started from WSL,
  ask the owner to start it.

## 1. Database
```bash
docker compose up -d db          # pgvector/pgvector:pg16 on localhost:5432, user/pass/db bb/bb/bookmark_brain
docker compose exec -T db pg_isready -U bb   # wait until "accepting connections"
```
`ConnectionRefusedError … 5432` from the backend means the container isn't running.

## 2. Backend
```bash
cd backend
cp .env.example .env             # fill in keys (see below)
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py   # http://localhost:8000, docs at /docs, /health/db checks pgvector
uv run pytest -q                 # all tests (no real LLM or network calls)
uv run ruff check . && uv run ruff format .
```
- The background job worker (`app/worker.py`) starts inside the API (FastAPI lifespan). Set
  `WORKER_ENABLED=false` to run the API without it. See the `background-jobs` skill.
- Tests use a separate `bookmark_brain_test` database in the same container (created automatically
  by `tests/conftest.py`, schema from the models, tables wiped between tests). The container must be
  running. Your dev data is never touched.

## 3. Frontend
```bash
cd frontend
cp .env.example .env.local       # VITE_API_URL, VITE_GOOGLE_CLIENT_ID
npm install
npm run dev                      # http://localhost:5173
npx tsc -b && npm run lint       # type-check + oxlint
```
Google sign-in needs `http://localhost:5173` in the OAuth client's *Authorised JavaScript origins*,
and the **client ID** (ends in `.apps.googleusercontent.com`), not an API key, in both
`VITE_GOOGLE_CLIENT_ID` and the backend's `GOOGLE_CLIENT_ID`.

## 4. Extension
```bash
cd extension
npm install
npm run build                    # -> .output/chrome-mv3/
npm run build:firefox            # -> .output/firefox-mv2/
npm run compile                  # type-check only
npm run icons                    # re-render public/icon/*.png after a logo change
```
**On WSL** (Chrome runs on Windows): `wxt dev` can't launch Windows Chrome, so build and load it
unpacked: `chrome://extensions` → Developer mode → Load unpacked →
`\\wsl$\Ubuntu\home\mansi\personal_projects\bookmark_brain\extension\.output\chrome-mv3`.
After code changes, rebuild and click the reload icon on the extension card.
Edge: same steps at `edge://extensions`. Firefox: `about:debugging` → Load Temporary Add-on → pick
`.output/firefox-mv2/manifest.json`.

Then click the extension's **Connect this browser**: it opens `/connect`, you click Connect, the page
shows a loader and then your feed. Manual fallback: Settings → Create token, then *Advanced: paste a
token* in the popup. Details in the `extension` skill.

## Backend env vars (`backend/.env`)
| Var | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://bb:bb@localhost:5432/bookmark_brain` |
| `FRONTEND_ORIGIN` | CORS, e.g. `http://localhost:5173` |
| `JWT_SECRET` | signs session JWTs (`openssl rand -hex 32`) |
| `GOOGLE_CLIENT_ID` | Google Sign-In (OAuth client, type "Web") |
| `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE` | prod only: `true` / `none` (cross-site) |
| `WORKER_ENABLED` | run the in-process job worker (default `true`) |
| `GOOGLE_API_KEY` | Gemini chat + embeddings (from AI Studio), Phase 2+ |
| `GROQ_API_KEY` | fallback LLM, Phase 2+ |
| `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT` | agent/chain traces |
| `AI_DAILY_LIMIT_PER_USER` | quota guard |
| `INTERNAL_CRON_SECRET` | protects `/internal/*` endpoints (Phase 7) |

Never print `.env` values; check whether a var is set with e.g.
`grep -c '^GOOGLE_CLIENT_ID=.\+' backend/.env`.

Extension (`extension/.env`, optional): `WXT_API_URL`, `WXT_APP_URL` (defaults are localhost:8000 / :5173).

## Useful checks
```bash
curl -s localhost:8000/health/db
docker compose exec db psql -U bb bookmark_brain -c "select kind, status, count(*) from jobs group by 1, 2"
docker compose exec db psql -U bb bookmark_brain -c "select count(*) from bookmarks where deleted_at is null"
```
