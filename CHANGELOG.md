# Changelog

All notable changes to Bookmark Brain are recorded here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
