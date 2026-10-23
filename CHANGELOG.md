# Changelog

All notable changes to Bookmark Brain are recorded here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### UI: first pass of the new design

#### Added
- **Design foundations**: the ui-design tokens (including the dark accent colours `accent` `#503931` / `accent2` `#564D3A` with white text, and the band gradient) as Tailwind `@theme` colours with a dark theme, Aleo / Geist / Geist Mono fonts, the logo as a favicon. No pure-white pages: an off-white page (`#ECEAE7`), panels behind the sidebar and the feed (`#F5F4F2`), and a card per article (`#FBFAF8`); the loading-bar colour is the warmer `#E7E4DF`.
- **Light / dark toggle** in the signed-in top bar (moon / sun, `aria-pressed`): follows the system setting until pressed, then remembers the choice in the browser (`useTheme`; a small script in `index.html` applies it before the page draws so it doesn't flash).
- **Shared components**: `Logo` (full and small drawings), `Nebula` (the dark Nude texture; the old Cloudlifter variant is gone), `SignInButtons`, `PublicHeader`, `SiteIcon` (the site's logo on a small white chip, or a letter tile when there's none), `StatePage` (a full-page card on the texture), `ErrorBoundary`.
- **Sign-up page** rebuilt as the one-screen landing page on the dark Nude texture (logo + wordmark, headline, sign-in buttons, "See how it works", a preview card, footer). The preview is a mini feed: a "Today · 2 bookmarks" band, one summarised row and one with the Summarise button, with site logos. The sample logos are bundled in `public/sample-icons`, so signed-out visitors' browsers don't contact those sites.
- **How it works page** (`/how-it-works`, new): texture header, three steps, features (with site logos in the summary, search and Ask examples), closing call to action, footer, on the off-white layers. Reachable signed out and signed in.
- **App shell**: top bar on the dark Nude texture with white text: logo, dark search field (disabled until search exists), tabs Feed · Settings (Feed stays current on all three sections; Ask joins in Phase 4), a How it works link, and an account menu with sign-out. How it works also works while signed in (its buttons then lead back to the feed).
- **Feed**: the image-free reading list grouped by save date (Today / This week / Earlier) under dark gradient bands; a views bar above the list on all three sections (All bookmarks · Unread · Read | Needs sign-in · Dead links, pill links with counts; reading states filter the main feed via `GET /api/bookmarks?read_state=` and `read_states` counts in facets); rows with site · folder · browser · age, Aleo title, page state (dark "Fetching page…" pill, "Couldn't read this page", "Needs sign-in" / "Subscribers only", dead with its status code and a "Find archived copy" button with checking / found / none / failed states) and reading time; empty states per section; sidebar filters with indented subfolders; a header with the section's bookmark count and how many are still being fetched. `GET /api/bookmarks/facets` now returns `total` and `pending` for this.
- **First run**: until a browser has synced anything, the feed shows a "Connect your first browser" card (two steps, *Get the extension*, *Connect by hand*) instead of the views bar and list.
- **Settings**: section menu and content on off-white panels, each section a card; "Connect a browser" (one-click steps on dark accent numbers, *Connect by hand* fold with the shown-once token on a dark notice), "Connected browsers" with Connected (dark pill) / Waiting (outlined) status and Revoke.
- **Connect page** (`/connect`) restyled as full-page cards on the texture, one per state: sign in first, connecting, first sync (with how many bookmarks have arrived), connected (opens the feed after a moment), extension didn't answer (token shown once + Copy), link expired, plus sync failed and error. It now connects on its own as soon as the extension says hello (no extra click), and if the extension rejects the link, the token it just created is revoked again.
- **Error pages**: "We couldn't find that page" for unknown addresses (instead of silently going to the feed), "Waking up the server…" while the first request waits (shown after 1.5 s; the free Render server can take up to a minute), "You've been signed out" when a request comes back 401 mid-session, and "Something went wrong" with *Try again* when the API can't be reached or a page crashes.
- **Extension popup**: dark Nude header strip with white text, off-white body, a status card for each state (not connected: plain card; connected: dark accent; syncing: second accent; token rejected: red), Sync now / Reconnect, Open feed, the *Advanced* fold, and a link to Settings.

#### Notes
- Google sign-in uses Google's own button in its dark style: only Google's button returns the ID token the backend verifies. GitHub sign-in is shown but disabled until the backend supports it.
- Not built yet, all designed: the Summarise button and the bookmark detail panel (next step), search (Phase 3), the Ask page (Phase 4), tags (Phase 5), the Digest page (Phase 7), sorting, the row "⋯" menu, and Settings' AI usage and Account sections. The Ask and Digest tabs join the top bar when their pages exist.

### Design (canvas)
- Phase 2 feed design: three sections (Feed · Needs sign-in · Dead links) under a top bar on the dark texture with the tabs, a How it works link and the account menu; the new section is named "Dead links"; the "Archived" reading state was later removed (reading states are Unread and Read); archive.org is only looked up from a dead row's "Find archived copy" button; empty states; on-demand Summarise button with working / failed / daily-limit states; row states with icons; no source or trust labels anywhere (owner's decision); accents: the owner's rule is to use only the dark Nude colours (`#503931`, `#564D3A`) with white text, never light tints; every group band uses the gradient. Reading states and the two sections share one views bar above the list (not the sidebar or top nav; the top tabs are Feed · Ask · Settings); the sidebar has only Browsers and Folders; the How it works page and the landing preview card use the dark accents too. Boards: `Main` (with a `section` setting), `FeedSignIn`, `FeedDead`, `FeedSignInEmpty`, `FeedDeadEmpty`, `RowStates`, `FeedDark`.
- The brand texture is now the dark version of Figma's Nude gradient (`#503931 → #564D3A`) with white text on it, replacing the light blue → pink Cloudlifter texture.
- The landing page was split into a one-screen sign-up page and a separate How it works page.
- Sign-in buttons are dark, with the real Google G and GitHub marks.
- The Components page has the new texture and new logo colour tests. The Gradient test page used to pick the texture was deleted.
- **No pure-white pages** (owner): three off-white layers (page `#ECEAE7` → panels `#F5F4F2` → cards `#FBFAF8`, lines `#E2DFDA`; dark `#141517` / `#1B1C1F` / `#232427`) everywhere: feed, Settings, popup body, How it works, the landing preview card. The only pure white left is the chip behind site logos.
- **Site logos**: the site's own logo at 14 px on a 20 px white chip in both themes, with a letter-tile fallback; also on the landing preview and the How it works examples, not in the sidebar.
- **Settings and the extension popup** restyled to the dark Nude texture, off-white panels and dark accents.
- **Light / dark toggle** in the top bar, before How it works.
- **More pages** designed (boards `FeedDetail`, `FeedSearch`, `FeedFirstRun`, `Ask`, `AskEmpty`, `Digest`, `ConnectStates`, `ErrorStates`): top nav Feed · Ask · Digest · Settings; a 480 px bookmark detail panel (summary and key points, Open page / Mark as read / Re-summarise, tags with AI suggestions, details); a Tags group in the sidebar; search results that replace the feed with highlighted matches; the first-run card; the three-panel Ask page with citations and sources; the weekly Digest with themed bands; every Connect state; and the error pages.
- Summarise stays available on Wayback Machine copies.
- Connect and error page cards follow the theme (dark card, light text and a light main button in dark mode; the texture stays the same). New boards `ConnectStatesDark` and `ErrorStatesDark`.
- The Connect board has three more states from the build: first sync failed, the token couldn't be made, and the page was opened without the extension's link. Their wording is waiting for the owner's review.
- The How it works copy (no Archived state) and the landing preview's second site (`docs.langchain.com`) were aligned with the build; the preview's logo chips use the `line` colour `#E2DFDA`.
- The loading-bar (`skeleton`) colour is now the warmer `#E7E4DF` (dark stays `#2B2D31`) on every board; Settings' dark inputs use the `surface` colour like everything else.
- Owner's backlog, not designed yet: the logo's colours, a logo animation while searching / summarising / checking the Wayback Machine, and a less black dark-mode background.
- The `ui-design` skill was updated with all of this; the design parts of `docs/PLAN.md` and the UI line in `CLAUDE.md` follow it.

