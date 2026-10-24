# Changelog

All notable changes to Bookmark Brain are recorded here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Background jobs (Phase 2 groundwork)

#### Added
- **`jobs` table** (migration `0003`): kind, JSON payload, status (`queued` / `running` / `done` / `failed`), attempts, `run_after`, `locked_at`, last error.
- **Job worker** (`app/worker.py`), started with the API (FastAPI lifespan; `WORKER_ENABLED=false` turns it off).
  - Four loops claim jobs with `SELECT … FOR UPDATE SKIP LOCKED`, so no job runs twice.
  - Failed jobs retry after 30 s and then 2 min, and are marked `failed` after 3 attempts.
  - A job left `running` by a restarted API is taken over after 10 minutes.
  - A handler's writes are committed together with the job being marked done.
- **Safe page fetcher** (`app/services/fetch.py`): refuses private, loopback and link-local addresses on every request and redirect (SSRF protection); 10 s timeout, 3 MB cap; classifies 429/5xx/timeouts as retryable.
- **Tests** for the queue (success, back-off, giving up, rollback, stale jobs) and the fetcher (blocked addresses, redirects to private IPs, status and content-type handling).

- **Docs**
  - New skills: `background-jobs` (queue internals, adding a job kind, testing, debugging), `extension` (sync model, one-click connect security rules, permissions, building, icons), `ui-design` (final design tokens, texture recipe, logo, landing page and feed layout), `git-workflow` (commit rules, branches, PRs, changelog, gh workarounds).
  - `docs/PLAN.md` brought up to date: status table, new decisions (one-click connect, minimal extension permissions, job queue, safe fetcher, no preview images), design direction, actual repo layout and data model, Phase 2 progress.
  - `CLAUDE.md`, `README.md` and the `dev-setup`, `deploy`, `db-migrations`, `llm-patterns` and `langgraph-agent` skills updated (worker, `WORKER_ENABLED`, SSRF rule, migration pitfalls, extension deploy steps, git rules).
  - `WORKER_ENABLED` added to `backend/.env.example`.

#### Decided
- Feed cards won't show page preview images (`og:image`): many bookmarked pages have none or a generic logo, hotlinked images break, and the feed design is now an image-free reading list.

### One-click extension connect

#### Added
- **Extension popup:** a **Connect this browser** button opens the web app's `/connect` page with a one-time code (nonce) and the browser name. The manual token form moved under *Advanced: paste a token*. The popup shows *Sync now* and *Reconnect* once connected.
- **Content script** (`entrypoints/connect.content.ts`): runs only on `http://localhost:5173/connect*`.
  - Accepts a `bb_pat_` token posted by that same page (same window, same origin) only when it carries the pending nonce.
  - The nonce is valid for 15 minutes and single use.
  - Saves the token, replies to the page, asks the background worker for a sync and reports the result (bookmark count or error) back to the page.
- **Web app `/connect` page:** detects the extension, creates a token named after the browser, and hands it over with `window.postMessage`. Shows a loader while the first sync runs, then opens the feed in the same tab. Otherwise it shows the sync error, an expired-link message, or the token as a manual fallback if the extension doesn't answer.
- **Extension icon:** the Bookmark Brain logo (brain on a bookmark, Mulberry aura) at 16/32/48/128 px. Sources are in `extension/assets/icon/` (a simplified version for 16/32 px); `npm run icons` regenerates the PNGs in `public/icon/`.
- **Build-time URLs:** `WXT_API_URL` / `WXT_APP_URL` set the extension's default API and web app origins (default `localhost:8000` / `localhost:5173`).

#### Changed
- Background worker answers a `sync-now` message once the full sync finishes (`fullSync` now returns the bookmark count).
- Settings page and README describe the one-click flow, with manual tokens as the fallback.

### Phase 1: Auth, extension sync and feed

#### Added
- **Database** (migration `0002`)
  - `users`: one row per Google account, keyed by Google's stable `sub` id.
  - `api_tokens`: personal access tokens for the extension; only a SHA-256 hash and a display prefix are stored.
  - `documents`: one row per normalised URL, shared across users (later phases cache AI output here).
  - `bookmarks`: one per user per document, with read state and soft delete.
  - `bookmark_sources`: where a bookmark lives in each browser install (browser, node id, folder, title), so the same URL saved in several browsers becomes one bookmark.
