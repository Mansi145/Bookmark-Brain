---
name: ui-design
description: Bookmark Brain's final visual design (dark Nude nebula texture, colours, fonts, logo, landing page and image-free reading-list feed) with exact tokens for building it in React/Tailwind. Use when building or restyling any frontend page or component, the extension popup, or design canvas boards.
---

# UI design

**Ask the owner before designing or restyling anything that isn't already decided here**: which
page, layout, what goes where. Present options with a recommendation; don't invent new looks.

Source of truth: the Claude design canvas https://claude.ai/artifact/88oGw1iJQJW2P8tB6jRBVT
(boards: `Login.dc.html` landing page, `Main.dc.html` feed, `FeedDark.dc.html`, `Settings.dc.html`,
`SettingsDark.dc.html`, `Popup.dc.html` with its states `PopupNotConnected` / `PopupSyncing` /
`PopupError` / `PopupDark`, `Texture.dc.html`, `Logo.dc.html`). Read a board's file through the
Artifact tool when you need exact markup.

## Tokens
| Token | Light | Dark | Use |
|---|---|---|---|
| bg | `#ECEAE7` | `#1F1C1A` | page (off-white, never pure white) |
| panel | `#F5F4F2` | `#262220` | rounded panels behind the filters and behind the main feed |
| surface | `#FBFAF8` | `#2D2926` | a card per article, inputs, pill buttons, empty-state box |
| line | `#E2DFDA` | `#423B36` | borders, dividers |
| ink | `#141516` | `#EEE8E2` | text, headings, primary buttons (`onInk` text: `#FFFFFF` light, `#1F1C1A` dark) |
| ink2 | `#2F3134` | `#CEC5BC` | secondary text, meta |
| muted | `#45484B` | `#ACA298` | small labels, counts |
| accent | `#503931` | `#503931` | selected filter / reading state, site tiles, step numbers, highlight boxes, empty-state icon |
| accent2 | `#564D3A` | `#564D3A` | in-progress pills ("Fetching page…", "Summarising…"), alternate tiles |
| band | `linear-gradient(90deg, #503931, #564D3A)` | same | every group header band |
| onAccent / onAccent2 | `#FFFFFF` / `#EFE8E2` | same | text on accent, accent2 and band |
| skeleton | `#E7E4DF` | `#3A3430` | loading bars and progress-bar tracks (warm grey to sit on the off-whites) |
| deadBg / deadFg | `#F8E3E3` / `#7C1D1D` | `#3D2224` / `#F5B5B5` | dead link notice |

