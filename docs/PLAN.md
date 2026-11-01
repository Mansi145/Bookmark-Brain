# Bookmark Brain: Plan and decisions

## Context
This is a learning project to understand how AI agents are integrated into real software. It will also go on a CV. The app collects your browser bookmarks (Chrome, Edge, Brave, Firefox), shows them as your own newspaper-style front page, summarises them with AI, and lets you search them by keyword and by meaning. Later phases add a chat agent that answers questions from your saved articles, auto-tagging, dead-link and reading-status tracking, and a weekly digest. The app is deployed and supports multiple users, so it works without your PC running. Everything runs on free tiers.

## Status
| Phase | What | State |
|---|---|---|
| 0 | Foundations | ✅ Done |
| 1 | Google sign-in, extension sync, feed | ✅ Done, plus one-click extension connect and the extension icon |
| 2 | Page fetching + AI summaries | ✅ Job queue, safe fetcher, `fetch_page` + `find_archive` (article text, reading time, Needs sign-in and Dead links sections), on-demand summaries (`ai/llm.py`, `summarise` job, daily limit, Limit reached dialog + maintainer email) and the bookmark detail panel |
| 3 | Hybrid search | Built: embeddings, search API and the search screens. Results aren't right yet (owner, 2026-11-01): fixing them is the first item under Later |
| 4–8 | Agent, tags, dead links, digest, deploy | Planned |
| UI | Apply the final design (below) to the React app; GitHub sign-in | ✅ Done: sign-up, How it works, Connect and error pages, the newspaper feed with its sections and detail panel, warm charcoal dark mode, account menu, Settings (Browsers, Account), free-plan note, Limit reached dialog, logo animations. Designed, built with their phases: Lens (3), Ask and Conversation (4), Digest (7). GitHub sign-in planned (the button is shown but disabled) |

