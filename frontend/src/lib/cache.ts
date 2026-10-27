import type { InfiniteData, QueryClient } from '@tanstack/react-query'
import type { Bookmark, BookmarkPage } from '../api/types'

// How long a story that no longer belongs in the current view fades out before the feed
// refetches and drops it (matches the `leave` animation in index.css).
export const LEAVE_MS = 250

/**
 * Put an updated bookmark into every cached copy straight away: the feed's pages (all views)
 * and the detail panel's single bookmark. The feed then shows the change before refetching.
 */
export function updateCachedBookmark(queryClient: QueryClient, updated: Bookmark) {
  queryClient.setQueriesData<InfiniteData<BookmarkPage> | Bookmark>({ queryKey: ['bookmarks'] }, (old) => {
    if (!old) return old
    if ('pages' in old) {
      return {
        ...old,
        pages: old.pages.map((page) => ({
          ...page,
          items: page.items.map((b) => (b.id === updated.id ? updated : b)),
        })),
      }
    }
    return old.id === updated.id ? updated : old
  })
}
