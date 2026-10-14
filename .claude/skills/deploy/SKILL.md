---
name: deploy
description: Deploying Bookmark Brain to Render (FastAPI), Neon (Postgres + pgvector) and Vercel (React), plus the keep-warm ping, cron jobs and extension publishing. Use when deploying, configuring production env vars, or debugging production issues.
---

# Deploy

## Neon (database)
1. Create project → enable pgvector (the first migration runs `CREATE EXTENSION vector`).
2. Use the pooled URL for the app (`postgresql+asyncpg://…-pooler…?ssl=require`) and the direct URL for migrations.
3. `DATABASE_URL=<direct> uv run alembic upgrade head`.

## Render (backend)
- Web Service from GitHub, root dir `backend/`, free instance.
- Build: `pip install uv && uv sync --frozen`
- Start: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health` (must be cheap: no DB or LLM calls).
- Env vars: everything in the `dev-setup` skill, with prod values; `FRONTEND_ORIGIN=https://<app>.vercel.app`.
- **Keep warm**: cron-job.org → `GET https://<api>.onrender.com/health` every 10 min. The free plan's 750 h/month covers one service running 24/7. This also keeps the in-process job worker alive.

## Vercel (frontend)
- Import repo, root dir `frontend/`, framework Vite.
- Env: `VITE_API_URL`, `VITE_GOOGLE_CLIENT_ID`.
- SPA rewrite: `vercel.json` → `{"rewrites":[{"source":"/(.*)","destination":"/"}]}`.

## Cross-site auth gotchas
Frontend (vercel.app) and API (onrender.com) are on different sites:
- Session cookie: `Secure; HttpOnly; SameSite=None`; CORS `allow_credentials=True` with an explicit origin (no `*`).
- Add both the Vercel URL and localhost to the Google OAuth client's authorised JavaScript origins.

## Scheduled jobs
GitHub Actions cron (`.github/workflows/cron.yml`) calls `POST /internal/digest` and `POST /internal/link-check` with header `X-Cron-Secret: $INTERNAL_CRON_SECRET`.

## Extension
- `npm run build` / `npm run zip` in `extension/`, then set `API_URL` to the Render URL.
- Chrome Web Store as **unlisted** (one-time $5 developer fee), or share the zip for "Load unpacked".
- Firefox: `npm run zip:firefox` → addons.mozilla.org (free).

## Rollback
Render: "Rollback" to a previous deploy. Vercel: promote a previous deployment. DB: write a new migration that reverses the change; don't run downgrade on prod with real data.
