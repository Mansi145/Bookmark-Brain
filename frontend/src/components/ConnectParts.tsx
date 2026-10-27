import Logo from './Logo'

// Pieces of the Connect page (design board ConnectStates, "Connect extras").

type Step = 1 | 2 | 3
const STEPS = ['Connect', 'Sync', 'Open feed']

/** Connect → Sync → Open feed: done steps get a check, the current one its number on accent. */
export function StepStrip({ current }: { current: Step }) {
  return (
    <ol aria-label="Steps" className="m-0 flex list-none items-center gap-2 p-0 text-[13px]">
      {STEPS.flatMap((label, i) => {
        const n = (i + 1) as Step
        const done = n < current
        const now = n === current
        const connector = (
          <li key={`${label}-line`} aria-hidden className={`h-0.5 min-w-3 flex-1 rounded-sm ${n <= current ? 'bg-accent' : 'bg-line'}`} />
        )
        const step = (
          <li key={label} aria-current={now ? 'step' : undefined} className="flex items-center gap-1.5 whitespace-nowrap">
            <span
              aria-hidden
              className={`grid size-[22px] flex-none place-items-center rounded-full text-xs font-semibold ${
                done || now ? 'bg-accent text-on-accent' : 'border-[1.5px] border-line text-muted'
              }`}
            >
              {done ? <Check size={12} /> : n}
            </span>
            <span className={now ? 'font-semibold text-ink' : done ? 'text-ink2' : 'text-muted'}>
              {done && <span className="sr-only">Done: </span>}
              {label}
            </span>
          </li>
        )
        return i > 0 ? [connector, step] : [step]
      })}
    </ol>
  )
}

// Bundled in public/browser-icons (from each browser's own site), so nothing loads from them.
const BROWSER_ICONS: Record<string, string> = {
  chrome: '/browser-icons/chrome.png',
  edge: '/browser-icons/edge.png',
  firefox: '/browser-icons/firefox.png',
  brave: '/browser-icons/brave.png',
}

/**
 * The browser's logo joined to ours: a dotted line moving while connecting, an accent line with
 * flowing gaps while syncing, solid with a check when done. Motion stops for reduced motion.
 */
export function LogoPair({ browser, state }: { browser: string | null; state: 'connecting' | 'syncing' | 'done' }) {
  const icon = browser ? BROWSER_ICONS[browser] : undefined
  return (
    <div aria-hidden className="flex items-center gap-2.5">
      <Chip>
        {icon ? (
          <img src={icon} alt="" width={34} height={34} className="size-[34px]" />
        ) : (
          <span className="font-serif text-2xl font-bold text-[#141516]">{(browser ?? '?').charAt(0).toUpperCase()}</span>
        )}
      </Chip>
      {state === 'done' ? (
        <span className="flex min-w-0 flex-1 items-center">
          <span className="h-[3px] flex-1 bg-accent" />
          <span className="grid size-6 flex-none place-items-center rounded-full bg-accent text-on-accent">
            <Check size={13} />
          </span>
          <span className="h-[3px] flex-1 bg-accent" />
        </span>
      ) : (
        <svg height="12" className="min-w-0 flex-1">
          {state === 'connecting' ? (
            <line x1="2" y1="6" x2="100%" y2="6" strokeWidth="3" strokeLinecap="round" strokeDasharray="1 8" className="animate-flow stroke-muted motion-reduce:animate-none" />
          ) : (
            <>
              <line x1="0" y1="6" x2="100%" y2="6" strokeWidth="3" className="stroke-accent" />
              <line x1="0" y1="6" x2="100%" y2="6" strokeWidth="3" strokeDasharray="3 5" className="animate-flow stroke-surface motion-reduce:animate-none" />
            </>
          )}
        </svg>
      )}
      <Chip>
        <Logo size={32} small />
      </Chip>
    </div>
  )
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="grid size-14 flex-none place-items-center rounded-[14px] border border-line bg-white">{children}</span>
  )
}

function Check({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="m5 12 4.5 4.5L19 7" />
    </svg>
  )
}

/** Under every Connect card, on the texture. */
export function PrivacyNote() {
  return (
    <p className="flex items-start gap-2 text-[13px] text-on-texture2">
      <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 flex-none">
        <rect x="5" y="11" width="14" height="9" rx="2" />
        <path d="M8 11V8a4 4 0 0 1 8 0v3" />
      </svg>
      We only read your bookmarks' titles, links and folders, plus the public pages they point to.
    </p>
  )
}

/** "Pin Bookmark Brain to your toolbar" with the puzzle-piece and pin marks. */
export function PinTip() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-panel px-3.5 py-3">
      <span aria-hidden className="flex flex-none items-center gap-1.5 rounded-full border border-line bg-surface py-1 pr-1 pl-2">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-ink2">
          <path d="M5 8h3a2 2 0 1 1 4 0h3v3a2 2 0 1 1 0 4v4H5z" />
        </svg>
        <span className="grid size-[26px] place-items-center rounded-full bg-accent text-on-accent">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 3h6l-1 6 3 3v2H7v-2l3-3z" />
            <path d="M12 14v7" />
          </svg>
        </span>
      </span>
      <p className="text-sm text-ink2">Pin Bookmark Brain to your toolbar (the puzzle-piece menu) to sync any time.</p>
    </div>
  )
}
