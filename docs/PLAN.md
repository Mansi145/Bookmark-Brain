# Bookmark Brain: Plan and decisions

## Context
This is a learning project to understand how AI agents are integrated into real software. It will also go on a CV. The app collects your browser bookmarks (Chrome, Edge, Brave, Firefox), shows them as your own newspaper-style front page, summarises them with AI, and lets you search them by keyword and by meaning. Later phases add a chat agent that answers questions from your saved articles, auto-tagging, dead-link and reading-status tracking, and a weekly digest. The app is deployed and supports multiple users, so it works without your PC running. Everything runs on free tiers.

## Status
| Phase | What | State |
|---|---|---|
| 0 | Foundations | ✅ Done |
| 1 | Google sign-in, extension sync, feed | ✅ Done, plus one-click extension connect and the extension icon |
| 2 | Page fetching + AI summaries | ✅ Job queue, safe fetcher, `fetch_page` + `find_archive` (article text, reading time, Needs sign-in and Dead links sections), on-demand summaries (`ai/llm.py`, `summarise` job, daily limit, Limit reached dialog + maintainer email) and the bookmark detail panel |
| 3–8 | Search, agent, tags, dead links, digest, deploy | Planned |
| UI | Apply the final design (below) to the React app; GitHub sign-in | ✅ Done: sign-up, How it works, Connect and error pages, the newspaper feed with its sections and detail panel, warm charcoal dark mode, account menu, Settings (Browsers, Account), free-plan note, Limit reached dialog, logo animations. Designed, built with their phases: Lens (3), Ask and Conversation (4), Digest (7). GitHub sign-in planned (the button is shown but disabled) |