## Decisions (and why)
| Area | Choice | Why |
|---|---|---|
| Bookmark source | **Browser extension** (Manifest V3, built with **WXT**) | Web pages can't read bookmarks; only extensions can, through `chrome.bookmarks`. WXT builds Chrome, Edge, Brave and Firefox versions from one codebase. |
| Extension permissions | Only `bookmarks`, `storage`, `alarms`, plus host access to our own API | Broad host access ("read and change all your data on all websites") would scare users. That's also why the extension never fetches pages itself; the server does. |
| Connecting the extension | **One-click connect**: the popup opens the web app's `/connect` page with a one-time code; the page creates a token and hands it to a content script via `window.postMessage` | Copy-pasting tokens is a bad first-run experience. The content script runs only on `/connect`, accepts messages only from that page, and only with the pending code (15 min, single use). Manual token paste stays as a fallback. Works the same in every browser. |
| Backend | **FastAPI**, SQLAlchemy 2 (async) + asyncpg, Alembic, pydantic-settings, `uv` | Modern async Python; Pydantic models double as API schemas. |
| LLM | **A chain of free models** through LangChain's `.with_fallbacks()`: Gemini Flash-Lite → Gemini Flash (its own quota, same key) → OpenRouter's free models → NVIDIA NIM (DeepSeek) → Groq. A provider without a key is skipped | All free. Each free tier has its own quota and its own outages (`gemini-3.5-flash` answered 503 most of the time), so several independent providers mean fewer failed summaries. Gemini handles long input well and supports tool calling. (The Claude API was considered but isn't free; a Claude.ai subscription can't be used by an app.) DeepSeek's own API has no free tier, so it comes through NVIDIA NIM; Mistral's free tier was left out because it requires opting into training on your data. |
| Embeddings | **`gemini-embedding-2`** at **768 dimensions** (free), stored in **pgvector** with the model's name | Free, and stored in the same database as everything else (no separate vector DB). 768 numbers per page instead of the default 3,072 is Google's recommended smaller size: a quarter of the storage and faster comparisons for almost the same quality. Vectors from different models can't be compared, so the model's name is stored, and changing models means re-embedding every page. |
| When pages are embedded | **Automatically**, as soon as a page is fetched, and again after it's summarised. One `embed_pages` job embeds up to 50 waiting pages per request | Unlike a summary (on demand), an embedding is cheap, cached per URL, and search and Ask can only find pages that have one. Batching means a 500-bookmark import is about 10 requests instead of 500, against a free quota we can't see, and a rate limit makes one job wait instead of hundreds retrying at once. Pages we couldn't read are embedded from their title and description. A summary states the page's meaning in a few clean sentences, so re-embedding from it gives better matches (owner). Sign-in pages we couldn't read get no embedding: all we saw was a login screen, and that sits close to every search. Pages with nothing but a title use the title the user saved, because a fetched title can be a placeholder ("Site en construction" was saved as "The Hacker Playbook 2") (owner, 2026-10-30). |
| Embedding fallback | **Keyword search only** when Gemini's embedding model is unavailable; no second provider | Search falls back to keyword matches, which look exactly like normal results: search never says how it matched (owner, 2026-11-01). A backup provider would need a second set of vectors, with every page embedded twice, because vectors from different models can't be mixed. NVIDIA NIM was the candidate, but its limit (about 40 requests a minute) isn't published and may be shared with the summary fallback; Groq has no embedding models, and OpenRouter's free allowance is shared with its chat models (owner, 2026-10-30). |
| Agent framework | **LangChain + LangGraph**, traced with **LangSmith** (free tier) | LangGraph shows the agent as nodes, edges and state. LangSmith lets you see every LLM and tool call, which helps a lot when learning. |
| Search | **Hybrid**: Postgres full-text (`tsvector`, English dictionary, title weighted most; also the title the user saved and their folder names) + pgvector similarity, merged with weighted Reciprocal Rank Fusion (RRF, k = 60, keyword matches weighted 1.5) over the top 50 of each | Keyword search finds exact terms; semantic search finds meaning. Folder names are labels the user chose ("Django", "Job hunt"), so a search for one finds everything filed there (owner). RRF is a simple, standard way to merge two ranked lists: it uses only each result's place in each list, so the two lists' very different scores never have to be compared. Keyword matches get priority (owner, 2026-10-30): a page containing your words is a surer match than one that's only close in meaning. Weighting them, rather than always putting them first, still lets a page both halves agree on rise; the 1.5 gets tuned with the script once keyword search exists. Meaning search always returns the *nearest* pages, even when none is close. A cutoff comes later (owner, 2026-10-30): one fixed score doesn't work, because unrelated pages score anywhere from 0.45 to 0.64 depending on the search. The best rule in tests (19 searches over the local pages) was a floor of 0.65 plus staying within 0.07 of that search's best match. |
| Search results | **At most 10**, best first, no Show more. Everything the user saved is searched (read stories, Needs sign-in, Dead links), and the sidebar's browser and folder filters narrow it (tags too, once they exist) | Owner's decisions (2026-10-30). 10 rather than 20 keeps the noise down while there's no cutoff, since meaning search always fills every slot. The count reads "Top 10 matches" when more matched, otherwise "N bookmarks". No results gets an empty card with tips; search never says how it matched, so keyword-only results look like any others (owner, 2026-11-01); a failed search gets "Couldn't search right now" with Try again inside the results sheet. The search field gets a clear × once there's text (Escape clears too, back to the feed), and results look the same whatever they matched on: no folder label on a folder match. |
| Search cost | **Searches don't count toward the daily AI limit** (owner); instead a per-user throttle the user never sees (owner: no message, not even Couldn't search or the Limit reached dialog), a short-lived cache of query embeddings, and the keyword fallback | A search is one embedding of the query (a few words, free tier, no text generated) plus two database queries; the ranking itself only compares stored numbers. Searching as you type (after a 0.4 s pause, once there are 3+ characters; Enter searches straight away) could otherwise make several calls per word, so the cache and the cap keep it cheap. |
| Frontend | **React + Vite + TypeScript**, TanStack Query, Tailwind v4, React Router | Industry standard; handles streaming chat UI well. |
| Auth | **Google Sign-In**; the backend verifies the ID token and issues its own JWT in an httpOnly cookie. **GitHub sign-in** to be added (the landing page design has both buttons) | The extension uses a personal access token (`bb_pat_…`, only a SHA-256 hash is stored). |
| Hosting | **Render** (API) + **Neon** (Postgres + pgvector) + **Vercel** (frontend). Free tier; cron-job.org pings `/health` every 10 min to stop Render sleeping | $0. The ping avoids the 30–50s cold start and keeps the background worker running. |
| Background jobs | **`jobs` table + in-process asyncio worker** (4 loops, `SELECT … FOR UPDATE SKIP LOCKED`), started from the FastAPI lifespan | No Redis or Celery needed (Render's free tier has no worker service). Jobs survive restarts; retries with back-off (30 s, 2 min) then `failed` after 3 attempts; a job stuck `running` for 10 min is taken over. Slow work never runs inside a request: it would make sync take minutes, hit request time limits, and let one slow site break everything. |
| Fetching pages | **`app/services/fetch.py`**: one HTTP client that refuses private/loopback/link-local addresses on every request and redirect | The server fetches URLs users choose, so without this a bookmark like `http://localhost:5432` or a cloud metadata address could make it probe its own network (SSRF). |
| Summaries | **On demand**: a *Summarise* button on every bookmark; nothing is summarised automatically. Results are cached per URL | Saves the shared free-tier quota for pages someone actually wants summarised. Pages without stored text are summarised from their title and description. Every summary records its source (page / archive / metadata), but the UI shows them all the same way (owner's decision: badges made the app look unreliable). A summary is a short paragraph (5–6 sentences) plus 3–5 key points; two sentences looked too thin (owner). The newspaper shows as much as each story's size allows and the detail panel shows it all. |
| Needs sign-in | Pages that need an **account or subscription** (sign-in redirects, password forms, logged-in web apps, `isAccessibleForFree: false`) get their own **Needs sign-in** section | We fetch anonymously, so these only ever show a sign-in screen. Detection uses signs sites leave, without network calls; bot challenges (403) are not sign-in. These URLs are never sent to archive.org, since they may be private. |
| Dead links | Pages that are **dead (404/410)** live in a separate **Dead links** section, never in the main feed. The Wayback Machine is asked **only when the user clicks "Find archived copy"** on a dead row | Keeps the feed about pages that work today. Automatic lookups sent many URLs to a third party and hit archive.org's rate limits; on demand, a user chooses each lookup. Private-looking URLs are never sent. The "Archived" reading state was dropped at the same time: it was confusing next to Dead links, so only Unread and Read remain. |
| Preview images | **Only on the top story.** The page's `og:image` URL is read while fetching; the reader's browser loads it from the site | Many bookmarks (docs, references) have no image or a generic logo, so the feed stays text-first; one image on the lead makes the front page look like a newspaper. If it fails to load, the lead is text-only. |
| Quota protection | Summaries/embeddings cached **per URL** (shared across users); a per-user daily AI limit, checked and counted in one SQL statement | Free quotas are per API key, so every user shares the same daily limit. One statement means two quick clicks can't both slip under the limit. |
| Email | **Resend** free plan (100 emails a day), one HTTPS call in `services/mail.py` | The only email so far is "a user hit the daily limit" to the maintainer, at most once a day per user. No SDK needed, and tests mock the call with `httpx.MockTransport`. |
| Account data | **Download my data** (a JSON file) and **Delete account** (type DELETE), web app session only | Users own their data. Deleting the user row removes everything personal through `ON DELETE CASCADE`; shared per-URL documents stay, since they aren't personal. Accepting only the session cookie means a leaked extension token can't export or wipe an account. |
| Feed paging | Scrolling (keyset cursor) for Today and This week; **numbered pages** (OFFSET + a total) for Earlier | A keyset cursor stays fast and stable while new bookmarks arrive, but can't jump to page 7. Earlier is a long archive where page numbers help, and OFFSET is fine at a few thousand bookmarks per user. |
| Logo animations | **CSS keyframes on the inline SVG**, not GIFs | Sharp at any size, almost no bytes, starts and stops with the app's state, and can move single parts (one B, a corner badge). With reduced motion it just stays still. A GIF would blur at 30 px, can't stop at the end of a turn, and would need re-exporting after every change. |
| Repo | One monorepo for backend, frontend and extension | Shared docs, one PR per feature across all three, simpler for a solo project. |

## Design (final direction)
Designs live on the Claude design canvas (https://claude.ai/artifact/88oGw1iJQJW2P8tB6jRBVT; private to the owner). Details and tokens are in the `ui-design` skill. Trials that were compared and decided (newspaper layouts, dark mode options) are kept on the canvas's Archive page for reference.
- **Brand texture**: a dark "Nude" nebula (blurred warm-brown circles over `#503931 → #564D3A` with film grain) with white text on it, used everywhere: the sign-up, How it works, Connect and error pages, the app's top bar and the extension popup header.
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
                                 LangChain: summaries Gemini → … → Groq (fallback chain), embeddings Gemini   (traces → LangSmith)
```

## Repo layout
```
bookmark_brain/
├── CLAUDE.md, .claude/skills/   conventions and how-tos for AI-assisted development
├── docker-compose.yml           local pgvector/pgvector:pg16
├── docs/PLAN.md                 this file
├── backend/
│   ├── alembic/versions/        0001 pgvector … 0009 (jobs, page content, summaries, preview images, limit notices, search)
│   ├── scripts/                 explore_search.py (dev only: explains how search ranks the local pages)
│   └── app/
│       ├── main.py              FastAPI app, CORS, routers, lifespan starts the worker
│       ├── config.py            pydantic-settings (env vars)
│       ├── db.py, models.py     engine/session, ORM models
│       ├── schemas.py           request/response models
│       ├── auth/                Google token check, session JWTs, PATs
│       ├── api/                 health, auth, tokens, sync, bookmarks, search, usage, account (later: chat, digest)
│       ├── services/            urls, sync, fetch (safe page fetcher), extract, access, archive, icons, preview,
│       │                        usage (daily limit), mail (Resend), search (hybrid search, query embeddings)
│       ├── worker.py            job queue: enqueue, claim, retry, handlers
│       └── ai/                  llm.py (models + embedder), embedding.py (what each page is embedded from),
│                                prompts/, chains.py (later: agent/)
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
- `documents` (normalized_url unique, url, site, status [pending/fetched/summarised/failed/dead], title, description, content_text, word_count, http_status, fetched_at, content_source [page/archive], archive_status, archive_url, archived_on, access [login/paywall], icon_url, image_url; summary, key_points jsonb, summary_status, summary_source, summary_model, summarised_at; embedding vector(768), embedding_model, embedded_at; `tsv`, a generated tsvector: title (A), description + summary + key points (B), the first 100,000 characters of page text (C)). **Shared across users**, so each URL is fetched, summarised and embedded once. Indexes: GIN on `tsv`, HNSW (cosine) on `embedding`.
- `bookmarks` (user_id, document_id, title, added_at, read_state [unread/read], deleted_at). Unique on (user_id, document_id). Soft-deleted when no browser has it any more.
- `bookmark_sources` (user_id, bookmark_id, source_id, browser, node_id, title, folder_path, added_at): where a bookmark lives in each browser install; unique on (user_id, source_id, node_id).
- `jobs` (kind, payload jsonb, status [queued/running/done/failed], attempts, run_after, locked_at, last_error)
- `ai_usage` (user_id, day, summaries, limit_reached_at, maintainer_notified_at): the per-user daily limit and the once-a-day maintainer email.

Planned:
- `documents.last_checked_at` (Phase 6).
- `tags`, `bookmark_tags` (user-scoped; `source` = ai|user); `chat_threads`, `chat_messages`; `digests`.

## Phases (each ends with something working and deployable)

**Phase 0: Foundations. ✅** Monorepo, docker-compose Postgres + pgvector, FastAPI `/health`, Alembic, Vite app, `CLAUDE.md` + skill files.

**Phase 1: Auth + extension sync (no AI yet). ✅**
- Google Sign-In → `POST /api/auth/google` → JWT in an httpOnly cookie.
- Extension: full sync on install/startup, incremental sync on bookmark events, hourly safety-net sync, retry alarm. Per-install source id so browsers and profiles merge correctly.
- Backend normalises URLs, upserts documents/bookmarks/sources idempotently, merges the same URL from several browsers into one bookmark.
- Feed with infinite scroll (keyset pagination) and folder/browser filters.
- Added after: **one-click connect** (popup → `/connect` → content script; the page shows steps and bookmarks arriving during the first sync, then a summary with an Open your feed button) and the **extension icon**.

**Phase 2: Ingestion + summaries (first AI integration). ✅ Released in v0.2.0.**
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
- *You'll learn:* prompts, structured output, fallbacks, cost and quota control, async job processing.

**Phase 3: Hybrid search.** Built in this order:
1. **Exploration script** (`backend/scripts/explore_search.py`, dev only): runs the real search on the local database and shows, for each result, its keyword place, its meaning place and similarity, and its merged score. It first showed what "close" means for real bookmarks (unrelated pages 0.45–0.64, real matches 0.68 and up); now it's for tuning the keyword weight and, later, the cutoff.
2. **Migration 0009**: `embedding vector(768)`, `embedding_model`, `embedded_at` and a generated `tsv` column on `documents`; a GIN index on `tsv` and an HNSW index on `embedding` (cosine); one `embed_pages` job queued to embed every page fetched before this.
3. **`embed_pages` job**: a page waits for it while `embedded_at` is null. `fetch_page` leaves it waiting when it finishes a page, as do `find_archive` (an archived copy's text) and `summarise` (a new summary), and each makes sure one job is queued (`queue_embedding`). The job embeds up to 50 waiting pages per request and queues itself again while more wait. Text in: title + description + the start of the page text; title + summary + key points once summarised; title + description for pages we couldn't read (the saved title when there's no description); nothing for sign-in pages we couldn't read. A rate limit makes it wait a minute without using up an attempt (for up to a day); a page left without an embedding is still found by keyword.
4. **`GET /api/search?q=`** (plus the feed's `folder` and `browser` filters): a keyword query (`websearch_to_tsquery('english', q)`, ranked with `ts_rank`, over the page's words plus the user's saved title and folder names) and a meaning query (cosine distance to the query's embedding; no cutoff yet), each the top 50 of the user's own bookmarks, merged with weighted RRF (`score = 1.5 / (60 + keyword rank) + 1 / (60 + meaning rank)`; a page missing from a list gets no term for it). Returns the best 10 and whether more matched; matching words come back marked (`ts_headline`). The query's embedding is cached for a few minutes; over the per-user throttle a search waits a moment for a free slot (the user just sees Searching…) and, if that takes too long, answers with keyword matches, never an error; if the embedding call fails, the keyword results come back alone, looking the same.
5. **Search UI**: the top-bar field searches after a 0.4 s pause once there are 3+ characters (Enter searches straight away). The results sheet replaces the feed, with its states: searching, results, no results, couldn't search (`ui-design` skill, Search). The logo plays Lens while a search runs.
6. **Tests**: a fake embedder that returns fixed vectors; RRF unit tests; user isolation, filters, the 10 cap, the keyword fallback and the throttle. No real API calls.
7. **If results still need help** (owner: measure the steps above first): embeddings at the model's full 3,072 numbers instead of 768 (pgvector's index then needs its `halfvec` type, since `vector` indexes stop at 2,000), and splitting long pages into pieces that are embedded separately (Phase 4's agent needs those pieces anyway, to quote passages).
- *You'll learn:* embeddings, cosine similarity, vector indexes (HNSW), full-text search, rank fusion.

**Phase 4: "Ask your bookmarks" agent (LangGraph).**
- Tools: `search_bookmarks(query)`, `get_article(doc_id)`, `list_by_tag(tag)`, `summarise_many(doc_ids)`. Every tool is limited to the current user's bookmarks.
- Before using LangGraph, write a ~50-line plain-Python tool-calling loop in `ai/agent/manual_loop.py` (for learning only) so you can see what LangGraph does for you.
- Graph: `agent` node (LLM with tools bound) ↔ `tools` node (ToolNode), with a conditional edge on whether the model requested tool calls. Conversation memory is saved with a Postgres checkpointer. Answers cite doc ids, which the UI renders as links.
- `POST /api/chat` streams tokens and tool steps over SSE. The logo plays Conversation until the answer starts.
- *You'll learn:* tool calling, agent loops, state, memory, streaming, tracing in LangSmith.

**Phase 5: Tags & smart collections.** A tag chain picks tags from the user's existing tags and suggests new ones (structured output). Collections are built by clustering embeddings (k-means, using the LLM to name each cluster). Near-duplicates are detected by cosine similarity above about 0.95.
- **User tags** (owner, 2026-10-30; not designed yet beyond the sidebar's Tags group and the detail panel's tags): a set of starter tags every user begins with, creating your own tags, tagging bookmarks by hand and filtering the feed by tag. Manual tagging works on its own, without AI; the tag chain then suggests from the same tags (`bookmark_tags.source` = user or ai). Whether starter tags are copied to each new user or shared is decided when this phase is planned.

**Phase 6: Dead links & reading status.** A periodic `link_check` job (same safe fetcher) re-checks pages over time: newly dead pages move to the Dead links section with their Wayback Machine copy (the first check already happens at sync time in Phase 2). Reading states are unread/read. Opening a bookmark never marks it read; the detail panel's Mark as read / Mark as unread does. The feed can filter by state and sort by reading time.

**Phase 7: Weekly digest.** A GitHub Actions cron calls `POST /internal/digest` (protected by a shared secret). It picks unread bookmarks older than 30 days, a digest chain writes a short themed overview, and the result is saved to `digests` and shown on the Digest page as a newsletter, with earlier weeks as back issues. Email (Resend free tier) is optional.

**Phase 8: Deploy & polish.** Neon DB + migrations, Render web service, Vercel frontend, CORS and cookie settings for cross-site use, keep-warm ping, publish the extension (Chrome Web Store unlisted, or load-unpacked; add the deployed `/connect` URL to the content script). README with architecture diagram + demo GIF for the CV. CI: ruff + pytest + tsc on GitHub Actions.

**Later: make search results right** (owner, 2026-11-01: "still not correct results"). Known causes and what to try, measured with `scripts/explore_search.py` on the same queries before and after each change:
- No cutoff yet, so weak meaning matches fill all 10 slots. The best rule in tests was a floor of 0.65 plus staying within 0.07 of that search's best match.
- A keyword match found only deep in a long page gets the full 1.5 keyword weight ("python job openings" ranks the Go essay 2nd with a meaning similarity of just 0.55). Option: count such matches less, or only when the page is also close in meaning.
- Step 7's options: embeddings at the full 3,072 numbers, and long pages split into pieces.
- Re-embedding after a summary scored slightly worse than the page's own text in testing; worth dropping.
- More bookmarks to test with: 23 local pages is a small sample.

**Later: work that runs while nobody is using the app** (owner, 2026-10-30). The worker already runs whenever the server is awake, and in production the keep-warm ping keeps it awake, so queued jobs finish without anyone having the app open. What's missing is something that *queues* work by itself: today jobs only start from a sync or a button. A scheduler (a timed loop in the worker, or an external cron calling a protected endpoint, as the digest will) could, for example, summarise unread bookmarks with quota left over at the end of the day, re-check links (Phase 6) and write the digest (Phase 7), all within the free quotas. New bookmarks can only arrive while a browser with the extension is open, since they live in the browser; the extension already syncs in the background (on every change and hourly) without the web app open.

**Later: a "time I have" page** (owner, 2026-10-30; not designed or scheduled). The user says how much time they have, say 20 minutes, and the app picks unread articles that fit it, using the reading time `fetch_page` already stores (from each page's word count).

**Later: Gemini's URL context tool** for pages we couldn't read (an idea, not planned).

## Skill files
How-tos live in `.claude/skills/<name>/SKILL.md` (listed in `CLAUDE.md`) and are updated as each phase lands.

## Verification
- **Backend:** `pytest` against a separate test Postgres database. Covers URL normalisation, auth, tokens, sync merging, user isolation, pagination (scrolling and numbered pages), the job queue, the fetcher, summaries and the model fallback order, the daily limit and the maintainer email, account export / delete, embeddings and search. No real network: models are faked and Resend is mocked with `httpx.MockTransport`. The agent will be tested the same way.
- **Agent:** an eval script with about 10 questions about fixture bookmarks, checking the cited documents. Inspect traces in LangSmith.
- **End-to-end (manual):** load the extension unpacked → click **Connect this browser** → sign in → the page shows the first sync, then a summary → **Open your feed** → click Summarise and the summary appears within about a minute → search "that article about X" finds it → ask the chat a question and get a cited answer. Repeat in Edge/Firefox to confirm the same URL merges into one bookmark.
- **Deployed:** the same flow against the Vercel URL. Check that `/health` responds in under 1s after a long idle period.