**Dark mode is "warm charcoal"** (owner, 2026-10-27; compared on the canvas's Dark mode page): lifted,
slightly warm greys with off-white text instead of near-black and bright white. Contrast on cards:
text 11.9, `ink2` 8.5, `muted` 5.7.

Theme follows the system (`prefers-color-scheme`). Text is near-black, never mid-grey; keep 4.5:1
contrast, even for 12–13 px meta text. Define these as CSS variables / Tailwind `@theme` tokens once,
not as scattered hex values.

**No pure-white pages (owner, 2026-10-23):** "the completely white background looks bad". Three
off-white layers: `bg` page → `panel` (radius 16 px, padding 18–24 px) behind the filters and behind
the main feed → `surface` card per article (radius 12 px, 1 px `line`). Neutral greys, not tints of
the gradient. Applies everywhere (feed, Settings, popup body, How it works, cards on the landing
page); the only pure white left is the favicon chip. Owner likes the shades; may revisit later.

**Accent rule (owner, 2026-10-23): never use light colours or tints of the gradient, always the dark
Nude colours**, with white text on them, in both themes. This replaced the old `blue` `#DCEAF3` /
`pink` `#FBEAF2` and a short-lived light peach / butter pair. Page, surfaces, lines and body text
stay as in the table. Primary action buttons stay `ink` (near-black) with white text.

**Fonts** (Google Fonts): **Aleo** 500/600/700 for headings, group names and bookmark titles;
**Geist** 400/500/600 for everything else (15 px base, 1.5 line height).
Sizes in the feed: page title 40 px, group band 19 px, row title 21 px, summary 14 px, meta 13 px.

## Nebula texture: dark Nude (decided 2026-10-23)
Replaces the old blue → pink Cloudlifter texture ("looked unprofessional"). It is the dark version
of Figma's **Nude** gradient (`#EB9571 → #FFDD92`, both stops mixed 72 % toward `#141518`), chosen
on a "Gradient test" page (since deleted). Rejected, don't retry: the light gradients, and anything with
purple. **Text on the texture is white** (`#FFFFFF`; secondary `#EFE8E2`). Recipe:
1. Base `linear-gradient(90deg, #503931 0%, #564D3A 100%)`, `overflow: hidden`.
2. A blurred layer (hero: `inset: -240px -16%`, `blur(140px)`; short bars: `inset: -60px -8%`,
   `blur(60px)`) of overlapping ellipses (`border-radius: 50%`): `#48332C` .85, `#624D46` .7,
   `#534336` .85, `#564D3A` .95, `#4C4433` .8, `#59433B` .8, `#675F4E` .7, white .06
   (opacity after each colour; same positions as before).
3. Film grain: full-size SVG `feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3"`
   + `feColorMatrix saturate 0`, **`mix-blend-mode: screen`, opacity 0.12** (multiply is invisible
   on dark).
Make it one reusable `<Nebula>` component.

On the texture: primary button white with `#141516` text; secondary button outlined
`rgba(255,255,255,.5)` on `rgba(255,255,255,.08)` with white text; white cards on it keep their own
near-black text.

**Rollout:** done everywhere (landing, How it works, feed, Settings, popup, Texture, logo tests).
Nothing uses Cloudlifter any more.

## Logo: Masthead BB (final, owner 2026-10-27)
Board `LogoFinal` (Components page) has both SVGs to copy. A backwards B and a B drawn as shapes
(no font), sharing one spine and mirrored on the centre line, between newspaper rules, on a cream
tile. Colours: tile `#F4EDE4`, letters `#141516`, rules `#503931` (accent). Same in both themes.
- **Full version** (64 px and up): thick accent rule + thin ink rule above and below the letters;
  tile corner radius 11 %.
- **Small version** (under 64 px: top bars at 30–34 px, popup, favicon, extension icons 16–48 px):
  thick rules only, letters 14 % bigger, radius 17 %. Tested at 16 px.
- Lockups: top bar = small mark + "Bookmark Brain" (Aleo 21 px, white on the texture); sign-up hero =
  full mark at 150 px + stacked "Bookmark / Brain" (Aleo 40 px).
- Clear space: one eighth of the logo's size. Don't recolour or stretch it.
- Previous logo (a cute brain on a bookmark ribbon with a Mulberry pink fill, `Logo`,
  `LogoVariants`) and the twelve `LogoDirections` tests are kept on the canvas for reference only.

## Landing page and How it works (signed out), split 2026-10-23
- **Landing / sign-up page** (`Login.dc.html`): one screen, entirely on the texture. Top bar (logo,
  How it works, Features, dark Sign in button), medium logo beside a stacked "Bookmark / Brain"
  wordmark, headline **"Saved it? Now actually use it."** (Aleo 64 px), the sign-in buttons, "Free ·
  Works with Chrome, Edge, Brave and Firefox", a clearly visible outlined pill **"See how it works →"**
  linking to the How it works page, an image-free product preview card (a mini front page: band rule, "Today's edition" masthead,
  a lead story with summary and two briefs, one with Summarise; site logos on white chips),
  and the footer on the texture.
- **Sign-in buttons**: dark (`#141516`, 1 px `#8E918F` border, white text, 52 px) with the real
  marks: Google's four-colour **G** (Google's sign-in guidelines use the G, not the Gmail logo) and
  GitHub's white Octocat. These two are filled brand marks, the one exception to stroke icons.
  GitHub sign-in needs backend work.
- **How it works page** (`HowItWorks.dc.html`): texture header band with the top bar (How it works
  current) and an Aleo 56 px "How it works" title; then the 3 steps (step 2 = click **Connect this
  browser**), "What it does with your bookmarks" (`#features`: **your own front page** with the same mini
  front page as the landing preview, then summaries (on Summarise), search by meaning, ask your
  bookmarks, plus dead links (archived copy on request) / reading status / digest), a closing call to action on the texture with
  the same sign-in buttons, and the footer.

