---
name: ui-design
description: Bookmark Brain's final visual design (dark Nude nebula texture, colours, warm charcoal dark mode, fonts, Masthead BB logo and its animations, landing page, newspaper front-page feed, search, tags, collections and duplicates, Ask, Settings, Digest) with exact tokens for building it in React/Tailwind. Use when building or restyling any frontend page or component, the extension popup, or design canvas boards.
---

# UI design

**Ask the owner before designing or restyling anything that isn't already decided here**: which
page, layout, what goes where. Present options with a recommendation; don't invent new looks.

Source of truth: the Claude design canvas https://claude.ai/artifact/88oGw1iJQJW2P8tB6jRBVT.
Read a board's file through the Artifact tool when you need exact markup. Its pages:
- **Home**: `Login` (sign-up), `HowItWorks`, `Main` (the feed; every feed board imports it) and a
  board for each screen and state, named after it (`FeedSearch…`, `FeedDetail…`, `Ask…`, `Digest`,
  `MarkAsRead`, the phone boards); each section below lists its boards. Dark versions share the
  name plus `Dark`. Phase 5 (tags, collections, duplicates) is in the rows at the bottom. `Login`
  and `HowItWorks` have no dark version: they look the same in both themes.
- **Components**: `Texture`, `LogoFinal`, `LogoAnimations`; the older logo boards (`Logo`,
  `LogoVariants`, `LogoDirections`) are for reference only.
- **Other screens**: `FeedDark`, Settings (Browsers, Account, delete dialog), `AccountMenu`, the
  popup states, Connect and error pages, `LimitDialog`, each with a dark version.
- **Archive**: decided trials (feed layouts, dark mode options, the dropped keyword-only search
  state), for reference only; don't build from them.

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

**Dark mode is "warm charcoal"**: lifted, slightly warm greys with off-white text instead of
near-black and bright white.

Theme follows the system (`prefers-color-scheme`) until the user flips the Dark mode switch in the
account menu; remember that choice. Text is near-black, never mid-grey; keep 4.5:1
contrast, even for 12–13 px meta text. Define these as CSS variables / Tailwind `@theme` tokens once,
not as scattered hex values.

**No pure-white pages (owner).** Three off-white layers: `bg` page → `panel` (radius 16 px, padding
18–24 px) behind the filters and behind the main feed → `surface` card per article (radius 12 px,
1 px `line`). Neutral greys, not tints of the gradient. Applies everywhere (feed, Settings, popup
body, How it works, cards on the landing page); the only pure white is the site-logo chip.

**Accent rule (owner): never light colours or tints of the gradient, always the dark Nude
colours**, with white text on them, in both themes. Primary action buttons are `ink` (near-black)
with white text.

**Fonts** (Google Fonts): **Aleo** 500/600/700 for headings, group names and bookmark titles;
**Geist** 400/500/600 for everything else (15 px base, 1.5 line height).
Sizes in the feed: page title 40 px; edition masthead 48 px (32 px for the small sheets, 30 / 24 px
on phones); headlines lead 44 px, second 28 px, standard 21 px, brief 17 px, with summaries at 18 /
15 / 14 px; source line 13 px (12 px on briefs).

## Nebula texture: dark Nude
Rejected, don't retry: light gradients (including the old blue → pink one) and anything
with purple. **Text on the texture is white** (`#FFFFFF`; secondary `#EFE8E2`). Recipe:
1. Base `linear-gradient(90deg, #503931 0%, #564D3A 100%)`, `overflow: hidden`.
2. A blurred layer (hero: `inset: -240px -16%`, `blur(140px)`; short bars: `inset: -60px -8%`,
   `blur(60px)`) of overlapping ellipses (`border-radius: 50%`): `#48332C` .85, `#624D46` .7,
   `#534336` .85, `#564D3A` .95, `#4C4433` .8, `#59433B` .8, `#675F4E` .7, white .06
   (opacity after each colour; positions in `frontend/src/components/Nebula.tsx`).
3. Film grain: full-size SVG `feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3"`
   + `feColorMatrix saturate 0`, **`mix-blend-mode: screen`, opacity 0.12**.
One reusable `<Nebula>` component.

On the texture: primary button white with `#141516` text; secondary button outlined
`rgba(255,255,255,.5)` on `rgba(255,255,255,.08)` with white text; white cards on it keep their own
near-black text.

## Logo: Masthead BB
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

