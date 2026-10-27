import { useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import type { Bookmark, ReadState } from '../api/types'
import { keptInPlace } from '../lib/cache'
import { editionDate, type Edition } from '../lib/editions'
import { age } from '../lib/format'
import { canSummarise } from '../lib/summaries'
import SiteIcon from './SiteIcon'
import { PageState } from './StoryParts'
import { OpenSummary, SummariseAction } from './Summarise'

// The feed as a classic newspaper front page (design boards NewsClassic and Main). Today /
// This week / Earlier are editions: one sheet each, with a masthead and thin column rules
// instead of a card per article. Newest unread stories are biggest (lead → second → standard →
// brief) and read ones go last, faded. Only the very first story (the lead) shows the page's
// preview image; a lead without one is text-only. Earlier is paged, 30 briefs a page, newest
// first, with a pager under it (?page=2). Needs sign-in and Dead links are one sheet
// each of standard stories (SectionSheet). At 760 px and below every column stacks into one
// and the column rules become horizontal dividers (`wide:` is the board's breakpoint).

type Size = 'lead' | 'second' | 'standard' | 'brief'
type EarlierPages = { page: number; total: number; pageSize: number }

const SHEET = 'rounded-xl border border-line bg-surface p-[18px] wide:p-7'

export default function Newspaper(props: {
  editions: Edition[]
  earlier: EarlierPages
  view: ReadState | null // the views bar: All (null), Unread or Read
}) {
  return (
    <div className="flex flex-col gap-6">
      {props.editions.map((edition, i) => {
        const earlier = edition.key === 'earlier'
        return (
          <EditionSheet
            key={edition.key}
            edition={edition}
            // The first edition is the front page (Earlier only on its first page, when there's
            // nothing newer); otherwise Earlier is all briefs.
            layout={i === 0 && !(earlier && props.earlier.page > 1) ? 'front' : earlier ? 'briefs' : 'middle'}
            pages={earlier ? props.earlier : undefined}
            view={props.view}
          />
        )
      })}
    </div>
  )
}

function EditionSheet(props: {
  edition: Edition
  layout: 'front' | 'middle' | 'briefs'
  pages?: EarlierPages // Earlier: which page, of how many bookmarks
  view: ReadState | null
}) {
  const { edition, layout, pages } = props
  const sheet = useRef<HTMLElement>(null)
  // Unread first, newest first; read ones last (also newest first). A story just marked read in
  // All bookmarks still counts as unread here, so it stays where it was. Earlier's pages are in
  // save-date order only (board Main), so a page holds the same 30 whatever was read.
  const upFront = (b: Bookmark) => b.read_state === 'unread' || keptInPlace.has(b.id)
  const stories = pages
    ? edition.items
    : [...edition.items.filter(upFront), ...edition.items.filter((b) => !upFront(b))]
  const unread = edition.items.length - edition.items.filter((b) => b.read_state === 'read').length
  const front = layout === 'front'
  const title = edition.key === 'today' ? "Today's edition" : edition.title

  const n = stories.length
  const count =
    edition.key === 'today'
      ? `${n} new · ${unread === n ? 'all unread' : `${unread} unread`}`
      : edition.key === 'week'
        ? `${n} ${n === 1 ? 'bookmark' : 'bookmarks'} · ${unread} unread`
        : `${pages?.total ?? n} ${(pages?.total ?? n) === 1 ? 'bookmark' : 'bookmarks'}`

  // Who gets which size: front = lead, two seconds, three standards; middle = a second and
  // two standards; everything after that is a brief.
  const [top, rest] = front
    ? [stories.slice(0, 6), stories.slice(6)]
    : layout === 'middle'
      ? [stories.slice(0, 3), stories.slice(3)]
      : [[], stories]
  const story = (b: Bookmark, size: Size) => (
    <Story
      key={b.id}
      bookmark={b}
      size={size}
      // Read stories are faded (All bookmarks and Read, board MarkAsRead). Unread / Read: a
      // story just marked the other way fades out until the feed refetches without it.
      faded={!upFront(b)}
      leaving={props.view !== null && b.read_state !== props.view}
    />
  )

  return (
    <section ref={sheet} aria-label={title} className={`${SHEET} scroll-mt-4`}>
      <Masthead left={editionDate(edition.key)} title={title} right={count} front={front} />

      {front && top.length > 0 && (
        <>
          <div className={`grid ${top.length > 1 ? 'wide:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]' : ''}`}>
            <div className={top.length > 1 ? 'wide:border-r wide:border-line wide:pr-6' : ''}>
              {story(top[0], 'lead')}
            </div>
            {top.length > 1 && (
              <div className="mt-4 flex flex-col gap-5 border-t border-line pt-4 wide:mt-0 wide:border-t-0 wide:pt-0 wide:pl-6">
                {top.slice(1, 3).map((b, i) => (
                  <div key={b.id} className={i > 0 ? 'border-t border-line pt-5' : ''}>
                    {story(b, 'second')}
                  </div>
                ))}
              </div>
            )}
          </div>
          {top.length > 3 && <Row columns={3}>{top.slice(3).map((b) => story(b, 'standard'))}</Row>}
        </>
      )}

      {layout === 'middle' && top.length > 0 && (
        <div className="grid wide:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)]">
          {top.map((b, i) => (
            <div key={b.id} className={cell(i)}>
              {story(b, i === 0 ? 'second' : 'standard')}
            </div>
          ))}
        </div>
      )}

      {/* Briefs come in rows of four, each with a rule above it (the board's "This week"). */}
      {chunks(rest, 4).map((row, i) => (
        <Row key={row[0].id} columns={4} first={layout === 'briefs' && i === 0}>
          {row.map((b) => story(b, 'brief'))}
        </Row>
      ))}

      {/* After paging, jump back to the top of Earlier so the new page starts in view. */}
      {pages && pages.total > pages.pageSize && (
        <Pager {...pages} onPage={() => sheet.current?.scrollIntoView({ block: 'start' })} />
      )}
    </section>
  )
}

/**
 * Earlier's pager (design board Main): "Showing 31–60 of 189 · newest first", then ‹ Newer,
 * page numbers (the current one on accent), an ellipsis for skipped pages, and Older ›. The
 * page is in the address (?page=2, page 1 has none), keeping the other filters.
 */
function Pager(props: EarlierPages & { onPage: () => void }) {
  const [params] = useSearchParams()
  const last = Math.ceil(props.total / props.pageSize)
  const from = (props.page - 1) * props.pageSize + 1
  const to = Math.min(props.page * props.pageSize, props.total)
  const href = (page: number) => {
    const next = new URLSearchParams(params)
    next.delete('bookmark')
    if (page > 1) next.set('page', String(page))
    else next.delete('page')
    return { search: next.toString() }
  }
  const box = 'flex h-9 items-center rounded-lg border text-sm no-underline'
  const off = `${box} gap-1.5 border-line px-3 text-muted opacity-60`
  const step = `${box} gap-1.5 border-line bg-surface px-3 font-medium text-ink`

  return (
    <nav
      aria-label="Earlier pages"
      className="mt-[22px] flex flex-wrap items-center justify-between gap-3 border-t border-ink pt-4"
    >
      <span className="text-[13px] text-ink2">
        Showing {from}–{to} of {props.total} · newest first
      </span>
      <div className="flex flex-wrap items-center gap-1.5">
        {props.page > 1 ? (
          <Link to={href(props.page - 1)} onClick={props.onPage} className={step}>
            <Chevron back />
            Newer
          </Link>
        ) : (
          <span aria-disabled="true" className={off}>
            <Chevron back />
            Newer
          </span>
        )}
        {pageNumbers(props.page, last).map((n, i) =>
          n === null ? (
            <span key={`gap-${i}`} aria-hidden className="px-1 text-muted">
              …
            </span>
          ) : (
            <Link
              key={n}
              to={href(n)}
              onClick={props.onPage}
              aria-label={`Page ${n}`}
              aria-current={n === props.page ? 'page' : undefined}
              className={`grid size-9 place-items-center rounded-lg border text-sm no-underline ${n === props.page ? 'border-accent bg-accent font-semibold text-on-accent' : 'border-line bg-surface font-medium text-ink'}`}
            >
              {n}
            </Link>
          ),
        )}
        {props.page < last ? (
          <Link to={href(props.page + 1)} onClick={props.onPage} className={step}>
            Older
            <Chevron />
          </Link>
        ) : (
          <span aria-disabled="true" className={off}>
            Older
            <Chevron />
          </span>
        )}
      </div>
    </nav>
  )
}

/**
 * Which page numbers to show: the first, the last, and the ones around the current page, with
 * null for a gap ("…"). Page 1 of 7: 1 2 3 … 7. Page 4 of 7: 1 … 3 4 5 … 7.
 */
function pageNumbers(current: number, last: number): (number | null)[] {
  const shown = new Set([1, last, current - 1, current, current + 1])
  if (current <= 2) shown.add(3)
  if (current >= last - 1) shown.add(last - 2)
  const pages = [...shown].filter((n) => n >= 1 && n <= last).sort((a, b) => a - b)
  return pages.flatMap((n, i) => (i > 0 && n - pages[i - 1] > 1 ? [null, n] : [n]))
}

function Chevron({ back = false }: { back?: boolean }) {
  return (
    <svg
      aria-hidden
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={back ? 'm15 6-6 6 6 6' : 'm9 6 6 6-6 6'} />
    </svg>
  )
}

/**
 * Needs sign-in or Dead links (design boards FeedSignIn / FeedDead): one sheet with a small
 * masthead, then standard stories in ruled rows of three, each with its state line.
 */
export function SectionSheet(props: { title: string; line: string; count: number; items: Bookmark[] }) {
  return (
    <section aria-label={props.title} className={SHEET}>
      <Masthead
        left={props.line}
        title={props.title}
        right={`${props.count} ${props.count === 1 ? 'bookmark' : 'bookmarks'}`}
      />
      {chunks(props.items, 3).map((row, i) => (
        <Row key={row[0].id} columns={3} first={i === 0}>
          {row.map((b) => (
            <Story key={b.id} bookmark={b} size="standard" faded={b.read_state === 'read'} leaving={false} />
          ))}
        </Row>
      ))}
    </section>
  )
}

/** The front page's shape in pulsing bars while the first page of the feed loads (FeedLoading). */
export function FrontPageLoading() {
  return (
    <section role="status" aria-label="Loading your front page" className={SHEET}>
      <div aria-hidden className="bg-band h-[5px] rounded-sm" />
      <div className="flex items-center justify-between gap-4 border-b border-ink pt-4 pb-3">
        <Bar className="h-3 w-[120px]" />
        <Bar className="h-[34px] w-[260px] max-w-[45%]" />
        <Bar className="h-3 w-[90px]" />
      </div>
      <div className="mt-[22px] grid wide:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-3 wide:border-r wide:border-line wide:pr-6">
          <Bar className="aspect-video w-full" />
          <Bar className="h-9 w-[70%]" />
          <Bar className="h-3 w-full" />
          <Bar className="h-3 w-[95%]" />
          <Bar className="h-3 w-[60%]" />
        </div>
        <div className="mt-4 flex flex-col gap-3 border-t border-line pt-4 wide:mt-0 wide:border-t-0 wide:pt-0 wide:pl-6">
          <Bar className="h-[26px] w-[85%]" />
          <Bar className="h-3 w-full" />
          <Bar className="h-3 w-[90%]" />
          <Bar className="mb-3.5 h-2.5 w-1/2" />
          <Bar className="h-[26px] w-[80%]" />
          <Bar className="h-3 w-full" />
          <Bar className="h-3 w-[70%]" />
        </div>
      </div>
      <Row columns={3}>
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex flex-col gap-2.5">
            <Bar className="h-5 w-[90%]" />
            <Bar className="h-3 w-full" />
            <Bar className="h-3 w-[60%]" />
          </div>
        ))}
      </Row>
      <p className="m-0 mt-[18px] text-sm text-ink2">Loading your front page…</p>
    </section>
  )
}

