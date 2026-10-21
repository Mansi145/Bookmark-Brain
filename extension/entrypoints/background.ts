// Background service worker: keeps the server in step with the browser's bookmarks.
//
// Manifest V3 can stop this worker at any time, so nothing important is kept in
// memory. Every change is pushed straight away, and if a push fails (offline, API
// asleep, worker killed) the next full sync, on a retry alarm or the hourly alarm,
// catches it up. The API treats repeated data as a no-op, so over-syncing is safe.

import { browser } from 'wxt/browser'
import { collectBookmarkIds, fullSync, getSettings, incrementalSync, itemForNode } from '../lib/sync'

const PERIODIC_ALARM = 'periodic-full-sync'
const RETRY_ALARM = 'retry-full-sync'

export default defineBackground(() => {
  browser.runtime.onInstalled.addListener(() => {
    browser.alarms.create(PERIODIC_ALARM, { periodInMinutes: 60 })
    void safeFullSync()
  })
  browser.runtime.onStartup.addListener(() => void safeFullSync())

  browser.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === PERIODIC_ALARM || alarm.name === RETRY_ALARM) void safeFullSync()
  })

  browser.bookmarks.onCreated.addListener((id) => void pushNode(id))
  browser.bookmarks.onChanged.addListener((id) => void pushNode(id))
  browser.bookmarks.onMoved.addListener((id) => void pushNode(id))
  browser.bookmarks.onRemoved.addListener((_id, info) => {
    void push(() => incrementalSync([], collectBookmarkIds(info.node)))
  })
})

/** A bookmark changed. If it's a folder, its children's paths changed too, so resync everything. */
async function pushNode(id: string) {
  const item = await itemForNode(id).catch(() => null)
  if (item) await push(() => incrementalSync([item], []))
  else await safeFullSync()
}

async function push(send: () => Promise<void>) {
  if (!(await getSettings())?.token) return // not connected yet
  try {
    await send()
  } catch {
    // Try again with a full sync in 5 minutes (alarms survive the worker being stopped).
    browser.alarms.create(RETRY_ALARM, { delayInMinutes: 5 })
  }
}

async function safeFullSync() {
  await push(fullSync)
}