## Landing page and How it works (signed out)
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
  A failed GitHub sign-in (cancelled, no verified email, unavailable) is one line of text under
  the buttons, like Google's "Sign-in failed: …".
- **How it works page** (`HowItWorks.dc.html`): texture header band with the top bar (How it works
  current) and an Aleo 56 px "How it works" title; then the 3 steps (step 2 = click **Connect this
  browser**), "What it does with your bookmarks" (`#features`: **your own front page** with the same mini
  front page as the landing preview, then summaries (on Summarise), search by meaning, ask your
  bookmarks, plus dead links (archived copy on request) / reading status / digest), a closing call to action on the texture with
  the same sign-in buttons, and the footer.

## App shell and feed (signed in)
Boards: `Main.dc.html` (feed; a `section` setting switches feed / signin / dead / states / search /
firstrun / loading / tag / tagnone / collection / dupes, `detail` and `unsummarised` open the detail
panel, `empty` shows the empty state, `dark` the dark theme, `menu` the account menu; the Phase 5
settings `tagUi`, `collections`, `select`, `detailTags`, `dupNote` and `dupes` are explained under
"Tags, collections and duplicates"), `FeedSignIn`, `FeedDead`, `FeedSignInEmpty`,
`FeedDeadEmpty`, `RowStates` (every story state in one place), `FeedDark`. The feed's layout is the
newspaper front page at the end of this section ("Newspaper feed").
- **Top bar** on the dark texture, white text: small logo + "Bookmark Brain" (Aleo 21 px); a dark
  search field (`rgba(23,24,26,.55)`, 1 px `rgba(255,255,255,.18)`, "Search by meaning or keyword…",
  `/` shortcut hint, hidden on phones; once there's text the hint becomes a **clear ×** button
  (36 px target, 24 px `rgba(255,255,255,.16)` circle) that goes back to the feed,
  as Escape does; the field wraps to its own full-width row on phones); **tabs Feed · Ask · Digest**
  (current tab on `rgba(255,255,255,.14)`, weight 600; Settings is in the account menu, and the
  feed sections are never tabs; **Ask** has a 14 px chevron and opens the recent-questions dropdown,
  see Ask); a quiet **How it works** link with a help icon; a white round
  account button (the user's initial). No theme button: the light / dark switch is in the account
  menu.
- **Account menu** (`AccountMenu`, `AccountMenuDark`): the account button (`aria-haspopup="menu"`,
  `aria-expanded`) opens a 272 px `surface` card under it, right-aligned, 1 px `line`, radius 14 px,
  soft shadow: avatar initial on `accent` + name + email, then rows (40 px, icon + label)
  **Settings**, **Dark mode** with a switch (`menuitemcheckbox`, track `accent`
  when on, `line` when off, white knob), a divider, **Sign out**. Closes on Escape or a click outside.
- **Three feed sections**, each bookmark in exactly one: **Feed** (pages we can read), **Needs
  sign-in** (needs an account: "Needs sign-in", or a subscription: "Subscribers only") and **Dead
  links** (links we can't fetch that no longer load on the internet, e.g. 404/410). Reading states
  are only Unread and Read (no "Archived").
- **Sidebar** (220–260 px): Browsers and Folders (indented subfolders) with counts, per section;
  in the Feed (and search) also **Tags** and **Collections** (see "Tags, collections and
  duplicates"). Selected item on `accent`, white text, weight 600. **Every section folds**
  (owner, 2026-11-03): its heading is a button (36 px, `aria-expanded`, `aria-controls`) with a
  14 px chevron before the name, pointing down when open and turned −90° when closed (0.15 s, none
  with reduced motion). All open by default; what was closed is remembered on this device. Tags
  keeps **+ New tag** on the right of its heading. Board `FeedSidebarFolded` (Main `collapsed`:
  none / some / all; some = Folders and Collections closed), plus `FeedSidebarFoldedDark`.
- **Header**: page title ("Feed" / "Needs sign-in" / "Dead links", Aleo 40 px) and a count line
  ("248 bookmarks · 2 being fetched · synced from Chrome 2 min ago"). No sort menu. On the Feed (also
  when filtered by tags or showing a collection), an outlined **Select** button (40 px, checkbox
  icon) sits on the right; chosen tags show under the count line.
- **Feed views bar** (owner: its own bar above the list, NOT in the top navigation or the sidebar),
  shown in all the sections: a row of 40 px pill links under the header: **All bookmarks · Unread
  · Read**, a thin vertical divider, then **Needs sign-in · Dead links · Possible duplicates**, each
  with its count. The current one (`aria-current`) on `accent` with white text, the rest `surface` with a
  `line` border. Reading states only filter the main feed; on the other sections none of them is
  selected.
- **Empty states** (bordered `surface` box, `accent` circle with a white check, Aleo 21 px title, one line):
  "Nothing needs sign-in" / "Pages that need an account or a subscription will show up here.";
  "No dead links" / "Links that stop working show up here. You can look each one up on the Wayback Machine."
  Filters stay with zero counts.
- "n min read" comes from the word count; read stories are faded; no grid/list toggle, no
  coloured chips.
- **Site logos (favicons)**: the site's own logo, 14 px, centred on a 20 px
  **white `#FFFFFF` chip** (radius 6 px, 1 px `line` border) in both themes, so dark marks (GitHub)
  stay visible on dark and colourful ones don't clash with the brown accents. Fallback when there's
  no logo or it fails to load: the 20 px letter tile on `accent` with a white letter. `aria-hidden`
  (the site name is next to it). Also used on the landing preview card and the How it works
  examples; NOT in the sidebar. Apart from these, the only image is the top lead story's preview
  image (see "Newspaper feed"); no other page images.
- **Summaries are on demand.** Every row without a summary has a **Summarise** button (36 px,
  outlined, three-lines icon) under the title, where the summary will appear:
  idle "Summarise" → working: `accent2` pill, white spinner + "Summarising…", + one skeleton bar →
  done: the summary, as many lines as the story's size allows (briefs: Open summary) → failed:
  "Couldn't summarise this page." + **Try again**. At the daily limit, pressing it opens the Limit
  reached dialog instead.
- **No source or trust labels** (owner: badges made the app look unreliable). Summaries from the
  live page, an archived copy or just the title and description all look the same; so does the
  site's own description when there is no page text.
- **Page states** (one 14 px line under the title, small stroke icon, `ink2` text, weight 500):
  "Fetching page…" (`accent2` pill + skeleton, like Summarising); "Couldn't read this page" (file
  icon; JS apps, bot-protected sites); "Needs sign-in" / "Subscribers only" (lock icon); dead in
  `deadFg`, weight 600: "Page no longer available (404)." (broken-link icon). Summarise stays
  available on unreadable and sign-in rows.
- **Dead links: the Wayback Machine only on request** (owner). A dead row has no
  Summarise button; in its place a **"Find archived copy"** button (36 px, outlined, history icon)
  looks up the latest Wayback Machine snapshot only when clicked. States: working = `accent2` pill
  "Checking the Wayback Machine…"; found = "· Archived copy · 9 Jan 2019" link appended to the dead
  line, and the **Summarise** button appears (summarises that copy); none = "No archived copy on the
  Wayback Machine." in `ink2`; failed = "Couldn't reach the Wayback Machine." + **Try again**.
  Nothing is fetched from archive.org automatically.
- **Newspaper feed** (`Main`): Today / This week / Earlier are editions, each one `surface` sheet with a
  masthead (band rule, Aleo title centred between the date and counts, double rule under it) and
  thin `line` column rules instead of a card per article. Newest unread stories are biggest (lead →
  second → standard → brief; read ones last and faded); summaries (a 5–6 sentence
  paragraph) show in full on the lead, 5 lines on second stories, 3 on standard, none on briefs; only the top lead shows the page's
  preview image (16:9, caption "Image from <site>"; no image → a text-only lead).
  - **Story anatomy**: every story starts with its **source line** (site logo ·
    site · read time · age) at the top, above the folder label and the headline; on the lead it sits
    just under the preview image. The tag line sits right under the headline. Same in the
    sections, states, search and the mini front pages.
  - **Briefs** never show summary text. Not summarised: a compact **Summarise** (32 px, lines icon)
    that opens the detail panel once the server accepts, where the summary appears (at the daily
    limit only the Limit reached dialog shows). Summary ready: a compact outlined **Open summary**
    (32 px, lines icon) that opens the detail panel.
  - **Earlier** is paginated, newest first (owner): 30 briefs per page in 4 ruled columns, then a
    pager under a thin `ink` rule: "Showing 1–30 of 189 · newest first" on the left; **‹ Newer**
    (disabled on page 1), page numbers (36 px squares; current on `accent`), an ellipsis, the last
    page, **Older ›** on the right.
  Built into `Main` (Home · feed) and every board that imports it:
  - **Sections**: Needs sign-in and Dead links are one sheet each (small masthead, standard stories
    in 3 ruled columns, each with its state line); empty states as before.
  - **Story states** (`RowStates`): Summarise idle / working / done / failed; page fetching /
    couldn't read / needs sign-in / subscribers only / site's own description / read; dead link not
    looked up / checking / copy found / found and summarised / no copy / couldn't reach. A state label
    pill sits above each example only on that board. Daily limit → the Limit reached dialog.
  - **Search** (`FeedSearch`; Main `section="search"` + `search`: results / searching / none /
    error): results replace the feed in place. The query stays in the top-bar field; title "Search
    results", line "Top 10 matches · Clear search"; the views bar is hidden, sidebar filters still
    apply. One sheet; the masthead is the query in quotes, centred, with the count on the right
    (the left side stays empty). Best match as a second-size story beside two briefs, then standard
    results in ruled columns; results include read stories (faded), subscribers-only and dead links,
    each with its usual state line. Matched words in summaries as `<mark>` on `accent` with white text.
    - **At most 10 results**, best first, no Show more or pager (owner). The server merges the top 50
      keyword and top 50 meaning matches and returns the best 10 (weak meaning matches are cut off,
      so a search with no real match shows the no-results card); when more than 10 matched the count reads
      **"Top 10 matches"**, otherwise "N bookmarks".
    - **Searching** (`FeedSearchLoading`): masthead "Searching your bookmarks…" (`role="status"`),
      the query, a skeleton count; skeleton stories in the results' shape (pulsing, still with
      reduced motion). The logo plays Lens meanwhile.
    - **No results** (`FeedSearchEmpty`, `FeedSearchEmptyDark`): "0 bookmarks"; centred: magnifier
      on a 52 px `accent` circle, "Nothing matched “…”" (Aleo 21 px), "Try different words, or fewer
      of them. Search looks through the titles, summaries and page text of everything you've saved,
      read or not." + "A browser, folder or tag picked in the sidebar narrows the search too." +
      outlined **Clear search** (40 px).
    - **Never say how it matched** (owner): no "matched by keyword / by meaning" text anywhere.
      When search by meaning is unavailable or a search is throttled, keyword matches come back
      and look exactly like normal results.
    - **Couldn't search** (`FeedSearchError`): the request failed. Masthead sides empty; centred:
      "!" on a 52 px `accent` circle, "Couldn't search right now", "That didn't work on our side.
      Your bookmarks are safe, so try again in a moment.", **Try again** (`ink`, `onInk` text,
      refresh icon, 40 px) + outlined **Clear search**. Header line "Search didn't finish".
    - **Not shown** (owner): no state for searching too fast (the backend throttles or
      rate-limits instead, so the user never sees it, and never the Limit reached dialog); no folder
      label on results that matched through their folder name.
    - Every state has a dark board (`FeedSearchDark`, `FeedSearchLoadingDark`, `FeedSearchEmptyDark`,
      `FeedSearchErrorDark`), built from the dark tokens like `FeedDark`.
  - **Loading** (`FeedLoading`): the front page's shape in `skeleton` bars (pulsing, still with
    reduced motion) + "Loading your front page…".
  - **Phone** (`FeedPhone`, `FeedPhoneDark`, 390 px): every column stacks into one, rules become
    horizontal dividers, sheet padding 18 px, masthead 30 px; sidebar and top bar stack above.

