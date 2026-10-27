// Runs only on the web app's /connect page. Receives the token the page creates and
// passes it to the extension. Everything else on the web is ignored.
//
// For a deployed app, add its /connect URL to `matches` (e.g. 'https://your-app.vercel.app/connect*')
// and build with WXT_APP_URL set to the same origin.

import { browser } from 'wxt/browser'
import { acceptToken, MSG, type SyncResult } from '../lib/connect'

export default defineContentScript({
  matches: ['http://localhost:5173/connect*'],
  main() {
    const reply = (message: object) => window.postMessage(message, window.location.origin)

    // Tell the page we're installed (and answer if it asks again after it loads).
    reply({ type: MSG.ready })

    window.addEventListener('message', async (event) => {
      // Only trust messages from this exact page, not iframes or other windows.
      if (event.source !== window || event.origin !== window.location.origin) return
      const data = event.data as { type?: string; token?: unknown; nonce?: unknown } | null
      if (!data || typeof data.type !== 'string') return

      if (data.type === MSG.ping) {
        reply({ type: MSG.ready })
        return
      }
      if (data.type !== MSG.connect) return

      const ok = await acceptToken(data.token, data.nonce)
      reply({ type: ok ? MSG.connected : MSG.rejected, nonce: data.nonce })
      if (!ok) return

      // Ask the background worker to sync and wait for it to finish, so the page can
      // show a loader and then the feed. (Content scripts can't call the API themselves:
      // the token stays inside the extension.)
      let result: SyncResult
      try {
        result = await browser.runtime.sendMessage({ type: 'sync-now' })
      } catch (err) {
        result = { ok: false, error: String(err instanceof Error ? err.message : err) }
      }
      reply({ type: MSG.synced, nonce: data.nonce, ...result })
    })
  },
})
