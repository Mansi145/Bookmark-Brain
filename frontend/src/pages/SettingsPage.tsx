import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api, API_URL } from '../api/client'
import type { ApiToken, CreatedApiToken } from '../api/types'
import AccountSettings from '../components/AccountSettings'
import { useMe } from '../hooks/useMe'

// Settings (design board Settings.dc.html): the section menu on one panel, the sections as cards
// on another. The menu switches between Browsers (connect a browser, one-click first and by hand
// as a fold, then the connected browsers) and Account (?section=account, AccountSettings).

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

const card = 'rounded-xl border border-line bg-surface'
const heading = 'font-serif text-[21px] leading-[1.25] font-bold'

export default function SettingsPage() {
  const [params] = useSearchParams()
  const section = params.get('section') === 'account' ? 'account' : 'browsers'
  const me = useMe()
  const queryClient = useQueryClient()
  const [name, setName] = useState('Browser extension')
  const [created, setCreated] = useState<CreatedApiToken | null>(null)

  const tokens = useQuery({ queryKey: ['tokens'], queryFn: () => api.get<ApiToken[]>('/api/tokens') })

  const create = useMutation({
    mutationFn: () => api.post<CreatedApiToken>('/api/tokens', { name }),
    onSuccess: (token) => {
      setCreated(token)
      queryClient.invalidateQueries({ queryKey: ['tokens'] })
    },
  })

  const revoke = useMutation({
    mutationFn: (id: number) => api.delete(`/api/tokens/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tokens'] }),
  })

  const connected = tokens.data?.filter((t) => t.last_used_at).length ?? 0

  return (
    <div className="mx-auto flex max-w-[1280px] flex-wrap items-start gap-8 px-6 pt-8 pb-16">
      <nav
        aria-label="Settings sections"
        className="flex max-w-[260px] flex-[1_1_220px] flex-col gap-0.5 rounded-2xl bg-panel px-3.5 py-[18px]"
      >
        <h2 className="mb-2 px-2.5 text-xs font-semibold tracking-[0.06em] text-ink2 uppercase">Settings</h2>
        <SectionLink to="/settings" current={section === 'browsers'}>
          Browsers
        </SectionLink>
        <SectionLink to="/settings?section=account" current={section === 'account'}>
          Account
        </SectionLink>
      </nav>

      <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-4 rounded-2xl bg-panel p-6">
        <div className="mb-1.5">
          <h1 className="font-serif text-[40px] leading-[1.1] font-bold tracking-[-0.015em]">Settings</h1>
          {tokens.data && (
            <p className="mt-2 text-sm text-ink2">
              {connected} {connected === 1 ? 'browser' : 'browsers'} connected
            </p>
          )}
        </div>

        {section === 'account' && me.data && <AccountSettings user={me.data} />}

        {section === 'browsers' && (
          <>
            <section id="browsers" aria-labelledby="connect-title" className={`${card} p-6`}>
              <h2 id="connect-title" className={heading}>
                Connect a browser
              </h2>
              <ol className="mt-3.5 flex list-none flex-col gap-3 p-0">
                <Step n={1}>Install the Bookmark Brain extension in each browser you use.</Step>
                <Step n={2}>
                  Click the extension's icon, then{' '}
                  <strong className="font-semibold text-ink">Connect this browser</strong>. It opens this app and
                  connects in a few seconds.
                </Step>
              </ol>

              <details className="group mt-5 border-t border-line pt-4">
                <summary className="flex min-h-9 cursor-pointer list-none items-center gap-2 font-semibold">
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
                    className="-rotate-90 transition group-open:rotate-0"
                  >
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                  Connect by hand
                </summary>
                <p className="mt-1 text-sm text-ink2">
                  Create a token, then paste it into the extension under <em>Advanced: paste a token</em>, with the API
                  URL <code className="font-mono">{API_URL}</code>. One token per browser lets you revoke just one
                  later.
                </p>

                <form
                  className="mt-3.5 flex flex-wrap items-end gap-2.5"
                  onSubmit={(e) => {
                    e.preventDefault()
                    create.mutate()
                  }}
                >
                  <label className="flex flex-[1_1_260px] flex-col gap-1.5 text-sm font-medium">
                    Token name
                    <input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      maxLength={100}
                      className="h-11 rounded-[10px] border border-line bg-surface px-3 font-normal text-ink"
                    />
                  </label>
                  <button
                    disabled={create.isPending || !name.trim()}
                    className="h-11 cursor-pointer rounded-[10px] border-0 bg-ink px-[18px] font-semibold text-on-ink disabled:opacity-50"
                  >
                    Create token
                  </button>
                </form>

                {created && (
                  <div role="status" className="mt-4 rounded-xl bg-accent2 p-4 text-on-accent">
                    <p className="text-sm font-semibold">Copy this token now. It won't be shown again.</p>
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      <code className="min-w-0 flex-[1_1_320px] rounded-lg border border-line bg-surface px-3 py-2.5 font-mono text-[13px] break-all text-ink">
                        {created.token}
                      </code>
                      <button
                        type="button"
                        onClick={() => navigator.clipboard.writeText(created.token)}
                        className="h-11 cursor-pointer rounded-lg border border-white/50 bg-white/[0.08] px-4 font-medium text-on-accent"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                )}
              </details>
            </section>

            <section aria-labelledby="sources-title" className={`${card} overflow-hidden`}>
              <div className="flex items-baseline justify-between gap-3 px-6 pt-5 pb-1.5">
                <h2 id="sources-title" className={heading}>
                  Connected browsers
                </h2>
                {tokens.data && (
                  <span className="text-[13px] text-ink2">
                    {tokens.data.length} {tokens.data.length === 1 ? 'browser' : 'browsers'}
                  </span>
                )}
              </div>
              {tokens.data?.length === 0 && (
                <p className="px-6 pt-2 pb-5 text-sm text-ink2">No browsers connected yet.</p>
              )}
              <ul className="m-0 list-none p-0">
                {tokens.data?.map((t) => (
                  <li
                    key={t.id}
                    className="flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-line px-6 py-3.5"
                  >
                    <span
                      aria-hidden
                      className="grid size-9 place-items-center rounded-[10px] bg-accent font-semibold text-on-accent"
                    >
                      {t.name.charAt(0).toUpperCase()}
                    </span>
                    <div className="min-w-0 flex-[1_1_240px]">
                      <div className="font-semibold">{t.name}</div>
                      <div className="text-[13px] text-ink2">
                        <code className="font-mono">{t.prefix}…</code> ·{' '}
                        {t.last_used_at
                          ? `last synced ${dateFormat.format(new Date(t.last_used_at))}`
                          : `created ${dateFormat.format(new Date(t.created_at))} · never used`}
                      </div>
                    </div>
                    {/* "Connected" once the extension has used the token, "Waiting" (outlined) until then. */}
                    <span
                      className={`rounded-full border px-2.5 py-[3px] text-[13px] font-medium ${t.last_used_at ? 'border-accent2 bg-accent2 text-on-accent' : 'border-line text-ink'}`}
                    >
                      {t.last_used_at ? 'Connected' : 'Waiting'}
                    </span>
                    <button
                      type="button"
                      aria-label={`Revoke ${t.name}`}
                      onClick={() => revoke.mutate(t.id)}
                      className="h-9 cursor-pointer rounded-lg border-0 bg-transparent px-3 font-semibold text-dead-fg"
                    >
                      Revoke
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

function SectionLink(props: { to: string; current: boolean; children: React.ReactNode }) {
  return (
    <Link
      to={props.to}
      aria-current={props.current ? 'page' : undefined}
      className={`flex min-h-9 items-center rounded-lg px-2.5 py-1.5 text-sm no-underline ${props.current ? 'bg-accent font-semibold text-on-accent' : 'text-ink'}`}
    >
      {props.children}
    </Link>
  )
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span
        aria-hidden
        className="grid size-7 flex-none place-items-center rounded-full bg-accent text-[13px] font-semibold text-on-accent"
      >
        {n}
      </span>
      <span className="pt-0.5 text-ink2">{children}</span>
    </li>
  )
}