## More pages
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
  "The site's own description…" line and the Summarise button, and there's no Re-summarise. Tags
  (see "Tags, collections and duplicates"); Details (browsers/folders, full URL).
- **Tags, collections and duplicates (Phase 5, owner 2026-11-03)**: Home boards `FeedTags`,
  `FeedTagsNone`, `FeedSelect`, `FeedSelectAdd`, `FeedSelectDone`, `FeedCollection`,
  `FeedDuplicates`, `FeedDuplicatesHidden`, `FeedDuplicatesEmpty`; sidebar states `FeedTagMenu`,
  `FeedTagRename`, `FeedTagRenameTaken`, `FeedTagMerge`, `FeedTagDelete`, `FeedTagNew`,
  `FeedTagLimit`, `FeedTagsUnused`, `FeedTagsFresh`, `FeedCollectionRename`,
  `FeedCollectionsBuilding`; detail `FeedDetailNoTags`, `FeedDetailTagAdd`, `FeedDetailTagCreate`,
  `FeedDetailTagsFull`, `FeedDetailTagError`, `FeedDetailDuplicate`; `SettingsAccountHidden`;
  phones `FeedTagsPhone`, `FeedDuplicatesPhone`; dark versions of the main ones.
  - **Limits**: tag names 1–30 characters, case doesn't matter, no repeats; at most **5 tags per
    bookmark** and **50 per account** (the starter tags count).
  - **Starter tags**, copied to every account as ordinary tags (renamable, deletable): Programming,
    AI, Design, Data, Business, Science, Health, Cooking, Travel, News.
  - **AI tags** come with the summary: when a summary is made, the AI adds up to 2 of the user's
    own tags straight away (never new tags, none on a bookmark at 5, never one the user removed).
    They look exactly like the user's tags: no suggestion state, no AI mark.
  - **On every story** (feed, sections, search, mini front pages): a tag line right under the
    headline: 13 px tag icon, then the tags as `ink2` links (weight 500) split by `muted` "·";
    a link adds that tag to the filter. No pills on stories. Stories without tags have no line.
  - **Sidebar Tags group**: "TAGS" heading with a **+ New tag** text button (36 px) on the right;
    rows like the other filters (name, count). Only tags in use show, biggest first, 8 then
    **Show all n**; **Show unused (n)** reveals tags on no bookmark under an "Unused" label (a new
    account's starter tags), so they can be renamed or deleted. A new account with no tags in use:
    "No tags on your bookmarks yet. Add one from a bookmark, or the AI adds them when it writes a
    summary." Several tags can be picked (`aria-pressed`, `accent` fill).
  - **Managing tags** happens in the sidebar: a 36 px **⋯** on each row (shown on hover or focus,
    always on touch screens) opens a 230 px menu: **Rename**, **Merge into another tag…**, a
    divider, **Delete tag** (`deadFg`). Rename turns the row into an input with Save / Cancel; a
    taken name: "There's already a tag called “Web performance”. To combine the two, use Merge."
    (`deadFg`, `role="alert"`). Merge: a dialog with the other tags as radio rows (count on the
    right), "Its 5 bookmarks get the tag you pick, then “Performance” is deleted.", **Merge into
    Web performance** (`ink`) + Cancel. Delete: alert dialog like Delete account (bin on `deadBg`),
    "Delete the tag “Design”?", "It comes off 9 bookmarks. The bookmarks stay, and so do their other
    tags.", **Delete tag** (`deadFg`, `onDead`) + Cancel. New tag: an input at the top of the list,
    **Add tag** + Cancel, "Up to 30 characters. The AI can use it from now on."; at 50: "You have 50
    tags, the most an account can have. Delete or merge one to add another."
  - **Filtering by tags**: several tags = bookmarks with **all** of them, on top of the views bar,
    browser and folder. Under the count line: "Tagged" + each tag as a 36 px `accent` pill with a
    × (28 px) + **Clear**. The count line says "4 bookmarks with both tags". Results are one sheet
    (small masthead "Data · Postgres", count on the right, ruled 2-column stories). None: tag icon
    on the `accent` circle, "No bookmarks have all these tags", "Nothing here is tagged both AI and
    Cooking. Remove a tag to see more." + outlined **Clear tags**.
  - **Select mode** (tagging several at once): **Select** in the header shows a checkbox (22 px box
    in a 36 px target, `role="checkbox"`; checked = `ink` fill with an `onInk` tick) at the top of
    each story, and a sticky bar replaces the views bar: "3 selected", **Add tag** and **Remove
    tag** (outlined 40 px), **Done** (`ink`) on the right. Add tag opens a 300 px picker: "Find or
    create a tag" field, the tags with counts, "Bookmarks that already have 5 tags are skipped."
    The result is a status line in the bar: "Added Programming to 2 bookmarks. 1 already had 5
    tags, so it was skipped."
  - **Detail panel tags**: outlined pills with remove ×, then an underlined **Add tag**. Add tag
    opens a combobox ("Find or create a tag") with a list of the user's other tags and counts (the
    highlighted option on `line`), and a typed name with no match offers "+ Create tag “Indexing”"
    ("New tags join your list, and the AI can use them too."); otherwise "3 more tags fit on this
    bookmark." None: "No tags yet." (not summarised: "No tags yet. When you summarise this page,
    the AI adds up to 2 of your tags."). At 5: Add tag goes and "5 tags is the most a bookmark can
    have. Remove one to add another." Not saved: "Couldn't add “Performance”. Check your
    connection and try again." (`deadFg`) + **Try again**.
  - **Smart collections**: a **Collections** group under Tags: similar pages grouped by AI, each
    with its count, linking to the collection; a pencil (hover / focus) renames it, the only edit
    (owner). Rename: input + "Your name stays when the collection is updated." Under the list:
    "Similar pages, grouped by AI. Not every bookmark fits one. Updated 2 November." Building:
    three skeleton bars + "Grouping similar pages… This can take a minute or two." Too few: "Once
    about 30 of your bookmarks have a summary or page text, similar ones are grouped here. 19 so
    far." A collection's page: title = its name, line "5 bookmarks · similar pages grouped by AI ·
    updated 2 November", one sheet with "Updated 2 November" left of the masthead.
  - **Possible duplicates** (different links, almost the same page; exact same links are already
    merged at sync, and only pages with page text or a summary are compared): a section in the
    views bar after Dead links. Header "3 pairs · different links to almost the same page"; one
    sheet with "Different links that lead to almost the same page. Hiding a copy only removes it
    from Bookmark Brain: it stays in your browser, and you can bring it back from Settings →
    Account." Each pair side by side (stacked on phones, rule between): source line with the save
    age, Aleo 21 px title, full URL, browser · folder, outlined **Hide this one**; under the pair an
    outlined **Not duplicates** + "Keeps both. This pair won't be shown again." After hiding, an
    `ink` status bar: "Hid the Edge copy of “Index Types”. It's still in your browser." + **Undo**.
    Empty: "No possible duplicates" / "Bookmarks with different links to almost the same page show
    up here. Only pages Bookmark Brain could read are compared." The detail panel of a bookmark in
    a pair has a `surface` note above the summary: copy icon, "Looks like a copy of another
    bookmark, **…**, saved in Edge." + **Review**.