- **Auth**
  - `POST /api/auth/google`: verifies a Google ID token and sets an httpOnly session cookie (JWT, 30 days).
  - `POST /api/auth/logout` and `GET /api/me`.
  - `CurrentUser` dependency accepting either the session cookie or an `Authorization: Bearer bb_pat_…` token.
  - Cookie `Secure` / `SameSite` settings configurable for cross-site production deploys.
- **Extension tokens**: `GET/POST /api/tokens` and `DELETE /api/tokens/{id}`; the plaintext token is returned once at creation; revoking someone else's token returns 404.
- **Sync**: `POST /api/sync` accepts a full snapshot or an incremental change set from one browser install.
  - Idempotent upserts (`INSERT … ON CONFLICT`), batched under Postgres' parameter limit.
  - Full syncs remove sources the browser no longer has; bookmarks with no sources left are soft-deleted and revived if re-added.
  - Editing a bookmark's URL moves it to the right document.
- **URL normalisation**: lower-cased host, default ports and fragments dropped, `utm_*` and common click-id parameters removed, query sorted, trailing slash trimmed; `chrome://`, `javascript:` and `file:` links skipped.
- **Feed API**
  - `GET /api/bookmarks`: newest first, keyset (cursor) pagination, `folder` (includes subfolders) and `browser` filters.
  - `GET /api/bookmarks/facets`: folder and browser counts for the filter sidebar.
- **Frontend**
  - Google Sign-In page (`@react-oauth/google`).
  - Layout with navigation, avatar and sign-out.
  - Feed with infinite scroll, bookmark cards, and folder/browser filters stored in the URL.
  - Settings page to create, copy (shown once) and revoke extension tokens.
  - Typed API client with error handling.
- **Browser extension** (`extension/`, WXT, Manifest V3; Chrome, Edge, Brave and Firefox builds)
  - Popup to enter the API URL and token, sync on demand and show the last sync status.
  - Background worker: full sync on install/startup, incremental sync on bookmark create/change/move/remove, a full sync on folder changes, an hourly safety-net sync and a retry alarm after failures.
  - Per-install source id and browser detection, so separate browsers and profiles merge correctly.
- **Tests**: URL normalisation, auth and cookies, token lifecycle, sync merging/removal across browsers, user isolation, pagination and filters (35 tests against a separate test database).
- **Docs**: `README.md` with app overview, structure and local setup; `dev-setup` skill updated with WSL extension loading and the test database.

#### Changed
- `pydantic-settings` config gained auth and cookie settings; `.env.example` files updated.

### Phase 0: Foundations

#### Added
- Monorepo layout: `backend/` (FastAPI), `frontend/` (React), shared docs and tooling at the root.
- **Backend**
  - FastAPI app with CORS configured for the frontend origin.
  - `GET /health`: lightweight liveness check (target of the keep-warm ping).
  - `GET /health/db`: confirms Postgres is reachable and reports the pgvector version.
  - Settings loaded from environment / `.env` via pydantic-settings (`app/config.py`), with `.env.example` template.
  - Async SQLAlchemy 2 engine, session dependency (`SessionDep`) and declarative `Base` (`app/db.py`).
  - Alembic (async template) wired to app settings and models; first migration `0001` enables the `vector` extension.
  - Tooling: `uv` for dependencies, `ruff` for lint/format, `pytest` with a health-check test.
- **Frontend**
  - Vite + React 19 + TypeScript app with Tailwind CSS v4 and TanStack Query.
  - `api/client.ts` fetch helper using `VITE_API_URL`.
  - Status page showing API and pgvector health.
- **Infrastructure**
  - `docker-compose.yml` running Postgres 16 with pgvector for local development.
  - `.gitignore` covering secrets, Python and Node artefacts.
- **Docs**
  - `docs/PLAN.md`: architecture, decisions and phased roadmap.
  - `CLAUDE.md` and project skills (`dev-setup`, `llm-patterns`, `langgraph-agent`, `db-migrations`, `deploy`).
