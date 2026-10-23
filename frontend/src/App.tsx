import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { sessionEnded } from './api/client'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import { useMe } from './hooks/useMe'
import ConnectPage, { ConnectSignedOutPage } from './pages/ConnectPage'
import { ErrorPage, NotFoundPage, SignedOutPage, WakingUpPage } from './pages/ErrorPages'
import FeedPage from './pages/FeedPage'
import HowItWorksPage from './pages/HowItWorksPage'
import LoginPage from './pages/LoginPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  const me = useMe()
  const queryClient = useQueryClient()

  // A request came back 401 mid-session: treat the user as signed out and say so. (It stays set
  // for this tab; "You've been signed out" is still true after a later manual sign-out.)
  const [signedOut, setSignedOut] = useState(false)
  useEffect(() => {
    const onEnded = () => {
      setSignedOut(true)
      queryClient.setQueryData(['me'], null)
    }
    sessionEnded.addEventListener('ended', onEnded)
    return () => sessionEnded.removeEventListener('ended', onEnded)
  }, [queryClient])

  if (me.isPending) return <WakingUpPage />
  if (me.isError) return <ErrorPage onRetry={() => void me.refetch()} />

  return (
    <BrowserRouter>
      <ErrorBoundary>
        {me.data ? (
          <Routes>
            <Route element={<Layout user={me.data} />}>
              <Route index element={<FeedPage section="main" />} />
              <Route path="sign-in-required" element={<FeedPage section="sign_in" />} />
              <Route path="dead-links" element={<FeedPage section="dead" />} />
              <Route path="archive" element={<Navigate to="/dead-links" replace />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
            <Route path="connect" element={<ConnectPage />} />
            <Route path="how-it-works" element={<HowItWorksPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        ) : (
          <Routes>
            <Route path="how-it-works" element={<HowItWorksPage />} />
            {/* Signed-out pages keep the address, so /connect?nonce=… carries on after signing in. */}
            <Route path="connect" element={<ConnectSignedOutPage />} />
            <Route path="*" element={signedOut ? <SignedOutPage /> : <LoginPage />} />
          </Routes>
        )}
      </ErrorBoundary>
    </BrowserRouter>
  )
}
