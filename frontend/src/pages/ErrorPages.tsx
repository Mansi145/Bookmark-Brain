import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import SignInButtons from '../components/SignInButtons'
import StatePage, { SlidingBar, StateText } from '../components/StatePage'
import { ICONS, stateAction } from '../components/statePageParts'

// Full-page states shown instead of the app (design board ErrorStates). Each says what
// happened and gives one way forward.

export function NotFoundPage() {
  return (
    <StatePage icon={ICONS.search} title="We couldn't find that page">
      <StateText>The link may be old or mistyped.</StateText>
      <Link to="/" className={stateAction}>
        Back to your feed
      </Link>
    </StatePage>
  )
}

/**
 * The first request is still waiting. Locally that takes milliseconds; in production the free
 * Render server sleeps when idle and takes up to a minute to start, so explain the wait, but
 * only after a moment, so a fast load doesn't flash this card.
 */
export function WakingUpPage() {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), 1500)
    return () => window.clearTimeout(timer)
  }, [])
  if (!slow) return null

  return (
    <StatePage icon={ICONS.moon} title="Waking up the server…" logoMotion="rewind">
      <StateText>
        Bookmark Brain runs on a free server that sleeps when nobody is using it. This can take up to a minute.
      </StateText>
      <SlidingBar />
    </StatePage>
  )
}

/** The session ended (cookie expired or revoked) while the app was open. */
export function SignedOutPage() {
  return (
    <StatePage icon={ICONS.person} title="You've been signed out">
      <StateText>Sign in again to get back to your bookmarks.</StateText>
      <SignInButtons />
    </StatePage>
  )
}

export function ErrorPage({ onRetry }: { onRetry: () => void }) {
  return (
    <StatePage icon={ICONS.alert} title="Something went wrong">
      <StateText>That didn't work on our side. Your bookmarks are safe.</StateText>
      <button type="button" onClick={onRetry} className={stateAction}>
        Try again
      </button>
    </StatePage>
  )
}
