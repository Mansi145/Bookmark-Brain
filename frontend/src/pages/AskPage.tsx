import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'
import { ApiError } from '../api/client'
import type { Bookmark, ChatSources } from '../api/types'
import AnswerText from '../components/AnswerText'
import BookmarkDetail from '../components/BookmarkDetail'
import FreePlanNote from '../components/FreePlanNote'
import SiteIcon from '../components/SiteIcon'
import { setAskWaiting, streamChat, type ChatStep } from '../lib/ask'
import { openLimitDialog } from '../lib/limit'

// Ask your bookmarks (design boards Ask, AskEmpty, AskWriting, AskStopped, AskNothingFound,
// AskPhone, AskPhoneSources and their dark versions): the conversation on one panel, the latest
// answer's Sources on another (on phones, a folded "Sources (n)" row under each answer instead).
//
// A question goes to POST /api/chat, which streams what the agent does (lib/ask.ts): each step
// appears as a check line when it's done, then the answer word by word with a caret; citations
// and sources arrive at the end. While it works, Send becomes Stop; stopping keeps what was
// written, with a "Stopped" line. Follow-ups stay in the same chat (the server keeps it in memory
// while it's open). Only a chat's first question is kept for good, for the Ask tab's Recent
// questions, which open this page with { ask } or { newChat } in the navigation state.

type Step = { id: string; tool: string; args: Record<string, unknown>; found?: number; title?: string }

type Turn = {
  question: string
  steps: Step[]
  draft: string // the answer so far; text written before a step is dropped
  status: 'searching' | 'writing' | 'done' | 'stopped'
  answer?: ChatSources
}

// The empty page's suggestion pills: questions anyone's bookmarks can answer.
const SUGGESTIONS = [
  'What have I saved about learning to code?',
  'Which of my bookmarks are about cooking?',
  'Find my bookmarks about travel',
  'What did I save about productivity?',
]

