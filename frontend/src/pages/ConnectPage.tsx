import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api } from '../api/client'
import type { CreatedApiToken, SyncSummary } from '../api/types'
import { LogoPair, PinTip, PrivacyNote, StepStrip } from '../components/ConnectParts'
import SignInButtons from '../components/SignInButtons'
import SiteIcon from '../components/SiteIcon'
import StatePage, { SlidingBar, StateText } from '../components/StatePage'
import { ICONS, stateAction } from '../components/statePageParts'

// Opened by the extension's "Connect this browser" button (design board ConnectStates): it
// connects on its own, shows bookmarks arriving during the first sync, then a summary with a
// button to open the feed (it doesn't jump there by itself).
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
  const queryClient = useQueryClient()

  // What this browser has sent so far: polled during the first sync ("Just arrived"), then
  // fetched once more for the Done summary.
  const summary = useQuery({
    queryKey: ['sync-summary', browser],
    queryFn: () => api.get<SyncSummary>(`/api/bookmarks/sync-summary?browser=${encodeURIComponent(browser!)}`),
    enabled: Boolean(browser) && (status === 'syncing' || status === 'done'),
    refetchInterval: status === 'syncing' ? 1500 : false,
  })

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
          // Drop any cached (empty) feed so it's fresh when opened, and get the final counts.
          void queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
          void queryClient.invalidateQueries({ queryKey: ['facets'] })
          void queryClient.invalidateQueries({ queryKey: ['sync-summary'] })
          setStatus('done')
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
  }, [nonce, queryClient])

  const note = <PrivacyNote />
  const progress = (step: 1 | 2 | 3, line: 'connecting' | 'syncing' | 'done') => (
    <>
      <StepStrip current={step} />
      <LogoPair browser={browser} state={line} />
    </>
  )

  if (!nonce) {
    return (
      <StatePage icon={ICONS.link} title="Connect from the extension" note={note}>
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
        <StatePage header={progress(1, 'connecting')} title={`Connecting ${name}…`} note={note}>
          <StateText>Keep this tab open. It only takes a few seconds.</StateText>
        </StatePage>
      )
    case 'syncing': {
      const s = summary.data
      return (
        <StatePage header={progress(2, 'syncing')} title="Syncing your bookmarks" note={note}>
          <StateText>
            {s && s.bookmarks > 0 && `${countLabel(s.bookmarks, 'bookmark')} in ${countLabel(s.folders, 'folder')} so far. `}
            Keep this tab open until it finishes.
          </StateText>
          <SlidingBar />
          {s && s.just_arrived.length > 0 && <JustArrived items={s.just_arrived} />}
        </StatePage>
      )
    }
    case 'done': {
      const s = summary.data
      return (
        <StatePage header={progress(3, 'done')} title={`${Name} is connected`} note={note}>
          {s && (
            <div className="flex gap-2.5">
              <StatTile value={s.bookmarks} label={s.bookmarks === 1 ? 'bookmark' : 'bookmarks'} />
              <StatTile value={s.folders} label={s.folders === 1 ? 'folder' : 'folders'} />
            </div>
          )}
          {s && s.other_browsers.length > 0 && (
            <StateText>
              <strong className="font-semibold text-ink">Also connected:</strong>{' '}
              {s.other_browsers.map((b) => browserNames(b).Name).join(', ')}. Links saved in more than one browser
              show up once.
            </StateText>
          )}
          <StateText>
            Pages are read in the background, and summaries come when you click <em>Summarise</em>.
          </StateText>
          <PinTip />
          <div className="flex flex-wrap items-center gap-x-[18px] gap-y-2">
            <Link to="/" replace className={stateAction}>
              Open your feed
            </Link>
            <Link to="/settings" className="font-medium text-ink underline underline-offset-[3px]">
              Connect another browser
            </Link>
          </div>
        </StatePage>
      )
    }
    case 'no-reply':
      return (
        <StatePage icon={ICONS.key} title="Connect by hand" note={note}>
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
        <StatePage icon={ICONS.clock} title="This link has expired" note={note}>
          <StateText>Connect links last 15 minutes. Open the extension and click Connect this browser again.</StateText>
        </StatePage>
      )
    case 'sync-failed':
      return (
        <StatePage icon={ICONS.alert} title="Connected, but the first sync failed" note={note}>
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
        <StatePage icon={ICONS.alert} title="Something went wrong" note={note}>
          <StateText>We couldn't connect {name}. Your bookmarks are safe.</StateText>
          <button type="button" onClick={() => void connect(true)} className={stateAction}>
            Try again
          </button>
        </StatePage>
      )
  }
}

function countLabel(n: number, word: string) {
  return `${n} ${n === 1 ? word : `${word}s`}`
}

/** The newest few bookmarks to arrive; the last one fades, as more are on the way. */
function JustArrived({ items }: { items: SyncSummary['just_arrived'] }) {
  return (
    <div>
      <p className="mt-1 mb-0.5 text-[13px] font-semibold text-ink2">Just arrived</p>
      <ul aria-live="polite" className="m-0 list-none border-t border-line p-0">
        {items.map((b, i) => (
          <li
            key={`${b.site}-${b.title}`}
            className={`flex items-center gap-2.5 border-b border-line py-2 ${i === 3 ? 'opacity-55' : ''}`}
          >
            <SiteIcon iconUrl={b.icon_url} site={b.site} />
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-sm font-medium">{b.title}</span>
              <span className="text-[13px] text-muted">{b.site}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function StatTile({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex-1 rounded-xl border border-line bg-panel px-3.5 py-2.5">
      <div className="font-serif text-[26px] leading-[1.15] font-bold">{value}</div>
      <div className="text-[13px] text-ink2">{label}</div>
    </div>
  )
}

/** Signed out when the extension opened this page: sign in first, then it connects. */
export function ConnectSignedOutPage() {
  const [params] = useSearchParams()
  const { name } = browserNames(params.get('browser'))
  return (
    <StatePage icon={ICONS.person} title={`Sign in to connect ${name}`} note={<PrivacyNote />}>
      <StateText>Sign in first; we'll connect this browser right after.</StateText>
      <SignInButtons />
    </StatePage>
  )
}
