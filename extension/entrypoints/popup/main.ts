import { DEFAULT_API_URL, fullSync, getSettings, getStatus, saveSettings } from '../../lib/sync'

const form = document.querySelector<HTMLFormElement>('#settings')!
const apiUrl = document.querySelector<HTMLInputElement>('#apiUrl')!
const token = document.querySelector<HTMLInputElement>('#token')!
const statusEl = document.querySelector<HTMLParagraphElement>('#status')!
const button = form.querySelector('button')!

async function showStatus() {
  const status = await getStatus()
  if (!status) {
    statusEl.textContent = 'Not synced yet'
    statusEl.className = 'status'
    return
  }
  const when = new Date(status.at).toLocaleString()
  statusEl.textContent = `${status.message} · ${when}`
  statusEl.className = `status ${status.ok ? 'ok' : 'error'}`
}

async function init() {
  const settings = await getSettings()
  apiUrl.value = settings?.apiUrl ?? DEFAULT_API_URL
  token.value = settings?.token ?? ''
  await showStatus()
}

form.addEventListener('submit', async (event) => {
  event.preventDefault()
  button.disabled = true
  statusEl.textContent = 'Syncing…'
  statusEl.className = 'status'
  try {
    await saveSettings({ apiUrl: apiUrl.value.trim(), token: token.value.trim() })
    await fullSync()
  } catch {
    // fullSync already recorded the error in the status.
  } finally {
    button.disabled = false
    await showStatus()
  }
})

void init()