## App shell and feed (signed in), updated 2026-10-23
Boards: `Main.dc.html` (feed; a `section` setting switches feed / signin / dead / states, `empty`
shows the empty state, `dark` the dark theme), `FeedSignIn`, `FeedDead`, `FeedSignInEmpty`,
`FeedDeadEmpty`, `RowStates` (every row state in one place), `FeedDark`.
- **Top bar** on the dark texture, white text: small logo + "Bookmark Brain" (Aleo 21 px); a dark
  search field (`rgba(23,24,26,.55)`, 1 px `rgba(255,255,255,.18)`, "Search by meaning or keyword…",
  `/` shortcut); **tabs Feed · Ask · Settings only** (owner: the sections are NOT in the top nav; the
  current tab on `rgba(255,255,255,.14)`, weight 600); a quiet **How it works** link with a
  help icon (to the How it works page); a white round account button (the user's initial).
  **No theme button in the top bar any more** (owner, 2026-10-27): the light / dark switch lives in
  the account menu. The theme still defaults to the system setting until changed; remember the choice.
- **Account menu** (`AccountMenu`, `AccountMenuDark`): the account button (`aria-haspopup="menu"`,
  `aria-expanded`) opens a 272 px `surface` card under it, right-aligned, 1 px `line`, radius 14 px,
  soft shadow: avatar initial on `accent` + name + email, then rows (40 px, icon + label)
  **Settings**, **How it works**, **Dark mode** with a switch (`menuitemcheckbox`, track `accent`
  when on, `line` when off, white knob), a divider, **Sign out**. Closes on Escape or a click outside.
- **Three feed sections**, each bookmark in exactly one: **Feed** (pages we can read), **Needs
  sign-in** (needs an account: "Needs sign-in", or a subscription: "Subscribers only") and **Dead
  links** (links we can't fetch that no longer load on the internet, e.g. 404/410). **There is no
  "Archived" reading state** (owner removed it 2026-10-23 to avoid confusion with dead links): the
  reading states are only Unread and Read.
- **Sidebar** (220–260 px): Browsers and Folders (indented subfolders) with counts, per section.
  Selected item on `accent`, white text, weight 600.
- **Header**: page title ("Feed" / "Needs sign-in" / "Dead links", Aleo 40 px), a count line
  ("248 bookmarks · 2 being fetched · synced from Chrome 2 min ago"), Sort select (Newest, Oldest,
  Shortest read).
- **Feed views bar** (owner: its own bar above the list, NOT in the top navigation or the sidebar),
  shown in all three sections: a row of 40 px pill links under the header: **All bookmarks · Unread
  · Read**, a thin vertical divider, then **Needs sign-in · Dead links**, each with its
  count. The current one (`aria-current`) on `accent` with white text, the rest `surface` with a
  `line` border. Reading states only filter the main feed; on the two sections none of them is
  selected.
- **Empty states** (bordered `surface` box, `accent` circle with a white check, Aleo 21 px title, one line):
  "Nothing needs sign-in" / "Pages that need an account or a subscription will show up here.";
  "No dead links" / "Links that stop working show up here. You can look each one up on the Wayback Machine."
  Filters stay with zero counts.
- **Reading list, no images** (decided: no `og:image` anywhere). Rows grouped by save date
  (**Today / This week / Earlier**); each group has a free-standing header band (radius 12 px, Aleo
  name + "n bookmarks", white / `onAccent2` text) on `band`, then the group's articles as separate
  `surface` cards (radius 12 px, 1 px `line`, 8 px apart), all on the feed `panel`.
  Row: meta line (site logo · site · folder · browser · age, plain
  text), Aleo title, then the state line / summary / Summarise area, right column with "⋯" menu
  (36 px) and "n min read" (from word count, shown before any summary). Read = row at 70 % opacity.
  No grid/list toggle, no coloured chips.
- **Site logos (favicons)** (owner, 2026-10-23): the site's own logo, 14 px, centred on a 20 px
  **white `#FFFFFF` chip** (radius 6 px, 1 px `line` border) in both themes, so dark marks (GitHub)
  stay visible on dark and colourful ones don't clash with the brown accents. Fallback when there's
  no logo or it fails to load: the 20 px letter tile on `accent` with a white letter. `aria-hidden`
  (the site name is next to it). Also used on the landing preview card and the How it works
  examples; NOT in the sidebar. The only image allowed anywhere: no page images still holds. Canvas
  boards use simple stand-in shapes because they can't load real favicons.
- **Summaries are on demand.** Every row without a summary has a **Summarise** button (36 px,
  outlined, three-lines icon) under the title, where the summary will appear:
  idle "Summarise" → working: `accent2` pill, white spinner + "Summarising…", + one skeleton bar → done: the
  2-line summary → failed: "Couldn't summarise this page." + **Try again** → daily limit: the button
  disabled (50 %) + "Daily summary limit reached · resets at midnight UTC" in `muted`.
- **No source or trust labels** (owner's decision: badges made the app look unreliable). Summaries
  from the live page, an archive.org copy, Gemini reading the URL, or a link-only guess all look the
  same; so does the site's own description when there is no page text.
- **Page states** (one 14 px line under the title, small stroke icon, `ink2` text, weight 500):
  "Fetching page…" (`accent2` pill + skeleton, like Summarising); "Couldn't read this page" (file
  icon; JS apps, bot-protected sites); "Needs sign-in" / "Subscribers only" (lock icon); dead in
  `deadFg`, weight 600: "Page no longer available (404)." (broken-link icon). Summarise stays
  available on unreadable and sign-in rows.
- **Dead links: the Wayback Machine only on request** (owner, 2026-10-23). A dead row has no
  Summarise button; in its place a **"Find archived copy"** button (36 px, outlined, history icon)
  looks up the latest Wayback Machine snapshot only when clicked. States: working = `accent2` pill
  "Checking the Wayback Machine…"; found = "· Archived copy · 9 Jan 2019" link appended to the dead
  line, and the **Summarise** button appears (summarises that copy); none = "No archived copy on the
  Wayback Machine." in `ink2`; failed = "Couldn't reach the Wayback Machine." + **Try again**.
  Nothing is fetched from archive.org automatically.
- Shortest-read sort shows a flat list (date groups only make sense for date sorts).

## More pages (designed 2026-10-23; owner chose the layouts)
Top nav is now **Feed · Ask · Digest · Settings** (Digest added as its own page).
- **Bookmark detail** (`FeedDetail`; Main `detail`): a **480 px side panel** from the right over a
  35 % dark backdrop (full screen on phones), on `panel`. Close button; logo chip + site · folder ·
  browser; Aleo 30 px title; "Saved 2 days ago · 6 min read"; **Open page** (`ink`), Mark as read,
  Re-summarise; a `surface` card with Summary + Key points. **Opening the panel never marks a
  bookmark read** (owner): the button stays "Mark as read" until the user presses it. Pressing it
  (`MarkAsRead` board): in the Unread view the story fades and folds out (~250 ms; instant with
  reduced motion) and the button becomes **Mark as unread**; switching to Read shows it there, faded,
  with Mark as unread, which moves it back the same way. No undo notice (owner). In **All
  bookmarks** the story stays where it is and only its button changes. Not
  summarised yet (`FeedDetailUnsummarised`): the card shows the site's own description, a muted
  "The site's own description…" line and the Summarise button, and there's no Re-summarise. Tags (outlined pills with remove ×; AI
  suggestions dashed with ✓ / ×; "Add tag"); Details (browsers/folders, full URL).
- **Tags**: a "Tags" group in the feed sidebar with counts, and in the detail panel. Not on rows.
- **Search results** (`FeedSearch`; Main `section="search"`): replace the feed in place. Query stays
  in the top-bar field; title "Results for “…”", line "5 bookmarks · matched by keyword and by meaning
  · Clear search"; one "Best matches" band, ranked rows; matching words in summaries highlighted as
  `<mark>` on `accent` with white text. Feed views bar hidden; sidebar filters still apply.
- **First run** (`FeedFirstRun`): one `surface` card: bookmark icon on `accent`, "Connect your first
  browser", two numbered steps, **Get the extension** (`ink`) + **Connect by hand** (to Settings).
- **Ask** (`Ask`, `AskEmpty`): three panels. Left: **New chat** (`ink`) + Recent chats (current on
  `accent`). Middle: thread title (Aleo 24 px); your messages in `ink` bubbles on the right; the
  agent's steps as small check lines ("Searched your bookmarks for “…” · 4 found"); answers in
  `surface` bubbles with numbered citation chips on `accent`; working = `accent2` pill "Searching your
  bookmarks…" + skeleton lines; composer (textarea + `ink` send button) and "Answers use only pages
  you've saved, and link to each one." Right: **Sources** (numbered cards with logo chip, site, Aleo
  title) + "Also found". Empty: "Ask your bookmarks" + 4 suggested-question pills.
- **Weekly digest** (`Digest`): left panel "Past digests" (weeks with counts); main panel "Weekly
  digest", "23–29 Oct · 9 unread bookmarks you saved more than 30 days ago", an AI overview card, then
  one band per theme with cards (logo, site · saved … ago · n min read, Aleo title, one line on why to
  read it, **Mark as read**).
- **Connect** (`ConnectStates`, all states on one board) and **error pages** (`ErrorStates`), on the
  dark texture with a `surface` card per state (icon on `accent`, Aleo 24 px title, one line, one
  action). Connect: signed out (sign-in buttons) → Connecting… → Syncing (n found, progress bar) →
  Connected ("Opening your feed…", Open feed now) → extension didn't answer (token shown once + Copy)
  → link expired (15 min). Errors: 404 (Back to your feed), server waking up (free server sleeps, up
  to a minute), signed out (sign-in buttons), something went wrong (Try again).
- These cards **follow the theme** (owner): `surface` / `ink` / `ink2`, so they turn dark in dark
  mode (main button `ink` with `onInk` text; sign-in buttons stay dark); the texture behind them is
  the same in both. Boards `ConnectStatesDark`, `ErrorStatesDark`.
- **Connect extras** (owner picked all; placement may move later):
  - Connecting / Syncing / Done start with a **step strip** (Connect → Sync → Open feed; done = `accent`
    check, current = `accent` number, upcoming = outlined) and the **browser's logo and ours** on
    56 px white chips joined by a line: dotted and moving while connecting, an `accent` line with
    flowing gaps while syncing, solid with an `accent` check when done (motion off for reduced motion).
  - Syncing: "231 bookmarks in 14 folders so far" + progress bar + **Just arrived** (the newest 4
    bookmarks with site logos, title and site).
  - Done **no longer opens the feed by itself**: two stat tiles (bookmarks, folders), "Also
    connected: …" (only when other browsers are), what happens next (pages read in the background,
    summaries on Summarise), a **pin the extension** tip, **Open your feed** + **Connect another
    browser** (to Settings).
  - Under every Connect card, on the texture: a lock icon + "We only read your bookmarks' titles,
    links and folders, plus the public pages they point to."
