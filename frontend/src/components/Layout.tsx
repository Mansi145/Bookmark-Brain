import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import type { User } from '../api/types'
import { useSignOut } from '../hooks/useSignOut'
import { useTheme } from '../hooks/useTheme'
import Avatar from './Avatar'
import DevTools from './DevTools'
import { LimitDialogHost } from './LimitDialog'
import Logo from './Logo'
import Nebula from './Nebula'

// App shell (design board Main.dc.html): top bar on the dark Nude texture with white text, then
// the page. The bar is on the texture in both themes, so its colours are fixed, not theme tokens.
// The light / dark switch lives in the account menu, not the bar (owner).

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 rounded-lg px-3.5 py-2.5 text-on-texture no-underline ${isActive ? 'bg-white/[0.14] font-semibold' : ''}`

// The feed's three sections live in the views bar above the list, so Feed stays the current tab.
const FEED_PATHS = ['/', '/sign-in-required', '/dead-links']

export default function Layout({ user }: { user: User }) {
  const onFeed = FEED_PATHS.includes(useLocation().pathname)

  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="relative text-on-texture">
        {/* The texture is clipped on its own layer, so the account menu can hang below the bar. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <Nebula variant="nude" size="bar" />
        </div>
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
              <svg
                aria-hidden
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#EFE8E2"
                strokeWidth="2"
                strokeLinecap="round"
              >
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

          {/* Tabs: Feed (Ask joins in Phase 4). Settings is in the account menu (owner). */}
          <nav aria-label="Main" className="ml-auto flex flex-wrap gap-1">
            <NavLink to="/" className={() => tabClass({ isActive: onFeed })} aria-current={onFeed ? 'page' : undefined}>
              Feed
            </NavLink>
          </nav>
          <Link
            to="/how-it-works"
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-2.5 text-sm text-on-texture2 no-underline"
          >
            <svg
              aria-hidden
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
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
      {/* Dev build only (`npm run dev`); left out of production builds. */}
      {import.meta.env.DEV && <DevTools />}
    </div>
  )
}

/**
 * The account menu (design boards AccountMenu / AccountMenuDark): the round account button opens
 * a 272 px card under it with who's signed in, Settings, the Dark mode switch (the only theme
 * control; it follows the system until changed) and Sign out. How it works stays a link in the
 * top bar, not here (owner). Closes on Escape, a click outside or Tab; arrow keys move between
 * the items.
 */
function AccountMenu({ user }: { user: User }) {
  const [open, setOpen] = useState(false)
  const wrapper = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  const list = useRef<HTMLDivElement>(null)
  const signOut = useSignOut()
  const { theme, toggle } = useTheme()
  const dark = theme === 'dark'

  const close = (refocus: boolean) => {
    setOpen(false)
    if (refocus) button.current?.focus()
  }

  useEffect(() => {
    if (!open) return
    list.current?.querySelector<HTMLElement>('[role^="menuitem"]')?.focus()
    const onClick = (e: MouseEvent) => !wrapper.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') return close(true)
    if (e.key === 'Tab') return setOpen(false)
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const items = [...(list.current?.querySelectorAll<HTMLElement>('[role^="menuitem"]') ?? [])]
    const at = items.indexOf(document.activeElement as HTMLElement)
    items[(at + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length]?.focus()
  }

  const item = 'flex min-h-10 w-full items-center gap-2.5 rounded-lg px-2.5 text-ink no-underline hover:bg-panel'
  return (
    <div ref={wrapper} className="relative">
      <button
        ref={button}
        type="button"
        aria-label="Account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="grid size-10 cursor-pointer place-items-center overflow-hidden rounded-full border-0 bg-white font-semibold text-[#141516]"
      >
        <Avatar user={user} />
      </button>
      {open && (
        <div
          ref={list}
          role="menu"
          aria-label="Account"
          onKeyDown={onKeyDown}
          className="absolute top-full right-0 z-30 mt-2.5 w-[272px] rounded-[14px] border border-line bg-surface p-2 text-sm text-ink shadow-[0_18px_50px_rgba(0,0,0,0.28)]"
        >
          <div className="flex items-center gap-2.5 border-b border-line px-2.5 pt-2.5 pb-3">
            <span className="grid size-9 flex-none place-items-center overflow-hidden rounded-full bg-accent font-semibold text-on-accent">
              <Avatar user={user} />
            </span>
            <span className="flex min-w-0 flex-col">
              <span className="font-semibold">{user.name ?? 'Signed in'}</span>
              <span className="truncate text-[13px] text-ink2">{user.email}</span>
            </span>
          </div>
          <Link role="menuitem" to="/settings" onClick={() => setOpen(false)} className={`mt-1.5 ${item}`}>
            <MenuIcon>{GEAR}</MenuIcon>
            Settings
          </Link>
          <button
            type="button"
            role="menuitemcheckbox"
            aria-checked={dark}
            onClick={toggle}
            className={`cursor-pointer border-0 bg-transparent text-left font-[inherit] ${item}`}
          >
            <MenuIcon>
              <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />
            </MenuIcon>
            <span className="flex-1">Dark mode</span>
            <span
              aria-hidden
              className={`flex h-5 w-9 flex-none rounded-full p-0.5 ${dark ? 'justify-end bg-accent' : 'justify-start bg-line'}`}
            >
              <span className="size-4 rounded-full bg-white shadow-[0_1px_2px_rgba(0,0,0,0.3)]" />
            </span>
          </button>
          <div aria-hidden className="my-1.5 h-px bg-line" />
          <button
            type="button"
            role="menuitem"
            onClick={() => signOut.mutate()}
            disabled={signOut.isPending}
            className={`cursor-pointer border-0 bg-transparent text-left font-[inherit] ${item}`}
          >
            <MenuIcon>
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <path d="m16 17 5-5-5-5" />
              <path d="M21 12H9" />
            </MenuIcon>
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

function MenuIcon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      aria-hidden
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="flex-none text-ink2"
    >
      {children}
    </svg>
  )
}

const GEAR = (
  <>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
  </>
)
