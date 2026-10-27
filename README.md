# Bookmark Brain

**Saved it? Now actually use it.**

Bookmark Brain collects the bookmarks you've saved in every browser (Chrome, Edge, Brave, Firefox) into one calm reading list. It summarises each page with AI, lets you search by what a page was *about* rather than its exact title, and lets you ask questions across everything you've saved.

It's a personal learning project for integrating AI agents into a real full-stack app: a FastAPI backend, a React frontend and a browser extension.

## Status

| Phase | What | State |
|---|---|---|
| 0 | Foundations: monorepo, FastAPI, Postgres + pgvector, Alembic, React app | ✅ Done |
| 1 | Google sign-in, one-click extension connect, bookmark sync, feed with filters | ✅ Done |
| 2 | Background job queue, page fetching, on-demand AI summaries (Gemini, Groq fallback) | ✅ Done |
| 3 | Hybrid search: keyword + semantic (embeddings) | Planned |
| 4 | "Ask your bookmarks" chat agent (LangGraph) | Planned |
| 5–7 | Auto-tags, dead-link checks, reading status, weekly digest | Planned |
| 8 | Deploy (Render + Neon + Vercel), CI | Planned |
| UI | Final design (texture top bar, image-free reading list), GitHub sign-in | Planned |

The full plan, with the reasoning behind each decision, is in [docs/PLAN.md](docs/PLAN.md).

## How it works

```
 Browser extension ──(access token, POST /api/sync)──┐
                                                     ▼
 React app ──(session cookie, REST)──► FastAPI ──► Postgres (+ pgvector)
                                          │
                                          │
                       in-process job worker (jobs table): fetch page → summarise (on demand) → embed
                                          ▼
                              Gemini ──fallback──► Groq
```

- **The extension** is the only part that can read your bookmarks; browsers don't let websites do it. On first run it sends your whole bookmark tree, then only the changes (added, edited, moved, removed). An hourly full sync catches anything it missed.
- **The backend** normalises URLs (lower-cases the host, drops tracking parameters like `utm_*` and `#fragments`), so the same article saved in two browsers becomes **one** bookmark with two sources. A bookmark disappears only when no browser has it any more.
- **Documents are shared, bookmarks are per user.** Each unique URL is stored once, so the AI work for it (summary, embedding) only has to happen once, however many people saved it.
- **Sign-in:** the web app signs in with Google and gets an httpOnly session cookie. The extension uses a personal access token that it receives through **one-click connect**: the popup opens the web app's `/connect` page, which creates the token and hands it to the extension. Only a hash of the token is stored.
- **Slow work runs in the background.** Fetching pages and AI summaries run as rows in a `jobs` table, processed by a worker inside the API. Syncs stay fast, jobs survive restarts, and failures are retried. The server only fetches public addresses, so a bookmark can't make it probe its own network.
- **A newspaper, text first.** The feed is your own front page: editions by when you saved things, the newest unread stories biggest, and only the top story shows the page's own preview image.

## Tech stack

| Part | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, pydantic-settings, `uv` |
| Database | PostgreSQL 16 + pgvector (Docker locally, Neon in production) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, React Router |
| Extension | WXT (Manifest V3), works in Chrome, Edge, Brave and Firefox |
| AI (planned) | LangChain + LangGraph, Gemini (primary), Groq (fallback), LangSmith tracing |
| Tooling | pytest, ruff, oxlint |

## Project structure

```
bookmark_brain/
├── backend/                  FastAPI API
│   ├── app/
│   │   ├── main.py           app setup, CORS, routers
│   │   ├── config.py         settings from env / .env
│   │   ├── db.py             async engine + session dependency
│   │   ├── models.py         users, api_tokens, documents, bookmarks, bookmark_sources
│   │   ├── schemas.py        request/response models
│   │   ├── auth/             Google token check, session JWTs, access tokens
│   │   ├── api/              routes: health, auth, tokens, sync, bookmarks
│   │   ├── services/         URL normalisation, sync/merge, safe page fetcher
│   │   └── worker.py         background job queue + worker
│   ├── alembic/              database migrations
│   └── tests/                pytest (uses a separate test database)
├── frontend/                 React web app
│   └── src/
│       ├── api/              fetch client + types
│       ├── pages/            Login (sign-up), HowItWorks, Feed, Settings, Connect
│       ├── components/       Layout, Newspaper (the feed's front page), StoryParts, BookmarkDetail, Logo, Nebula (texture), SignInButtons
│       └── hooks/            useMe (current user)
├── extension/                Browser extension (WXT)
│   ├── entrypoints/          background worker, popup, /connect content script
│   ├── lib/                  sync.ts (bookmarks → API), connect.ts (one-click connect)
│   └── assets/icon/          logo SVGs (`npm run icons` renders the PNG icons)
├── docs/PLAN.md              roadmap and design decisions
├── docker-compose.yml        local Postgres + pgvector
└── CLAUDE.md, .claude/skills project conventions and how-tos (dev setup, jobs, extension, design, …)
```