- **First run** (`FeedFirstRun`): one `surface` card: bookmark icon on `accent`, "Connect your first
  browser", two numbered steps, **Get the extension** (`ink`) + **Connect by hand** (to Settings).
- **Ask** (`Ask`, `AskEmpty`, `AskMenu`): two panels. Main: thread title (Aleo 24 px) with an
  outlined **New chat** (40 px, plus icon) on the right; your messages in `ink` bubbles on the right;
  the agent's steps as small check lines ("Searched your bookmarks for “…” · 4 found"); answers in
  `surface` bubbles with numbered citation chips on `accent`; working = `accent2` pill "Searching
  your bookmarks…" + skeleton lines; composer (textarea + `ink` send button) and "Answers use only
  pages you've saved, and link to each one." Right: **Sources** (numbered cards with logo chip,
  site, Aleo title) + "Also found". Empty: "Ask your bookmarks" + 4 suggested-question pills.
  - **Citations, source cards and "Also found" open the bookmark detail panel** (owner), as in the
    feed.
  - **History** (owner): only the **first question** of each chat is kept, never the answers.
    There's no chat list on the page. The **Ask tab** opens a dropdown (`AskMenu`; styled like the
    account menu, 300 px, under the tab): **New chat**, a divider, "Recent questions" and the last
    3 first-questions (40 px rows, a "repeat" icon, one line with an ellipsis). Picking one opens
    Ask and asks it again for a fresh answer. With no questions yet the tab just opens Ask.
    Follow-up questions work while a chat is open.
  - **The latest turn** (owner; Ask `turn` setting): **searching** = `accent2` pill + skeleton
    lines. **Writing** (`AskWriting`): each step appears as a check line as it happens, then the
    answer fills in word by word with a 2 px blinking `ink` cursor (still under reduced motion;
    `aria-live="polite"`). Text the model writes before a step is dropped. Citations and sources
    arrive at the end. While searching or writing, the send button becomes **Stop** (`ink`, square
    icon + "Stop", 44 px). **Stopped** (`AskStopped`): the partial answer stays, with a 13 px
    `muted` "Stopped" line and a small square under it. **Nothing found** (`AskNothingFound`): a
    normal answer bubble ("I couldn't find anything about … in your bookmarks."), the step line ends
    "· 0 found", and the Sources panel says "No sources for this answer."
  - **Couldn't answer** (every free AI service failed): the Limit reached dialog's "AI is busy"
    version (see below).
  - **Phone** (`AskPhone`, `AskPhoneSources`, `AskPhoneDark`; ≤ 760 px): one column. The Sources
    panel is hidden. Under each answer, a 40 px outlined "Sources (n)" row with a chevron unfolds
    into compact source cards and "Also found". Citations still open the detail panel (full screen
    on phones).
