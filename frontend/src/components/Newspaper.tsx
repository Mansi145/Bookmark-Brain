import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import type { Bookmark, ReadState } from '../api/types'
import { editionDate, type Edition } from '../lib/editions'
import { age } from '../lib/format'
import { canSummarise } from '../lib/summaries'
import { ProgressPill } from './RowButton'
import SiteIcon from './SiteIcon'
import { SummariseAction } from './Summarise'

// The main feed as a classic newspaper front page (design board NewsClassic). Today / This
// week / Earlier are editions: one sheet each, with a masthead and thin column rules instead
// of a card per article. Newest unread stories are biggest (lead → second → standard →
// brief) and read ones go last, faded. Only the very first story (the lead) shows the page's
// preview image; a lead without one is text-only.

type Size = 'lead' | 'second' | 'standard' | 'brief'

export default function Newspaper(props: {
  editions: Edition[]
  complete: boolean
  view: ReadState | null // the views bar: All (null), Unread or Read
}) {
  return (
    <div className="flex flex-col gap-6">
      {props.editions.map((edition, i) => (
        <EditionSheet
          key={edition.key}
          edition={edition}
          // The first edition is the front page; Earlier is always briefs.
          layout={i === 0 ? 'front' : edition.key === 'earlier' ? 'briefs' : 'middle'}
          // Earlier keeps growing as more pages load, so only count it once everything's here.
          complete={edition.key !== 'earlier' || props.complete}
          view={props.view}
        />
      ))}
    </div>
  )
}

