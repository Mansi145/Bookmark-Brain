import type { Bookmark } from '../api/types'
import { useSummarise } from '../hooks/useSummarise'
import { useUsage } from '../hooks/useUsage'
import { ProgressPill, RowButton } from './RowButton'

// The summary area of a row (design board RowStates, "Summarise" group). Summaries are made
// on demand: idle → Summarise button; working → "Summarising…" pill; done → the 2-line
// summary; failed → "Couldn't summarise this page." + Try again; daily limit → button
// disabled + "Daily summary limit reached · resets at midnight UTC".

/** The AI summary, or the site's own description; both look the same (owner's decision). */
export function SummaryText({ bookmark }: { bookmark: Bookmark }) {
  const text = bookmark.summary ?? bookmark.description
  if (!text) return null
  return <p className="m-0 line-clamp-2 max-w-[760px] text-sm text-ink2">{text}</p>
}

export function SummariseAction({ bookmark }: { bookmark: Bookmark }) {
  const summarise = useSummarise(bookmark.id)
  const { limitReached } = useUsage()

  if (summarise.isPending || bookmark.summary_status === 'working') {
    return <ProgressPill>Summarising…</ProgressPill>
  }
  if (bookmark.summary_status === 'done') return null

  const blocked = limitReached || summarise.hitLimit
  if ((bookmark.summary_status === 'failed' || summarise.isError) && !blocked) {
    return (
      <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-sm text-ink2">Couldn't summarise this page.</span>
        <RowButton onClick={() => summarise.mutate(false)}>Try again</RowButton>
      </div>
    )
  }
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <RowButton icon={LINES} onClick={() => summarise.mutate(false)} disabled={blocked} label={`Summarise ${bookmark.title}`}>
        Summarise
      </RowButton>
      {blocked && <span className="text-[13px] text-muted">Daily summary limit reached · resets at midnight UTC</span>}
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
