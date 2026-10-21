// Reads bookmarks from the browser and sends them to the Bookmark Brain API.
// Shared by the background worker (automatic syncs) and the popup ("Sync now").

import { browser, type Browser } from 'wxt/browser'

type BookmarkNode = Browser.bookmarks.BookmarkTreeNode

export type Settings = { apiUrl: string; token: string }
export type SyncStatus = { at: string; ok: boolean; message: string }

type SyncItem = {
  node_id: string
  url: string
  title: string
  folder_path: string
  added_at: string
}

export const DEFAULT_API_URL = 'http://localhost:8000'

// --- Stored state -----------------------------------------------------------

export async function getSettings(): Promise<Settings | null> {
  const { settings } = await browser.storage.local.get('settings')
  return (settings as Settings | undefined) ?? null
}

export async function saveSettings(settings: Settings): Promise<void> {
  await browser.storage.local.set({ settings })
}

export async function getStatus(): Promise<SyncStatus | null> {
  const { status } = await browser.storage.local.get('status')
  return (status as SyncStatus | undefined) ?? null
}

async function setStatus(ok: boolean, message: string): Promise<void> {
  await browser.storage.local.set({ status: { at: new Date().toISOString(), ok, message } })
}

/** A random id per install, so two Chrome profiles count as two sources. */
async function getSourceId(): Promise<string> {
  const { sourceId } = await browser.storage.local.get('sourceId')
  if (typeof sourceId === 'string') return sourceId
  const id = crypto.randomUUID()
  await browser.storage.local.set({ sourceId: id })
  return id
}

function detectBrowser(): string {
  if (import.meta.env.FIREFOX) return 'firefox'
  const nav = navigator as Navigator & {
    brave?: unknown
    userAgentData?: { brands: { brand: string }[] }
  }
  const brands = nav.userAgentData?.brands.map((b) => b.brand).join(' ') ?? navigator.userAgent
  if (brands.includes('Edge') || navigator.userAgent.includes('Edg/')) return 'edge'
  if (nav.brave) return 'brave'
  if (brands.includes('Opera') || navigator.userAgent.includes('OPR/')) return 'opera'
  return 'chrome'
}

// --- Reading the bookmark tree ----------------------------------------------

function toItem(node: BookmarkNode, folderPath: string): SyncItem {
  return {
    node_id: node.id,
    url: node.url!,
    title: node.title,
    folder_path: folderPath,
    added_at: new Date(node.dateAdded ?? Date.now()).toISOString(),
  }
}

/** Every bookmark (not folder) under `nodes`, with its folder path. */
function flatten(nodes: BookmarkNode[], path: string[] = []): SyncItem[] {
  return nodes.flatMap((node) => {
    if (node.url) return [toItem(node, path.join('/'))]
    // The invisible root has an empty title; don't put it in paths.
    const childPath = node.title ? [...path, node.title] : path
    return flatten(node.children ?? [], childPath)
  })
}

/** Ids of every bookmark inside a removed node (a removed folder takes its contents with it). */
export function collectBookmarkIds(node: BookmarkNode): string[] {
  if (node.url) return [node.id]
  return (node.children ?? []).flatMap(collectBookmarkIds)
}

async function folderPathOf(parentId: string | undefined): Promise<string> {
  const names: string[] = []
  let id = parentId
  while (id) {
    const [folder] = await browser.bookmarks.get(id)
    if (!folder) break
    if (folder.title) names.unshift(folder.title)
    id = folder.parentId
  }
  return names.join('/')
}

export async function itemForNode(nodeId: string): Promise<SyncItem | null> {
  const [node] = await browser.bookmarks.get(nodeId)
  if (!node?.url) return null
  return toItem(node, await folderPathOf(node.parentId))
}

// --- Talking to the API -----------------------------------------------------

async function post(body: object): Promise<{ active_bookmarks: number }> {
  const settings = await getSettings()
  if (!settings?.token) throw new Error('Not connected: add a token in the extension popup')

  const res = await fetch(`${settings.apiUrl.replace(/\/$/, '')}/api/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${settings.token}` },
    body: JSON.stringify({ source: { id: await getSourceId(), browser: detectBrowser() }, ...body }),
  })
  if (res.status === 401) throw new Error('Token rejected: create a new one in Settings')
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}

/** Send the whole bookmark tree. Anything the server has that isn't in it gets removed. */
export async function fullSync(): Promise<void> {
  try {
    const items = flatten(await browser.bookmarks.getTree())
    const result = await post({ full: true, upserts: items })
    await setStatus(true, `Synced ${result.active_bookmarks} bookmarks`)
  } catch (err) {
    await setStatus(false, String(err instanceof Error ? err.message : err))
    throw err
  }
}

/** Send just what changed. */
export async function incrementalSync(upserts: SyncItem[], removedNodeIds: string[]): Promise<void> {
  try {
    const result = await post({ full: false, upserts, removed_node_ids: removedNodeIds })
    await setStatus(true, `Synced ${result.active_bookmarks} bookmarks`)
  } catch (err) {
    await setStatus(false, String(err instanceof Error ? err.message : err))
    throw err
  }
}
