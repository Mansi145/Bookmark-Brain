import type { Bookmark } from '../api/types'
import { useSummarise } from '../hooks/useSummarise'
import { ProgressPill, RowButton } from './RowButton'

// The summary area of a row (design board RowStates, "Summarise" group). Summaries are made
// on demand: idle → Summarise button; working → "Summarising…" pill; done → the 2-line
// summary; failed → "Couldn't summarise this page." + Try again. At the daily limit there's
// no inline text (board "Story states"): pressing Summarise opens the Limit reached dialog.

/** The AI summary, or the site's own description; both look the same (owner's decision). */
export function SummaryText({ bookmark }: { bookmark: Bookmark }) {
  const text = bookmark.summary ?? bookmark.description
  if (!text) return null
  return <p className="m-0 line-clamp-2 max-w-[760px] text-sm text-ink2">{text}</p>
}

/**
 * `compact`: the smaller button on the newspaper's briefs. `onStarted` runs once the server has
 * accepted the request (briefs use it to open the detail panel, since they never show a summary).
 */
export function SummariseAction(props: { bookmark: Bookmark; compact?: boolean; onStarted?: () => void }) {
  const { bookmark, compact = false } = props
  const summarise = useSummarise(bookmark.id)
  const start = () => summarise.mutate(false, { onSuccess: props.onStarted })

  if (summarise.isPending || bookmark.summary_status === 'working') {
    return <ProgressPill>Summarising…</ProgressPill>
  }
  if (bookmark.summary_status === 'done') return null

  if (bookmark.summary_status === 'failed' || (summarise.isError && !summarise.hitLimit)) {
    return (
      <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-sm text-ink2">Couldn't summarise this page.</span>
        <RowButton onClick={start} compact={compact}>
          Try again
        </RowButton>
      </div>
    )
  }
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <RowButton icon={LINES} onClick={start} label={`Summarise ${bookmark.title}`} compact={compact}>
        Summarise
      </RowButton>
    </div>
  )
}

const LINES = (
  <>
    <path d="M4 6h16" />
    <path d="M4 12h12" />
    <path d="M4 18h8" />
  </>
)
