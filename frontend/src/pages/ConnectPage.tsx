import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { api } from '../api/client'
import type { CreatedApiToken } from '../api/types'

// Must match extension/lib/connect.ts (MSG).
const MSG = {
  ping: 'bookmark-brain:ping',
  ready: 'bookmark-brain:extension-ready',
  connect: 'bookmark-brain:connect',
  connected: 'bookmark-brain:connected',
  rejected: 'bookmark-brain:connect-rejected',
  synced: 'bookmark-brain:synced',
} as const

// 'syncing': the extension has the token and is uploading bookmarks; we wait for MSG.synced.
type Status = 'idle' | 'connecting' | 'syncing' | 'sync-failed' | 'rejected' | 'no-reply' | 'error'

const browserLabel = (b: string | null) =>
  b ? b.charAt(0).toUpperCase() + b.slice(1) : 'This browser'

/**
 * Opened by the extension's "Connect" button. Creates a token and hands it to the
 * extension's content script with window.postMessage (same page, same origin only).
 */
export default function ConnectPage() {
  const [params] = useSearchParams()
  const nonce = params.get('nonce')
  const browserName = browserLabel(params.get('browser'))

  const [extensionReady, setExtensionReady] = useState(false)
  const [status, setStatus] = useState<Status>('idle')
  const [fallbackToken, setFallbackToken] = useState<string | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)
  const timeout = useRef<number | undefined>(undefined)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.source !== window || event.origin !== window.location.origin) return
      const type = event.data?.type
      if (type === MSG.ready) setExtensionReady(true)
      if (type === MSG.connected && event.data.nonce === nonce) {
        window.clearTimeout(timeout.current)
        setStatus('syncing')
      }
      if (type === MSG.synced && event.data.nonce === nonce) {
        if (event.data.ok) {
          // Drop any cached (empty) feed so it's fetched fresh, then show it in this tab.
          void queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
          void queryClient.invalidateQueries({ queryKey: ['facets'] })
          navigate('/', { replace: true })
        } else {
          setSyncError(String(event.data.error ?? 'Unknown error'))
          setStatus('sync-failed')
        }
      }
      if (type === MSG.rejected && event.data.nonce === nonce) {
        window.clearTimeout(timeout.current)
        setStatus('rejected')
      }
    }
    window.addEventListener('message', onMessage)
    // The content script may have loaded before React; ask it to say hello again.
    window.postMessage({ type: MSG.ping }, window.location.origin)
    return () => {
      window.removeEventListener('message', onMessage)
      window.clearTimeout(timeout.current)
    }
  }, [nonce, navigate, queryClient])

  async function connect() {
    setStatus('connecting')
    try {
      const created = await api.post<CreatedApiToken>('/api/tokens', { name: `${browserName} extension` })
      window.postMessage({ type: MSG.connect, token: created.token, nonce }, window.location.origin)
      // No answer from the extension: show the token so it can still be pasted by hand.
      timeout.current = window.setTimeout(() => {
        setFallbackToken(created.token)
        setStatus('no-reply')
      }, 4000)
    } catch {
      setStatus('error')
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 py-16">
      <div className="rounded-2xl border border-stone-200 bg-white p-8">
        <h1 className="text-2xl font-bold">Connect {browserName}</h1>

        {!nonce && (
          <p className="mt-3 text-sm text-stone-600">
            Open this page from the Bookmark Brain extension: click its icon, then <strong>Connect this browser</strong>.
          </p>
        )}

        {nonce && status === 'idle' && (
          <>
            <p className="mt-3 text-stone-600">
              The extension will sync this browser's bookmarks to your account. You can disconnect it any time from
              Settings.
            </p>
            {!extensionReady && (
              <p className="mt-3 text-sm text-amber-700">Looking for the extension in this browser…</p>
            )}
            <button
              onClick={connect}
              className="mt-6 w-full rounded-lg bg-stone-900 px-4 py-3 font-medium text-white disabled:opacity-50"
            >
              Connect this browser
            </button>
          </>
        )}

        {status === 'connecting' && <p className="mt-4 text-stone-600">Connecting…</p>}

        {status === 'syncing' && (
          <div role="status" className="mt-6 flex items-center gap-3 text-stone-700">
            <span
              aria-hidden
              className="size-5 animate-spin rounded-full border-2 border-stone-300 border-t-stone-900"
            />
            <span>Connected. Syncing your bookmarks…</span>
          </div>
        )}

        {status === 'sync-failed' && (
          <div role="alert" className="mt-4 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-medium">Connected, but the first sync failed.</p>
            <p className="mt-1">{syncError}</p>
            <p className="mt-1">
              The extension will retry in a few minutes, or you can click <em>Sync now</em> in its popup.{' '}
              <Link to="/" className="underline">
                Go to your feed
              </Link>
            </p>
          </div>
        )}

        {status === 'rejected' && (
          <p role="alert" className="mt-4 rounded-lg bg-red-50 p-4 text-red-800">
            This connect link has expired or was already used. Click <strong>Connect</strong> in the extension again.
          </p>
        )}

        {status === 'no-reply' && fallbackToken && (
          <div role="alert" className="mt-4 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-medium">The extension didn't respond.</p>
            <p className="mt-1">
              Open the extension, choose <em>Advanced: paste a token</em>, and paste this token (shown once):
            </p>
            <code className="mt-2 block break-all rounded bg-white px-2 py-1">{fallbackToken}</code>
          </div>
        )}

        {status === 'error' && (
          <p role="alert" className="mt-4 text-red-700">
            Couldn't create a token. Check that the API is running and try again.
          </p>
        )}
      </div>
    </main>
  )
}
