import { useQuery } from '@tanstack/react-query'
import { apiGet } from './api/client'

type DbHealth = { status: string; pgvector: string }

export default function App() {
  const health = useQuery({
    queryKey: ['health', 'db'],
    queryFn: () => apiGet<DbHealth>('/health/db'),
  })

  return (
    <main className="mx-auto max-w-2xl p-8 font-sans">
      <h1 className="text-3xl font-bold">Bookmark Brain</h1>
      <p className="mt-2 text-gray-600">Your bookmarks, read and remembered.</p>

      <section className="mt-8 rounded-lg border p-4">
        <h2 className="font-semibold">Backend status</h2>
        {health.isPending && <p className="text-gray-500">Checking…</p>}
        {health.isError && (
          <p className="text-red-600">Can't reach the API: {health.error.message}</p>
        )}
        {health.isSuccess && (
          <p className="text-green-700">
            API {health.data.status} · pgvector {health.data.pgvector}
          </p>
        )}
      </section>
    </main>
  )
}