- **Weekly digest** (`Digest`, `DigestDark`), a **newsletter**: no sidebar. One
  `panel` with "Weekly digest" (Aleo 40 px), "Unread bookmarks you saved more than 30 days ago,
  gathered once a week.", then **back-issue tabs** (This week · 16–22 Oct · 9–15 Oct · 2–8 Oct ·
  Older; underline style, current = 3 px `accent` underline, counts in `muted`). Below, one centred
  `surface` sheet, max 720 px, padding 36/44 px (20/18 on phones):
  - masthead: band rule, "23–29 October" · **The weekly digest** (Aleo 36 px, centred) · "9 stories",
    double `ink` rule;
  - "This week" label + the AI overview as an editor's note (Aleo 19 px, 1.6 line height, a 58 px
    drop cap);
  - one section per theme: thin band rule, Aleo 24 px theme name + "n stories", then a list of
    stories split by `line` rules: source line (logo · site · n min read · saved … ago), Aleo 20 px
    title (opens the detail panel), one line on why to read it, and a compact **Open summary** or
    **Summarise** (32 px), exactly like briefs in the feed. No Mark as read on the page (it's in the
    detail panel);
  - footer under an `ink` rule: "That's this week. The next digest arrives on Monday." +
    "Back to your feed".
- **Connect** (`ConnectStates`, all states on one board) and **error pages** (`ErrorStates`), on the
  dark texture with a `surface` card per state (icon on `accent`, Aleo 24 px title, one line, one
  action). Connect: signed out (sign-in buttons) → Connecting… → Syncing (n found, progress bar) →
  Connected (a summary with Open your feed; see Connect extras) → extension didn't answer (token
  shown once + Copy) → link expired (15 min), plus three more:
  "Connected, but the first sync failed" (the extension's error + Go to your feed), "Something went
  wrong" (the token couldn't be made; Try again) and "Connect from the extension" (page opened
  without the extension's link; Connect by hand). Errors: 404 (Back to your feed), server waking up
  (free server sleeps, up to a minute), signed out (sign-in buttons), something went wrong (Try
  again).
- These cards **follow the theme** (owner): `surface` / `ink` / `ink2`, so they turn dark in dark
  mode (main button `ink` with `onInk` text; sign-in buttons stay dark); the texture behind them is
  the same in both. Boards `ConnectStatesDark`, `ErrorStatesDark`.
- **Connect extras**:
  - Connecting / Syncing / Done start with a **step strip** (Connect → Sync → Open feed; done = `accent`
    check, current = `accent` number, upcoming = outlined) and the **browser's logo and ours** on
    56 px white chips joined by a line: dotted and moving while connecting, an `accent` line with
    flowing gaps while syncing, solid with an `accent` check when done (motion off for reduced motion).
  - Syncing: "231 bookmarks in 14 folders so far" + progress bar + **Just arrived** (the newest 4
    bookmarks with site logos, title and site).
  - Done **doesn't open the feed by itself**: two stat tiles (bookmarks, folders), "Also
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
  **"AI is busy" version** (owner; version 4 on the board): opens instead when every free AI
  service fails (for Ask, or a summary). It has a cloud icon, "AI is busy right now", and "The free AI services Bookmark
  Brain uses are all busy or down at the moment. This usually passes in a few minutes, and it
  doesn't use up your daily limit." The rest is the same (Notify the maintainer + Close; footnote
  "Sends the maintainer your account email and the time."). Sending and Sent work the same.