- **Free-plan note** (owner): next to AI actions only (under the Ask composer, under the detail
  panel's Open page / Mark as read / Re-summarise), 13 px `muted` with an info icon: "Bookmark
  Brain is a personal learning project on free plans. AI features share a small daily limit and
  may stop early."
- **Limit reached dialog** (`LimitDialog`, owner): opens when Summarise, Re-summarise or Ask is
  refused because the daily AI allowance is used up. Modal `surface` card on a dimmed page: gauge
  icon on `accent`, "Limit reached", why it happens + "comes back at midnight UTC", **Please click
  below to notify the maintainer.**, **Notify the maintainer** (`ink`, emails the owner) + Close.
  Then Sending… → "Thanks, the maintainer knows". **Per user** (owner wants the data): every
  signed-in person can send it each time they hit the limit, no "already reported" state; the
  email carries their account email and the time, and the dialog says so under the button.
  No "couldn't send" screen or retry button (owner): the states are only default, Sending…, Sent.
- **Newspaper feed: the owner chose the classic front page** (`NewsClassic`). It replaces the
  date-grouped list: Today / This week / Earlier are editions, each one `surface` sheet with a
  masthead (band rule, Aleo title centred between the date and counts, double rule under it) and
  thin `line` column rules instead of a card per article. Newest unread stories are biggest (lead →
  second → standard → brief; read ones last and faded); summaries (a 5–6 sentence
  paragraph) show in full on the lead, 5 lines on second stories, 3 on standard, none on briefs; only the top lead shows the page's
  preview image (16:9, caption "Image from <site>"; no image → a text-only lead). `NewsGrid` and
  `NewsSections` were the other trials.
  Built into `Main` (Home · feed) and every board that imports it:
  - **Sections**: Needs sign-in and Dead links are one sheet each (small masthead, standard stories
    in 3 ruled columns, each with its state line); empty states as before.
  - **Story states** (`RowStates`): Summarise idle / working / done / failed; page fetching /
    couldn't read / needs sign-in / subscribers only / site's own description / read; dead link not
    looked up / checking / copy found / found and summarised / no copy / couldn't reach. A state label
    pill sits above each example only on that board. Daily limit → the Limit reached dialog.
  - **Search** (`FeedSearch`): one sheet, masthead is the query in quotes, best match as a second-size
    story beside two briefs, then standard results; matched words on `accent` with white text.
  - **Loading** (`FeedLoading`): the front page's shape in `skeleton` bars (pulsing, still with
    reduced motion) + "Loading your front page…".
  - **Phone** (`FeedPhone`, `FeedPhoneDark`, 390 px): every column stacks into one, rules become
    horizontal dividers, sheet padding 18 px, masthead 30 px; sidebar and top bar stack above.
  - First run: "Your bookmarks will show up here as your own front page."
