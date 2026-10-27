import { browser } from 'wxt/browser'
import { startConnect } from '../../lib/connect'
import { APP_URL, DEFAULT_API_URL, fullSync, getSettings, getStatus, saveSettings } from '../../lib/sync'

// The status card has four designed states (ui-design skill, "Extension popup"):
// not-connected, connected, syncing, error (token rejected, or any failed sync).
type State = 'not-connected' | 'connected' | 'syncing' | 'error'

const card = document.querySelector<HTMLDivElement>('#card')!
const cardTitle = document.querySelector<HTMLSpanElement>('#card-title')!
const statusEl = document.querySelector<HTMLParagraphElement>('#status')!
const connectButton = document.querySelector<HTMLButtonElement>('#connect')!
const syncButton = document.querySelector<HTMLButtonElement>('#sync')!
const openFeedButton = document.querySelector<HTMLButtonElement>('#open-feed')!
const settingsLink = document.querySelector<HTMLAnchorElement>('#settings-link')!
const form = document.querySelector<HTMLFormElement>('#settings')!
const apiUrl = document.querySelector<HTMLInputElement>('#apiUrl')!
const token = document.querySelector<HTMLInputElement>('#token')!

const timeFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

function show(state: State, title: string, body: string) {
  card.dataset.state = state
  cardTitle.textContent = title
  statusEl.textContent = body
}

async function render() {
  const [settings, status] = await Promise.all([getSettings(), getStatus()])
  const connected = Boolean(settings?.token)
  const rejected = status && !status.ok && status.message.startsWith('Token rejected')

  // Connected: Sync now is the main action. Rejected token: Reconnect instead.
  connectButton.hidden = connected && !rejected
  connectButton.textContent = connected ? 'Reconnect' : 'Connect this browser'
  syncButton.hidden = !connected || Boolean(rejected)
  syncButton.disabled = false
  syncButton.textContent = 'Sync now'
  openFeedButton.hidden = !connected

  apiUrl.value = settings?.apiUrl ?? DEFAULT_API_URL
  token.value = settings?.token ?? ''

  if (!connected) {
    show('not-connected', 'Not connected yet', 'Click Connect and sign in to the web app. Your bookmarks start syncing straight away.')
  } else if (rejected) {
    show('error', 'Token rejected', 'This browser’s token was revoked. Reconnect to keep syncing.')
  } else if (status && !status.ok) {
    show('error', 'Sync failed', `${status.message}. It will try again in a few minutes.`)
  } else if (status) {
    show('connected', 'Connected · syncing automatically', `${status.message}. Last sync ${timeFormat.format(new Date(status.at))}.`)
  } else {
    show('connected', 'Connected · syncing automatically', 'Waiting for the first sync…')
  }
}

async function runSync(button: HTMLButtonElement) {
  button.disabled = true
  syncButton.textContent = 'Syncing…'
  show('syncing', 'Syncing…', 'Sending this browser’s bookmarks to your library.')
  try {
    await fullSync()
  } catch {
    // fullSync already recorded the error in the status.
  } finally {
    button.disabled = false
    await render()
  }
}

function openApp(path: string) {
  void browser.tabs.create({ url: new URL(path, APP_URL).toString() })
}

connectButton.addEventListener('click', () => {
  // Opens the web app in a new tab; the popup closes and the token arrives via the content script.
  void startConnect()
})

syncButton.addEventListener('click', () => void runSync(syncButton))
openFeedButton.addEventListener('click', () => openApp('/'))
settingsLink.addEventListener('click', (event) => {
  event.preventDefault()
  openApp('/settings')
})

form.addEventListener('submit', async (event) => {
  event.preventDefault()
  await saveSettings({ apiUrl: apiUrl.value.trim(), token: token.value.trim() })
  await runSync(form.querySelector('button')!)
})

void render()
