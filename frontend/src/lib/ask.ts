import { useSyncExternalStore } from 'react'
import { API_URL, ApiError } from '../api/client'
import type { ChatSources } from '../api/types'

// Talking to POST /api/chat (backend app/api/chat.py). The answer comes back as Server-Sent
// Events while the agent works: the browser's EventSource only does GET, so this reads the
// stream from fetch, event by event. Aborting the signal (Stop) closes the connection, and the
// server stops the agent.

export type ChatStep =
  | { id: string; status: 'running'; tool: string; args: Record<string, unknown> }
  | { id: string; status: 'done'; found: number; title?: string }

export type ChatEvent =
  | { kind: 'chat'; data: { chat_id: string } }
  | { kind: 'step'; data: ChatStep }
  | { kind: 'token'; data: { text: string } }
  | { kind: 'done'; data: ChatSources }
  | { kind: 'error'; data: { reason: 'busy'; message: string } }

export async function streamChat(
  body: { message: string; chat_id: string | null },
  onEvent: (event: ChatEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) {
    const detail = await res
      .json()
      .then((data) => data.detail)
      .catch(() => res.statusText)
    throw new ApiError(res.status, typeof detail === 'string' ? detail : res.statusText)
  }

  // Events are "event: <kind>\ndata: <json>" blocks ending in a blank line; a block can arrive
  // split across chunks, so keep what's left over until the rest comes.
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) return
    buffer += value
    let end
    while ((end = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, end)
      buffer = buffer.slice(end + 2)
      const kind = block.match(/^event: (.*)$/m)?.[1]
      const data = block.match(/^data: (.*)$/m)?.[1]
      if (kind && data) onEvent({ kind, data: JSON.parse(data) } as ChatEvent)
    }
  }
}

// From sending a question until the answer starts to appear, the top-bar logo plays
// "Conversation" (useLogoMotion). The page sets it; the logo reads it.
let waiting = false
const listeners = new Set<() => void>()

export function setAskWaiting(value: boolean) {
  if (value === waiting) return
  waiting = value
  listeners.forEach((listener) => listener())
}

export function useAskWaiting() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    () => waiting,
  )
}