## Settings
Same dark-texture top bar as the feed (no tab is current, since Settings opens from the account
menu). The section menu (Browsers,
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
- **Account** (`SettingsAccount`, `SettingsAccountGithub`, `SettingsAccountLinked`,
  `SettingsAccountLinkError`, `SettingsAccountHidden`, each with a dark board; Settings
  `section="account"`, `providers` google / github / both, `linkError`, `hidden`), four cards, plus
  **Hidden bookmarks** between Sign-in methods and Download my data when something is hidden:
  - **Your account**: 56 px avatar initial on `accent`, name, email, an outlined **Sign out**
    button, and "Your name and picture come from your Google or GitHub account. Change them there."
    No provider line here: the next card shows it.
  - **Sign-in methods** (owner, 2026-11-03): "Either one signs you in to this account." (14 px
    `ink2`), then a row each for Google and GitHub, split by a `line` divider. Each row has the 20 px
    mark in a 36 px `surface` box (1 px `line`, radius 10 px; the Octocat in `ink`), the name
    (weight 600), and a 13 px `ink2` status: "Linked", "Linked · your only sign-in method" or "Not
    linked". On the right:
    - **Linked**: **Unlink**, a text button in `deadFg` like Revoke. It's hidden on the only method
      left, so nobody can lock themselves out.
    - **Not linked**: a dark 40 px button, the same for both providers. Google's is Google's own
      button (its library: `filled_black`, size large, "Continue with Google"), because only that
      button returns a sign-in we can verify. GitHub's is ours, drawn to match: "Continue with
      GitHub", `#141516` with a 1 px `#8E918F` border and the white Octocat, like the sign-up
      page's buttons.
    - Linking works even when the emails differ (the same verified email joins automatically).
      A provider account that has its own Bookmark Brain account can't be linked. A problem is one
      13 px `deadFg` line (weight 500, `role="alert"`) under the rows, above a `line` divider,
      e.g. "That GitHub account has its own Bookmark Brain account, so it can't be linked here."
      (`SettingsAccountLinkError`).
  - **Hidden bookmarks** (owner, 2026-11-03; only when there are some): "Copies you hid from
    Possible duplicates. They're still in your browser; Unhide puts them back in Bookmark Brain."
    Rows split by `line`: title (weight 600), "postgresql.org/docs/16/indexes-types.html · Edge ·
    hidden today" (13 px `ink2`), an outlined **Unhide** (40 px).
  - **Download my data**: "A JSON file with your bookmarks, folders, browsers, read states, tags and
    their summaries. It's ready in a few seconds." + **Download my data** (`ink`, download icon).
  - **Delete account** (heading in `deadFg`): "Permanently deletes your account, your bookmarks, read
    states, tags and connected browsers. The extension stops syncing. This can't be undone." +
    **Delete account…** filled with `deadFg`, `onDead` text, which opens a dialog (`SettingsAccountDelete`):
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

Dark mode: the popup body uses the dark tokens (`PopupDark` and the `…Dark` state boards); the
texture header is the same in both themes.

## Logo animations
The top-left masthead BB in the top bar animates while the app works, a different movement per job
(board `LogoAnimations`, CSS keyframes on the SVG parts). Every one stops and shows the still logo
under `prefers-reduced-motion: reduce`, and the status is always also said in words.
- **Summarise → "Page back"**: a copy of the right B in `accent` turns over the spine to the left
  (scaleX 1 → −1 around x = 100, ~0.7 s) and fades. Plays once as a flash on click, then repeats
  every 2 s until the summary is ready.
- **Page loading → "Rewind"**: the whole mark turns one full turn anticlockwise (2.2 s,
  `cubic-bezier(.6,0,.3,1)`, turning for the first 70 %, resting for the rest), looping while a page
  loads, including the free server waking up.
- **Ask → "Conversation"**: the two B's take turns lifting 8/200 of the mark (1.2 s cycle, the left
  B 0.6 s behind the right), from sending a question until the answer starts to appear.
