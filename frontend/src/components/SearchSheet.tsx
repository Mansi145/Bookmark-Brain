import { Fragment } from 'react'
import { Link, type To } from 'react-router'
import type { SearchResult } from '../api/types'
import { chunks, searchCount } from '../lib/format'
import { Bar, Masthead, Row, SHEET, Story, type Size } from './Newspaper'

// Search results replace the feed in place (design boards FeedSearch, FeedSearchLoading,
// FeedSearchEmpty, FeedSearchError and their dark versions): one sheet whose masthead is the query
// in quotes, with the count on the right. The best match is a second-size story beside two short
// briefs, then standard stories in ruled rows: two, then threes. Read stories, Needs sign-in and
// Dead links come up too, each with its usual state line. Search never says how a result matched
// (owner), so keyword-only results look like any others.

export default function SearchSheet(props: {
  query: string
  status: 'pending' | 'error' | 'success'
  items: SearchResult[]
  more: boolean
  onRetry: () => void
  clearTo: To // back to the feed, keeping the sidebar's filters
}) {
  const quoted = `“${props.query}”`
  if (props.status === 'pending') return <Searching quoted={quoted} />
  if (props.status === 'error') {
    return (
      <section aria-label="Search results" className={SHEET}>
        <Masthead left="" title={quoted} right="" />
        <Notice
          role="alert"
          icon={
            <>
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7.5v5.5" />
              <path d="M12 16.5h.01" />
            </>
          }
          title="Couldn’t search right now"
          lines={['That didn’t work on our side. Your bookmarks are safe, so try again in a moment.']}
        >
          <div className="mt-2 flex flex-wrap justify-center gap-2.5">
            <button
              type="button"
              onClick={props.onRetry}
              className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-lg border-0 bg-ink px-4 text-sm font-semibold text-on-ink"
            >
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
              >
                <path d="M21 12a9 9 0 1 1-3-6.7" />
                <path d="M21 4v5h-5" />
              </svg>
              Try again
            </button>
            <ClearSearch to={props.clearTo} />
          </div>
        </Notice>
      </section>
    )
  }
  if (props.items.length === 0) {
    return (
      <section aria-label="Search results" className={SHEET}>
        <Masthead left="" title={quoted} right="0 bookmarks" />
        <Notice
          role="status"
          icon={
            <>
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </>
          }
          title={`Nothing matched ${quoted}`}
          lines={[
            'Try different words, or fewer of them. Search looks through the titles, summaries and page text of everything you’ve saved, read or not.',
            'A browser, folder or tag picked in the sidebar narrows the search too.',
          ]}
        >
          <ClearSearch to={props.clearTo} className="mt-2" />
        </Notice>
      </section>
    )
  }

  const [best, ...rest] = props.items
  const side = rest.slice(0, 2)
  const pair = rest.slice(2, 4)
  const story = (result: SearchResult, size: Size) => (
    <Story
      key={result.id}
      bookmark={result}
      size={size}
      faded={result.read_state === 'read'}
      leaving={false}
      highlighted={result.highlighted}
    />
  )

  return (
    <section aria-label="Search results" className={SHEET}>
      <Masthead left="" title={quoted} right={searchCount(props.items.length, props.more)} />
      <div className={`grid ${side.length > 0 ? 'wide:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]' : ''}`}>
        <div className={side.length > 0 ? 'wide:border-r wide:border-line wide:pr-6' : ''}>{story(best, 'second')}</div>
        {side.length > 0 && (
          <div className="mt-4 flex flex-col gap-[18px] border-t border-line pt-4 wide:mt-0 wide:border-t-0 wide:pt-0 wide:pl-6">
            {side.map((result, i) => (
              <Fragment key={result.id}>
                {i > 0 && <div aria-hidden className="h-px bg-line" />}
                {story(result, 'side')}
              </Fragment>
            ))}
          </div>
        )}
      </div>
      {pair.length > 0 && <Row columns={2}>{pair.map((result) => story(result, 'standard'))}</Row>}
      {chunks(rest.slice(4), 3).map((row) => (
        <Row key={row[0].id} columns={3} rule="line">
          {row.map((result) => story(result, 'standard'))}
        </Row>
      ))}
    </section>
  )
}

/** The results' shape in pulsing bars while a search runs (board FeedSearchLoading). */
function Searching({ quoted }: { quoted: string }) {
  const story = (headline: string, lines: string[]) => (
    <div className="flex flex-col gap-2.5">
      <Bar className="h-3 w-[46%]" />
      <Bar className={`w-[88%] ${headline}`} />
      {lines.map((width, i) => (
        <Bar key={i} className={`h-3 ${width}`} />
      ))}
    </div>
  )
  return (
    <section aria-label="Search results" aria-busy="true" className={SHEET}>
      <Masthead
        left={<span role="status">Searching your bookmarks…</span>}
        title={quoted}
        right={<Bar className="ml-auto h-3 w-[84px]" />}
      />
      <div className="grid wide:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="wide:border-r wide:border-line wide:pr-6">
          {story('h-[30px]', ['w-full', 'w-[92%]', 'w-[64%]', 'w-[80%]', 'w-[55%]'])}
        </div>
        <div className="mt-4 flex flex-col gap-[18px] border-t border-line pt-4 wide:mt-0 wide:border-t-0 wide:pt-0 wide:pl-6">
          {story('h-[18px]', ['w-full', 'w-[92%]'])}
          <div aria-hidden className="h-px bg-line" />
          {story('h-[18px]', ['w-full', 'w-[92%]'])}
        </div>
      </div>
      <Row columns={2}>
        {[0, 1].map((i) => (
          <Fragment key={i}>{story('h-[22px]', ['w-full', 'w-[92%]', 'w-[64%]'])}</Fragment>
        ))}
      </Row>
    </section>
  )
}

/** The centred card for no results and for a failed search: icon on accent, title, lines. */
function Notice(props: {
  role: 'status' | 'alert'
  icon: React.ReactNode
  title: string
  lines: string[]
  children: React.ReactNode
}) {
  return (
    <div role={props.role} className="flex flex-col items-center gap-2.5 px-4 pt-10 pb-7 text-center">
      <span aria-hidden className="grid size-[52px] place-items-center rounded-full bg-accent text-on-accent">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {props.icon}
        </svg>
      </span>
      <h3 className="mt-1.5 font-serif text-[21px] font-bold text-ink">{props.title}</h3>
      {props.lines.map((line) => (
        <p key={line} className="m-0 max-w-[460px] text-sm text-ink2">
          {line}
        </p>
      ))}
      {props.children}
    </div>
  )
}

function ClearSearch({ to, className = '' }: { to: To; className?: string }) {
  return (
    <Link
      to={to}
      className={`inline-flex h-10 items-center rounded-lg border border-line bg-surface px-4 text-sm font-medium text-ink no-underline ${className}`}
    >
      Clear search
    </Link>
  )
}
