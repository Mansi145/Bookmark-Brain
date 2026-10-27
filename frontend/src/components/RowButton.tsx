// The 36 px outlined row action (Summarise, Find archived copy, Try again; 32 px and 13 px text
// when `compact`, on the newspaper's briefs) and the small stroke icons used on rows (design
// boards RowStates and NewsClassic).

export function RowButton(props: {
  icon?: React.ReactNode
  onClick: () => void
  disabled?: boolean
  label?: string // aria-label, when the visible text needs more context
  compact?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      disabled={props.disabled}
      aria-label={props.label}
      className={`flex cursor-pointer items-center gap-1.5 rounded-lg border border-line bg-surface px-3 font-medium ${props.compact ? 'h-8 text-[13px]' : 'h-9 text-sm'} text-ink hover:bg-skeleton disabled:cursor-default disabled:opacity-50 disabled:hover:bg-surface`}
    >
      {props.icon && <Icon>{props.icon}</Icon>}
      {props.children}
    </button>
  )
}

export function Icon({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <svg aria-hidden width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={`flex-none ${className}`}>
      {children}
    </svg>
  )
}

/** The accent2 "in progress" pill with a spinner, plus a skeleton bar (Fetching, Summarising). */
export function ProgressPill({ children, bar = true }: { children: React.ReactNode; bar?: boolean }) {
  return (
    <div role="status" className="flex items-center gap-3">
      <span className="flex items-center gap-1.5 rounded-full bg-accent2 px-2.5 py-[3px] text-[13px] font-medium whitespace-nowrap text-on-accent">
        <Icon className="animate-spin motion-reduce:animate-none">
          <path d="M12 3a9 9 0 1 0 9 9" />
        </Icon>
        {children}
      </span>
      {bar && <span aria-hidden className="h-2.5 max-w-[420px] flex-1 rounded bg-skeleton" />}
    </div>
  )
}
