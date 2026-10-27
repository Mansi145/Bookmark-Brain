# Changelog

All notable changes to Bookmark Brain are recorded here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Account menu, Settings → Account and Earlier's pages

#### Added
- **Earlier is paginated** (design board Main, owner): 30 briefs a page in save-date order, newest first, and under them a pager: "Showing 31–60 of 189 · newest first", ‹ Newer, page numbers (the current one on accent), an ellipsis for skipped pages, the last page and Older ›. The page is in the address (`?page=2`) and keeps the other filters; changing a filter goes back to page 1; paging scrolls back to the top of Earlier and keeps the old page on screen until the new one arrives. A page past the end (an old link) goes to the last page. The pager only shows when there's more than one page. Today and This week still load by scrolling.
- **`GET /api/bookmarks` takes `saved_after` / `saved_before`** (the feed splits at the start of the week, sent as an exact moment so the browser and the server agree) and **`page`**: numbered pages with OFFSET and a `total`, because keyset paging can't jump to page 7.
- **Account menu** (design boards AccountMenu / AccountMenuDark): the round account button (`aria-haspopup="menu"`) opens a 272 px card with your name and email, Settings, a **Dark mode** switch and Sign out (How it works stays a link in the top bar, owner). Closes on Escape, a click outside or Tab; arrow keys move between items. Shows your Google picture when you have one, else your initial.
- **Settings → Account** (design boards SettingsAccount / SettingsAccountDark / SettingsAccountDelete), switched from the Settings menu (`/settings?section=account`):
  - **Your account**: picture or initial, name, email, "Signed in with Google", Sign out.
  - **Download my data**: `GET /api/account/export`, a JSON file with every bookmark (title, URL, site, saved date, read state, which browsers and folders have it, summary and key points) and the connected browsers (names and dates only, never token secrets).
  - **Delete account**: a confirmation dialog with the real counts (`GET /api/account`) that stays off until DELETE is typed, then `DELETE /api/account` (`{"confirm": "DELETE"}`, checked on the server too). Deleting the user row removes everything personal through the database's cascades (bookmarks, which browser has each, extension tokens, AI usage) and signs you out; the shared per-URL pages and summaries stay.
- **Account actions only from the web app** (`WebUser`): export and delete accept only the session cookie, never an extension token, so a leaked extension token can't download or wipe the account.
- **`onDead` colour** for text on a deadFg fill (white in light, `#1F1C1A` in dark).

#### Changed
- **Settings left the top bar's tabs** (owner): it's in the account menu, so the tabs are just Feed for now.
- **The light / dark button left the top bar**; the switch lives in the account menu. The theme still follows the system until changed, and the choice is remembered.
- **The top bar's texture is clipped on its own layer**, so the account menu can hang below the bar.

#### Notes
- If deleting fails, "Couldn't delete your account. Please try again." replaces the hint under the dialog's buttons (added in the build so a failure isn't silent, then approved on board SettingsAccountDeleteError).
- The logo animations (five, one per job) are designed but not built yet.

### Open summary on briefs, dev tools, warm charcoal dark mode, read stories in place and every feed screen as a newspaper

#### Added
- **Open summary** (owner): a brief whose summary is ready shows an *Open summary* button where Summarise was, opening the detail panel. Before, the button just disappeared, because briefs never show the summary itself.
- **Dev tools box** (local testing only, not a designed screen): bottom left in `npm run dev`, with *Use up today's limit* and *Reset*, to try the Limit reached dialog and its email without making 50 real summaries. Reset also lets the maintainer email be sent again. It's left out of production builds, and its endpoints (`POST /api/usage/dev/use-up`, `/dev/reset`) answer 404 unless `DEV_TOOLS=true`.

