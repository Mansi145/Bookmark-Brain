// One-click connect: the popup opens the web app's /connect page, the page creates a
// token and hands it to our content script, which stores it here.
//
// The nonce is a one-time random code the popup creates when the user clicks
// Connect. The content script only accepts a token that comes back with that same
// code, so a web page can't plant a token unless the user actually started a connect.

import { browser } from 'wxt/browser'
import { APP_URL, DEFAULT_API_URL, detectBrowser, getSettings, saveSettings } from './sync'

const NONCE_TTL_MS = 15 * 60 * 1000

// Message types exchanged with the /connect page via window.postMessage.
export const MSG = {
  ping: 'bookmark-brain:ping',
  ready: 'bookmark-brain:extension-ready',
  connect: 'bookmark-brain:connect',
  connected: 'bookmark-brain:connected',
  rejected: 'bookmark-brain:connect-rejected',
  synced: 'bookmark-brain:synced',
} as const

/** What the background worker answers to a 'sync-now' message. */
export type SyncResult = { ok: true; count: number } | { ok: false; error: string }

/** Called from the popup: remember a fresh nonce and open the web app's connect page. */
export async function startConnect(): Promise<void> {
  const nonce = crypto.randomUUID()
  await browser.storage.local.set({ connect: { nonce, at: Date.now() } })
  const url = new URL('/connect', APP_URL)
  url.searchParams.set('nonce', nonce)
  url.searchParams.set('browser', detectBrowser())
  await browser.tabs.create({ url: url.toString() })
}

/** Called from the content script. Returns true if the token was accepted and saved. */
export async function acceptToken(token: unknown, nonce: unknown): Promise<boolean> {
  if (typeof token !== 'string' || !token.startsWith('bb_pat_')) return false
  if (typeof nonce !== 'string') return false

  const { connect } = await browser.storage.local.get('connect')
  const pending = connect as { nonce: string; at: number } | undefined
  if (!pending || pending.nonce !== nonce || Date.now() - pending.at > NONCE_TTL_MS) return false

  // Keep an API URL the user set manually; otherwise use this build's default.
  const current = await getSettings()
  await saveSettings({ apiUrl: current?.apiUrl || DEFAULT_API_URL, token })
  await browser.storage.local.remove('connect') // one use only
  return true
}
