import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import type { Bookmark } from '../api/types'

/**
 * Summarise (or, with `again`, Re-summarise) one bookmark. The server answers at once: either
 * the cached summary, or summary_status "working" while a job runs; the feed and the detail
 * panel then poll until it's done.
 */
export function useSummarise(bookmarkId: number) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (again: boolean = false) =>
      api.post<Bookmark>(`/api/bookmarks/${bookmarkId}/summarise${again ? '?again=true' : ''}`),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
      void queryClient.invalidateQueries({ queryKey: ['usage'] })
    },
  })
  const hitLimit = mutation.error instanceof ApiError && mutation.error.status === 429
  return { ...mutation, hitLimit }
}
