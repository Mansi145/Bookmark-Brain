import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { api, API_URL } from '../api/client'
import type { Account, User } from '../api/types'
import { useSignOut } from '../hooks/useSignOut'
import Avatar from './Avatar'

// Settings → Account (design boards SettingsAccount, SettingsAccountDark, SettingsAccountDelete):
// Your account (who's signed in, Sign out), Download my data (a JSON file) and Delete account,
// which asks for DELETE to be typed. Both account actions only work with the web app's session
// cookie, never an extension token (backend app/api/account.py).

// A plain link: the browser downloads it with the session cookie (the server sends it as an
// attachment), so there's nothing to build or store on our side.
const EXPORT_URL = `${API_URL}/api/account/export`

const card = 'rounded-xl border border-line bg-surface p-6'
const heading = 'font-serif text-[21px] leading-[1.25] font-bold'

export default function AccountSettings({ user }: { user: User }) {
  const signOut = useSignOut()
  const [confirming, setConfirming] = useState(false)

  return (
    <>
      <section aria-labelledby="profile-title" className={card}>
        <h2 id="profile-title" className={heading}>
          Your account
        </h2>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-3.5">
          <span
            aria-hidden
            className="grid size-14 flex-none place-items-center overflow-hidden rounded-full bg-accent text-[22px] font-semibold text-on-accent"
          >
            <Avatar user={user} />
          </span>
          <div className="min-w-0 flex-[1_1_220px]">
            <div className="text-base font-semibold">{user.name ?? user.email}</div>
            <div className="truncate text-sm text-ink2">{user.email}</div>
            {/* Google is the only sign-in so far; GitHub joins when the backend supports it. */}
            <div className="mt-1 flex items-center gap-1.5 text-[13px] text-ink2">
              <GoogleMark />
              Signed in with Google
            </div>
          </div>
          <button
            type="button"
            onClick={() => signOut.mutate()}
            disabled={signOut.isPending}
            className="h-11 cursor-pointer rounded-[10px] border border-line bg-surface px-4 font-medium text-ink"
          >
            Sign out
          </button>
        </div>
        <p className="mt-3.5 text-[13px] text-ink2">
          Your name and picture come from your Google or GitHub account. Change them there.
        </p>
      </section>

      <section aria-labelledby="export-title" className={card}>
        <h2 id="export-title" className={heading}>
          Download my data
        </h2>
        <p className="mt-1.5 text-sm text-ink2">
          A JSON file with your bookmarks, folders, browsers, read states, tags and their summaries. It's ready in a few
          seconds.
        </p>
        <a
          href={EXPORT_URL}
          className="mt-3.5 inline-flex h-11 items-center gap-2 rounded-[10px] bg-ink px-[18px] font-semibold text-on-ink no-underline"
        >
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
            <path d="M12 4v11" />
            <path d="m7 10 5 5 5-5" />
            <path d="M5 20h14" />
          </svg>
          Download my data
        </a>
      </section>

      <section aria-labelledby="delete-title" className={card}>
        <h2 id="delete-title" className={`${heading} text-dead-fg`}>
          Delete account
        </h2>
        <p className="mt-1.5 text-sm text-ink2">
          Permanently deletes your account, your bookmarks, read states, tags and connected browsers. The extension
          stops syncing. This can't be undone.
        </p>
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className="mt-3.5 h-11 cursor-pointer rounded-[10px] border border-dead-fg bg-dead-fg px-4 font-semibold text-on-dead"
        >
          Delete account…
        </button>
      </section>

      {confirming && <DeleteAccountDialog onClose={() => setConfirming(false)} />}
    </>
  )
}

/** "Delete your account?" with the real counts; Delete everything stays off until DELETE is typed. */
function DeleteAccountDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const [typed, setTyped] = useState('')
  const counts = useQuery({ queryKey: ['account'], queryFn: () => api.get<Account>('/api/account') })
  const remove = useMutation({
    mutationFn: () => api.delete<void>('/api/account', { confirm: typed }),
    // The account is gone and the session cookie with it: back to the sign-up page.
    onSuccess: () => {
      queryClient.clear()
      queryClient.setQueryData(['me'], null)
      navigate('/', { replace: true })
    },
  })
  const ready = typed === 'DELETE' && !remove.isPending

  // Focus the input; Escape closes; focus goes back to "Delete account…" afterwards.
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  })
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null
    input.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCloseRef.current()
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      before?.focus()
    }
  }, [])

  const what = counts.data
    ? `${plural(counts.data.bookmarks, 'bookmark')}, ${plural(counts.data.browsers, 'connected browser')}, read states and tags`
    : 'your bookmarks, connected browsers, read states and tags'

  return (
    <div className="fixed inset-0 z-40 grid place-items-start justify-center overflow-auto p-4 pt-[150px]">
      <div aria-hidden className="fixed inset-0 bg-[rgba(20,21,22,0.55)]" onClick={onClose} />
      <form
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-body"
        onSubmit={(e) => {
          e.preventDefault()
          if (ready) remove.mutate()
        }}
        className="relative flex w-full max-w-[460px] flex-col gap-3 rounded-2xl bg-surface p-7 text-ink shadow-[0_24px_60px_rgba(0,0,0,0.35)]"
      >
        <span aria-hidden className="grid size-12 place-items-center rounded-full bg-dead-bg text-dead-fg">
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
            <path d="M4 7h16" />
            <path d="M10 11v6M14 11v6" />
            <path d="M6 7l1 13h10l1-13" />
            <path d="M9 7V4h6v3" />
          </svg>
        </span>
        <h2 id="delete-dialog-title" className="mt-1 font-serif text-2xl leading-[1.2] font-bold">
          Delete your account?
        </h2>
        <p id="delete-dialog-body" className="m-0 text-ink2">
          This permanently deletes your account and everything in it: {what}. It can't be undone.
        </p>
        <p className="m-0 text-sm text-ink2">
          Want a copy first?{' '}
          <a href={EXPORT_URL} className="font-medium text-ink">
            Download my data
          </a>
        </p>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Type DELETE to confirm
          <input
            ref={input}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            autoComplete="off"
            placeholder="DELETE"
            className="h-11 rounded-[10px] border border-line bg-surface px-3 font-normal text-ink"
          />
        </label>
        <div className="mt-1 flex flex-wrap gap-2.5">
          <button
            type="submit"
            disabled={!ready}
            className="h-11 cursor-pointer rounded-[10px] border-0 bg-dead-fg px-[18px] font-semibold text-on-dead disabled:cursor-default disabled:opacity-50"
          >
            {remove.isPending ? 'Deleting…' : 'Delete everything'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="h-11 cursor-pointer rounded-[10px] border border-line bg-surface px-4 font-medium text-ink"
          >
            Cancel
          </button>
        </div>
        {remove.isError ? (
          <p role="alert" className="m-0 text-[13px] text-dead-fg">
            Couldn't delete your account. Please try again.
          </p>
        ) : (
          <p className="m-0 text-[13px] text-ink2">The button turns on once DELETE is typed.</p>
        )}
      </form>
    </div>
  )
}

function plural(n: number, word: string) {
  return `${n} ${n === 1 ? word : `${word}s`}`
}

function GoogleMark() {
  return (
    <svg aria-hidden width="14" height="14" viewBox="0 0 48 48" className="flex-none">
      <path
        fill="#EA4335"
        d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
      />
      <path
        fill="#FBBC05"
        d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
      />
    </svg>
  )
}
