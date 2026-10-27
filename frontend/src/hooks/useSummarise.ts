import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import type { Bookmark } from '../api/types'
import { openLimitDialog } from '../lib/limit'

/**
 * Summarise (or, with `again`, Re-summarise) one bookmark. The server answers at once: either
 * the cached summary, or summary_status "working" while a job runs; the feed and the detail
 * panel then poll until it's done. A 429 (daily limit) opens the Limit reached dialog.
 */
export function useSummarise(bookmarkId: number) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    // The top-bar logo plays Page back while any of these is on its way (useLogoMotion).
    mutationKey: ['summarise'],
    mutationFn: (again: boolean = false) =>
      api.post<Bookmark>(`/api/bookmarks/${bookmarkId}/summarise${again ? '?again=true' : ''}`),
    onError: (error) => {
      if (error instanceof ApiError && error.status === 429) openLimitDialog()
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ['bookmarks'] }),
  })
  // Refused for the limit: the dialog explains it, so the button just goes back to normal.
  const hitLimit = mutation.error instanceof ApiError && mutation.error.status === 429
  return { ...mutation, hitLimit }
}