export default function AskPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [turns, setTurns] = useState<Turn[]>([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const chatId = useRef<string | null>(null)
  const controller = useRef<AbortController | null>(null)
  // Each request gets a number; only the latest may change the page, so an answer abandoned by
  // New chat can't land in the new chat.
  const runs = useRef(0)
  const input = useRef<HTMLTextAreaElement>(null)
  const thread = useRef<HTMLDivElement>(null)

  /** Change the latest turn. */
  const update = (change: (turn: Turn) => Turn) =>
    setTurns((all) => (all.length ? [...all.slice(0, -1), change(all[all.length - 1])] : all))

  const ask = async (question: string) => {
    if (controller.current) return
    const run = ++runs.current
    const live = () => run === runs.current
    const first = chatId.current === null
    const abort = new AbortController()
    controller.current = abort
    setBusy(true)
    setText('')
    setTurns((all) => [...all, { question, steps: [], draft: '', status: 'searching' }])
    setAskWaiting(true)

    // A question that got no answer at all goes back in the box, so it can be sent again.
    const giveUp = () => {
      setTurns((all) => all.slice(0, -1))
      setText(question)
    }
    try {
      await streamChat(
        { message: question, chat_id: chatId.current },
        (event) => {
          if (!live()) return
          if (event.kind === 'chat') {
            chatId.current = event.data.chat_id
            if (first) void queryClient.invalidateQueries({ queryKey: ['ask', 'recent'] })
          } else if (event.kind === 'step') {
            update((turn) => withStep(turn, event.data))
          } else if (event.kind === 'token') {
            setAskWaiting(false)
            update((turn) => ({ ...turn, draft: turn.draft + event.data.text, status: 'writing' }))
          } else if (event.kind === 'done') {
            update((turn) => ({ ...turn, draft: event.data.answer, answer: event.data, status: 'done' }))
          } else if (event.kind === 'error') {
            giveUp()
            openLimitDialog('busy')
          }
        },
        abort.signal,
      )
    } catch (error) {
      if (!live()) return
      if (abort.signal.aborted) {
        update((turn) => ({ ...turn, status: 'stopped' }))
      } else if (error instanceof ApiError && error.status === 429) {
        giveUp()
        openLimitDialog('limit')
      } else {
        giveUp()
        openLimitDialog('busy')
      }
    } finally {
      if (live()) {
        controller.current = null
        setBusy(false)
        setAskWaiting(false)
      }
    }
  }

  const stop = () => controller.current?.abort()

  /** Drop the chat (stopping an answer in progress) and start empty. */
  const reset = () => {
    runs.current++
    controller.current?.abort()
    controller.current = null
    chatId.current = null
    setBusy(false)
    setAskWaiting(false)
    setTurns([])
  }

  const newChat = () => {
    reset()
    setText('')
    input.current?.focus()
  }

  // The Ask tab's dropdown: New chat, or a recent question asked again in a new chat. The note
  // in the navigation's state is used once, then cleared, so Back or a reload doesn't repeat it
  // (and React running effects twice in development doesn't either).
  const handled = useRef<string | null>(null)
  const state = location.state as { newChat?: true; ask?: string } | null
  const startOver = (question?: string) => {
    reset()
    setText('')
    if (question) void ask(question)
  }
  const startOverRef = useRef(startOver)
  useEffect(() => {
    startOverRef.current = startOver
  })
  const { key, pathname, search } = location
  useEffect(() => {
    if (!state || handled.current === key) return
    handled.current = key
    navigate({ pathname, search }, { replace: true, state: null })
    queueMicrotask(() => startOverRef.current(state.ask))
  }, [key, pathname, search, state, navigate])

  // Leaving the page stops an answer in progress.
  useEffect(
    () => () => {
      runs.current++
      controller.current?.abort()
      setAskWaiting(false)
    },
    [],
  )

  // Keep the newest turn in view as it grows.
  const last = turns.at(-1)
  useEffect(() => {
    thread.current?.lastElementChild?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [turns.length, last?.status, last?.steps.length])

  // The detail panel (?bookmark=<id>), as in the feed: Back closes it.
  const openId = Number(params.get('bookmark')) || null
  const open = (id: number) => {
    const next = new URLSearchParams(params)
    next.set('bookmark', String(id))
    setParams(next)
  }
  const closeDetail = () => {
    const next = new URLSearchParams(params)
    next.delete('bookmark')
    setParams(next, { replace: true })
  }

  const send = () => {
    const question = text.trim()
    if (question && !busy) void ask(question)
  }
  const latestAnswer = [...turns].reverse().find((turn) => turn.answer)?.answer

  return (
    <div className="mx-auto flex max-w-[1280px] flex-wrap items-stretch gap-6 px-3.5 pt-3.5 pb-8 wide:px-6 wide:pt-8 wide:pb-12">
      <main className="flex min-w-0 flex-[999_1_520px] flex-col gap-[18px] rounded-2xl bg-panel p-4 wide:p-6">
        {turns.length === 0 ? (
          <Empty onPick={(question) => void ask(question)} />
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2.5">
              <h1 className="m-0 font-serif text-2xl font-bold">{turns[0].question}</h1>
              <button
                type="button"
                onClick={newChat}
                className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-[10px] border border-line bg-surface px-3.5 text-sm font-medium text-ink"
              >
                <svg
                  aria-hidden
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                >
                  <path d="M12 5v14M5 12h14" />
                </svg>
                New chat
              </button>
            </div>
            <div ref={thread} className="flex flex-1 flex-col gap-4">
              {turns.map((turn, i) => (
                <TurnView key={i} turn={turn} onOpen={open} />
              ))}
            </div>
          </>
        )}

        <form
          className="m-0 flex flex-col gap-1.5"
          onSubmit={(e) => {
            e.preventDefault()
            send()
          }}
        >
          <div className="flex items-end gap-2 rounded-[14px] border border-line bg-surface py-2 pr-2 pl-3.5">
            <label className="flex flex-1">
              <span className="sr-only">Ask your bookmarks</span>
              <textarea
                ref={input}
                rows={2}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  // Enter sends; Shift+Enter starts a new line.
                  if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault()
                    send()
                  }
                }}
                maxLength={2000}
                placeholder={turns.length ? 'Ask a follow-up…' : 'Ask your bookmarks…'}
                className="min-h-11 flex-1 resize-none border-0 bg-transparent font-[inherit] text-ink outline-none placeholder:text-muted"
              />
            </label>
            {busy ? (
              <button
                type="button"
                onClick={stop}
                aria-label="Stop answering"
                className="flex h-11 flex-none cursor-pointer items-center gap-2 rounded-[10px] border-0 bg-ink px-3.5 font-semibold text-on-ink"
              >
                <svg aria-hidden width="14" height="14" viewBox="0 0 24 24">
                  <rect x="5" y="5" width="14" height="14" rx="2" fill="currentColor" />
                </svg>
                Stop
              </button>
            ) : (
              <button
                type="submit"
                aria-label="Send"
                className="grid size-11 flex-none cursor-pointer place-items-center rounded-[10px] border-0 bg-ink text-on-ink"
              >
                <svg
                  aria-hidden
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 12h14" />
                  <path d="m13 6 6 6-6 6" />
                </svg>
              </button>
            )}
          </div>
          <p className="m-0 text-[13px] text-muted">Answers use only pages you've saved, and link to each one.</p>
          <FreePlanNote />
        </form>
      </main>

      <aside
        aria-label="Sources"
        className="hidden max-w-[300px] flex-[1_1_260px] flex-col gap-2.5 rounded-2xl bg-panel px-3.5 py-[18px] wide:flex"
      >
        <h2 className={RAIL_HEADING}>Sources</h2>
        {!latestAnswer ? (
          <p className="m-0 px-1.5 text-sm text-ink2">The bookmarks an answer uses show up here.</p>
        ) : (
          <SourceList answer={latestAnswer} onOpen={open} />
        )}
      </aside>

      {openId && <BookmarkDetail key={openId} id={openId} onClose={closeDetail} />}
    </div>
  )
}

