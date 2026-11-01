import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

// The top bar's search field (design board Main). The query lives in the address (/?q=…), so
// results survive a reload and Back works. It searches as you type: after a short pause once
// there are 3 characters (fewer would match almost everything), or straight away on Enter, which
// also accepts short words like "go". The clear × (and Escape) goes back to the feed; "/" jumps
// to the field from anywhere on the page.

const PAUSE_MS = 400
const MIN_CHARS = 3

export default function SearchField() {
  const [params] = useSearchParams()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const onFeed = pathname === '/'
  const q = onFeed ? (params.get('q') ?? '') : ''

  const [text, setText] = useState(q)
  // Follow the address when it changes from outside (Clear search, Back): React's "adjust state
  // when a prop changes" pattern, without an effect.
  const [shown, setShown] = useState(q)
  if (q !== shown) {
    setShown(q)
    setText(q)
  }

  const input = useRef<HTMLInputElement>(null)
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => () => window.clearTimeout(timer.current), [])

  // Search for `value` (or go back to the feed when it's empty), keeping the sidebar's filters.
  // Refining a search replaces its history entry, so Back doesn't step through every pause.
  const go = (value: string) => {
    window.clearTimeout(timer.current)
    const query = value.trim()
    const next = new URLSearchParams()
    for (const key of ['folder', 'browser']) {
      const filter = onFeed && params.get(key)
      if (filter) next.set(key, filter)
    }
    if (query) next.set('q', query)
    navigate({ pathname: '/', search: next.toString() }, { replace: Boolean(q && query) })
  }

  const onChange = (value: string) => {
    setText(value)
    window.clearTimeout(timer.current)
    const query = value.trim()
    if (query.length >= MIN_CHARS || (query === '' && q)) {
      timer.current = window.setTimeout(() => go(value), PAUSE_MS)
    }
  }

  const clear = () => {
    setText('')
    if (q) go('')
    else window.clearTimeout(timer.current)
  }

  // "/" anywhere (except while typing somewhere else) puts the cursor in the field.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      const typing = target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
      if (e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault()
        input.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  return (
    <form
      role="search"
      className="m-0 max-w-[560px] flex-[1_1_320px]"
      onSubmit={(e) => {
        e.preventDefault()
        if (text.trim() || q) go(text)
      }}
    >
      <div className="flex h-11 items-center gap-2.5 rounded-[10px] border border-white/[0.18] bg-[rgba(23,24,26,0.55)] pr-3 pl-3.5 focus-within:border-white/60">
        <label className="flex h-full min-w-0 flex-1 items-center gap-2.5">
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
            ref={input}
            type="search"
            value={text}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                e.preventDefault()
                clear()
              }
            }}
            aria-label="Search your bookmarks"
            placeholder="Search by meaning or keyword…"
            // The browser's own clear button is hidden: ours goes back to the feed too.
            className="min-w-0 flex-1 border-0 bg-transparent text-on-texture outline-none placeholder:text-on-texture2 [&::-webkit-search-cancel-button]:appearance-none"
          />
        </label>
        {text ? (
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => {
              clear()
              input.current?.focus()
            }}
            className="-mr-1.5 grid size-9 flex-none cursor-pointer place-items-center rounded-full border-0 bg-transparent p-0"
          >
            <span aria-hidden className="grid size-6 place-items-center rounded-full bg-white/[0.16]">
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#F2F2F4"
                strokeWidth="2.6"
                strokeLinecap="round"
              >
                <path d="M6 6l12 12" />
                <path d="M18 6 6 18" />
              </svg>
            </span>
          </button>
        ) : (
          // The shortcut hint; phones have no "/" key to press, so it's hidden there.
          <kbd className="hidden rounded-md border border-white/30 px-[7px] py-px font-sans text-xs text-on-texture wide:inline-block">
            /
          </kbd>
        )}
      </div>
    </form>
  )
}