#### Changed
- **Site line first** (owner): in the newspaper, each story's site logo, site, read time and age now sit at the top of the story, above the folder label and headline (under the lead's image).
- **Warm charcoal dark mode** (design, owner): the dark theme's near-black greys are replaced by lifted, slightly warm ones with off-white text (page `#1F1C1A`, panels `#262220`, cards `#2D2926`, lines `#423B36`, text `#EEE8E2` / `#CEC5BC` / `#ACA298`), in the web app and the extension popup. Accents, the texture and the dead-link colours are unchanged.
- **In All bookmarks, a story marked read stays where it is** (design board MarkAsRead): same place, same look, only the panel's button changes to Mark as unread. It joins the other read stories, faded and last, the next time the page loads. Unread → Read still fades and folds the story out.
- **Read stories are faded in the Read view too**, as on the board (they already were in All bookmarks).
- **Needs sign-in and Dead links are newspaper sheets** (design boards FeedSignIn / FeedDead): one sheet each with a small masthead ("Pages behind an account or a subscription" / "Pages that no longer load on the web", and the count), then standard stories in ruled rows of three, each with its state line. They replace the date-grouped list cards (`BookmarkCard` is gone; its state lines moved to `StoryParts.tsx`).
- **Story states in the newspaper style** (design board Story states): every story shows its page state under the headline (Fetching page…, Couldn't read this page, Needs sign-in, Subscribers only, the dead-link flow with *Find archived copy*), as a 14 px line with a 15 px icon. Until a story has a summary, the site's own description shows in its place, with Summarise under it (not on briefs). The Fetching and Summarising pills now have a pulsing bar under them (still with reduced motion).
- **Loading front page** (design board FeedLoading): while the first page of the feed loads, the front page's shape in pulsing bars and "Loading your front page…".
- **Phone width** (design boards FeedPhone / FeedPhoneDark): at 760 px and below every newspaper column stacks into one with horizontal dividers, sheets have 18 px padding, mastheads are 30 px (small ones 24 px), the sidebar goes full width and the main panel's padding is 14 px. One breakpoint (`wide:`, 761 px and up) replaces the old two-column step.
- **First run** says "Your bookmarks will show up here as your own front page."
- **Sign-up preview and How it works** (design boards Login / HowItWorks): the preview card is now a mini front page (band rule, today's date, "Today's edition", a lead with its summary beside two briefs, one with Summarise), shared by a new first How it works feature, "Your own front page". How it works copy: step 3, the Summaries feature and Dead link checks now match the board.

### New logo, the Limit reached dialog and the free-plan note

#### Added
- **Limit reached dialog** (design board LimitDialog): opens when Summarise or Re-summarise is refused because today's AI allowance is used up. It explains why and when it comes back (midnight UTC), and **Notify the maintainer** emails the owner the user's account email and the time they hit the limit. States: default, Sending…, "Thanks, the maintainer knows". If the email fails the button simply comes back; there's no "couldn't send" screen.
- **`POST /api/usage/notify-maintainer`**: sends that email through [Resend](https://resend.com) (`app/services/mail.py`, one HTTPS call; free plan 100 emails a day). Only for users who really are at the limit (409 otherwise), and at most once per user per day: a second press answers 204 without sending, which keeps the email quota safe. Claimed and set in one SQL statement so a double click sends one email; if Resend refuses, the claim is undone so the user can try again (502). Off without `RESEND_API_KEY` / `MAINTAINER_EMAIL` (503). Sent in the request, not as a job, so the dialog only says "sent" once it has.
- **`ai_usage.limit_reached_at` and `maintainer_notified_at`** (migration `0008`): when each user was first refused that day and when they told the maintainer, so the owner can see who runs out and when.
- **Free-plan note** under the detail panel's buttons: "Bookmark Brain is a personal learning project on free plans. AI features share a small daily limit and may stop early." (`FreePlanNote`, ready for the Ask composer.)

#### Changed
- **New logo, "Masthead BB"** (design board LogoFinal): a backwards B and a B sharing one spine, between newspaper rules on a cream tile, the same in both themes. The full version (64 px and up) is on the sign-up page; the small one is in the top bars, Connect, the error pages, the extension popup, the favicon and the 16/32/48 px extension icons (128 px uses the full version). Replaces the brain logo everywhere.
- **Summarise on a brief opens the detail panel** (owner): briefs never show a summary, so before this the button just disappeared when the summary finished and nothing seemed to happen. The panel opens once the server has accepted the request (so at the daily limit only the Limit reached dialog shows) and the summary appears there as it arrives. Bigger stories still show theirs in place.
- **At the daily limit, Summarise and Re-summarise stay clickable** and open the Limit reached dialog, instead of being disabled with "Daily summary limit reached · resets at midnight UTC" (design board Story states). The unused `useUsage` hook is gone; `GET /api/usage` stays.
- **Newspaper briefs** match the board more closely: they come in rows of four, each row with a full-width rule above it; briefs use a smaller Summarise button (32 px, 13 px text) and an 18 px site-icon chip; the lead's summary is 18 px.

#### Fixed
- **A title with no spaces (a bare URL) no longer spills into the next column**: bookmark titles in the newspaper, the lists and the detail panel break inside a word that's too long for its column.

#### Notes
- Designed but not built yet: what Earlier's "N more from earlier" button does (waiting for the owner), and search (Phase 3).

### AI summaries, the bookmark detail panel and the newspaper feed

#### Added
- **Newspaper feed** (design board NewsClassic): the main feed is now a classic front page.
  - **Editions:** Today, This week and Earlier are editions, each one sheet with a masthead (band rule, Aleo title between the date and the counts, double rule) and thin column rules instead of a card per story.
  - **Story sizes:** newest unread stories are biggest (lead → seconds → standards → briefs), and read ones go last, faded. The first edition gets the front-page layout; Earlier is all briefs.
  - **Summary length per size:** a lead shows its whole summary, a second 5 lines, a standard 3, and a brief none. A story without a summary shows its Summarise button.
  - **Columns:** one on phones, two on small screens, the full grid on wide ones.
  - **Other sections:** Needs sign-in and Dead links keep the list until they're redesigned.
- **Preview image on the top story only** (`services/preview.py`): `og:image` / `twitter:image` from the page's `<head>`, stored as `documents.image_url` while the page is fetched. The browser loads it from the site, so our server never downloads images; if it fails, the lead is text-only. Captioned "Image from <site>". Migration `0007` adds the column and queues a new `find_image` job for pages fetched before, which reads the page again but only stores the image (text, section and summary untouched).
- **`app/ai/llm.py`**, the one place that talks to models, chaining free providers with LangChain's `.with_fallbacks()`:
  - Gemini `gemini-3.5-flash-lite`
  - Gemini `gemini-2.5-flash`, with its own free quota on the same key
  - OpenRouter's free `nvidia/nemotron-3.5-super-vl:free`
  - NVIDIA NIM, which hosts DeepSeek (`deepseek-ai/deepseek-v4.1-flash`) for free
  - Groq `openai/gpt-oss-120b`

  Providers without a key (`OPENROUTER_API_KEY`, `NVIDIA_API_KEY`) are skipped. An answer that doesn't fit the schema also moves on to the next model. `get_structured_model(Schema)` returns typed answers instead of text to parse, and reports which model answered. Model names are settings (`GEMINI_MODEL`, `GROQ_MODEL`); each client retries once and times out after 45 s, so the fallback kicks in fast.
- **Summarise chain** (`app/ai/chains.py`, prompt in `app/ai/prompts/summarise.md`): a short paragraph (5–6 sentences, about 800 characters) plus 3–5 key points. The page goes in `<article>` tags and the prompt treats it as data, not instructions (bookmarked pages are untrusted). Input is capped at 12,000 characters; answers that are empty, unparseable or far too long are rejected.
- **`summarise` job**: uses the page's text, a Wayback copy's text for a dead link, or only the title and description. It waits up to 2 minutes for a page that's still being fetched, retries a model failure once, then shows "Couldn't summarise this page." Records `summary_source` and `summary_model` (stored, never shown).
- **`POST /api/bookmarks/{id}/summarise`** (`?again=true` for Re-summarise). Summaries are cached per URL, so one someone already made comes back at once and costs nothing. Otherwise it counts towards the per-user daily limit (`AI_DAILY_LIMIT_PER_USER`, default 50; 429 "Daily summary limit reached"), checked and counted in a single SQL statement so two quick clicks can't both slip under it. Dead links need an archived copy first (409).
- **`GET /api/usage`**: today's summaries used, the limit, and when it resets (midnight UTC).
- **`PATCH /api/bookmarks/{id}`** (`read_state`) and **`GET /api/bookmarks/{id}`** for the detail panel. `BookmarkOut` gains `description`, `summary`, `key_points` and `summary_status`.
- **Migration `0006`**: `documents.summary`, `key_points`, `summary_status`, `summary_source`, `summary_model`, `summarised_at`, and the `ai_usage` table.
- **Feed rows**:
  - the summary, or the site's own description, in two lines
  - a Summarise button with Summarising… / failed + Try again / daily-limit states
  - on dead links, Summarise appears once an archived copy is found
  - the feed keeps refreshing while a summary is being made
- **Bookmark detail panel**: clicking a row's title opens a 480 px panel (full screen on phones) over a dark backdrop. It's part of the address (`?bookmark=`), so Back closes it. It shows:
  - the site, title and when it was saved
  - Open page, Mark as read / unread, and Re-summarise
  - the summary and key points; before a summary, the site's description, a line saying so, and the Summarise button
  - where the bookmark is saved, and the full URL

  Escape or the backdrop closes it.
- **Mark as read / unread**: in the Unread view the story fades and folds out (about 250 ms; at once with reduced motion) and appears under Read, where *Mark as unread* moves it back the same way. The cached feed updates straight away, then refreshes with the new counts. Opening a bookmark never marks it read.
- **Tests**: with a fake model, so nothing reaches Gemini or Groq. They cover:
  - summarising page text, with the prompt framing checked
  - shared summaries being free for other users
  - Re-summarise, and the daily limit
  - the title-and-description fallback
  - dead links needing a copy
  - retry-then-fail and rejected answers
  - the input budget, mark read / unread, and getting one bookmark

#### Decided
- **Model choice:** `gemini-3.5-flash-lite` became the main model after a live comparison. `gemini-3.5-flash` returned 503 "high demand" on 3 of 4 calls, while the lite model and `gemini-2.5-flash` answered every time. A two-sentence summary doesn't need the bigger model, and lite models usually get the largest free quota.
- **More free models, and DeepSeek:** DeepSeek's own API has no free tier (pay-as-you-go), and no free DeepSeek is listed on OpenRouter. NVIDIA NIM hosts it for free, so it joins the chain there. Mistral's free tier was left out because it requires opting into training on your data.
- **Preview images are back, for one spot only:** the owner reversed the no-`og:image` rule for the newspaper's lead story. Everywhere else stays image-free apart from site logos.
- **Summary length:** a short paragraph instead of two sentences (owner: the summary looked too short). Feed rows still show two lines; the detail panel shows it all.
- **Input size:** article input is 12,000 characters, not 24,000. Groq's free tier allows only 8,000 tokens a minute, and a full-length page used about 6,300 of them.

#### Notes
- Not built yet: the detail panel's Tags (Phase 5), the free-plan note and the "Limit reached" dialog (need an email service), and trying Gemini's URL-reading tool for pages we couldn't fetch. Settings' "AI usage" section was dropped (owner: users shouldn't see AI usage).

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
- **Connect page** (`/connect`) restyled as full-page cards on the texture, one per state: sign in first, connecting, first sync, connected, extension didn't answer (token shown once + Copy), link expired, plus sync failed and error. It now connects on its own as soon as the extension says hello (no extra click), and if the extension rejects the link, the token it just created is revoked again.
  - Connecting, syncing and done start with a step strip (Connect → Sync → Open feed) and the browser's logo joined to ours by a line that moves while connecting and syncing (still for reduced motion) and gets a check when done. The four browser logos are bundled in `public/browser-icons`.
  - While syncing: "231 bookmarks in 14 folders so far" and a *Just arrived* list of the last 4 bookmarks received, polled from the new `GET /api/bookmarks/sync-summary?browser=` (counts, folders, the newest received bookmarks with a guessed `/favicon.ico` until their page is fetched, and the user's other browsers).
  - Done no longer opens the feed by itself: bookmark and folder counts, "Also connected: …" when other browsers have synced, what happens next, a tip to pin the extension, *Open your feed* and *Connect another browser*.
  - A privacy line under every card: "We only read your bookmarks' titles, links and folders, plus the public pages they point to."
- **Error pages**: "We couldn't find that page" for unknown addresses (instead of silently going to the feed), "Waking up the server…" while the first request waits (shown after 1.5 s; the free Render server can take up to a minute), "You've been signed out" when a request comes back 401 mid-session, and "Something went wrong" with *Try again* when the API can't be reached or a page crashes.
- **Extension popup**: dark Nude header strip with white text, off-white body, a status card for each state (not connected: plain card; connected: dark accent; syncing: second accent; token rejected: red), Sync now / Reconnect, Open feed, the *Advanced* fold, and a link to Settings.

#### Notes
- Google sign-in uses Google's own button in its dark style: only Google's button returns the ID token the backend verifies. GitHub sign-in is shown but disabled until the backend supports it.
- Not built yet, all designed: the Summarise button and the bookmark detail panel (next step), search (Phase 3), the Ask page (Phase 4), tags (Phase 5), the Digest page (Phase 7), sorting, the row "⋯" menu, and Settings' AI usage and Account sections. The Ask and Digest tabs join the top bar when their pages exist.

### Design (canvas)
- Weekly digest redesigned as a newsletter: back-issue tabs instead of the sidebar, one centred sheet with a masthead, the AI overview as an editor's note with a drop cap, a section per theme with stories that open the detail panel (Summarise / Open summary like feed briefs), and a footer. Not built yet.
- Logo animations for searching (Lens) and the Wayback Machine (Hourglass); Settings moved out of the top-bar tabs into the account menu; How it works left the account menu; delete-account error line.
- Logo animations: Page back while summarising, Rewind while a page loads, Conversation while Ask works. Not built yet.
- Stories start with their source line; briefs get Summarise / Open summary buttons that open the detail panel; Earlier is paginated, newest first.
- Account menu with name, Settings, How it works, a dark-mode switch and Sign out (the theme button left the top bar); Settings → Account with profile, sign out, download my data and delete account (typed confirmation). Not built yet.
- Softer "warm charcoal" dark mode everywhere; every feed screen rebuilt as the newspaper front page (sections, story states, search, loading, phone width); sign-up preview and How it works updated to match. Not built yet.
- Connect states 7–9 wording approved.
- Limit reached dialog has no "couldn't send" state.
- Final logo: Masthead BB (mirrored BB between newspaper rules), now on every screen; the old brain logo is kept for reference. Mark as read: no undo notice; in All bookmarks a read story stays in place.
- Mark as read moves a story to Read with a Mark as unread button; logo direction chosen (Masthead BB), not rolled out yet.
- Opening a bookmark no longer marks it read; detail panel 'not summarised yet' state; AI usage removed from Settings; newspaper summary lengths per story size; logo directions with a BB monogram (exploration).
- Feed redesigned as a classic newspaper front page (editions, newest unread biggest, image on the top lead only); a free-plan note next to AI actions; a 'Limit reached' dialog that lets each user notify the maintainer. Not built yet.
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
- Connect screen: a step strip, a browser-to-app logo line, bookmarks arriving live with a folder count, a Done summary with other connected browsers, what happens next, a pin-the-extension tip and *Connect another browser* (no automatic jump to the feed), and a privacy line under every card. The owner considers the layout provisional.
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
- **Tests**: the sync summary for the Connect page, extraction, logos, sign-in detection, sync queueing, the live fetch outcomes, nothing sent to archive.org automatically, finding a copy / no copy / archive.org unreachable then retried, only your own dead links can be looked up, the shared rate-limit pause, section and read-state filtering for the feed and facets, and the private-URL rule.

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
  - `dev-setup` skill and README troubleshooting: random backend test failures on WSL2 ("Not signed in", pages stuck pending) come from the clock jumping while WSL's time sync and `systemd-timesyncd` fight; how to check, and `sudo systemctl stop systemd-timesyncd` to stop it until the next restart.

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
