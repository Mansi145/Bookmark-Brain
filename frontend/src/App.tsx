import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import Layout from './components/Layout'
import ConnectPage from './pages/ConnectPage'
import { useMe } from './hooks/useMe'
import FeedPage from './pages/FeedPage'
import LoginPage from './pages/LoginPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  const me = useMe()

  if (me.isPending) {
    return <div className="flex min-h-screen items-center justify-center text-stone-500">Loading…</div>
  }
  if (me.isError) {
    return (
      <div className="flex min-h-screen items-center justify-center text-red-600">
        Can't reach the API: {me.error.message}
      </div>
    )
  }
  if (!me.data) return <LoginPage />

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout user={me.data} />}>
          <Route index element={<FeedPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="connect" element={<ConnectPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
