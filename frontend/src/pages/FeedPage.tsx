import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api } from '../api/client'
import type { BookmarkPage, Facets } from '../api/types'
import BookmarkCard from '../components/BookmarkCard'

export default function FeedPage() {
  // Filters live in the URL (?folder=...&browser=...) so they survive reloads and can be shared.
  const [params, setParams] = useSearchParams()
  const folder = params.get('folder')
  const browser = params.get('browser')

  const facets = useQuery({
    queryKey: ['facets'],
    queryFn: () => api.get<Facets>('/api/bookmarks/facets'),
  })

  const feed = useInfiniteQuery({
    queryKey: ['bookmarks', { folder, browser }],
    queryFn: ({ pageParam }) => {
      const query = new URLSearchParams({ limit: '30' })
      if (pageParam) query.set('cursor', pageParam)
      if (folder) query.set('folder', folder)
      if (browser) query.set('browser', browser)
      return api.get<BookmarkPage>(`/api/bookmarks?${query}`)
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
  })

  // Infinite scroll: load the next page when the sentinel below the grid scrolls into view.
  const sentinel = useRef<HTMLDivElement>(null)
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = feed
  useEffect(() => {
    const el = sentinel.current
    if (!el) return
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) fetchNextPage()
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  const setFilter = (key: 'folder' | 'browser', value: string | null) => {
    const next = new URLSearchParams(params)
    if (value === null || next.get(key) === value) next.delete(key)
    else next.set(key, value)
    setParams(next)
  }

  const bookmarks = feed.data?.pages.flatMap((p) => p.items) ?? []
  const isEmptyLibrary = facets.isSuccess && facets.data.browsers.length === 0

  return (
    <div className="mx-auto flex max-w-6xl gap-6 px-4 py-6">
      <aside className="hidden w-56 shrink-0 md:block">
        <FilterList
          title="Browsers"
          items={facets.data?.browsers ?? []}
          active={browser}
          onSelect={(v) => setFilter('browser', v)}
          capitalize
        />
        <FilterList
          title="Folders"
          items={facets.data?.folders ?? []}
          active={folder}
          onSelect={(v) => setFilter('folder', v)}
        />
      </aside>

      <main className="min-w-0 flex-1">
        {(folder || browser) && (
          <div className="mb-4 flex items-center gap-2 text-sm text-stone-600">
            Showing {[browser, folder].filter(Boolean).join(' · ')}
            <button onClick={() => setParams({})} className="text-sky-700 hover:underline">
              Clear
            </button>
          </div>
        )}

        {isEmptyLibrary && (
          <div className="rounded-xl border border-dashed border-stone-300 bg-white p-10 text-center">
            <h2 className="font-semibold">No bookmarks yet</h2>
            <p className="mt-1 text-sm text-stone-600">
              Install the browser extension and connect it with a token from{' '}
              <Link to="/settings" className="text-sky-700 hover:underline">
                Settings
              </Link>
              .
            </p>
          </div>
        )}

        {feed.isError && <p className="text-red-600">Couldn't load bookmarks: {feed.error.message}</p>}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {bookmarks.map((b) => (
            <BookmarkCard key={b.id} bookmark={b} />
          ))}
        </div>

        <div ref={sentinel} className="py-8 text-center text-sm text-stone-500">
          {(feed.isPending || isFetchingNextPage) && 'Loading…'}
        </div>
      </main>
    </div>
  )
}

function FilterList(props: {
  title: string
  items: { value: string; count: number }[]
  active: string | null
  onSelect: (value: string) => void
  capitalize?: boolean
}) {
  if (props.items.length === 0) return null
  return (
    <section className="mb-6">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">{props.title}</h3>
      <ul className="space-y-0.5">
        {props.items.map((item) => (
          <li key={item.value}>
            <button
              onClick={() => props.onSelect(item.value)}
              className={`flex w-full items-center justify-between rounded-md px-2 py-1 text-left text-sm ${
                props.active === item.value ? 'bg-stone-900 text-white' : 'hover:bg-stone-100'
              } ${props.capitalize ? 'capitalize' : ''}`}
            >
              <span className="truncate">{item.value || '(no folder)'}</span>
              <span className="ml-2 text-xs opacity-60">{item.count}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
