import { keepPreviousData, useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api } from '../api/client'
import type { Bookmark, BookmarkPage, FacetCount, Facets, FeedSection, ReadState } from '../api/types'
import BookmarkDetail from '../components/BookmarkDetail'
import Newspaper, { FrontPageLoading, SectionSheet } from '../components/Newspaper'
import { groupBySaveDate, startOfWeek, type Edition } from '../lib/editions'

// Earlier's pages (design board Main): 30 briefs each, newest first.
const EARLIER_PAGE_SIZE = 30

// main: the feed. sign_in: "Needs sign-in" (an account or subscription). dead: "Dead links"
// (404/410, and pages we could only read from archive.org). Each bookmark is in one section.
export default function FeedPage({ section }: { section: FeedSection }) {
  // Filters live in the URL (?folder=...&browser=...) so they survive reloads and can be shared.
  const [params, setParams] = useSearchParams()
  const folder = params.get('folder')
  const browser = params.get('browser')
  // Reading state (main feed only): all | unread | read.
  const readState = section === 'main' ? (params.get('state') as ReadState | null) : null

  const facets = useFacets(section)

  // The main feed splits at the start of the week: Today and This week load by scrolling (all
  // of them), Earlier in numbered pages (?page=2), newest first. The two sections just scroll.
  const weekStart = section === 'main' ? startOfWeek().toISOString() : null
  const earlierPage = Math.max(1, Math.floor(Number(params.get('page'))) || 1)
  const withFilters = (query: URLSearchParams) => {
    if (folder) query.set('folder', folder)
    if (browser) query.set('browser', browser)
    if (readState) query.set('read_state', readState)
    return query
  }

  const feed = useInfiniteQuery({
    queryKey: ['bookmarks', { section, folder, browser, readState, weekStart }],
    queryFn: ({ pageParam }) => {
      const query = withFilters(new URLSearchParams({ limit: '30', section }))
      if (pageParam) query.set('cursor', pageParam)
      if (weekStart) query.set('saved_after', weekStart)
      return api.get<BookmarkPage>(`/api/bookmarks?${query}`)
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    refetchInterval: (query) =>
      pollInterval(query.state.data?.pages.flatMap((p) => p.items) ?? [], query.state.dataUpdateCount),
  })

  const earlier = useQuery({
    queryKey: ['bookmarks', 'earlier', { folder, browser, readState, weekStart, page: earlierPage }],
    enabled: weekStart !== null,
    queryFn: () => {
      const query = withFilters(
        new URLSearchParams({ section, limit: String(EARLIER_PAGE_SIZE), page: String(earlierPage) }),
      )
      query.set('saved_before', weekStart!)
      return api.get<BookmarkPage>(`/api/bookmarks?${query}`)
    },
    // Keep showing the current page while the next one loads, so the sheet doesn't jump.
    placeholderData: keepPreviousData,
    refetchInterval: (query) => pollInterval(query.state.data?.items ?? [], query.state.dataUpdateCount),
  })

  // A page past the end (bookmarks were removed, or an old link): go to the last page instead.
  const earlierTotal = earlier.data?.total ?? 0
  const lastPage = Math.max(1, Math.ceil(earlierTotal / EARLIER_PAGE_SIZE))
  useEffect(() => {
    if (earlier.isSuccess && !earlier.isPlaceholderData && earlierPage > lastPage) {
      const next = new URLSearchParams(params)
      if (lastPage > 1) next.set('page', String(lastPage))
      else next.delete('page')
      setParams(next, { replace: true })
    }
  }, [earlier.isSuccess, earlier.isPlaceholderData, earlierPage, lastPage, params, setParams])

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
    next.delete('page') // a different filter starts Earlier from its first page
    setParams(next)
  }

  // The detail panel (?bookmark=<id>): part of the address, so Back closes it.
  const openId = Number(params.get('bookmark')) || null
  const closeDetail = () => {
    const next = new URLSearchParams(params)
    next.delete('bookmark')
    setParams(next)
  }

  const bookmarks = feed.data?.pages.flatMap((p) => p.items) ?? []
  // First run: no browser has synced anything yet (facets list every browser, even at 0).
  const isFirstRun = facets.isSuccess && facets.data.browsers.length === 0
  const isEmpty = facets.isSuccess && facets.data.total === 0 && !isFirstRun
  const editions: Edition[] = groupBySaveDate(bookmarks)
  if (earlier.data && earlier.data.items.length > 0) {
    editions.push({ key: 'earlier', title: 'Earlier', items: earlier.data.items })
  }

  return (
    <div className="mx-auto flex max-w-[1280px] flex-wrap items-start gap-8 px-6 pt-8 pb-16">
      <aside
        aria-label="Filters"
        className="flex flex-[1_1_220px] flex-col gap-7 rounded-2xl bg-panel px-3.5 py-[18px] wide:max-w-[260px]"
      >
        <FilterList
          title="Browsers"
          items={(facets.data?.browsers ?? []).map((f) => ({
            ...f,
            label: f.value,
            indent: 0,
          }))}
          active={browser}
          onSelect={(v) => setFilter('browser', v)}
          capitalize
        />
        <FilterList
          title="Folders"
          items={folderItems(facets.data?.folders ?? [])}
          active={folder}
          onSelect={(v) => setFilter('folder', v)}
        />
      </aside>

      <main className="min-w-0 flex-[999_1_560px] rounded-2xl bg-panel p-3.5 wide:p-6">
        <div className="mb-[22px]">
          <h1 className="font-serif text-[40px] leading-[1.1] font-bold tracking-[-0.015em]">{TITLES[section]}</h1>
          {facets.data && (
            <p className="mt-2 text-sm text-ink2">
              {facets.data.total} {facets.data.total === 1 ? 'bookmark' : 'bookmarks'}
              {isFirstRun && ' · no browser connected yet'}
              {facets.data.pending > 0 && ` · ${facets.data.pending} being fetched`}
            </p>
          )}
        </div>

        {!isFirstRun && <FeedViewsBar section={section} readState={readState} />}

        {(folder || browser) && (
          <div className="mb-4 flex items-center gap-2 text-sm text-ink2">
            Showing {[browser, folder].filter(Boolean).join(' · ')}
            <button onClick={() => setParams({})} className="cursor-pointer border-0 bg-transparent text-ink underline">
              Clear
            </button>
          </div>
        )}

        {isFirstRun && <FirstRun />}
        {isEmpty && <EmptyState section={section} />}
        {feed.isError && <p className="text-dead-fg">Couldn't load bookmarks: {feed.error.message}</p>}

        {/* Everything is a newspaper (board Main): the feed as editions, the two sections as one
            sheet each. */}
        {section === 'main' && feed.isPending && !isFirstRun && <FrontPageLoading />}
        {section === 'main' && (
          <Newspaper
            editions={editions}
            earlier={{ page: earlierPage, total: earlierTotal, pageSize: EARLIER_PAGE_SIZE }}
            view={readState}
          />
        )}
        {section !== 'main' && bookmarks.length > 0 && (
          <SectionSheet {...SHEETS[section]} count={facets.data?.total ?? bookmarks.length} items={bookmarks} />
        )}

        <div ref={sentinel} className="py-7 text-center text-sm text-ink2">
          {((section !== 'main' && feed.isPending) || isFetchingNextPage) && 'Loading more…'}
        </div>
      </main>
      {openId && <BookmarkDetail key={openId} id={openId} onClose={closeDetail} />}
    </div>
  )
}

/**
 * Pages are fetched in the background after a sync. While any shown bookmark is still pending,
 * refetch every few seconds so results appear without a reload; stop after ~2 minutes in case
 * something stays pending (e.g. the worker is off). Also poll while something the user asked
 * for is running: a Wayback Machine lookup or a summary (a few seconds each).
 */
function pollInterval(items: Bookmark[], updates: number) {
  const pending = items.some((b) => b.status === 'pending')
  const asked = items.some((b) => b.archive_status === 'checking' || b.summary_status === 'working')
  return asked || (pending && updates < 40) ? 3000 : false
}

// The two section sheets' mastheads (boards FeedSignIn / FeedDead).
const SHEETS = {
  sign_in: { title: 'Needs sign-in', line: 'Pages behind an account or a subscription' },
  dead: { title: 'Dead links', line: 'Pages that no longer load on the web' },
}

/** Counts for one section. Shared by the page and the views bar (same cache key). */
function useFacets(section: FeedSection) {
  return useQuery({
    queryKey: ['facets', section],
    queryFn: () => api.get<Facets>(`/api/bookmarks/facets?section=${section}`),
    // Counts change as pages finish fetching (and may move to another section).
    refetchInterval: (query) =>
      (query.state.data?.pending ?? 0) > 0 && query.state.dataUpdateCount < 40 ? 3000 : false,
  })
}

const TITLES: Record<FeedSection, string> = {
  main: 'Feed',
  sign_in: 'Needs sign-in',
  dead: 'Dead links',
}

/**
 * The views bar (its own bar above the list, owner's decision): the reading states, which filter
 * the main feed, a divider, then the Needs sign-in and Dead links sections, each with a count.
 */
function FeedViewsBar({ section, readState }: { section: FeedSection; readState: ReadState | null }) {
  const main = useFacets('main').data
  const signIn = useFacets('sign_in').data
  const dead = useFacets('dead').data

  const states: { value: ReadState | null; label: string; count?: number }[] = [
    { value: null, label: 'All bookmarks', count: main?.total },
    { value: 'unread', label: 'Unread', count: main?.read_states.unread },
    { value: 'read', label: 'Read', count: main?.read_states.read },
  ]
  return (
    <nav aria-label="Feed views" className="mb-[22px] flex flex-wrap items-center gap-2">
      {states.map((s) => (
        <ViewPill
          key={s.label}
          to={s.value ? `/?state=${s.value}` : '/'}
          current={section === 'main' && readState === s.value}
          label={s.label}
          count={s.count}
        />
      ))}
      <span aria-hidden className="mx-1 h-6 w-px bg-line" />
      <ViewPill to="/sign-in-required" current={section === 'sign_in'} label="Needs sign-in" count={signIn?.total} />
      <ViewPill to="/dead-links" current={section === 'dead'} label="Dead links" count={dead?.total} />
    </nav>
  )
}

function ViewPill(props: { to: string; current: boolean; label: string; count?: number }) {
  return (
    <Link
      to={props.to}
      aria-current={props.current ? 'page' : undefined}
      className={`flex h-10 items-center gap-2 rounded-full px-4 text-sm no-underline ${
        props.current
          ? 'border border-accent bg-accent font-semibold text-on-accent'
          : 'border border-line bg-surface text-ink hover:bg-skeleton'
      }`}
    >
      {props.label}
      {props.count !== undefined && (
        <span className={`text-xs ${props.current ? 'text-on-accent2' : 'text-muted'}`}>{props.count}</span>
      )}
    </Link>
  )
}

type FilterItem = {
  value: string
  label: string
  count: number
  indent: number
}

/** Subfolders are indented under their parent when the parent is listed too. */
function folderItems(folders: FacetCount[]): FilterItem[] {
  const paths = new Set(folders.map((f) => f.value))
  return folders.map((f) => {
    const parts = f.value.split('/')
    const parent = parts.slice(0, -1).join('/')
    const nested = parts.length > 1 && paths.has(parent)
    return {
      ...f,
      label: (nested ? parts[parts.length - 1] : f.value) || '(no folder)',
      indent: nested ? parts.length - 1 : 0,
    }
  })
}

function FilterList(props: {
  title: string
  items: FilterItem[]
  active: string | null
  onSelect: (value: string) => void
  capitalize?: boolean
}) {
  if (props.items.length === 0) return null
  return (
    <section>
      <h2 className="mb-2 text-xs font-semibold tracking-[0.06em] text-ink2 uppercase">{props.title}</h2>
      <ul className="m-0 flex list-none flex-col gap-0.5 p-0">
        {props.items.map((item) => {
          const active = props.active === item.value
          return (
            <li key={item.value}>
              <button
                type="button"
                aria-pressed={active}
                title={item.value}
                onClick={() => props.onSelect(item.value)}
                className={`flex min-h-9 w-full cursor-pointer items-center justify-between gap-2 rounded-lg border-0 px-2.5 py-1.5 text-left text-sm ${
                  active ? 'bg-accent font-semibold text-on-accent' : 'bg-transparent text-ink hover:bg-skeleton'
                } ${props.capitalize ? 'capitalize' : ''}`}
              >
                <span className="truncate" style={{ paddingLeft: item.indent * 14 }}>
                  {item.label}
                </span>
                <span className={`text-xs ${active ? 'text-on-accent2' : 'text-muted'}`}>{item.count}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

// Until the extension is in the browser stores, "Get the extension" points to the install steps.
const EXTENSION_URL = 'https://github.com/Mansi145/Bookmark-Brain#4-browser-extension'

/** No browser connected yet (design board FeedFirstRun). */
function FirstRun() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-line bg-surface px-8 py-12 text-center">
      <span aria-hidden className="grid size-14 place-items-center rounded-full bg-accent text-on-accent">
        <svg
          width="26"
          height="26"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 3h12v18l-6-4-6 4z" />
        </svg>
      </span>
      <h2 className="mt-1.5 font-serif text-[28px] font-bold">Connect your first browser</h2>
      <p className="max-w-[460px] text-ink2">
        Your bookmarks will show up here as your own front page. It takes about a minute.
      </p>
      <ol className="mt-3 flex list-none flex-col gap-2.5 p-0 text-left">
        <FirstRunStep n={1}>Add the Bookmark Brain extension to Chrome, Edge, Brave or Firefox.</FirstRunStep>
        <FirstRunStep n={2}>
          Click its icon, then <strong className="font-semibold text-ink">Connect this browser</strong>.
        </FirstRunStep>
      </ol>
      <div className="mt-3.5 flex flex-wrap justify-center gap-2.5">
        <a
          href={EXTENSION_URL}
          target="_blank"
          rel="noreferrer"
          className="flex h-11 items-center rounded-[10px] bg-ink px-[18px] font-semibold text-on-ink no-underline"
        >
          Get the extension
        </a>
        <Link
          to="/settings"
          className="flex h-11 items-center rounded-[10px] border border-line px-[18px] font-medium text-ink no-underline"
        >
          Connect by hand
        </Link>
      </div>
    </div>
  )
}

function FirstRunStep({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-3">
      <span
        aria-hidden
        className="grid size-7 flex-none place-items-center rounded-full bg-accent text-[13px] font-semibold text-on-accent"
      >
        {n}
      </span>
      <span className="text-ink2">{children}</span>
    </li>
  )
}

function EmptyState({ section }: { section: FeedSection }) {
  const { title, body } = {
    main: {
      title: 'No bookmarks yet',
      body: (
        <>
          Install the browser extension and click <strong>Connect this browser</strong>. See{' '}
          <Link to="/settings" className="text-ink">
            Settings
          </Link>{' '}
          for details.
        </>
      ),
    },
    sign_in: {
      title: 'Nothing needs sign-in',
      body: 'Pages that need an account or a subscription will show up here.',
    },
    dead: {
      title: 'No dead links',
      body: 'Links that stop working show up here. You can look each one up on the Wayback Machine.',
    },
  }[section]
  return (
    <div className="flex flex-col items-center rounded-xl border border-line bg-surface px-6 py-10 text-center">
      <span aria-hidden className="grid size-12 place-items-center rounded-full bg-accent text-on-accent">
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m5 12 4.5 4.5L19 7" />
        </svg>
      </span>
      <h2 className="mt-4 font-serif text-[21px] font-bold">{title}</h2>
      <p className="mt-1 text-sm text-ink2">{body}</p>
    </div>
  )
}