### Phase 2: page fetching, Needs sign-in and Dead links

#### Added
- **`fetch_page` job**: every document seen for the first time in a sync gets a job (in the same transaction, using `INSERT … ON CONFLICT DO NOTHING RETURNING` so re-syncs and other users' copies don't queue duplicates). It downloads the live page with the safe fetcher and extracts it with `trafilatura` (`services/extract.py`):
  - article text → `fetched`, storing the page's title, description, text and word count (`content_source = "page"`)
  - 404 / 410 → `dead` ("Dead links")
  - everything else → `failed` ("Couldn't read this page"): 403 bot protection, PDFs, JavaScript-only pages, under 50 words (sign-in walls, placeholders), private addresses (never retried), or a final failed retry
  - title and description are kept even without article text (JavaScript apps like YouTube still describe themselves in `<head>`); parsing runs in a thread
- **Sign-in detection** (`services/access.py`, no network calls): `access = "login"` for HTTP 401, a redirect to a sign-in address (`/login`, `/users/sign_in`, `accounts.…`), a password form with no article, or a logged-in web app address (web mail, Discord channels, Slack, Teams, WhatsApp Web, Google Docs/Drive); `access = "paywall"` for schema.org `isAccessibleForFree: false` (e.g. Medium members-only teasers). Address checks only apply when there's no readable article, so docs *about* authentication aren't flagged. Cloudflare bot challenges (403) are deliberately not treated as sign-in.
- **Site logos** (`services/icons.py`): while a page is fetched, its declared icons are read from `<head>` (SVG > apple-touch-icon > largest favicon; Safari mask icons skipped; small inline SVGs kept), falling back to the site's `/favicon.ico`. Only the URL is stored (`documents.icon_url`); the browser loads it from the site and falls back to the letter tile if it fails. Private addresses get none. On the owner's bookmarks 24 of 25 got a logo, including pages behind bot protection or sign-in.
- **Find archived copy** (Wayback Machine, only when the user asks): `POST /api/bookmarks/{id}/find-archive` (your own dead links only; 409 otherwise) sets `archive_status = "checking"` and queues a `find_archive` job (`services/archive.py`), which ends as `found` (`archive_url`, `archived_on`, and the copy's text stored as `content_source = "archive"` so it can be summarised), `none`, or `failed` (archive.org busy or unreachable; the user can try again).
  - Polite to archive.org: one request at a time, at least 1.5 s apart across all worker loops; a 429 opens a shared circuit breaker that pauses every lookup (archive.org's `Retry-After`, or a cool-down doubling from 60 s up to 30 min).
  - Private-looking URLs (accounts./login./mail./outlook. hosts, Google Docs/Drive, intranet names without a dot) are never sent to archive.org.
- **`RetryLater`** in the worker: a handler can ask to run again later ("the other side is busy") without it counting as a failed attempt.
- **Feed sections**: `GET /api/bookmarks?section=main|sign_in|dead` (and the same for `facets`, which lists every folder and browser with 0 where a section has none). Every bookmark is in exactly one: dead → `dead`; needs sign-in or a subscription → `sign_in`; everything else → `main`. Frontend: `/sign-in-required` ("Needs sign-in") and `/dead-links` ("Dead links"; `/archive` redirects there), reached from the feed's views bar, each with its own empty state.
- **Reading states** are only Unread and Read: `GET /api/bookmarks?read_state=unread|read`, and `read_states` counts in facets. Migration `0005` removes `archived` from the `read_state` enum (rebuilding the Postgres type; any archived bookmarks become read).
- **Migration `0004`**: `documents.title`, `description`, `content_text`, `word_count`, `http_status`, `fetched_at`, `content_source`, `archive_status`, `archive_url`, `archived_on`, `access`, `icon_url`; queues a fetch for every existing pending document.
- **Feed API**: `reading_minutes` (word count ÷ 230, rounded up), `http_status`, `content_source`, `archive_status`, `archive_url`, `archived_on`, `access`, `icon_url`.
- **Tests**: extraction, logos, sign-in detection, sync queueing, the live fetch outcomes, nothing sent to archive.org automatically, finding a copy / no copy / archive.org unreachable then retried, only your own dead links can be looked up, the shared rate-limit pause, section and read-state filtering for the feed and facets, and the private-URL rule.

#### Decided
- **Summaries are on demand.** Nothing is summarised automatically; every bookmark will get a *Summarise* button (next step). Saves the shared free-tier quota for pages people actually care about.
- **archive.org is only asked when the user clicks "Find archived copy"** on a dead link. Earlier in this work, lookups ran automatically for every unreadable page; that sent many URLs to a third party and hit its rate limits, so it was dropped.
- **Dead links and pages that need sign-in or a subscription live in their own sections**, never in the main feed. The "Archived" reading state was removed.

#### Notes
- Final sections for the owner's 25 real bookmarks: main 20, Needs sign-in 4 (Google sign-in, Discord, a company GitLab, Outlook), Dead links 1 (its Wayback lookup found a 23 Jul 2021 copy).
- The live page gave article text for 11 of 25; 4 were behind bot protection (403: Stack Overflow, Medium, Fender, Indeed), 6 were JavaScript-only apps, 2 were sign-in/placeholder pages, 1 was a `localhost` bookmark blocked by the private-address guard and 1 was dead. A browser-like user agent doesn't get past the 403s, so the honest one stays. Those pages stay in the feed as "Couldn't read this page"; the Summarise step will try Gemini reading the URL for them.

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