## Decisions (and why)
| Area | Choice | Why |
|---|---|---|
| Bookmark source | **Browser extension** (Manifest V3, built with **WXT**) | Web pages can't read bookmarks; only extensions can, through `chrome.bookmarks`. WXT builds Chrome, Edge, Brave and Firefox versions from one codebase. |
| Extension permissions | Only `bookmarks`, `storage`, `alarms`, plus host access to our own API | Broad host access ("read and change all your data on all websites") would scare users. That's also why the extension never fetches pages itself; the server does. |
| Connecting the extension | **One-click connect**: the popup opens the web app's `/connect` page with a one-time code; the page creates a token and hands it to a content script via `window.postMessage` | Copy-pasting tokens is a bad first-run experience. The content script runs only on `/connect`, accepts messages only from that page, and only with the pending code (15 min, single use). Manual token paste stays as a fallback. Works the same in every browser. |
| Backend | **FastAPI**, SQLAlchemy 2 (async) + asyncpg, Alembic, pydantic-settings, `uv` | Modern async Python; Pydantic models double as API schemas. |
| LLM | **A chain of free models** through LangChain's `.with_fallbacks()`: Gemini Flash-Lite → Gemini Flash (its own quota, same key) → OpenRouter's free models → NVIDIA NIM (DeepSeek) → Groq. A provider without a key is skipped | All free. Each free tier has its own quota and its own outages (`gemini-3.5-flash` answered 503 most of the time), so several independent providers mean fewer failed summaries. Gemini handles long input well and supports tool calling. (The Claude API was considered but isn't free; a Claude.ai subscription can't be used by an app.) |
| Embeddings | **Gemini embedding model** (free), stored in **pgvector** | Free, and stored in the same database as everything else (no separate vector DB). |
| Agent framework | **LangChain + LangGraph**, traced with **LangSmith** (free tier) | LangGraph shows the agent as nodes, edges and state. LangSmith lets you see every LLM and tool call, which helps a lot when learning. |
| Search | **Hybrid**: Postgres full-text (`tsvector`) + pgvector similarity, merged with Reciprocal Rank Fusion (RRF) | Keyword search finds exact terms; semantic search finds meaning. RRF is a simple, standard way to merge two ranked lists. |
| Frontend | **React + Vite + TypeScript**, TanStack Query, Tailwind v4, React Router | Industry standard; handles streaming chat UI well. |
| Auth | **Google Sign-In**; the backend verifies the ID token and issues its own JWT in an httpOnly cookie. **GitHub sign-in** to be added (the landing page design has both buttons) | The extension uses a personal access token (`bb_pat_…`, only a SHA-256 hash is stored). |
| Hosting | **Render** (API) + **Neon** (Postgres + pgvector) + **Vercel** (frontend). Free tier; cron-job.org pings `/health` every 10 min to stop Render sleeping | $0. The ping avoids the 30–50s cold start and keeps the background worker running. |
| Background jobs | **`jobs` table + in-process asyncio worker** (4 loops, `SELECT … FOR UPDATE SKIP LOCKED`), started from the FastAPI lifespan | No Redis or Celery needed (Render's free tier has no worker service). Jobs survive restarts; retries with back-off (30 s, 2 min) then `failed` after 3 attempts; a job stuck `running` for 10 min is taken over. Slow work never runs inside a request: it would make sync take minutes, hit request time limits, and let one slow site break everything. |
| Fetching pages | **`app/services/fetch.py`**: one HTTP client that refuses private/loopback/link-local addresses on every request and redirect | The server fetches URLs users choose, so without this a bookmark like `http://localhost:5432` or a cloud metadata address could make it probe its own network (SSRF). |
| Summaries | **On demand**: a *Summarise* button on every bookmark; nothing is summarised automatically. Results are cached per URL | Saves the shared free-tier quota for pages someone actually wants summarised. Pages without stored text are summarised from their title and description. Every summary records its source (page / archive / metadata), but the UI shows them all the same way (owner's decision: badges made the app look unreliable). |
| Needs sign-in | Pages that need an **account or subscription** (sign-in redirects, password forms, logged-in web apps, `isAccessibleForFree: false`) get their own **Needs sign-in** section | We fetch anonymously, so these only ever show a sign-in screen. Detection uses signs sites leave, without network calls; bot challenges (403) are not sign-in. These URLs are never sent to archive.org, since they may be private. |
| Dead links | Pages that are **dead (404/410)** live in a separate **Dead links** section, never in the main feed. The Wayback Machine is asked **only when the user clicks "Find archived copy"** on a dead row | Keeps the feed about pages that work today. Automatic lookups sent many URLs to a third party and hit archive.org's rate limits; on demand, a user chooses each lookup. Private-looking URLs are never sent. |
| Preview images | **Only on the top story.** The page's `og:image` URL is read while fetching; the reader's browser loads it from the site | Many bookmarks (docs, references) have no image or a generic logo, so the feed stays text-first; one image on the lead makes the front page look like a newspaper. If it fails to load, the lead is text-only. |
| Quota protection | Summaries/embeddings cached **per URL** (shared across users); a per-user daily AI limit, checked and counted in one SQL statement | Free quotas are per API key, so every user shares the same daily limit. One statement means two quick clicks can't both slip under the limit. |
| Email | **Resend** free plan (100 emails a day), one HTTPS call in `services/mail.py` | The only email so far is "a user hit the daily limit" to the maintainer, at most once a day per user. No SDK needed, and tests mock the call with `httpx.MockTransport`. |
| Account data | **Download my data** (a JSON file) and **Delete account** (type DELETE), web app session only | Users own their data. Deleting the user row removes everything personal through `ON DELETE CASCADE`; shared per-URL documents stay, since they aren't personal. Accepting only the session cookie means a leaked extension token can't export or wipe an account. |
| Feed paging | Scrolling (keyset cursor) for Today and This week; **numbered pages** (OFFSET + a total) for Earlier | A keyset cursor stays fast and stable while new bookmarks arrive, but can't jump to page 7. Earlier is a long archive where page numbers help, and OFFSET is fine at a few thousand bookmarks per user. |
| Logo animations | **CSS keyframes on the inline SVG**, not GIFs | Sharp at any size, almost no bytes, starts and stops with the app's state, and can move single parts (one B, a corner badge). With reduced motion it just stays still. A GIF would blur at 30 px, can't stop at the end of a turn, and would need re-exporting after every change. |
| Repo | One monorepo for backend, frontend and extension | Shared docs, one PR per feature across all three, simpler for a solo project. |

## Design (final direction)
Designs live on the Claude design canvas (https://claude.ai/artifact/88oGw1iJQJW2P8tB6jRBVT; private to the owner). Details and tokens are in the `ui-design` skill. Trials that were compared and decided (newspaper layouts, dark mode options) are kept on the canvas's Archive page for reference.
- **Brand texture**: a dark "Nude" nebula (blurred warm-brown circles over `#503931 → #564D3A` with film grain) with white text on it, used everywhere: the sign-up, How it works, Connect and error pages, the app's top bar and the extension popup header (replaced the earlier blue → pink Cloudlifter texture on 2026-10-23).
- **Backgrounds**: never pure white. Three off-white layers: page `#ECEAE7` → panels `#F5F4F2` behind the filters and the feed → a card `#FBFAF8` per article. Near-black text.
- **Accents**: always the dark Nude colours (`#503931`, `#564D3A`) with white text, never light tints, in both themes. **Fonts**: Aleo (headings, titles), Geist (UI). Light and dark themes: follows the system until the user flips the Dark mode switch in the account menu. Dark mode is **warm charcoal** (`#1F1C1A` page, `#2D2926` cards, `#EEE8E2` text), chosen over a near-black version that felt too harsh.
- **Logo**: "Masthead BB", a backwards B and a B sharing one spine, between newspaper rules on a cream tile (same in both themes). A full version for 64 px and up and a small one for top bars, the popup, the favicon and the extension icons.
- **Sign-up page**: one screen on the texture with "Saved it? Now actually use it.", dark Google + GitHub sign-in buttons with the real marks, an image-free preview of the feed, and a link to a separate **How it works** page (steps, features, closing call to action).
- **App**: top nav Feed · Ask · Digest; the account button opens a menu with Settings, the Dark mode switch and Sign out. The feed is a filter sidebar (Browsers, Folders, Tags) plus a **newspaper front page**: Today / This week / Earlier are editions (one sheet each, a masthead, thin column rules), the newest unread stories are biggest (lead → second → standard → brief) and read ones go last, faded. A bar above it switches All · Unread · Read | Needs sign-in · Dead links; those two sections are one sheet each. Each story: site logo · site · read time · age, Aleo headline, its state line, the summary (full on the lead, fewer lines as stories get smaller, none on briefs) or a **Summarise** button. Small stories (briefs) show a compact Summarise / Open summary instead of summary text. Earlier is split into numbered pages of 30, newest first. Clicking a headline opens a detail side panel; opening it never marks a bookmark read, and **Mark as read** moves the story to Read (with Mark as unread to move it back). One column at 760 px and below. Search results replace the feed; Ask is a chat with a sources rail; Digest is a weekly **newsletter** (back-issue tabs, a masthead, the AI overview as an editor's note, a section per theme).
- **Settings**: Browsers (connect, connected browsers) and Account (your account, Download my data, Delete account with "Type DELETE to confirm"). No AI usage is shown to users.
- **Free plan**: a short note next to AI actions says the project runs on free plans with a small shared daily limit; when the limit is hit, a **Limit reached** dialog lets the user email the maintainer (with their account email and the time).
- **Logo animations**: the top-bar logo moves while the app works, a different movement per job: Page back (summarising), Rewind (a page loading), Hourglass (the Wayback Machine), Lens (searching) and Conversation (Ask). Lens and Conversation arrive with search and the Ask page.

## Architecture
```
 Extension ──(PAT, POST /api/sync)──────────────┐
   ▲ one-click connect: /connect page → content script hands over the token
   │                                            ▼
 React app (Vercel) ──(cookie, REST + SSE)──► FastAPI (Render) ──► Neon Postgres (+pgvector, FTS)
                                                │   ▲
                         in-process job worker: fetch page (safe fetcher) → extract text (trafilatura)
                                                │       → summarise → embed → tag
                                                ▼
                                 LangChain: Gemini ──fallback──► Groq      (traces → LangSmith)
```

## Repo layout
```
bookmark_brain/
├── CLAUDE.md, .claude/skills/   conventions and how-tos for AI-assisted development
├── docker-compose.yml           local pgvector/pgvector:pg16
├── docs/PLAN.md                 this file
├── backend/
│   ├── alembic/versions/        0001 pgvector … 0008 (jobs, page content, summaries, preview images, limit notices)
│   └── app/
│       ├── main.py              FastAPI app, CORS, routers, lifespan starts the worker
│       ├── config.py            pydantic-settings (env vars)
│       ├── db.py, models.py     engine/session, ORM models
│       ├── schemas.py           request/response models
│       ├── auth/                Google token check, session JWTs, PATs
│       ├── api/                 health, auth, tokens, sync, bookmarks, usage, account (later: search, chat, digest)
│       ├── services/            urls, sync, fetch (safe page fetcher), extract, access, archive, icons, preview,
│       │                        usage (daily limit), mail (Resend)
│       ├── worker.py            job queue: enqueue, claim, retry, handlers
│       └── ai/                  llm.py (fallback chain), prompts/, chains.py (later: agent/)
│   └── tests/
├── frontend/src/
│   ├── api/                     fetch client + types (mirror schemas.py)
│   ├── pages/                   Login, HowItWorks, Feed, Settings, Connect, ErrorPages
│   ├── components/              Layout, Newspaper (feed), StoryParts, BookmarkDetail, LimitDialog, AccountSettings, Logo
│   ├── hooks/                   useMe, useSummarise, useLogoMotion, useTheme, useSignOut
│   └── lib/                     cache helpers, editions, limit
└── extension/
    ├── entrypoints/             background.ts (sync), connect.content.ts, popup/
    ├── lib/                     sync.ts (bookmarks → API), connect.ts (one-click connect)
    ├── assets/icon/             logo SVG sources; `npm run icons` → public/icon/*.png
    └── wxt.config.ts            manifest, permissions
```

## Data model
Built so far:
- `users` (google_sub, email, name, avatar_url)
- `api_tokens` (user_id, name, token_hash, prefix, last_used_at): PATs for the extension
- `documents` (normalized_url unique, url, site, status [pending/fetched/summarised/failed/dead], title, description, content_text, word_count, http_status, fetched_at, content_source [page/archive], archive_status, archive_url, archived_on, access [login/paywall], icon_url, image_url; summary, key_points jsonb, summary_status, summary_source, summary_model, summarised_at). **Shared across users**, so each URL is fetched and summarised once.
- `bookmarks` (user_id, document_id, title, added_at, read_state [unread/read], deleted_at). Unique on (user_id, document_id). Soft-deleted when no browser has it any more.
- `bookmark_sources` (user_id, bookmark_id, source_id, browser, node_id, title, folder_path, added_at): where a bookmark lives in each browser install; unique on (user_id, source_id, node_id).
- `jobs` (kind, payload jsonb, status [queued/running/done/failed], attempts, run_after, locked_at, last_error)
- `ai_usage` (user_id, day, summaries, limit_reached_at, maintainer_notified_at): the per-user daily limit and the once-a-day maintainer email.

Planned:
- `documents`: embedding vector + embedding_model, tsv tsvector (Phase 3); last_checked_at (Phase 6).
- `tags`, `bookmark_tags` (user-scoped; `source` = ai|user); `chat_threads`, `chat_messages`; `digests`.
- Indexes: GIN on `tsv`, HNSW on `embedding`.

## Phases (each ends with something working and deployable)

**Phase 0: Foundations. ✅** Monorepo, docker-compose Postgres + pgvector, FastAPI `/health`, Alembic, Vite app, `CLAUDE.md` + skill files.

**Phase 1: Auth + extension sync (no AI yet). ✅**
- Google Sign-In → `POST /api/auth/google` → JWT in an httpOnly cookie.
- Extension: full sync on install/startup, incremental sync on bookmark events, hourly safety-net sync, retry alarm. Per-install source id so browsers and profiles merge correctly.
- Backend normalises URLs, upserts documents/bookmarks/sources idempotently, merges the same URL from several browsers into one bookmark.
- Feed with infinite scroll (keyset pagination) and folder/browser filters.
- Added after: **one-click connect** (popup → `/connect` → content script; the page shows steps and bookmarks arriving during the first sync, then a summary with an Open your feed button) and the **extension icon**.

**Phase 2: Ingestion + summaries (first AI integration). ✅**
- ✅ `jobs` table, worker, safe page fetcher.
- ✅ `fetch_page`: sync enqueues it for new documents; the handler extracts title, description and article text with `trafilatura` (under 50 words = no article), and reading time comes from the word count. Real-world result: roughly half of typical bookmarks yield article text; the rest are bot-protected (403), JavaScript apps or sign-in walls, which keep their title/description.
- ✅ Dead links (404/410) form the **Dead links** section; `find_archive` looks up a Wayback copy only when the user clicks "Find archived copy" (`POST /api/bookmarks/{id}/find-archive`). Site logos are read from each page's `<head>`.
- ✅ Sign-in detection (`services/access.py`): pages needing an account or subscription form the **Needs sign-in** section and are never sent to archive.org.
- ✅ `ai/llm.py`: a fallback chain via `.with_fallbacks()`: `gemini-3.5-flash-lite` → `gemini-2.5-flash` → OpenRouter `nvidia/nemotron-3.5-super-vl:free` → NVIDIA NIM `deepseek-ai/deepseek-v4.1-flash` → Groq `openai/gpt-oss-120b`; model names come from config, and a provider without a key is skipped. `gemini-3.5-flash` was tried first but was mostly overloaded (503s) on the free tier.
- ✅ Summarise chain (`ai/chains.py`): `with_structured_output(Summary)` → `{summary, key_points[]}`; the page goes in `<article>` tags as untrusted data; input cut to 12,000 characters (about 3,000 tokens) because Groq's free tier allows 8,000 tokens a minute.
- ✅ `summarise` job started by the **Summarise** button (`POST /api/bookmarks/{id}/summarise`, `?again=true` for Re-summarise), counted against the per-user daily limit (`ai_usage`, checked and counted in one SQL statement). Cached per URL: a summary someone already made is free. Input: page text, a Wayback copy's text, or the title and description. Retried once, then "Couldn't summarise this page."
- ✅ Feed rows show the summary (or the site's description), with Summarise / "Summarising…" / failed / daily-limit states; the title opens the **detail panel** (summary, key points, Open page, Mark as read, Re-summarise, where it's saved).
- ✅ The main feed is a **newspaper front page** (editions, newest unread biggest); only the lead story shows the page's preview image (`og:image`, loaded from the site; `find_image` backfills older pages).
- ✅ The free-plan note next to AI actions and the per-user "Limit reached" dialog (email the maintainer). Any 429 from an AI action opens it; "Notify the maintainer" sends at most one email per user per day through Resend.
- ✅ The top-bar logo animates while the app works: Page back while summarising, Rewind while a page loads, Hourglass while the Wayback Machine is asked.
- Later: try Gemini's URL context tool for pages we couldn't read.
- *You'll learn:* prompts, structured output, fallbacks, cost and quota control, async job processing.

**Phase 3: Hybrid search.**
- An embed job writes `documents.embedding` (title + summary + first part of content). A generated column keeps `tsv` updated.
- `GET /api/search?q=` runs an FTS query (`websearch_to_tsquery`) and a vector query (cosine distance), each limited to the user's bookmarks, then merges them with RRF (`score = Σ 1/(60+rank)`).
- Search bar in the top bar with debounce; matching words highlighted (`ts_headline`). The logo plays Lens while a search runs.
- *You'll learn:* embeddings, vector indexes, ranking.

**Phase 4: "Ask your bookmarks" agent (LangGraph).**
- Tools: `search_bookmarks(query)`, `get_article(doc_id)`, `list_by_tag(tag)`, `summarise_many(doc_ids)`. Every tool is limited to the current user's bookmarks.
- Before using LangGraph, write a ~50-line plain-Python tool-calling loop in `ai/agent/manual_loop.py` (for learning only) so you can see what LangGraph does for you.
- Graph: `agent` node (LLM with tools bound) ↔ `tools` node (ToolNode), with a conditional edge on whether the model requested tool calls. Conversation memory is saved with a Postgres checkpointer. Answers cite doc ids, which the UI renders as links.
- `POST /api/chat` streams tokens and tool steps over SSE. The logo plays Conversation until the answer starts.
- *You'll learn:* tool calling, agent loops, state, memory, streaming, tracing in LangSmith.

**Phase 5: Auto-tags & smart collections.** A tag chain picks tags from the user's existing tags and suggests new ones (structured output). Collections are built by clustering embeddings (k-means, using the LLM to name each cluster). Near-duplicates are detected by cosine similarity above about 0.95.

**Phase 6: Dead links & reading status.** A periodic `link_check` job (same safe fetcher) re-checks pages over time: newly dead pages move to the Dead links section with their Wayback Machine copy (the first check already happens at sync time in Phase 2). Reading states are unread/read. Opening a bookmark never marks it read; the detail panel's Mark as read / Mark as unread does. The feed can filter by state and sort by reading time.

**Phase 7: Weekly digest.** A GitHub Actions cron calls `POST /internal/digest` (protected by a shared secret). It picks unread bookmarks older than 30 days, a digest chain writes a short themed overview, and the result is saved to `digests` and shown on the Digest page as a newsletter, with earlier weeks as back issues. Email (Resend free tier) is optional.

**Phase 8: Deploy & polish.** Neon DB + migrations, Render web service, Vercel frontend, CORS and cookie settings for cross-site use, keep-warm ping, publish the extension (Chrome Web Store unlisted, or load-unpacked; add the deployed `/connect` URL to the content script). README with architecture diagram + demo GIF for the CV. CI: ruff + pytest + tsc on GitHub Actions.

## Skill files
Stored in `.claude/skills/<name>/SKILL.md` and updated as each phase lands:
- **dev-setup**: run everything locally; env vars.
- **background-jobs**: how the queue works and how to add a job kind.
- **extension**: sync model, one-click connect and its security rules, building, icons.
- **ui-design**: the final design direction and tokens for building the React UI.
- **llm-patterns**: how we call LLMs (single entry point, prompts, structured output, quotas).
- **langgraph-agent**: adding tools/nodes to the chat agent.
- **db-migrations**: Alembic + pgvector workflow and autogenerate pitfalls.
- **git-workflow**: branches, PRs, changelog, commit rules.
- **deploy**: Render / Neon / Vercel, keep-warm ping, extension publishing.

## Verification
- **Backend:** `pytest` against a separate test Postgres database. Covers URL normalisation, auth, tokens, sync merging, user isolation, pagination (scrolling and numbered pages), the job queue, the fetcher, summaries and the model fallback order, the daily limit and the maintainer email, and account export / delete. No real network: models are faked and Resend is mocked with `httpx.MockTransport`. The agent will be tested the same way.
- **Agent:** an eval script with about 10 questions about fixture bookmarks, checking the cited documents. Inspect traces in LangSmith.
- **End-to-end (manual):** load the extension unpacked → click **Connect this browser** → sign in → the page shows the first sync, then a summary → **Open your feed** → click Summarise and the summary appears within about a minute → search "that article about X" finds it → ask the chat a question and get a cited answer. Repeat in Edge/Firefox to confirm the same URL merges into one bookmark.
- **Deployed:** the same flow against the Vercel URL. Check that `/health` responds in under 1s after a long idle period.
