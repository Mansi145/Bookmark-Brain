import type { To } from 'react-router'
import type { Bookmark } from '../api/types'
import { useSummarise } from '../hooks/useSummarise'
import { ProgressPill, RowButton, RowLink } from './RowButton'

// A story's Summarise button and its states (design board Story states, "Summarise" sheet).
// Summaries are made on demand: idle → Summarise button; working → "Summarising…" pill and a
// pulsing bar; done → the story shows the summary; failed → "Couldn't summarise this page." +
// Try again. At the daily limit there's no inline text: pressing Summarise opens the Limit
// reached dialog.

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

/** A brief that has a summary: it doesn't show it, so this opens the detail panel (owner). */
export function OpenSummary({ to }: { to: To }) {
  return (
    <RowLink to={to} icon={LINES} compact>
      Open summary
    </RowLink>
  )
}

const LINES = (
  <>
    <path d="M4 6h16" />
    <path d="M4 12h12" />
    <path d="M4 18h8" />
  </>
)