const RAIL_HEADING = 'm-0 px-1.5 text-xs font-semibold tracking-[0.06em] text-ink2 uppercase'

/** A step from the stream: a new one when it starts, filled in when it's done. A step after
 * some answer text means that text wasn't the answer, so it's dropped. */
function withStep(turn: Turn, step: ChatStep): Turn {
  if (step.status === 'running') {
    return {
      ...turn,
      draft: '',
      status: 'searching',
      steps: [...turn.steps, { id: step.id, tool: step.tool, args: step.args }],
    }
  }
  return {
    ...turn,
    steps: turn.steps.map((s) => (s.id === step.id ? { ...s, found: step.found, title: step.title } : s)),
  }
}

function TurnView({ turn, onOpen }: { turn: Turn; onOpen: (id: number) => void }) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const numbers = new Map((turn.answer?.sources ?? []).map((b, i) => [b.id, i + 1]))
  const done = turn.steps.filter((step) => step.found !== undefined)

  return (
    <>
      <p className="m-0 max-w-[75%] self-end rounded-[14px_14px_4px_14px] bg-ink px-3.5 py-2.5 whitespace-pre-wrap text-on-ink">
        {turn.question}
      </p>
      {done.length > 0 && (
        <ul aria-label="What the agent did" className="m-0 flex list-none flex-col gap-1 p-0 text-[13px] text-ink2">
          {stepLines(done).map((line, i) => (
            <li key={i} className="flex items-center gap-2">
              <svg
                aria-hidden
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="flex-none"
              >
                <path d="m5 12 4.5 4.5L19 7" />
              </svg>
              {line}
            </li>
          ))}
        </ul>
      )}

      {turn.status === 'searching' ? (
        <div role="status" className="flex flex-col gap-2.5">
          <span className="flex items-center gap-1.5 self-start rounded-full bg-accent2 px-2.5 py-[3px] text-[13px] font-medium text-on-accent">
            <svg
              aria-hidden
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              className="animate-spin motion-reduce:animate-none"
            >
              <path d="M12 3a9 9 0 1 0 9 9" />
            </svg>
            Searching your bookmarks…
          </span>
          <span aria-hidden className="h-2.5 w-[70%] animate-sk rounded bg-skeleton motion-reduce:animate-none" />
          <span aria-hidden className="h-2.5 w-[52%] animate-sk rounded bg-skeleton motion-reduce:animate-none" />
        </div>
      ) : (
        <div
          aria-live={turn.status === 'writing' ? 'polite' : undefined}
          className="max-w-[88%] rounded-[14px_14px_14px_4px] border border-line bg-surface px-[18px] py-4"
        >
          <AnswerText text={turn.draft} numbers={numbers} onOpen={onOpen} writing={turn.status === 'writing'} />
        </div>
      )}

      {turn.status === 'stopped' && (
        <p className="-mt-2 mb-0 flex items-center gap-1.5 text-[13px] text-muted">
          <svg aria-hidden width="12" height="12" viewBox="0 0 24 24">
            <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
          </svg>
          Stopped
        </p>
      )}

      {/* Phones: the Sources panel is hidden, and each answer's sources fold in under it. */}
      {turn.answer && turn.answer.sources.length + turn.answer.also_found.length > 0 && (
        <div className="flex max-w-[88%] flex-col gap-2 wide:hidden">
          <button
            type="button"
            aria-expanded={sourcesOpen}
            onClick={() => setSourcesOpen(!sourcesOpen)}
            className="flex h-10 w-full cursor-pointer items-center justify-between rounded-[10px] border border-line bg-surface px-3 text-sm font-semibold text-ink"
          >
            Sources ({turn.answer.sources.length})
            <svg
              aria-hidden
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d={sourcesOpen ? 'm6 15 6-6 6 6' : 'm6 9 6 6 6-6'} />
            </svg>
          </button>
          {sourcesOpen && <SourceList answer={turn.answer} onOpen={onOpen} compact />}
        </div>
      )}
    </>
  )
}