function Bar({ className }: { className: string }) {
  return (
    <span aria-hidden className={`block animate-sk rounded-md bg-skeleton motion-reduce:animate-none ${className}`} />
  )
}

/** Band rule, then the date (or what the sheet holds) · title · count, then a double rule. */
function Masthead(props: { left: string; title: string; right: string; front?: boolean }) {
  return (
    <header className="mb-5">
      <div aria-hidden className={`bg-band rounded-sm ${props.front ? 'h-[5px]' : 'h-[3px]'}`} />
      <div
        className={`flex flex-wrap items-baseline gap-x-4 gap-y-1.5 border-b border-ink pb-2.5 ${props.front ? 'pt-3.5' : 'pt-2.5'}`}
      >
        <span className="flex-[1_1_140px] text-[13px] text-ink2">{props.left}</span>
        <h2
          className={`text-center font-serif leading-[1.05] font-bold tracking-[-0.02em] ${props.front ? 'text-[30px] wide:text-[48px]' : 'text-2xl wide:text-[32px]'}`}
        >
          {props.title}
        </h2>
        <span className="flex-[1_1_140px] text-right text-[13px] text-ink2">{props.right}</span>
      </div>
      <div aria-hidden className="mt-[3px] h-px bg-ink" />
    </header>
  )
}