- Connect also has three states the build added, on the board as 7–9; the owner
  approved their wording: "Connected, but the first sync failed" (the extension's error + Go to
  your feed), "Something went wrong" (the token couldn't be made; Try again) and "Connect from the
  extension" (page opened without the extension's link; Connect by hand).

## Settings
Same dark-texture top bar as the feed (Settings current). The section menu (Browsers,
Account; selected on `accent`, white text, weight 600) sits on a `panel`; the main column is another
`panel` with page title "Settings" (Aleo 40 px) and each section as a bordered `surface` card,
radius 12 px, Aleo 21 px headings:
- **Connect a browser**: one-click first. Two numbered steps (round `accent` tiles, white numbers):
  install the extension, then click **Connect this browser**. Below, a **Connect by hand** fold: token
  name + "Create token" (`ink` button), then the shown-once token on an `accent2` notice with white
  text, the token in a `surface` code box, and an outlined white Copy button.
- **Connected browsers**: rows with a 36 px initial tile on `accent` (white letter), token name
  ("Chrome extension"), `bb_pat_…` prefix + bookmark count + last sync, a status pill (`accent2` with
  white text when syncing/connected; outlined with `ink` text when waiting) and a **Revoke** text
  button in `deadFg`.
- **No AI usage section** (owner): users aren't shown AI usage at all. The only hint is the
  free-plan note and, when it happens, the Limit reached dialog.
- **Account** (`SettingsAccount`, `SettingsAccountDark`; Settings `section="account"`), three cards:
  - **Your account**: 56 px avatar initial on `accent`, name, email, "Signed in with Google" (or
    GitHub) with the provider's mark, an outlined **Sign out** button, and "Your name and picture
    come from your Google or GitHub account. Change them there."
  - **Download my data**: "A JSON file with your bookmarks, folders, browsers, read states, tags and
    their summaries. It's ready in a few seconds." + **Download my data** (`ink`, download icon).
  - **Delete account** (heading in `deadFg`): "Permanently deletes your account, your bookmarks, read
    states, tags and connected browsers. The extension stops syncing. This can't be undone." +
    outlined `deadFg` **Delete account…**, which opens a dialog (`SettingsAccountDelete`):
    bin icon on `deadBg`, "Delete your account?", what will be deleted with real counts, a
    "Download my data" link, "Type DELETE to confirm" input, **Delete everything** (`deadFg` fill,
    `onDead` text: white light / `#1F1C1A` dark; disabled until DELETE is typed) + Cancel.

## Extension popup
360 px wide, grows with its content. 64 px dark-texture header strip with the small logo + white
"Bookmark Brain" (Aleo 19 px). Body on `panel`: a status card, the main button (`ink`, 44 px) beside
**Open feed** (outlined `surface`), a collapsed **Advanced: paste a token** fold (API URL, Access token, "Save & sync now"),
and "Manage connected browsers in Settings" at the bottom. Status card per state:
| State | Card | Icon | Main button |
|---|---|---|---|
| Not connected | `surface` + `line` border | link | Connect this browser (no Open feed) |
| Connected | `accent`, white text | check | Sync now |
| Syncing | `accent2`, white text (like the in-progress pills) | spinner | Syncing… (disabled) |
| Token rejected | `deadBg`, `deadFg` text | alert circle | Reconnect |

Dark mode: Settings and the popup use the dark tokens; the dark texture is the same in both themes.

## Later (owner's backlog, don't design until they say so)
- **Logo animations** (next up): animate the top-left masthead BB while the app works, with a
  **different animation for each action** (searching, summarising, checking the Wayback Machine).

## Rules
- Real `<button>`, `<a href>`, `<label>`; `aria-label` on icon buttons; visible focus; touch targets
  ≥ 44 px (≥ 36 px for dense row actions).
- Works at phone width: the sidebar stacks above the list, the top bar wraps.
- Icons: inline stroke SVG, never emoji. No gradient washes or left-border accent cards.
