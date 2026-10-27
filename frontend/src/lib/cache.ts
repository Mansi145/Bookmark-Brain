import type { InfiniteData, QueryClient } from '@tanstack/react-query'
import type { Bookmark, BookmarkPage } from '../api/types'

// How long a story that no longer belongs in the current view fades out before the feed
// refetches and drops it (matches the `leave` animation in index.css).
export const LEAVE_MS = 250

// What's cached under 'bookmarks': the feed's scrolling pages, Earlier's numbered page, or the
// detail panel's single bookmark.
type CachedBookmarks = InfiniteData<BookmarkPage> | BookmarkPage | Bookmark

/**
 * Put an updated bookmark into every cached copy straight away: the feed's scrolling pages (all
 * views), Earlier's numbered page and the detail panel's single bookmark. The feed then shows
 * the change before refetching.
 */
export function updateCachedBookmark(queryClient: QueryClient, updated: Bookmark) {
  const swap = (items: Bookmark[]) => items.map((b) => (b.id === updated.id ? updated : b))
  queryClient.setQueriesData<CachedBookmarks>({ queryKey: ['bookmarks'] }, (old) => {
    if (!old) return old
    if ('items' in old) return { ...old, items: swap(old.items) }
    if ('pages' in old) {
      return {
        ...old,
        pages: old.pages.map((page) => ({
          ...page,
          items: swap(page.items),
        })),
      }
    }
    return old.id === updated.id ? updated : old
  })
}

/**
 * The bookmarks on screen: the cached copies that a mounted feed or detail panel is using (and
 * polling). Copies left over from views the user has moved away from aren't refreshed, so they're
 * left out.
 */
export function shownBookmarks(queryClient: QueryClient): Bookmark[] {
  return queryClient
    .getQueriesData<CachedBookmarks>({ queryKey: ['bookmarks'], type: 'active' })
    .flatMap(([, data]) => {
      if (!data) return []
      if ('items' in data) return data.items
      if ('pages' in data) return data.pages.flatMap((page) => page.items)
      return [data]
    })
}

/**
 * Stories marked read while looking at All bookmarks during this visit. They keep their place
 * and look in the newspaper (design board MarkAsRead: "only its button changes") instead of
 * jumping to the end, faded; after a reload they sit with the other read stories.
 */
export const keptInPlace = new Set<number>()