function chunks<T>(items: T[], size: number): T[][] {
  const rows: T[][] = []
  for (let i = 0; i < items.length; i += size) rows.push(items.slice(i, i + size))
  return rows
}

/** A row of stories with thin column rules; `first` = it starts the sheet (no rule above). */
function Row({ columns, first = false, children }: { columns: 3 | 4; first?: boolean; children: React.ReactNode[] }) {
  return (
    <div
      className={`grid wide:gap-y-[22px] ${columns === 3 ? 'wide:grid-cols-3' : 'wide:grid-cols-4'} ${first ? '' : 'mt-[22px] border-t border-ink pt-5'}`}
    >
      {children.map((child, i) => (
        <div key={i} className={cell(i)}>
          {child}
        </div>
      ))}
    </div>
  )
}

/**
 * Column rules between the cells of one row. Wide: a rule on the left of every cell but the
 * first. Phones (one column): a divider above every story but the first. (Class names are
 * written out in full: Tailwind only generates classes it can find in the source.)
 */
function cell(i: number) {
  return i === 0
    ? 'min-w-0 wide:pr-[18px]'
    : 'min-w-0 mt-4 border-t border-line pt-4 wide:mt-0 wide:border-t-0 wide:border-l wide:pt-0 wide:pr-[18px] wide:pl-[18px]'
}