function EditionSheet(props: {
  edition: Edition
  layout: 'front' | 'middle' | 'briefs'
  complete: boolean
  view: ReadState | null
}) {
  const { edition, layout } = props
  // Unread first, newest first; read ones last (also newest first).
  const stories = [
    ...edition.items.filter((b) => b.read_state === 'unread'),
    ...edition.items.filter((b) => b.read_state === 'read'),
  ]
  const unread = edition.items.length - edition.items.filter((b) => b.read_state === 'read').length
  const front = layout === 'front'
  const title = edition.key === 'today' ? "Today's edition" : edition.title

  const n = stories.length
  const count =
    edition.key === 'today'
      ? `${n} new · ${unread === n ? 'all unread' : `${unread} unread`}`
      : edition.key === 'week'
        ? `${n} ${n === 1 ? 'bookmark' : 'bookmarks'} · ${unread} unread`
        : `${n}${props.complete ? '' : '+'} ${n === 1 ? 'bookmark' : 'bookmarks'}`

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
      // All bookmarks: read stories stay, faded. Unread / Read: a story just marked the other
      // way fades out until the feed refetches without it.
      faded={props.view === null && b.read_state === 'read'}
      leaving={props.view !== null && b.read_state !== props.view}
    />
  )

  return (
    <section aria-label={title} className="rounded-xl border border-line bg-surface p-5 sm:p-7">
      <header className="mb-5">
        <div aria-hidden className={`bg-band rounded-sm ${front ? 'h-[5px]' : 'h-[3px]'}`} />
        <div
          className={`flex flex-wrap items-baseline gap-x-4 gap-y-1.5 border-b border-ink pb-2.5 ${front ? 'pt-3.5' : 'pt-2.5'}`}
        >
          <span className="flex-[1_1_140px] text-[13px] text-ink2">{editionDate(edition.key)}</span>
          <h2
            className={`text-center font-serif leading-[1.05] font-bold tracking-[-0.02em] ${front ? 'text-[36px] sm:text-[48px]' : 'text-[28px] sm:text-[32px]'}`}
          >
            {title}
          </h2>
          <span className="flex-[1_1_140px] text-right text-[13px] text-ink2">{count}</span>
        </div>
        <div aria-hidden className="mt-[3px] h-px bg-ink" />
      </header>

      {front && top.length > 0 && (
        <>
          <div className={`grid ${top.length > 1 ? 'md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]' : ''}`}>
            <div className={top.length > 1 ? 'md:border-r md:border-line md:pr-6' : ''}>{story(top[0], 'lead')}</div>
            {top.length > 1 && (
              <div className="mt-5 flex flex-col gap-5 border-t border-line pt-5 md:mt-0 md:border-t-0 md:pt-0 md:pl-6">
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
        <div className="grid gap-y-5 sm:grid-cols-2 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)]">
          {top.map((b, i) => (
            <div key={b.id} className={cell(i, 3)}>
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
    </section>
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
      className={`grid gap-y-5 sm:grid-cols-2 ${columns === 3 ? 'md:grid-cols-3' : 'lg:grid-cols-4'} ${first ? '' : 'mt-[22px] border-t border-ink pt-5'}`}
    >
      {children.map((child, i) => (
        <div key={i} className={cell(i, columns)}>
          {child}
        </div>
      ))}
    </div>
  )
}

/**
 * Column rules between cells. Phones: one column, a rule above each story. Small screens: two
 * columns. Wide: `columns` columns. A cell that starts a row has no rule on its left. (Class
 * names are written out in full: Tailwind only generates classes it can find in the source.)
 */
function cell(i: number, columns: 3 | 4) {
  const classes = ['min-w-0 sm:pr-[18px]']
  if (i > 0) classes.push('border-t border-line pt-5 sm:border-t-0 sm:pt-0')
  classes.push(i % 2 === 1 ? 'sm:border-l sm:border-line sm:pl-[18px]' : 'sm:border-l-0 sm:pl-0')
  if (columns === 3) classes.push(i % 3 === 0 ? 'md:border-l-0 md:pl-0' : 'md:border-l md:pl-[18px]')
  else classes.push(i % 4 === 0 ? 'lg:border-l-0 lg:pl-0' : 'lg:border-l lg:pl-[18px]')
  return classes.join(' ')
}

const TITLE: Record<Size, string> = {
  lead: 'text-[32px] sm:text-[44px] leading-[1.06]',
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

  // Stories show the AI summary; one that isn't summarised yet shows its Summarise button.
  const summarised = bookmark.summary_status === 'done' && bookmark.summary
  const folder = bookmark.sources.find((s) => s.folder_path)?.folder_path
  const meta = [
    bookmark.site,
    bookmark.reading_minutes && `${bookmark.reading_minutes} min read`,
    age(bookmark.added_at),
    bookmark.read_state === 'read' && 'Read',
  ]

  return (
    <article
      aria-hidden={props.leaving || undefined}
      className={`flex min-w-0 flex-col ${size === 'lead' ? 'gap-3' : 'gap-2'} ${props.faded ? 'opacity-70' : ''} ${props.leaving ? 'origin-top animate-leave motion-reduce:hidden' : ''}`}
    >
      {size === 'lead' && <LeadImage bookmark={bookmark} />}
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

      {bookmark.status === 'pending' && <ProgressPill bar={false}>Fetching page…</ProgressPill>}
      {summarised && TEXT[size] && <p className={`m-0 text-ink2 ${TEXT[size]}`}>{bookmark.summary}</p>}
      {/* A brief never shows its summary, so Summarise there opens the detail panel to show it
          arriving (owner). */}
      {!summarised && canSummarise(bookmark) && (
        <SummariseAction
          bookmark={bookmark}
          compact={size === 'brief'}
          onStarted={size === 'brief' ? () => setParams(detail) : undefined}
        />
      )}

      <span className={`flex min-w-0 items-center gap-2 text-ink2 ${size === 'brief' ? 'text-xs' : 'text-[13px]'}`}>
        <SiteIcon iconUrl={bookmark.icon_url} site={bookmark.site} brief={size === 'brief'} />
        <span className="truncate">{meta.filter(Boolean).join(' · ')}</span>
      </span>
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
