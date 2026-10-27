import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Bookmark } from '../api/types'
import SiteIcon from './SiteIcon'

// One row of the reading list (design board Main.dc.html): meta line, Aleo title, then the
// page's state, with the reading time on the right. No images (owner's decision).
//
// Not here yet: the Summarise button and summaries (next Phase 2 step) and the "⋯" row menu.
// No source/trust labels: the owner decided every summary and description looks the same.

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' })

export default function BookmarkCard({ bookmark }: { bookmark: Bookmark }) {
  const folders = [...new Set(bookmark.sources.map((s) => s.folder_path).filter(Boolean))]
  const browsers = [...new Set(bookmark.sources.map((s) => s.browser))]
  const meta = [bookmark.site, folders.join(', '), browsers.map(capitalize).join(', '), age(bookmark.added_at)]

  return (
    <article
      className={`flex gap-5 rounded-xl border border-line bg-surface px-5 py-[18px] ${bookmark.read_state === 'read' ? 'opacity-70' : ''}`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 text-[13px] text-ink2">
          <SiteIcon iconUrl={bookmark.icon_url} site={bookmark.site} />
          {meta.filter(Boolean).map((part, i) => (
            <span key={i} className="flex items-center gap-2">
              {i > 0 && <span aria-hidden>·</span>}
              {part}
            </span>
          ))}
        </div>

        <a
          href={bookmark.url}
          target="_blank"
          rel="noreferrer"
          className="font-serif text-[21px] leading-[1.25] font-bold text-ink no-underline hover:underline"
        >
          {bookmark.title}
        </a>

        <PageState bookmark={bookmark} />
      </div>

      <div className="flex flex-none flex-col items-end justify-end">
        {bookmark.reading_minutes && (
          <span className="text-[13px] whitespace-nowrap text-ink2">{bookmark.reading_minutes} min read</span>
        )}
      </div>
    </article>
  )
}

// One 14 px line under the title with a small stroke icon (design board RowStates.dc.html).
function PageState({ bookmark }: { bookmark: Bookmark }) {
  if (bookmark.status === 'pending') {
    return (
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1.5 rounded-full bg-accent2 px-2.5 py-[3px] text-[13px] font-medium whitespace-nowrap text-on-accent">
          <Icon className="animate-spin">
            <path d="M12 3a9 9 0 1 0 9 9" />
          </Icon>
          Fetching page…
        </span>
        <span aria-hidden className="h-2.5 max-w-[420px] flex-1 rounded bg-skeleton" />
      </div>
    )
  }

  if (bookmark.status === 'dead') return <DeadLink bookmark={bookmark} />

  if (bookmark.access) {
    return (
      <StateLine icon={LOCK}>{bookmark.access === 'paywall' ? 'Subscribers only' : 'Needs sign-in'}</StateLine>
    )
  }

  if (bookmark.status === 'failed') {
    return <StateLine icon={FILE}>Couldn't read this page</StateLine>
  }

  // Readable page (from the live page or an archive.org copy).
  return bookmark.content_source === 'archive' && bookmark.archive_url ? <ArchiveLink bookmark={bookmark} /> : null
}

/**
 * Dead links (RowStates board, "Dead links" group). The Wayback Machine is only asked when the
 * user clicks "Find archived copy": never → checking → found (link appended) / none / failed.
 */
function DeadLink({ bookmark }: { bookmark: Bookmark }) {
  const queryClient = useQueryClient()
  const lookUp = useMutation({
    mutationFn: () => api.post<Bookmark>(`/api/bookmarks/${bookmark.id}/find-archive`),
    // Refetch so the row shows "Checking…"; the feed then polls until the lookup finishes.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bookmarks'] }),
  })
  const state = lookUp.isPending ? 'checking' : bookmark.archive_status
  const found = state === 'found' && bookmark.archive_url

  return (
    <div className="flex flex-col items-start gap-2">
      <p className="m-0 text-sm font-semibold text-dead-fg">
        Page no longer available{bookmark.http_status ? ` (${bookmark.http_status})` : ''}.
        {found && (
          <>
            {' · '}
            <ArchiveLink bookmark={bookmark} inline />
          </>
        )}
      </p>

      {state === null && (
        <RowButton icon={HISTORY} onClick={() => lookUp.mutate()}>
          Find archived copy
        </RowButton>
      )}
      {state === 'checking' && (
        <span className="flex items-center gap-1.5 rounded-full bg-accent2 px-2.5 py-[3px] text-[13px] font-medium text-on-accent">
          <Icon className="animate-spin">
            <path d="M12 3a9 9 0 1 0 9 9" />
          </Icon>
          Checking the Wayback Machine…
        </span>
      )}
      {state === 'none' && <p className="m-0 text-sm text-ink2">No archived copy on the Wayback Machine.</p>}
      {(state === 'failed' || lookUp.isError) && (
        <div className="flex flex-wrap items-center gap-3">
          <p className="m-0 text-sm text-ink2">Couldn't reach the Wayback Machine.</p>
          <RowButton onClick={() => lookUp.mutate()}>Try again</RowButton>
        </div>
      )}
    </div>
  )
}

/** The 36 px outlined row action (Summarise, Find archived copy, Try again). */
function RowButton(props: { icon?: React.ReactNode; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      className="flex h-9 cursor-pointer items-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink hover:bg-skeleton"
    >
      {props.icon && <Icon>{props.icon}</Icon>}
      {props.children}
    </button>
  )
}

function StateLine({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <p className="m-0 flex items-center gap-1.5 text-sm font-medium text-ink2">
      <Icon>{icon}</Icon>
      {children}
    </p>
  )
}

function ArchiveLink({ bookmark, inline = false }: { bookmark: Bookmark; inline?: boolean }) {
  return (
    <a
      href={bookmark.archive_url!}
      target="_blank"
      rel="noreferrer"
      className={
        inline
          ? 'text-inherit underline'
          : 'flex w-fit items-center gap-1.5 text-sm font-medium text-ink2 underline'
      }
    >
      {!inline && <Icon>{BROKEN_LINK}</Icon>}
      Archived copy{bookmark.archived_on && ` · ${dateFormat.format(new Date(bookmark.archived_on))}`}
    </a>
  )
}

function Icon({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <svg aria-hidden width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={`flex-none ${className}`}>
      {children}
    </svg>
  )
}

const HISTORY = (
  <>
    <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
    <path d="M3 3v5h5" />
    <path d="M12 7v5l3 2" />
  </>
)
const LOCK = (
  <>
    <rect x="5" y="11" width="14" height="9" rx="2" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
  </>
)
const FILE = (
  <>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5" />
  </>
)
const BROKEN_LINK = (
  <>
    <path d="M9 17H7a5 5 0 0 1 0-10h2" />
    <path d="M15 7h2a5 5 0 0 1 4 8" />
    <path d="M8 12h3" />
    <path d="m3 3 18 18" />
  </>
)

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/** "just now", "5 min ago", "3 h ago", "2d ago", "3w ago", "4mo ago", then a date. */
function age(iso: string) {
  const minutes = (Date.now() - new Date(iso).getTime()) / 60_000
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${Math.floor(minutes)} min ago`
  const hours = minutes / 60
  if (hours < 24) return `${Math.floor(hours)} h ago`
  const days = hours / 24
  if (days < 7) return `${Math.floor(days)}d ago`
  if (days < 30) return `${Math.floor(days / 7)}w ago`
  if (days < 365) return `${Math.floor(days / 30)}mo ago`
  return dateFormat.format(new Date(iso))
}