const TITLE: Record<Size, string> = {
  lead: 'text-[32px] wide:text-[44px] leading-[1.06]',
  second: 'text-[28px] leading-[1.15]',
  standard: 'text-[21px] leading-[1.22]',
  brief: 'text-[17px] leading-[1.3]',
}
// How much of the summary each size shows (owner): the lead all of it, a second 5 lines, a
// standard 3, a brief none (headline and meta only). The detail panel always has it all.
const TEXT: Record<Size, string | null> = {
  lead: 'text-lg leading-[1.55]',
  second: 'text-[15px] leading-[1.5] line-clamp-5',
  standard: 'text-sm leading-[1.5] line-clamp-3',
  brief: null,
}

function Story(props: { bookmark: Bookmark; size: Size; faded: boolean; leaving: boolean }) {
  const { bookmark, size } = props
  const [params, setParams] = useSearchParams()
  const detail = new URLSearchParams(params)
  detail.set('bookmark', String(bookmark.id))

  // Stories show the AI summary (a brief: an Open summary button instead). Until there is one,
  // the site's own description stands in, looking the same (no source labels, owner), with the
  // Summarise button under it.
  const summarised = bookmark.summary_status === 'done' && bookmark.summary
  const description = !summarised && TEXT[size] ? bookmark.description : null
  const folder = bookmark.sources.find((s) => s.folder_path)?.folder_path
  const meta = [
    bookmark.site,
    bookmark.reading_minutes && `${bookmark.reading_minutes} min read`,
    age(bookmark.added_at),
    bookmark.read_state === 'read' && !keptInPlace.has(bookmark.id) && 'Read',
  ]

  return (
    <article
      aria-hidden={props.leaving || undefined}
      className={`flex min-w-0 flex-col ${size === 'lead' ? 'gap-3' : 'gap-2'} ${props.faded ? 'opacity-70' : ''} ${props.leaving ? 'origin-top animate-leave motion-reduce:hidden' : ''}`}
    >
      {size === 'lead' && <LeadImage bookmark={bookmark} />}
      {/* Where it's from comes first (owner): site logo, site, read time, age. */}
      <span className={`flex min-w-0 items-center gap-2 text-ink2 ${size === 'brief' ? 'text-xs' : 'text-[13px]'}`}>
        <SiteIcon iconUrl={bookmark.icon_url} site={bookmark.site} brief={size === 'brief'} />
        <span className="truncate">{meta.filter(Boolean).join(' · ')}</span>
      </span>
      {(size === 'lead' || size === 'second') && folder && (
        <span className="text-xs font-semibold tracking-[0.08em] text-ink2 uppercase">
          {folder.split('/').join(' / ')}
        </span>
      )}
      {/* wrap-anywhere: a title that's a bare URL has no spaces and would spill into the next column. */}
      <h3 className={`font-serif font-bold tracking-[-0.01em] wrap-anywhere ${TITLE[size]}`}>
        <Link to={{ search: detail.toString() }} className="text-ink no-underline hover:underline">
          {bookmark.title}
        </Link>
      </h3>

      {/* Fetching, couldn't read, needs sign-in, dead link (board Story states). */}
      <PageState bookmark={bookmark} />
      {summarised && TEXT[size] && <p className={`m-0 text-ink2 ${TEXT[size]}`}>{bookmark.summary}</p>}
      {description && <p className={`m-0 text-ink2 ${TEXT[size]}`}>{description}</p>}
      {summarised && size === 'brief' && <OpenSummary to={{ search: detail.toString() }} />}
      {/* A brief never shows its summary, so Summarise there opens the detail panel to show it
          arriving (owner). */}
      {!summarised && canSummarise(bookmark) && (
        <SummariseAction
          bookmark={bookmark}
          compact={size === 'brief'}
          onStarted={size === 'brief' ? () => setParams(detail) : undefined}
        />
      )}
    </article>
  )
}

/** The lead's preview image, loaded from the site. If it fails, the lead is text-only. */
function LeadImage({ bookmark }: { bookmark: Bookmark }) {
  const [broken, setBroken] = useState(false)
  if (!bookmark.image_url || broken) return null
  return (
    <figure className="m-0 flex flex-col gap-1.5">
      <img
        src={bookmark.image_url}
        alt=""
        referrerPolicy="no-referrer"
        onError={() => setBroken(true)}
        className="aspect-video w-full rounded-lg bg-skeleton object-cover"
      />
      <figcaption className="text-xs text-muted">Image from {bookmark.site}</figcaption>
    </figure>
  )
}
