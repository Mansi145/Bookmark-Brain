import { GoogleLogin } from '@react-oauth/google'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation, useSearchParams } from 'react-router'
import { api, API_URL } from '../api/client'
import type { User } from '../api/types'
import { GitHubMark } from './ProviderMarks'

// The design's dark buttons with the real Google G and GitHub marks.
//
// Google: we use Google's own rendered button (theme "filled_black"), not a custom one. Only
// Google's button returns the signed ID token our backend verifies, and Google's branding
// rules ask for their button anyway.
// GitHub: a plain link to the API, which sends the browser to GitHub and back (app/auth/github.py),
// returning to this same page signed in, e.g. to /connect mid one-click connect. If it didn't
// work, the API says why in ?github_error=….

const GITHUB_ERRORS: Record<string, string> = {
  cancelled: 'GitHub sign-in was cancelled.',
  no_email: 'Your GitHub account needs a verified primary email address to sign in.',
  unavailable: 'Sign-in with GitHub isn’t available right now.',
  failed: 'Couldn’t sign in with GitHub. Please try again.',
}

export default function SignInButtons() {
  const queryClient = useQueryClient()
  const login = useMutation({
    // Google gives us a signed ID token ("credential"); the backend verifies it
    // and replies with our own session cookie.
    mutationFn: (credential: string) => api.post<User>('/api/auth/google', { credential }),
    onSuccess: (user) => queryClient.setQueryData(['me'], user),
  })

  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const githubError = params.get('github_error')
  const here = new URLSearchParams(params)
  here.delete('github_error') // a second try shouldn't come back with the old error
  const next = here.toString() ? `${pathname}?${here}` : pathname
  const githubHref = `${API_URL}/api/auth/github?${new URLSearchParams({ next })}`

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <GoogleLogin
          onSuccess={(res) => res.credential && login.mutate(res.credential)}
          onError={() => login.reset()}
          theme="filled_black"
          size="large"
          text="continue_with"
          shape="rectangular"
        />
        <a
          href={githubHref}
          className="flex h-[52px] items-center gap-3 rounded-xl border border-[#8E918F] bg-[#141516] pr-[22px] pl-[18px] font-medium text-white no-underline"
        >
          <GitHubMark size={20} />
          Continue with GitHub
        </a>
      </div>
      {login.isPending && <p className="mt-3 text-sm">Signing in…</p>}
      {login.isError && <p className="mt-3 text-sm">Sign-in failed: {login.error.message}</p>}
      {githubError && (
        <p role="alert" className="mt-3 text-sm">
          {GITHUB_ERRORS[githubError] ?? GITHUB_ERRORS.failed}
        </p>
      )}
    </div>
  )
}
