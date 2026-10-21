import { useMutation, useQueryClient } from '@tanstack/react-query'
import { NavLink, Outlet } from 'react-router'
import { api } from '../api/client'
import type { User } from '../api/types'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm ${isActive ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100'}`

export default function Layout({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const logout = useMutation({
    mutationFn: () => api.post('/api/auth/logout'),
    onSuccess: () => {
      queryClient.clear()
      queryClient.setQueryData(['me'], null)
    },
  })

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <span className="font-bold">Bookmark Brain</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={navClass}>
              Feed
            </NavLink>
            <NavLink to="/settings" className={navClass}>
              Settings
            </NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {user.avatar_url && (
              <img src={user.avatar_url} alt="" className="h-8 w-8 rounded-full" referrerPolicy="no-referrer" />
            )}
            <span className="hidden text-sm text-stone-600 sm:inline">{user.name ?? user.email}</span>
            <button
              onClick={() => logout.mutate()}
              className="rounded-md px-3 py-1.5 text-sm text-stone-600 hover:bg-stone-100"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  )
}
