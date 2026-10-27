import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { api } from '../api/client'
import type { User } from '../api/types'
import { useTheme } from '../hooks/useTheme'
import { LimitDialogHost } from './LimitDialog'
import Logo from './Logo'
import Nebula from './Nebula'

// App shell (design board Main.dc.html): top bar on the dark Nude texture with white text, then
// the page. The bar is on the texture in both themes, so its colours are fixed, not theme tokens.

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 rounded-lg px-3.5 py-2.5 text-on-texture no-underline ${isActive ? 'bg-white/[0.14] font-semibold' : ''}`

// The feed's three sections live in the views bar above the list, so Feed stays the current tab.
const FEED_PATHS = ['/', '/sign-in-required', '/dead-links']

export default function Layout({ user }: { user: User }) {
  const onFeed = FEED_PATHS.includes(useLocation().pathname)

  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="relative overflow-hidden text-on-texture">
        <Nebula variant="nude" size="bar" />
        <div className="relative mx-auto flex max-w-[1280px] flex-wrap items-center gap-x-6 gap-y-3 px-6 py-[18px]">
          <Link to="/" className="flex items-center gap-2.5 text-on-texture no-underline">
            <Logo size={30} small />
            <span className="font-serif text-[21px] font-bold tracking-[-0.01em]">Bookmark Brain</span>
          </Link>

          {/* Search arrives in Phase 3; the box is here so the layout matches the design. */}
          <form role="search" className="m-0 max-w-[560px] flex-[1_1_320px]" onSubmit={(e) => e.preventDefault()}>
            <label
              className="flex h-11 items-center gap-2.5 rounded-[10px] border border-white/[0.18] bg-[rgba(23,24,26,0.55)] pr-3 pl-3.5"
              title="Search is coming soon"
            >
              <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EFE8E2" strokeWidth="2" strokeLinecap="round">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              <input
                type="search"
                disabled
                aria-label="Search your bookmarks (coming soon)"
                placeholder="Search by meaning or keyword… (soon)"
                className="min-w-0 flex-1 border-0 bg-transparent text-on-texture outline-none placeholder:text-on-texture2"
              />
            </label>
          </form>

          {/* Tabs Feed · Ask · Settings; "Ask" joins in Phase 4. */}
          <nav aria-label="Main" className="ml-auto flex flex-wrap gap-1">
            <NavLink to="/" className={() => tabClass({ isActive: onFeed })} aria-current={onFeed ? 'page' : undefined}>
              Feed
            </NavLink>
            <NavLink to="/settings" className={tabClass}>
              Settings
            </NavLink>
          </nav>
          <ThemeToggle />
          <Link to="/how-it-works" className="flex items-center gap-1.5 rounded-lg px-2.5 py-2.5 text-sm text-on-texture2 no-underline">
            <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6" />
              <path d="M12 17h.01" />
            </svg>
            How it works
          </Link>
          <AccountMenu user={user} />
        </div>
      </header>
      <Outlet />
      <LimitDialogHost />
    </div>
  )
}

/** Light/dark switch: a moon in light mode (press for dark), a sun in dark mode. */
function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const dark = theme === 'dark'
  return (
    <button
      type="button"
      aria-label="Dark mode"
      aria-pressed={dark}
      onClick={toggle}
      className="grid size-10 cursor-pointer place-items-center rounded-full border border-white/30 bg-white/[0.08] text-on-texture"
    >
      <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {dark ? (
          <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          </>
        ) : (
          <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />
        )}
      </svg>
    </button>
  )
}

function AccountMenu({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const menu = useRef<HTMLDivElement>(null)
  const logout = useMutation({
    mutationFn: () => api.post('/api/auth/logout'),
    onSuccess: () => {
      queryClient.clear()
      queryClient.setQueryData(['me'], null)
    },
  })

  // Close when clicking elsewhere or pressing Escape.
  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => !menu.current?.contains(e.target as Node) && setOpen(false)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const initial = (user.name ?? user.email).charAt(0).toUpperCase()
  return (
    <div ref={menu} className="relative">
      <button
        type="button"
        aria-label="Account menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="grid size-10 cursor-pointer place-items-center overflow-hidden rounded-full border-0 bg-white font-semibold text-[#141516]"
      >
        {user.avatar_url ? <img src={user.avatar_url} alt="" referrerPolicy="no-referrer" className="size-10" /> : initial}
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-2 w-60 rounded-xl border border-line bg-surface p-2 text-ink shadow-lg">
          <div className="px-3 py-2">
            <div className="font-semibold">{user.name ?? 'Signed in'}</div>
            <div className="truncate text-[13px] text-ink2">{user.email}</div>
          </div>
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="mt-1 w-full cursor-pointer rounded-lg border-0 bg-transparent px-3 py-2 text-left text-ink hover:bg-skeleton"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}
