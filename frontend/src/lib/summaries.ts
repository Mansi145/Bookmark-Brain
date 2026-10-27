import type { Bookmark } from '../api/types'

/** A dead link can only be summarised from its Wayback copy; a page still being fetched waits. */
export function canSummarise(bookmark: Bookmark) {
  if (bookmark.status === 'pending') return false
  return bookmark.status !== 'dead' || bookmark.content_source === 'archive'
}