- **Searching → "Lens"**: a brown (`accent`) lens ring (r 30/200, 7 stroke, white fill at 35 %) with
  a short handle slides over the letters from left to right and back (translateX 0 → 76/200, 2.2 s
  ease-in-out loop), clipped to the tile, while a search runs.
- **Wayback Machine → "Hourglass"**: a 30/200 `accent` badge (cream outline) in the bottom-right
  corner of the tile holds a white hourglass that turns over every 1.8 s (still for 40 %, turns
  180° over 20 %, still again), while we look for an archived copy.
- **In code**: `frontend/src/components/Logo.tsx` (`motion` prop), keyframes in `index.css`
  (`animate-page-back`, `animate-rewind`, `animate-hourglass`, `animate-conversation`,
  `animate-lens`), and `hooks/useLogoMotion.ts` picks one at a time, the more specific job first:
  Hourglass, Page back, Conversation, Lens, Rewind. When the work ends, the logo finishes its
  current cycle.

## Later (owner's backlog, don't design until they say so)
- Phone boards (`FeedPhone`, `FeedPhoneDark`) need another pass: the owner said they don't look
  good yet (low priority).

## Rules
- Real `<button>`, `<a href>`, `<label>`; `aria-label` on icon buttons; visible focus; touch targets
  ≥ 44 px (≥ 36 px for dense row actions).
- Works at phone width: the sidebar stacks above the list, the top bar wraps.
- Icons: inline stroke SVG, never emoji. No gradient washes or left-border accent cards.
