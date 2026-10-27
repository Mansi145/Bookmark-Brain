import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { limitHit } from '../lib/limit'

// Limit reached (design board LimitDialog): opens when Summarise, Re-summarise or Ask is refused
// because today's shared AI allowance is used up. "Notify the maintainer" emails the owner the
// user's account email and the time (POST /api/usage/notify-maintainer, sent with Resend).
// States: default → Sending… → "Thanks, the maintainer knows". There's no "couldn't send"
// screen (owner): if the email fails, the button simply comes back so they can press it again.

/** Mounted once in the layout; opens whenever an AI action hits the limit. */
export function LimitDialogHost() {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const onHit = () => setOpen(true)
    limitHit.addEventListener('hit', onHit)
    return () => limitHit.removeEventListener('hit', onHit)
  }, [])
  // Mounted fresh each time, so it always opens in its default state.
  return open ? <LimitDialog onClose={() => setOpen(false)} /> : null
}

function LimitDialog({ onClose }: { onClose: () => void }) {
  const notify = useMutation({ mutationFn: () => api.post<void>('/api/usage/notify-maintainer') })
  const sent = notify.isSuccess
  const notifyButton = useRef<HTMLButtonElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)

  // Focus starts on the main button and moves to Close once it's sent; on closing it goes back
  // to whatever was focused before (usually the Summarise button that opened this).
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null
    notifyButton.current?.focus()
    return () => before?.focus()
  }, [])
  useEffect(() => {
    if (sent) closeButton.current?.focus()
  }, [sent])

  // Escape closes. Listened for on window in the capture phase and stopped there, so the
  // detail panel underneath (which also closes on Escape) stays open.
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  })
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.stopPropagation()
      onCloseRef.current()
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [])

  return (
    <div className="fixed inset-0 z-40 grid place-items-center overflow-auto p-4">
      <div aria-hidden className="absolute inset-0 bg-[rgba(20,21,22,0.55)]" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="limit-title"
        className="relative flex w-full max-w-[440px] flex-col gap-3 rounded-2xl bg-surface p-7 text-ink shadow-[0_24px_60px_rgba(0,0,0,0.35)]"
      >
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="absolute top-3.5 right-3.5 grid size-9 cursor-pointer place-items-center rounded-full border-0 bg-transparent text-ink2"
        >
          <svg
            aria-hidden
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        </button>
        <span aria-hidden className="grid size-12 place-items-center rounded-full bg-accent text-on-accent">
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {sent ? (
              <path d="m5 12 4.5 4.5L19 7" />
            ) : (
              <>
                <path d="M4 15a8 8 0 1 1 16 0" />
                <path d="m12 15 4-5" />
                <path d="M3 19h18" />
              </>
            )}
          </svg>
        </span>

        {/* Announced when it changes to the "sent" text. */}
        <div aria-live="polite" className="flex flex-col gap-3">
          <h2 id="limit-title" className="mt-1 font-serif text-2xl leading-[1.2] font-bold">
            {sent ? 'Thanks, the maintainer knows' : 'Limit reached'}
          </h2>
          {sent ? (
            <p className="m-0 text-ink2">
              They've been emailed that today's limit was reached. Summaries and Ask come back at midnight UTC.
            </p>
          ) : (
            <>
              <p className="m-0 text-ink2">
                Today's AI allowance has run out. Bookmark Brain is a personal learning project on free plans, so this
                can happen early in the day. Summaries and Ask come back at midnight UTC.
              </p>
              <p className="m-0 font-semibold text-ink">Please click below to notify the maintainer.</p>
            </>
          )}
        </div>

        <div className="mt-1 flex flex-wrap gap-2.5">
          {!sent && (
            <button
              ref={notifyButton}
              type="button"
              onClick={() => notify.mutate()}
              disabled={notify.isPending}
              aria-busy={notify.isPending || undefined}
              className="flex h-11 cursor-pointer items-center gap-2 rounded-[10px] border-0 bg-ink px-[18px] font-semibold text-on-ink disabled:cursor-default disabled:opacity-75"
            >
              {notify.isPending ? (
                <svg
                  aria-hidden
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  className="animate-spin motion-reduce:animate-none"
                >
                  <path d="M12 3a9 9 0 1 0 9 9" />
                </svg>
              ) : (
                <svg
                  aria-hidden
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="3" y="5" width="18" height="14" rx="2" />
                  <path d="m3 7 9 6 9-6" />
                </svg>
              )}
              {notify.isPending ? 'Sending…' : 'Notify the maintainer'}
            </button>
          )}
          <button
            ref={closeButton}
            type="button"
            onClick={onClose}
            className="h-11 cursor-pointer rounded-[10px] border border-line bg-surface px-4 font-medium text-ink"
          >
            Close
          </button>
        </div>
        {!sent && (
          <p className="m-0 text-[13px] text-ink2">
            Sends the maintainer your account email and the time you hit the limit.
          </p>
        )}
      </div>
    </div>
  )
}
