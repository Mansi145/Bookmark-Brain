---
name: extension
description: How the Bookmark Brain browser extension (WXT, Manifest V3) syncs bookmarks, how one-click connect works and its security rules, and how to build, load and give it icons. Use when changing anything in extension/, the web app's /connect page, the sync API contract, or extension permissions.
---

# Browser extension

## Files
| File | Role |
|---|---|
| `wxt.config.ts` | Manifest: name, permissions, host permissions, Firefox add-on id |
| `entrypoints/background.ts` | Service worker: when to sync (events, alarms, `sync-now` messages) |
| `entrypoints/connect.content.ts` | Content script on the web app's `/connect` page only |
| `entrypoints/popup/` | Popup: Connect / Reconnect, Sync now, *Advanced: paste a token* |
| `lib/sync.ts` | Reads the bookmark tree, talks to `POST /api/sync`, stores settings and status |
| `lib/connect.ts` | One-click connect: nonce, message types, `acceptToken` checks |
| `assets/icon/*.svg`, `scripts/icons.mjs` | Logo sources and the PNG generator |

State lives in `storage.local`: `settings {apiUrl, token}`, `status {at, ok, message}`, `sourceId`
(random per install, so two profiles are two sources), and a pending `connect {nonce, at}`.

## Sync model
- Full sync (whole tree, `full: true`) on install, browser startup, the hourly alarm, a retry alarm
  5 min after a failure, folder changes, and connect. The server removes anything this source no
  longer has.
- Incremental sync on `onCreated / onChanged / onMoved / onRemoved` for single bookmarks.
- MV3 can kill the service worker at any time, so nothing important is kept in memory; alarms survive.
  The API is idempotent, so over-syncing is always safe.
- `fullSync()` returns the account's active bookmark count; it records `status` either way.
- Payload shape is `SyncIn` in `backend/app/schemas.py`. Change both sides together.

## One-click connect (and why it's safe)
1. Popup `startConnect()`: random nonce → `storage.local.connect` → opens
   `${APP_URL}/connect?nonce=…&browser=…`.
2. `/connect` page (`frontend/src/pages/ConnectPage.tsx`, signed-in user) pings, gets `ready` from
   the content script, creates a token (`POST /api/tokens`, named "<Browser> extension") and posts
   `{type: connect, token, nonce}` to its own window.
3. Content script accepts it only if: `event.source === window`, `event.origin === location.origin`,
   the token starts with `bb_pat_`, and the nonce matches the pending one and is < 15 min old. The
   nonce is deleted (single use). It keeps the existing API URL or the build default: **the page can
   never choose where the extension sends data.**
4. It replies `connected`, then sends `sync-now` to the background and waits; the background answers
   (`sendResponse` + `return true`, works in Chrome and Firefox) with `{ok, count}` or `{ok:false, error}`,
   relayed to the page as `synced`. The page shows a loader, then navigates to the feed.
5. No reply within 4 s: the page shows the token once for a manual paste.

Message names live in `lib/connect.ts` `MSG` **and** are duplicated in `ConnectPage.tsx`: keep them
in sync. Never widen the content script's `matches`, accept messages from other origins, or let a
message set `apiUrl`.

## Permissions
`bookmarks`, `storage`, `alarms`, and host access to our API only (`http://localhost:8000/*`,
`https://*.onrender.com/*`). Don't add `<all_urls>`, `tabs` or `scripting`: the install warning would
read "read and change all your data on all websites". Page fetching happens on the server.

## Build-time URLs
`WXT_API_URL` (default `http://localhost:8000`) and `WXT_APP_URL` (default `http://localhost:5173`)
in `extension/.env` or the shell. For a deployed build also add `https://<app>/connect*` to `matches`
in `connect.content.ts`, and the API host to `host_permissions` if it isn't on onrender.com.

## Build and load
```bash
cd extension
npm run build            # Chrome/Edge/Brave → .output/chrome-mv3/
npm run build:firefox    # → .output/firefox-mv2/
npm run compile          # type-check
npm run zip / zip:firefox
```
On WSL, `wxt dev` can't launch Windows Chrome: build, then `chrome://extensions` → Developer mode →
Load unpacked → `\\wsl$\Ubuntu\home\mansi\personal_projects\bookmark_brain\extension\.output\chrome-mv3`.
After changes: rebuild and click reload on the extension card. Content scripts only attach to tabs
opened or reloaded after that.

## Icons
`assets/icon/logo.svg` (full logo, used at 48/128 px) and `logo-small.svg` (outline, eyes and ribbon
with thicker strokes, used at 16/32 px, where fine detail turns to mush). `npm run icons` renders
`public/icon/{16,32,48,128}.png` with `@resvg/resvg-js`; WXT adds them to the manifest automatically.
Regenerate after any logo change and commit the PNGs. The logo itself is defined in the `ui-design` skill.

## Debugging
- Background: `chrome://extensions` → the extension → "service worker" → console.
- Content script: DevTools console on the `/connect` tab (select the extension's context).
- Popup: right-click the popup → Inspect.
- "Token rejected" = 401: the token was revoked; click Reconnect.
