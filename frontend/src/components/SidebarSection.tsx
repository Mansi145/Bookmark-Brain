import { useId, useState } from 'react'

// Folded sections, remembered on this device (design v115). Only a convenience, so a browser
// that blocks storage just starts with everything open.
const CLOSED_KEY = 'bb.sidebar.closed'

function closedSections(): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(CLOSED_KEY) ?? '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

function remember(id: string, open: boolean) {
  try {
    const closed = new Set(closedSections())
    if (open) closed.delete(id)
    else closed.add(id)
    localStorage.setItem(CLOSED_KEY, JSON.stringify([...closed]))
  } catch {
    // storage blocked: the section still folds, it just isn't remembered
  }
}

/**
 * A sidebar section that folds from its heading (board FeedSidebarFolded): the heading is a
 * 36 px button with a chevron that turns −90° when closed. Open by default. `action` sits on
 * the right of the heading while it's open (Tags' "+ New tag").
 */
export default function SidebarSection(props: {
  id: string
  title: string
  action?: React.ReactNode
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(() => !closedSections().includes(props.id))
  const listId = useId()
  const toggle = () => {
    setOpen(!open)
    remember(props.id, !open)
  }
  return (
    <section>
      <div className="flex items-center justify-between gap-2">
        <h2 className="m-0">
          <button
            type="button"
            aria-expanded={open}
            aria-controls={listId}
            onClick={toggle}
            className="flex h-9 cursor-pointer items-center gap-1.5 border-0 bg-transparent p-0 text-xs font-semibold tracking-[0.06em] text-ink2 uppercase"
          >
            <svg
              aria-hidden
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`transition-transform duration-150 motion-reduce:transition-none ${open ? '' : '-rotate-90'}`}
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
            {props.title}
          </button>
        </h2>
        {open && props.action}
      </div>
      <div id={listId} hidden={!open}>
        {props.children}
      </div>
    </section>
  )
}
