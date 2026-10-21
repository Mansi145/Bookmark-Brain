import { GoogleLogin } from '@react-oauth/google'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { User } from '../api/types'

export default function LoginPage() {
  const queryClient = useQueryClient()
  const login = useMutation({
    // Google gives us a signed ID token ("credential"); the backend verifies it
    // and replies with our own session cookie.
    mutationFn: (credential: string) => api.post<User>('/api/auth/google', { credential }),
    onSuccess: (user) => queryClient.setQueryData(['me'], user),
  })

  return (
    <main className="flex min-h-screen items-center justify-center bg-stone-50 p-6">
      <div className="w-full max-w-sm rounded-2xl border border-stone-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-stone-900">Bookmark Brain</h1>
        <p className="mt-2 text-sm text-stone-600">
          All your browser bookmarks in one feed, summarised and searchable.
        </p>
        <div className="mt-8 flex justify-center">
          <GoogleLogin
            onSuccess={(res) => res.credential && login.mutate(res.credential)}
            onError={() => login.reset()}
          />
        </div>
        {login.isPending && <p className="mt-4 text-sm text-stone-500">Signing in…</p>}
        {login.isError && (
          <p className="mt-4 text-sm text-red-600">Sign-in failed: {login.error.message}</p>
        )}
      </div>
    </main>
  )
}