## Running locally

### Prerequisites

- Python 3.12 and [`uv`](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 24 and npm
- Docker (on Windows/WSL: Docker Desktop with WSL integration turned on)
- A Google Cloud **OAuth client ID** (type "Web application") with `http://localhost:5173` under *Authorised JavaScript origins*

### 1. Start the database

```bash
docker compose up -d db
```

This runs Postgres 16 with pgvector on `localhost:5432` (user `bb`, password `bb`, database `bookmark_brain`). Data is kept in a Docker volume between restarts.

### 2. Backend

```bash
cd backend
cp .env.example .env          # then fill in the values (see below)
uv sync                       # install dependencies
uv run alembic upgrade head   # create the tables
uv run fastapi dev app/main.py
```

The API runs at http://localhost:8000, with the background job worker running inside it. Interactive docs are at http://localhost:8000/docs. Check http://localhost:8000/health/db, which should return `{"status":"ok","pgvector":"0.8.x"}`.

**`backend/.env`**

| Variable | Needed for | Notes |
|---|---|---|
| `DATABASE_URL` | always | default matches docker-compose |
| `FRONTEND_ORIGIN` | always | `http://localhost:5173` |
| `JWT_SECRET` | sign-in | generate with `openssl rand -hex 32` |
| `GOOGLE_CLIENT_ID` | sign-in | your OAuth client ID |
| `GOOGLE_API_KEY` | Phase 2+ | Gemini key from Google AI Studio |
| `GEMINI_MODEL` / `GROQ_MODEL` | optional | override the models (defaults `gemini-3.5-flash-lite` / `openai/gpt-oss-120b`) |
| `GROQ_API_KEY` | Phase 2+ | fallback model |
| `LANGSMITH_API_KEY` | Phase 4 | optional tracing |
| `AI_DAILY_LIMIT_PER_USER` | Phase 2+ | protects the free-tier quota |
| `RESEND_API_KEY` / `MAINTAINER_EMAIL` | optional | "Notify the maintainer" in the Limit reached dialog ([Resend](https://resend.com), free 100 emails a day). Without your own domain, `MAINTAINER_EMAIL` must be the address you signed up to Resend with. `EMAIL_FROM` overrides the sender |
| `DEV_TOOLS` | local only | `true` turns on `/api/usage/dev/*`, which the dev build's "Dev tools" box uses to use up or reset today's AI limit (to try the Limit reached dialog). Never in production |
| `WORKER_ENABLED` | optional | `false` runs the API without the background job worker (default `true`) |

In production also set `SESSION_COOKIE_SECURE=true` and `SESSION_COOKIE_SAMESITE=none`, because the frontend and API are on different domains.

> `.env` is git-ignored. Never commit real keys.

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local    # set VITE_API_URL and VITE_GOOGLE_CLIENT_ID
npm install
npm run dev
```

Open http://localhost:5173 and sign in with Google.

| Variable | Value |
|---|---|
| `VITE_API_URL` | `http://localhost:8000` |
| `VITE_GOOGLE_CLIENT_ID` | the same OAuth client ID as the backend |

### 4. Browser extension

```bash
cd extension
npm install
npm run build              # Chrome / Edge / Brave → .output/chrome-mv3/
npm run build:firefox      # Firefox → .output/firefox-mv2/
```

Load it into your browser:

- **Chrome / Edge / Brave:** go to `chrome://extensions` (or `edge://extensions`), turn on **Developer mode**, click **Load unpacked**, and pick `extension/.output/chrome-mv3`.
  - On **WSL** the path from Windows is `\\wsl$\<distro>\home\<you>\…\bookmark_brain\extension\.output\chrome-mv3`. Run `wsl -l` in PowerShell to see your distro name.
- **Firefox:** go to `about:debugging` → *This Firefox* → **Load Temporary Add-on**, and pick `extension/.output/firefox-mv2/manifest.json`.

After you change extension code, rebuild it and click the reload icon on the extension's card.

### 5. Connect it all

1. Click the extension icon, then **Connect this browser**. The web app opens at `/connect`.
2. Sign in if asked, then click **Connect this browser** on that page. The extension receives its token automatically and syncs. The page shows a loader, then opens your feed when the first sync finishes.
3. Add or remove a bookmark in the browser and refresh the feed to see it update.

Manual fallback: in the web app, open **Settings → Create token** and copy the token (it's shown only once). Then in the extension choose **Advanced: paste a token**, keep the API URL as `http://localhost:8000`, and click **Save & sync now**.

How one-click connect stays safe: the extension's content script runs only on the app's `/connect` page. It accepts a token only from that same page, and only together with the one-time code the popup created when you clicked Connect (valid for 15 minutes, single use). The page never chooses which API the extension talks to.

The extension can only reach API addresses listed in `host_permissions` in [extension/wxt.config.ts](extension/wxt.config.ts) (`localhost:8000` and `*.onrender.com` by default).

### Tests and linting

```bash
cd backend
uv run pytest              # needs the database container running
uv run ruff check . && uv run ruff format --check .

cd ../frontend && npm run build && npm run lint
cd ../extension && npm run compile
```

Backend tests run against a separate `bookmark_brain_test` database, which they create and wipe automatically. Your dev data is never touched.

## API overview

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | liveness check |
| GET | `/health/db` | none | database + pgvector check |
| POST | `/api/auth/google` | none | exchange a Google ID token for a session cookie |
| POST | `/api/auth/logout` | none | clear the session cookie |
| GET | `/api/me` | cookie or token | current user |
| GET / POST | `/api/tokens` | cookie or token | list / create extension tokens |
| DELETE | `/api/tokens/{id}` | cookie or token | revoke a token |
| POST | `/api/sync` | cookie or token | full or incremental bookmark sync from the extension |
| GET | `/api/bookmarks` | cookie or token | feed, newest first; `limit`, `cursor`, `folder`, `browser`, `section` (`main` / `sign_in` / `dead`), `read_state`, `saved_after` / `saved_before` (the newspaper's week split), `page` (numbered pages with a `total`, for Earlier) |
| GET | `/api/bookmarks/facets` | cookie or token | counts for a `section`: total, pending, unread/read, folders and browsers |
| GET | `/api/bookmarks/sync-summary` | cookie or token | what one `browser` has sent so far (Connect page): bookmarks, folders, the last 4 received, other browsers |
| POST | `/api/bookmarks/{id}/find-archive` | cookie or token | look up a dead link on the Wayback Machine (queues a job) |
| GET / PATCH | `/api/bookmarks/{id}` | cookie or token | one bookmark (detail panel) / mark it read or unread |
| POST | `/api/bookmarks/{id}/summarise` | cookie or token | AI summary on demand (`again=true` to redo); cached per URL, counted against the daily limit |
| GET | `/api/usage` | cookie or token | today's summaries used, the daily limit, when it resets |
| GET | `/api/account` | cookie only | what deleting the account would remove: bookmark and connected-browser counts |
| GET | `/api/account/export` | cookie only | Download my data: a JSON file (bookmarks, where they're saved, read states, summaries, connected browsers; never token secrets) |
| DELETE | `/api/account` | cookie only | delete the account and everything personal (body `{"confirm": "DELETE"}`); shared per-URL pages and summaries stay |
| POST | `/api/usage/notify-maintainer` | cookie or token | email the owner that this user hit today's limit (once a day per user; 409 if not at the limit, 503 if email isn't set up, 502 if Resend refused) |

## Troubleshooting

- **`Connect call failed ('127.0.0.1', 5432)`:** the database isn't running. Start Docker Desktop, then `docker compose up -d db`.
- **Connect page says the extension didn't respond:** reload the extension in `chrome://extensions`, then open Connect again from the popup (content scripts only attach to tabs opened after the reload).
- **Something stays "pending":** check the job queue with `docker compose exec db psql -U bb bookmark_brain -c "select kind, status, last_error from jobs where status <> 'done'"`.
- **The Google button shows an error:** `http://localhost:5173` is missing from your OAuth client's authorised JavaScript origins, or `VITE_GOOGLE_CLIENT_ID` doesn't match `GOOGLE_CLIENT_ID`.
- **The extension says "Token rejected":** the token was revoked. Click **Reconnect** in the popup.
- **Backend tests fail at random on WSL2** ("Not signed in", or pages stuck `pending`): the clock is jumping because WSL's time sync and `systemd-timesyncd` fight. Run `sudo systemctl stop systemd-timesyncd` (it comes back after a WSL restart; `sudo systemctl start systemd-timesyncd` to undo). Details in the `dev-setup` skill.
- **The extension can't reach the API:** check that the API is running and that its URL matches `host_permissions` in `wxt.config.ts`.

## License

[MIT](LICENSE) © 2026 Mansi Gupta
