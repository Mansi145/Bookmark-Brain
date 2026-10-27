import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { api } from '../api/client'
import type { Bookmark } from '../api/types'
import { useSummarise } from '../hooks/useSummarise'
import { useUsage } from '../hooks/useUsage'
import { age, capitalize } from '../lib/format'
import { LEAVE_MS, updateCachedBookmark } from '../lib/cache'
import { canSummarise } from '../lib/summaries'
import SiteIcon from './SiteIcon'
import { SummariseAction } from './Summarise'

// Bookmark detail (design board FeedDetail): a 480 px panel from the right over a dark
// backdrop (full screen on phones). Close button; site; title; when it was saved; Open page,
// Mark as read, Re-summarise; the summary and key points; where it's saved and the full URL.
// The design's Tags section waits for tagging (Phase 5).

export default function BookmarkDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const close = useRef<HTMLButtonElement>(null)
  const bookmark = useQuery({
    // Under 'bookmarks', so anything that refreshes the feed refreshes this too.
    queryKey: ['bookmarks', 'one', id],
    queryFn: () => api.get<Bookmark>(`/api/bookmarks/${id}`),
    refetchInterval: (query) => (query.state.data?.summary_status === 'working' ? 2000 : false),
  })

  // Escape closes; focus starts on the close button so keyboard users land in the panel.
  // onClose is new on every feed render (it polls), so keep the latest in a ref and set this
  // up once, or focus would jump back to the close button every few seconds.
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  })
  useEffect(() => {
    close.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCloseRef.current()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div className="fixed inset-0 z-30">
      <div aria-hidden className="absolute inset-0 bg-[rgba(20,21,22,0.35)]" onClick={onClose} />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
        className="absolute inset-y-0 right-0 flex w-full flex-col gap-5 overflow-auto bg-panel px-7 pt-6 pb-10 text-ink shadow-[-24px_0_60px_rgba(0,0,0,0.25)] sm:w-[480px]"
      >
        <div className="flex items-center justify-between gap-3">
          {bookmark.data ? <SiteLine bookmark={bookmark.data} /> : <span />}
          <button
            ref={close}
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="grid size-10 flex-none cursor-pointer place-items-center rounded-full border border-line bg-surface text-ink"
          >
            <svg
              aria-hidden
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
            >
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>

        {bookmark.isError && <p className="text-dead-fg">Couldn't load this bookmark.</p>}
        {bookmark.data && <Details bookmark={bookmark.data} />}
      </aside>
    </div>
  )
}

function SiteLine({ bookmark }: { bookmark: Bookmark }) {
  const folders = [...new Set(bookmark.sources.map((s) => s.folder_path).filter(Boolean))]
  const browsers = [...new Set(bookmark.sources.map((s) => capitalize(s.browser)))]
  return (
    <div className="flex min-w-0 items-center gap-2 text-[13px] text-ink2">
      <SiteIcon iconUrl={bookmark.icon_url} site={bookmark.site} />
      <span className="truncate">
        {[bookmark.site, folders.join(', '), browsers.join(', ')].filter(Boolean).join(' · ')}
      </span>
    </div>
  )
}

function Details({ bookmark }: { bookmark: Bookmark }) {
  const saved = [`Saved ${age(bookmark.added_at)}`, bookmark.reading_minutes && `${bookmark.reading_minutes} min read`]
  return (
    <>
      <div className="flex flex-col gap-3">
        <h2 id="detail-title" className="font-serif text-[30px] leading-[1.15] font-bold">
          {bookmark.title}
        </h2>
        <p className="-mt-1 text-[13px] text-ink2">{saved.filter(Boolean).join(' · ')}</p>
      </div>

      <Actions bookmark={bookmark} />

      {canSummarise(bookmark) && (
        <section aria-labelledby="detail-summary" className="rounded-xl border border-line bg-surface px-5 py-[18px]">
          <Heading id="detail-summary">Summary</Heading>
          {bookmark.summary_status === 'done' && bookmark.summary ? (
            <>
              <p className="mt-2">{bookmark.summary}</p>
              {bookmark.key_points.length > 0 && (
                <>
                  <Heading className="mt-4">Key points</Heading>
                  <ul className="mt-2 flex flex-col gap-1.5 pl-5 text-ink2">
                    {bookmark.key_points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <div className="mt-2 flex flex-col gap-3">
              {bookmark.description && (
                <>
                  <p className="text-ink2">{bookmark.description}</p>
                  <p className="text-[13px] text-muted">
                    The site's own description. Summarise to get a short summary and key points.
                  </p>
                </>
              )}
              <SummariseAction bookmark={bookmark} />
            </div>
          )}
        </section>
      )}

      <section aria-labelledby="detail-info" className="text-[13px] text-ink2">
        <Heading id="detail-info" className="mb-2">
          Details
        </Heading>
        <div>{savedIn(bookmark)}</div>
        <div className="break-all">{bookmark.url}</div>
      </section>
    </>
  )
}

function Actions({ bookmark }: { bookmark: Bookmark }) {
  const queryClient = useQueryClient()
  const read = bookmark.read_state === 'read'
  const markRead = useMutation({
    mutationFn: () => api.patch<Bookmark>(`/api/bookmarks/${bookmark.id}`, { read_state: read ? 'unread' : 'read' }),
    // Show it at once: in the Unread (or Read) view the story fades out, then the feed and
    // the Unread / Read counts refresh and it moves to the other view.
    onSuccess: (updated) => {
      updateCachedBookmark(queryClient, updated)
      window.setTimeout(() => {
        void queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
        void queryClient.invalidateQueries({ queryKey: ['facets'] })
      }, LEAVE_MS)
    },
  })
  const summarise = useSummarise(bookmark.id)
  const { limitReached } = useUsage()
  const outline =
    'flex h-10 cursor-pointer items-center rounded-[10px] border border-line bg-surface px-3.5 font-medium text-ink disabled:cursor-default disabled:opacity-50'

  return (
    <div className="flex flex-wrap gap-2">
      <a
        href={bookmark.url}
        target="_blank"
        rel="noreferrer"
        className="flex h-10 items-center gap-2 rounded-[10px] bg-ink px-4 font-semibold text-on-ink no-underline"
      >
        Open page
        <svg
          aria-hidden
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M7 17 17 7M9 7h8v8" />
        </svg>
      </a>
      <button type="button" onClick={() => markRead.mutate()} disabled={markRead.isPending} className={outline}>
        {read ? 'Mark as unread' : 'Mark as read'}
      </button>
      {bookmark.summary_status === 'done' && canSummarise(bookmark) && (
        <button
          type="button"
          onClick={() => summarise.mutate(true)}
          disabled={summarise.isPending || limitReached}
          title={limitReached ? 'Daily summary limit reached · resets at midnight UTC' : undefined}
          className={outline}
        >
          Re-summarise
        </button>
      )}
    </div>
  )
}

function Heading(props: { id?: string; className?: string; children: React.ReactNode }) {
  return (
    <h3
      id={props.id}
      className={`text-xs font-semibold tracking-[0.06em] text-ink2 uppercase ${props.className ?? ''}`}
    >
      {props.children}
    </h3>
  )
}

/** "Saved in Chrome (Reading/Databases) and Edge (Reading)". */
function savedIn(bookmark: Bookmark) {
  const byBrowser = new Map<string, string[]>()
  for (const s of bookmark.sources) {
    const folders = byBrowser.get(s.browser) ?? []
    if (s.folder_path && !folders.includes(s.folder_path)) folders.push(s.folder_path)
    byBrowser.set(s.browser, folders)
  }
  const parts = [...byBrowser].map(([browser, folders]) =>
    folders.length ? `${capitalize(browser)} (${folders.join(', ')})` : capitalize(browser),
  )
  const list = parts.length > 1 ? `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}` : parts[0]
  return `Saved in ${list}`
}
