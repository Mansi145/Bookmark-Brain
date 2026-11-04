import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { api, ApiError } from '../api/client'
import type { TagCount, TagErrorCode } from '../api/types'

// Tags (design: ui-design skill, "Tags, collections and duplicates"). The limits match the
// backend's (app/services/tags.py), which enforces them.
export const MAX_TAG_NAME = 30
export const MAX_PER_BOOKMARK = 5
export const MAX_PER_USER = 50

/**
 * The tags picked in the sidebar, in the URL like the other filters (?tag=3&tag=7): bookmarks
 * with all of them. At most 5, since no bookmark has more.
 */
export function useTagFilter() {
  const [params, setParams] = useSearchParams()
  const picked = params.getAll('tag').map(Number).filter(Boolean)
  const set = (ids: number[]) => {
    const next = new URLSearchParams(params)
    next.delete('tag')
    for (const id of ids.slice(0, MAX_PER_BOOKMARK)) next.append('tag', String(id))
    next.delete('page') // a different filter starts Earlier from its first page
    setParams(next)
  }
  return {
    picked,
    toggle: (id: number) => set(picked.includes(id) ? picked.filter((p) => p !== id) : [...picked, id]),
    remove: (id: number) => set(picked.filter((p) => p !== id)),
    clear: () => set([]),
  }
}

/** The address with one more tag picked (a story's tag line links there). */
export function withTag(params: URLSearchParams, id: number) {
  const next = new URLSearchParams(params)
  if (!next.getAll('tag').includes(String(id)) && next.getAll('tag').length < MAX_PER_BOOKMARK) {
    next.append('tag', String(id))
  }
  next.delete('page')
  next.delete('bookmark')
  return next
}

/** Every tag with its count, unused ones too (Show unused, Merge, the Add tag lists). */
export function useTags() {
  return useQuery({
    queryKey: ['tags'],
    queryFn: () => api.get<TagCount[]>('/api/tags'),
  })
}

/** After any tag change: the tag list, the sidebar's counts and the stories' tag lines. */
export function refreshAfterTagChange(queryClient: QueryClient) {
  for (const queryKey of [['tags'], ['facets'], ['bookmarks']]) void queryClient.invalidateQueries({ queryKey })
}

export function useRefreshTags() {
  const queryClient = useQueryClient()
  return () => refreshAfterTagChange(queryClient)
}

/** The rule a refused change broke (a 409 from the tags API), or null for any other failure. */
export function tagErrorCode(error: unknown): TagErrorCode | null {
  return error instanceof ApiError && error.status === 409 ? (error.message as TagErrorCode) : null
}

export const LIMIT_TEXT = {
  account: `You have ${MAX_PER_USER} tags, the most an account can have. Delete or merge one to add another.`,
  bookmark: `${MAX_PER_BOOKMARK} tags is the most a bookmark can have. Remove one to add another.`,
}

/** "4 bookmarks with both tags": the count line while tags are picked. */
export function taggedCount(total: number, tags: number) {
  const which = tags === 1 ? 'this tag' : tags === 2 ? 'both tags' : `all ${tags} tags`
  return `${total} ${total === 1 ? 'bookmark' : 'bookmarks'} with ${which}`
}
