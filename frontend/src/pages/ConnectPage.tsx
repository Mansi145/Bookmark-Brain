import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { api } from '../api/client'
import type { CreatedApiToken, Facets } from '../api/types'
import SignInButtons from '../components/SignInButtons'
import StatePage, { SlidingBar, StateText } from '../components/StatePage'
import { ICONS, stateAction } from '../components/statePageParts'

// Opened by the extension's "Connect this browser" button (design board ConnectStates): it
// connects on its own, waits for the first sync, then opens the feed.
//
// How the token reaches the extension: the page creates it and hands it to the extension's
// content script with window.postMessage (same page, same origin only). The extension checks
// the nonce it put in the URL, so a stale or copied link is rejected.

// Must match extension/lib/connect.ts (MSG).
const MSG = {
  ping: 'bookmark-brain:ping',
  ready: 'bookmark-brain:extension-ready',
  connect: 'bookmark-brain:connect',
  connected: 'bookmark-brain:connected',
  rejected: 'bookmark-brain:connect-rejected',
  synced: 'bookmark-brain:synced',
} as const

// How long to wait for the extension to say hello, then to accept the token.
const FIND_EXTENSION_MS = 3000
const ACCEPT_TOKEN_MS = 4000
// "Connected" shows for a moment before the feed opens.
const OPEN_FEED_MS = 1500

type Status = 'connecting' | 'syncing' | 'done' | 'sync-failed' | 'expired' | 'no-reply' | 'error'

/** "Chrome" / "this browser", from ?browser= in the link the extension opened. */
function browserNames(param: string | null) {
  if (!param) return { name: 'this browser', Name: 'This browser' }
  const Name = param.charAt(0).toUpperCase() + param.slice(1)
  return { name: Name, Name }
}

