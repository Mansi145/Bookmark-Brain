// The free-plan note (owner): only next to AI actions, under the detail panel's buttons and
// (later) under the Ask composer. Users never see usage numbers; this and the Limit reached
// dialog are the only hints that there's a daily limit.
export default function FreePlanNote({ className = '' }: { className?: string }) {
  return (
    <p className={`m-0 flex items-start gap-1.5 text-[13px] text-muted ${className}`}>
      <svg
        aria-hidden
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="mt-[3px] flex-none"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v5" />
        <path d="M12 8h.01" />
      </svg>
      Bookmark Brain is a personal learning project on free plans. AI features share a small daily limit and may stop
      early.
    </p>
  )
}
