---
name: ui-design
description: Bookmark Brain's final visual design (Cloudlifter nebula texture, colours, fonts, logo, landing page and image-free reading-list feed) with exact tokens for building it in React/Tailwind. Use when building or restyling any frontend page or component, the extension popup, or design canvas boards.
---

# UI design

**Ask the owner before designing or restyling anything that isn't already decided here**: which
page, layout, what goes where. Present options with a recommendation; don't invent new looks.

Source of truth: the Claude design canvas https://claude.ai/artifact/88oGw1iJQJW2P8tB6jRBVT
(boards: `Login.dc.html` landing page, `Main.dc.html` feed, `FeedDark.dc.html`, `Texture.dc.html`,
`Logo.dc.html`; `Settings.dc.html` and `Popup.dc.html` still use the old styling). Read a board's
file through the Artifact tool when you need exact markup.

## Tokens
| Token | Light | Dark | Use |
|---|---|---|---|
| bg | `#FBFBFC` | `#17181A` | page |
| surface | `#FFFFFF` | `#212225` | cards, rows, inputs |
| line | `#E5E7EC` | `#34363B` | borders, dividers |
| ink | `#141516` | `#F2F2F4` | text, headings, primary buttons (white text) |
| ink2 | `#2F3134` | `#C9CBD1` | secondary text, meta |
| muted | `#45484B` | `#A8ABB2` | small labels, counts |
| blue | `#DCEAF3` | `#25343F` | selected filter, group bands, site tiles |
| pink | `#FBEAF2` | `#3B2833` | "Summarising…" pill, alternate group bands |
| skeleton | `#EEF0F4` | `#2B2D31` | loading bars |
| deadBg / deadFg | `#F8E3E3` / `#7C1D1D` | `#3D2224` / `#F5B5B5` | dead link notice |

Theme follows the system (`prefers-color-scheme`). Text is near-black, never mid-grey; keep 4.5:1
contrast, even for 12–13 px meta text. Define these as CSS variables / Tailwind `@theme` tokens once,
not as scattered hex values.

**Fonts** (Google Fonts): **Aleo** 500/600/700 for headings, group names and bookmark titles;
**Geist** 400/500/600 for everything else (15 px base, 1.5 line height).
Sizes in the feed: page title 40 px, group band 19 px, row title 21 px, summary 14 px, meta 13 px.

## Cloudlifter nebula texture
Used on the landing page hero + closing call to action and the app's top bar (in both themes; text
on it is always near-black). Recipe:
1. Base `linear-gradient(90deg, #8BB6D2 0%, #F4D4E5 100%)`, `overflow: hidden`.
2. A layer `inset: -60px -8%` with `filter: blur(60px)` holding 5–6 overlapping ellipses
   (`border-radius: 50%`), left to right: `#7FAACB` .85, `#DCEAF3` .9, `#BEC3DD` .85,
   white .5, `#F4D4E5` .95, `#E9B9D3` .8 (opacity after each colour).
3. Film grain: full-size SVG `feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3"`
   + `feColorMatrix saturate 0`, `mix-blend-mode: multiply`, opacity **0.26**.
Make it one reusable `<Nebula>` component.

## Logo
A cute brain (lobes, centre fissure, a few folds, pill eyes, small smile) on a bookmark-ribbon body
with little arms. Line art: `#141516` strokes, 6 px, rounded caps/joins, even weight. Fill: radial
"Mulberry" aura `#955E7D → #CA8FB9 (0.45) → #FFC0F5`, `userSpaceOnUse cx=100 cy=76 r=150 fy=70`,
applied only as the fill of the brain and ribbon so colour never leaks outside the outline.
SVG source: `extension/assets/icon/logo.svg` (reuse it in the web app). Rejected styles, don't retry:
grunge/chrome metal, robot head, heart, dry brush, zig-zag scribble, uneven stroke weight.

## Landing page (signed out)
Texture hero: medium logo beside a stacked "Bookmark / Brain" wordmark, headline
**"Saved it? Now actually use it."** (Aleo 64 px), **Continue with Google** and **Continue with
GitHub** buttons (GitHub needs backend work), and a product preview of the reading list. Then
"How it works" (3 steps), "What it does with your bookmarks" (summaries, search by meaning, ask your
bookmarks, plus dead links / reading status / digest), a closing call to action on the texture, footer.

## App shell and feed (signed in)
- **Top bar** on the texture: logo + "Bookmark Brain" (Aleo 21 px), search field ("Search by meaning
  or keyword…", `/` shortcut, white 82 % background), nav Feed / Ask / Settings (current page on a
  white 75 % pill), round account button.
- **Sidebar** (220–260 px): Library (All, Unread, Read, Archived), Browsers, Folders (indented
  subfolders) with counts; the selected item on `blue`, weight 600.
- **Header**: page title (e.g. "Unread", Aleo 40 px), a line like "196 bookmarks · 4 being summarised
  · synced from Chrome 2 min ago", Sort select (Newest, Oldest, Shortest read).
- **Reading list, no images** (decided: no `og:image` anywhere). Rows grouped by save date
  (**Today / This week / Earlier**); each group has a header band (radius 12 px on top, Aleo name +
  "n bookmarks") alternating `blue`, `pink`, `blue`, above a bordered `surface` list.
  Row: meta line (20 px rounded site-initial tile on `blue` · site · folder · browser · age, plain
  text), Aleo title, 2-line summary clamped at ~760 px wide, right column with "⋯" menu (36 px) and
  "6 min read". States: pending = pink pill with spinner ("Fetching page…" / "Summarising…") + one
  skeleton bar; dead = one red line "Page no longer available (404)." + "Open archived copy";
  read = row at 70 % opacity. No grid/list toggle, no coloured chips.
- Shortest-read sort shows a flat list (date groups only make sense for date sorts).

## Rules
- Real `<button>`, `<a href>`, `<label>`; `aria-label` on icon buttons; visible focus; touch targets
  ≥ 44 px (≥ 36 px for dense row actions).
- Works at phone width: the sidebar stacks above the list, the top bar wraps.
- Icons: inline stroke SVG, never emoji. No gradient washes or left-border accent cards.