export default function ConnectPage() {
  const [params] = useSearchParams()
  const nonce = params.get('nonce')
  const browser = params.get('browser')
  const { name, Name } = browserNames(browser)

  const [status, setStatus] = useState<Status>('connecting')
  const [fallbackToken, setFallbackToken] = useState<string | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)
  const started = useRef(false)
  const tokenId = useRef<number | null>(null)
  const timeout = useRef<number | undefined>(undefined)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // While the first sync runs, count what has arrived so far (polls the feed's counts).
  const counts = useQuery({
    queryKey: ['facets', 'main'],
    queryFn: () => api.get<Facets>('/api/bookmarks/facets?section=main'),
    enabled: status === 'syncing',
    refetchInterval: status === 'syncing' ? 1500 : false,
  })
  const found = browser
    ? counts.data?.browsers.find((b) => b.value === browser)?.count
    : counts.data?.total

  async function connect(extensionFound: boolean) {
    setStatus('connecting')
    try {
      const created = await api.post<CreatedApiToken>('/api/tokens', { name: `${Name} extension` })
      tokenId.current = created.id
      if (!extensionFound) {
        setFallbackToken(created.token)
        setStatus('no-reply')
        return
      }
      window.postMessage({ type: MSG.connect, token: created.token, nonce }, window.location.origin)
      // No answer from the extension: show the token so it can still be pasted by hand.
      timeout.current = window.setTimeout(() => {
        setFallbackToken(created.token)
        setStatus('no-reply')
      }, ACCEPT_TOKEN_MS)
    } catch {
      setStatus('error')
    }
  }

  useEffect(() => {
    if (!nonce) return
    // Connect once, as soon as we know whether the extension is here. (The ref also stops
    // React's development double-run from creating two tokens.)
    const begin = (extensionFound: boolean) => {
      if (started.current) return
      started.current = true
      void connect(extensionFound)
    }
    const notFound = window.setTimeout(() => begin(false), FIND_EXTENSION_MS)

    const onMessage = (event: MessageEvent) => {
      if (event.source !== window || event.origin !== window.location.origin) return
      const type = event.data?.type
      if (type === MSG.ready) begin(true)
      if (event.data?.nonce !== nonce) return
      if (type === MSG.connected) {
        window.clearTimeout(timeout.current)
        setStatus('syncing')
      }
      if (type === MSG.rejected) {
        window.clearTimeout(timeout.current)
        // The extension refused this link, so nobody will use the token we just made.
        if (tokenId.current !== null) void api.delete(`/api/tokens/${tokenId.current}`).catch(() => {})
        setStatus('expired')
      }
      if (type === MSG.synced) {
        if (event.data.ok) {
          // Drop any cached (empty) feed so it's fetched fresh, then open it in this tab.
          void queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
          void queryClient.invalidateQueries({ queryKey: ['facets'] })
          setStatus('done')
          timeout.current = window.setTimeout(() => navigate('/', { replace: true }), OPEN_FEED_MS)
        } else {
          setSyncError(String(event.data.error ?? 'Unknown error'))
          setStatus('sync-failed')
        }
      }
    }
    window.addEventListener('message', onMessage)
    // The content script may have loaded before React; ask it to say hello again.
    window.postMessage({ type: MSG.ping }, window.location.origin)
    return () => {
      window.removeEventListener('message', onMessage)
      window.clearTimeout(notFound)
      window.clearTimeout(timeout.current)
    }
    // connect() only uses refs and stable setters, so it doesn't need to be a dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, navigate, queryClient])

  if (!nonce) {
    return (
      <StatePage icon={ICONS.link} title="Connect from the extension">
        <StateText>
          Click the Bookmark Brain extension's icon, then <strong className="font-semibold text-ink">Connect this browser</strong>.
          It opens this page and connects in a few seconds.
        </StateText>
        <Link to="/settings" className={stateAction}>
          Connect by hand
        </Link>
      </StatePage>
    )
  }

  switch (status) {
    case 'connecting':
      return (
        <StatePage icon={ICONS.spinner} title={`Connecting ${name}…`}>
          <StateText>Keep this tab open. It only takes a few seconds.</StateText>
        </StatePage>
      )
    case 'syncing':
      return (
        <StatePage icon={ICONS.sync} title="Syncing your bookmarks">
          <StateText>
            {found ? `${found} ${found === 1 ? 'bookmark' : 'bookmarks'} found so far. ` : ''}
            Your feed opens as soon as this finishes.
          </StateText>
          <SlidingBar />
        </StatePage>
      )
    case 'done':
      return (
        <StatePage icon={ICONS.check} title={`${Name} is connected`}>
          <StateText>Opening your feed…</StateText>
          <Link to="/" replace className={stateAction}>
            Open feed now
          </Link>
        </StatePage>
      )
    case 'no-reply':
      return (
        <StatePage icon={ICONS.key} title="Connect by hand">
          <StateText>
            The extension didn't reply. Copy this token and paste it into the extension under{' '}
            <em>Advanced: paste a token</em>. It's only shown once.
          </StateText>
          <div className="flex flex-wrap gap-2">
            <code className="min-w-0 flex-[1_1_200px] rounded-lg border border-line bg-panel px-3 py-2.5 font-mono text-[13px] break-all">
              {fallbackToken}
            </code>
            <button
              type="button"
              onClick={() => fallbackToken && navigator.clipboard.writeText(fallbackToken)}
              className="h-11 cursor-pointer rounded-lg border-0 bg-ink px-4 font-semibold text-on-ink"
            >
              Copy
            </button>
          </div>
        </StatePage>
      )
    case 'expired':
      return (
        <StatePage icon={ICONS.clock} title="This link has expired">
          <StateText>Connect links last 15 minutes. Open the extension and click Connect this browser again.</StateText>
        </StatePage>
      )
    case 'sync-failed':
      return (
        <StatePage icon={ICONS.alert} title="Connected, but the first sync failed">
          <StateText>
            {syncError} The extension will try again in a few minutes, or you can click <em>Sync now</em> in its popup.
          </StateText>
          <Link to="/" replace className={stateAction}>
            Go to your feed
          </Link>
        </StatePage>
      )
    case 'error':
      return (
        <StatePage icon={ICONS.alert} title="Something went wrong">
          <StateText>We couldn't connect {name}. Your bookmarks are safe.</StateText>
          <button type="button" onClick={() => void connect(true)} className={stateAction}>
            Try again
          </button>
        </StatePage>
      )
  }
}

/** Signed out when the extension opened this page: sign in first, then it connects. */
export function ConnectSignedOutPage() {
  const [params] = useSearchParams()
  const { name } = browserNames(params.get('browser'))
  return (
    <StatePage icon={ICONS.person} title={`Sign in to connect ${name}`}>
      <StateText>Sign in first; we'll connect this browser right after.</StateText>
      <SignInButtons />
    </StatePage>
  )
}
