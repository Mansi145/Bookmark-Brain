import { notifyManager, useIsFetching, useIsMutating, useQueryClient } from '@tanstack/react-query'
import { useCallback, useSyncExternalStore } from 'react'
import type { Bookmark } from '../api/types'
import type { LogoMotion } from '../components/Logo'
import { shownBookmarks } from '../lib/cache'

/**
 * What the top-bar logo is doing (ui-design skill, "Logo animations"): Hourglass while we look
 * for an archived copy, Page back while a summary is being made, Rewind while a page loads. One
 * at a time, in that order, so the more specific job wins.
 *
 * Summarise and Find archived copy count from the click (the request, by its mutation key) until
 * the bookmark says the job is over: the server answers at once with "working" / "checking" while
 * a job runs, and the feed or the detail panel polls until that changes. The words for each
 * ("Summarising…", "Checking the Wayback Machine…") are on the story itself.
 */
export function useLogoMotion(): LogoMotion | null {
  const lookingUp = useIsMutating({ mutationKey: ['find-archive'] }) > 0
  const archiveJob = useAnyShownBookmark((b) => b.archive_status === 'checking')
  const summarising = useIsMutating({ mutationKey: ['summarise'] }) > 0
  const summaryJob = useAnyShownBookmark((b) => b.summary_status === 'working')
  // A page loading: a query with nothing to show yet (the first feed load, another Earlier
  // page). Polling and "Loading more…" don't count; they already have something on screen.
  const loading = useIsFetching({ predicate: (query) => query.state.data === undefined }) > 0

  if (lookingUp || archiveJob) return 'hourglass'
  if (summarising || summaryJob) return 'page-back'
  if (loading) return 'rewind'
  return null
}

/** Whether any bookmark on screen passes `test`, kept up to date as the cache changes. */
function useAnyShownBookmark(test: (bookmark: Bookmark) => boolean) {
  const queryClient = useQueryClient()
  const subscribe = useCallback(
    (onChange: () => void) => queryClient.getQueryCache().subscribe(notifyManager.batchCalls(onChange)),
    [queryClient],
  )
  return useSyncExternalStore(subscribe, () => shownBookmarks(queryClient).some(test))
}
