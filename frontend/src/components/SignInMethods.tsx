import { GoogleLogin } from '@react-oauth/google'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { api, API_URL, ApiError } from '../api/client'
import type { Provider, User } from '../api/types'
import { PROVIDER_NAMES } from '../lib/format'
import { GitHubMark, GoogleMark } from './ProviderMarks'

// Settings → Account → Sign-in methods (owner): one row per provider, Linked with Unlink, or Link.
// Linking adds that provider to this account even with another email, since being signed in here
// and approving on Google or GitHub proves it's the same person. Unlink is there to fix linking
// the wrong account, and never shows for the only method left, so nobody locks themselves out.
//
// Google links with Google's own button (only it gives the server a token it can verify).
// GitHub links with a trip to GitHub and back here, like signing in (backend app/api/auth.py),
// and says what went wrong in ?github_error=….

const LINK_GITHUB = `${API_URL}/api/auth/github/link?${new URLSearchParams({ next: '/settings?section=account' })}`

const GITHUB_ERRORS: Record<string, string> = {
  cancelled: 'Linking GitHub was cancelled.',
  no_email: 'Your GitHub account needs a verified primary email address.',
  in_use: 'That GitHub account has its own Bookmark Brain account, so it can’t be linked here.',
  unavailable: 'Linking GitHub isn’t available right now.',
  failed: 'Couldn’t link GitHub. Please try again.',
}

const heading = 'font-serif text-[21px] leading-[1.25] font-bold'

export default function SignInMethods({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const [params] = useSearchParams()
  const githubError = params.get('github_error')

  const linkGoogle = useMutation({
    mutationFn: (credential: string) => api.post<User>('/api/auth/google/link', { credential }),
    onSuccess: (updated) => queryClient.setQueryData(['me'], updated),
  })
  const unlink = useMutation({
    mutationFn: (provider: Provider) => api.delete<User>(`/api/auth/${provider}/link`),
    onSuccess: (updated) => queryClient.setQueryData(['me'], updated),
  })

  const onlyOne = user.providers.length === 1
  const row = (provider: Provider, mark: React.ReactNode, link: React.ReactNode) => {
    const linked = user.providers.includes(provider)
    return (
      <li className="flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-line px-6 py-3.5">
        <span aria-hidden className="grid size-9 place-items-center">
          {mark}
        </span>
        <div className="min-w-0 flex-[1_1_240px]">
          <div className="font-semibold">{PROVIDER_NAMES[provider]}</div>
          <div className="text-[13px] text-ink2">
            {!linked ? 'Not linked' : onlyOne ? 'Linked · your only sign-in method' : 'Linked'}
          </div>
        </div>
        {!linked
          ? link
          : !onlyOne && (
              <button
                type="button"
                aria-label={`Unlink ${PROVIDER_NAMES[provider]}`}
                onClick={() => unlink.mutate(provider)}
                disabled={unlink.isPending}
                className="h-9 cursor-pointer rounded-lg border-0 bg-transparent px-3 font-semibold text-dead-fg"
              >
                Unlink
              </button>
            )}
      </li>
    )
  }

  const error = linkGoogle.isError
    ? linkGoogle.error instanceof ApiError && linkGoogle.error.status === 409
      ? 'That Google account has its own Bookmark Brain account, so it can’t be linked here.'
      : 'Couldn’t link Google. Please try again.'
    : unlink.isError && unlink.variables
      ? `Couldn’t unlink ${PROVIDER_NAMES[unlink.variables]}. Please try again.`
      : githubError && !user.providers.includes('github')
        ? (GITHUB_ERRORS[githubError] ?? GITHUB_ERRORS.failed)
        : null

  return (
    <section aria-labelledby="methods-title" className="overflow-hidden rounded-xl border border-line bg-surface">
      <div className="px-6 pt-5 pb-3.5">
        <h2 id="methods-title" className={heading}>
          Sign-in methods
        </h2>
        <p className="mt-1.5 text-sm text-ink2">Either one signs you in to this account.</p>
      </div>
      <ul className="m-0 list-none p-0">
        {row(
          'google',
          <GoogleMark size={20} />,
          <GoogleLogin
            onSuccess={(res) => res.credential && linkGoogle.mutate(res.credential)}
            onError={() => linkGoogle.reset()}
            theme="filled_black"
            size="medium"
            text="continue_with"
            shape="rectangular"
          />,
        )}
        {row(
          'github',
          <span className="text-ink">
            <GitHubMark size={20} />
          </span>,
          <a
            href={LINK_GITHUB}
            className="inline-flex h-9 items-center rounded-lg border border-line bg-surface px-3.5 font-medium text-ink no-underline"
          >
            Link
          </a>,
        )}
      </ul>
      {error && (
        <p role="alert" className="m-0 border-t border-line px-6 py-3 text-[13px] text-dead-fg">
          {error}
        </p>
      )}
    </section>
  )
}
