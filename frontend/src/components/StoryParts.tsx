import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Bookmark } from '../api/types'
import { formatDate } from '../lib/format'
import { ProgressPill, RowButton } from './RowButton'

// What we could get from a story's page, as one 14 px line under its headline with a small
// stroke icon (design board Story states, "Page" and "Dead links" sheets). Shared by every
// newspaper story, in the feed and in the Needs sign-in / Dead links sheets.

export function PageState({ bookmark }: { bookmark: Bookmark }) {
  if (bookmark.status === 'pending') return <ProgressPill>Fetching page…</ProgressPill>

  if (bookmark.status === 'dead') return <DeadLink bookmark={bookmark} />

  if (bookmark.access) {
    return <StateLine icon={LOCK}>{bookmark.access === 'paywall' ? 'Subscribers only' : 'Needs sign-in'}</StateLine>
  }

  if (bookmark.status === 'failed') return <StateLine icon={UNREADABLE}>Couldn't read this page</StateLine>

  // A readable page we could only get from archive.org (the live one blocked us).
  if (bookmark.content_source === 'archive' && bookmark.archive_url) {
    return (
      <StateLine icon={HISTORY}>
        <ArchiveLink bookmark={bookmark} />
      </StateLine>
    )
  }
  return null
}

/**
 * Dead links. The Wayback Machine is only asked when the user clicks "Find archived copy":
 * not looked up → checking → copy found (link after the dead line, and Summarise appears) /
 * no copy / couldn't reach it (+ Try again).
 */
function DeadLink({ bookmark }: { bookmark: Bookmark }) {
  const queryClient = useQueryClient()
  const lookUp = useMutation({
    // The top-bar logo shows the Hourglass while any of these is on its way (useLogoMotion).
    mutationKey: ['find-archive'],
    mutationFn: () => api.post<Bookmark>(`/api/bookmarks/${bookmark.id}/find-archive`),
    // Refetch so the story shows "Checking…"; the feed then polls until the lookup finishes.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bookmarks'] }),
  })
  const state = lookUp.isPending ? 'checking' : bookmark.archive_status
  const found = state === 'found' && bookmark.archive_url

  return (
    <>
      <p className="m-0 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-dead-fg">
        <StateIcon>{DEAD}</StateIcon>
        <span className="font-semibold">
          Page no longer available{bookmark.http_status ? ` (${bookmark.http_status})` : ''}.
        </span>
        {found && <ArchiveLink bookmark={bookmark} />}
      </p>

      {state === null && (
        <RowButton icon={HISTORY} onClick={() => lookUp.mutate()} label={`Find an archived copy of ${bookmark.title}`}>
          Find archived copy
        </RowButton>
      )}
      {state === 'checking' && <ProgressPill bar={false}>Checking the Wayback Machine…</ProgressPill>}
      {state === 'none' && (
        <p role="status" className="m-0 text-sm text-ink2">
          No archived copy on the Wayback Machine.
        </p>
      )}
      {(state === 'failed' || lookUp.isError) && (
        <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <span className="text-sm text-ink2">Couldn't reach the Wayback Machine.</span>
          <RowButton onClick={() => lookUp.mutate()} label="Try the Wayback Machine again">
            Try again
          </RowButton>
        </div>
      )}
    </>
  )
}

function StateLine({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <p className="m-0 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink2">
      <StateIcon>{icon}</StateIcon>
      <span className="font-medium">{children}</span>
    </p>
  )
}

function StateIcon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      aria-hidden
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="flex-none"
    >
      {children}
    </svg>
  )
}

function ArchiveLink({ bookmark }: { bookmark: Bookmark }) {
  return (
    <a href={bookmark.archive_url!} target="_blank" rel="noreferrer" className="text-inherit underline">
      Archived copy{bookmark.archived_on && ` · ${formatDate(bookmark.archived_on)}`}
    </a>
  )
}

const HISTORY = (
  <>
    <path d="M3 12a9 9 0 1 0 3-6.7" />
    <path d="M3 4v5h5" />
    <path d="M12 8v4l3 2" />
  </>
)
const LOCK = (
  <>
    <rect x="5" y="11" width="14" height="10" rx="2" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
  </>
)
const UNREADABLE = (
  <>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5" />
    <path d="m9.5 12.5 5 5" />
    <path d="m14.5 12.5-5 5" />
  </>
)
const DEAD = (
  <>
    <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-.6.6" />
    <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l.6-.6" />
    <path d="M4 4l16 16" />
  </>
)