/** The check lines: "Searched your bookmarks for "…" · 4 found", and the pages read in a row
 * as one line: "Read "A" and "B"". */
function stepLines(steps: Step[]): string[] {
  const lines: string[] = []
  let reads: string[] = []
  const flushReads = () => {
    if (reads.length) lines.push(`Read ${joinTitles(reads)}`)
    reads = []
  }
  for (const step of steps) {
    if (step.tool === 'read_bookmark') {
      if (step.title) reads.push(`“${step.title}”`)
      continue
    }
    flushReads()
    const query = typeof step.args.query === 'string' ? step.args.query : ''
    lines.push(`Searched your bookmarks for “${query}” · ${step.found} found`)
  }
  flushReads()
  return lines
}

function joinTitles(titles: string[]) {
  return titles.length < 2 ? titles.join('') : `${titles.slice(0, -1).join(', ')} and ${titles.at(-1)}`
}

/** Sources (numbered, as cited) and Also found, in the rail or folded under an answer. */
function SourceList({
  answer,
  onOpen,
  compact = false,
}: {
  answer: ChatSources
  onOpen: (id: number) => void
  compact?: boolean
}) {
  if (answer.sources.length === 0 && answer.also_found.length === 0) {
    return <p className="m-0 px-1.5 text-sm text-ink2">No sources for this answer.</p>
  }
  return (
    <>
      {answer.sources.map((bookmark, i) => (
        <button
          key={bookmark.id}
          type="button"
          onClick={() => onOpen(bookmark.id)}
          className={`flex cursor-pointer flex-col border border-line bg-surface text-left font-[inherit] text-ink ${compact ? 'gap-0.5 rounded-[10px] px-3 py-2.5' : 'gap-1 rounded-xl px-3.5 py-3'}`}
        >
          {compact ? (
            <span className="text-xs text-ink2">
              {i + 1} · {bookmark.site}
            </span>
          ) : (
            <span className="flex items-center gap-2 text-[13px] text-ink2">
              <span
                aria-hidden
                className="grid h-[18px] min-w-[18px] place-items-center rounded-[5px] bg-accent px-1 text-[11px] font-semibold text-on-accent"
              >
                {i + 1}
              </span>
              <SiteIcon iconUrl={bookmark.icon_url} site={bookmark.site} />
              {bookmark.site}
            </span>
          )}
          <span className={`font-serif leading-[1.25] font-bold ${compact ? 'text-base' : 'text-[17px]'}`}>
            {bookmark.title}
          </span>
        </button>
      ))}
      {answer.also_found.length > 0 && (
        <>
          <h2 className={`${RAIL_HEADING} ${compact ? 'mt-1' : 'mt-2.5'}`}>Also found</h2>
          {answer.also_found.map((bookmark: Bookmark) => (
            <button
              key={bookmark.id}
              type="button"
              onClick={() => onOpen(bookmark.id)}
              className="flex cursor-pointer items-center gap-2 border-0 bg-transparent p-1.5 text-left font-[inherit] text-sm text-ink"
            >
              {!compact && <SiteIcon iconUrl={bookmark.icon_url} site={bookmark.site} />}
              {bookmark.title}
            </button>
          ))}
        </>
      )}
    </>
  )
}

/** The empty page (board AskEmpty). */
function Empty({ onPick }: { onPick: (question: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2.5 px-3 py-12 text-center">
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
          <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
        </svg>
      </span>
      <h1 className="mt-1.5 mb-0 font-serif text-[32px] font-bold">Ask your bookmarks</h1>
      <p className="m-0 max-w-[460px] text-ink2">
        Get answers drawn only from the pages you've saved, with a link to every source.
      </p>
      <div className="mt-4 flex max-w-[620px] flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onPick(question)}
            className="min-h-10 cursor-pointer rounded-full border border-line bg-surface px-3.5 py-2 font-[inherit] text-sm text-ink"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  )
}
