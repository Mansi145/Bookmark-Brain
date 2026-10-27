import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router'
import { api } from '../api/client'
import type { Bookmark } from '../api/types'
import { age, capitalize, formatDate } from '../lib/format'
import { canSummarise } from '../lib/summaries'
import { Icon, ProgressPill, RowButton } from './RowButton'
import SiteIcon from './SiteIcon'
import { SummariseAction, SummaryText } from './Summarise'

// One row of the reading list (design board Main.dc.html): meta line, Aleo title (opens the
// detail panel), the page's state, the summary or Summarise, and the reading time on the
// right. No images and no source/trust labels (owner's decisions).
//
// Not here yet: the row "⋯" menu.

export default function BookmarkCard({ bookmark }: { bookmark: Bookmark }) {
  const [params] = useSearchParams()
  const folders = [...new Set(bookmark.sources.map((s) => s.folder_path).filter(Boolean))]
  const browsers = [...new Set(bookmark.sources.map((s) => s.browser))]
  const meta = [bookmark.site, folders.join(', '), browsers.map(capitalize).join(', '), age(bookmark.added_at)]

  // The detail panel is part of the address (?bookmark=), so Back closes it.
  const detail = new URLSearchParams(params)
  detail.set('bookmark', String(bookmark.id))

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

        <Link
          to={{ search: detail.toString() }}
          className="font-serif text-[21px] leading-[1.25] font-bold text-ink no-underline hover:underline"
        >
          {bookmark.title}
        </Link>

        <PageState bookmark={bookmark} />
        <SummaryText bookmark={bookmark} />
        {canSummarise(bookmark) && <SummariseAction bookmark={bookmark} />}
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
  if (bookmark.status === 'pending') return <ProgressPill>Fetching page…</ProgressPill>

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
 * Once a copy is found, the row's Summarise button summarises that copy.
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
      {state === 'checking' && <ProgressPill bar={false}>Checking the Wayback Machine…</ProgressPill>}
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
      Archived copy{bookmark.archived_on && ` · ${formatDate(bookmark.archived_on)}`}
    </a>
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
