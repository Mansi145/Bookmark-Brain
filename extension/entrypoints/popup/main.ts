import { startConnect } from '../../lib/connect'
import { DEFAULT_API_URL, fullSync, getSettings, getStatus, saveSettings } from '../../lib/sync'

const statusEl = document.querySelector<HTMLParagraphElement>('#status')!
const connectButton = document.querySelector<HTMLButtonElement>('#connect')!
const syncButton = document.querySelector<HTMLButtonElement>('#sync')!
const form = document.querySelector<HTMLFormElement>('#settings')!
const apiUrl = document.querySelector<HTMLInputElement>('#apiUrl')!
const token = document.querySelector<HTMLInputElement>('#token')!

async function render() {
  const [settings, status] = await Promise.all([getSettings(), getStatus()])
  const connected = Boolean(settings?.token)

  // Connected: syncing is the main action; reconnecting stays available.
  connectButton.textContent = connected ? 'Reconnect' : 'Connect this browser'
  connectButton.className = connected ? 'secondary' : ''
  syncButton.hidden = !connected

  apiUrl.value = settings?.apiUrl ?? DEFAULT_API_URL
  token.value = settings?.token ?? ''

  if (!connected) {
    statusEl.textContent = 'Not connected yet. Click Connect and sign in to the web app.'
    statusEl.className = 'status'
  } else if (!status) {
    statusEl.textContent = 'Connected. Waiting for the first sync…'
    statusEl.className = 'status'
  } else {
    statusEl.textContent = `${status.message} · ${new Date(status.at).toLocaleString()}`
    statusEl.className = `status ${status.ok ? 'ok' : 'error'}`
  }
}

async function runSync(button: HTMLButtonElement) {
  button.disabled = true
  statusEl.textContent = 'Syncing…'
  statusEl.className = 'status'
  try {
    await fullSync()
  } catch {
    // fullSync already recorded the error in the status.
  } finally {
    button.disabled = false
    await render()
  }
}

connectButton.addEventListener('click', () => {
  // Opens the web app in a new tab; the popup closes and the token arrives via the content script.
  void startConnect()
})

syncButton.addEventListener('click', () => void runSync(syncButton))

form.addEventListener('submit', async (event) => {
  event.preventDefault()
  await saveSettings({ apiUrl: apiUrl.value.trim(), token: token.value.trim() })
  await runSync(form.querySelector('button')!)
})

void render()
