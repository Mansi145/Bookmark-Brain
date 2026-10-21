import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, API_URL } from '../api/client'
import type { ApiToken, CreatedApiToken } from '../api/types'

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export default function SettingsPage() {
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

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="text-2xl font-bold">Settings</h1>

      <section className="mt-6 rounded-xl border border-stone-200 bg-white p-6">
        <h2 className="font-semibold">Connect a browser</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-stone-600">
          <li>Install the Bookmark Brain extension in each browser you use.</li>
          <li>Create a token below (one per browser makes it easy to revoke later).</li>
          <li>
            Open the extension, paste the token, and set the API URL to{' '}
            <code className="rounded bg-stone-100 px-1">{API_URL}</code>.
          </li>
        </ol>

        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            create.mutate()
          }}
        >
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
            className="flex-1 rounded-md border border-stone-300 px-3 py-1.5 text-sm"
            aria-label="Token name"
          />
          <button
            disabled={create.isPending || !name.trim()}
            className="rounded-md bg-stone-900 px-4 py-1.5 text-sm text-white disabled:opacity-50"
          >
            Create token
          </button>
        </form>

        {created && (
          <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm">
            <p className="font-medium">Copy this token now. It won't be shown again.</p>
            <div className="mt-2 flex gap-2">
              <code className="flex-1 break-all rounded bg-white px-2 py-1">{created.token}</code>
              <button
                onClick={() => navigator.clipboard.writeText(created.token)}
                className="rounded-md border border-stone-300 bg-white px-3 text-sm"
              >
                Copy
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="mt-6 rounded-xl border border-stone-200 bg-white p-6">
        <h2 className="font-semibold">Active tokens</h2>
        {tokens.data?.length === 0 && <p className="mt-2 text-sm text-stone-500">No tokens yet.</p>}
        <ul className="mt-2 divide-y divide-stone-100">
          {tokens.data?.map((t) => (
            <li key={t.id} className="flex items-center gap-3 py-3 text-sm">
              <div className="flex-1">
                <div className="font-medium">{t.name}</div>
                <div className="text-xs text-stone-500">
                  <code>{t.prefix}…</code> · created {dateFormat.format(new Date(t.created_at))} ·{' '}
                  {t.last_used_at ? `last used ${dateFormat.format(new Date(t.last_used_at))}` : 'never used'}
                </div>
              </div>
              <button
                onClick={() => revoke.mutate(t.id)}
                className="rounded-md px-3 py-1 text-red-600 hover:bg-red-50"
              >
                Revoke
              </button>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
