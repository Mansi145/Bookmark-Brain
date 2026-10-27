import { useState } from 'react'

// "Masthead BB" (design board LogoFinal, see the ui-design skill): a backwards B and a B drawn as
// shapes, sharing one spine, between newspaper rules on a cream tile. Same colours in both themes.
// Same drawing as extension/assets/icon/logo.svg and logo-small.svg.
//
// Full version (64 px and up): a thick accent rule and a thin ink rule above and below. `small`
// (under 64 px: top bars, popup, favicon) keeps only the thick rules, with bigger letters and a
// rounder tile, because the thin rules disappear at ~30 px.
//
// `motion` (design board LogoAnimations): what the logo does while the app works. CSS keyframes
// on parts of the drawing (index.css); with reduced motion the logo stays still.

// One B; the other is the same path mirrored, so the two share the vertical stroke in the middle.
const B =
  'M91 52 H128 C147 52 155 62 155 75 C155 86 148 94 138 97 C151 100 159 110 159 123 C159 139 148 148 129 148 H91 Z M109 64 H126 C134 64 138 69 138 75 C138 82 134 87 125 87 H109 Z M109 99 H128 C137 99 142 106 142 115 C142 126 136 136 127 136 H109 Z'

const TILE = '#F4EDE4'
const ACCENT = '#503931'
const INK = '#141516'

/** Page back: summarising. Rewind: a page loading. Hourglass: looking for an archived copy. */
export type LogoMotion = 'page-back' | 'rewind' | 'hourglass'

// Turning around the middle of the drawing (100, 100), where the two B's share their spine.
const AROUND_SPINE = 'transform-view origin-center'

function lettersScale(scale?: number) {
  return scale ? `translate(100 100) scale(${scale}) translate(-100 -100)` : undefined
}

function Letters({ scale }: { scale?: number }) {
  return (
    <g fill={INK} transform={lettersScale(scale)}>
      <path fillRule="evenodd" d={B} />
      <path fillRule="evenodd" transform="translate(200 0) scale(-1 1)" d={B} />
    </g>
  )
}

export default function Logo({
  size = 32,
  small = false,
  motion = null,
}: {
  size?: number
  small?: boolean
  motion?: LogoMotion | null
}) {
  // When the work is done, the movement still finishes its cycle (each cycle ends at rest), so
  // the logo never stops halfway through a turn, and a summary that comes back at once still
  // shows one Page back.
  const [last, setLast] = useState(motion)
  if (motion && motion !== last) setLast(motion)
  const shown = motion ?? last
  const scale = small ? 1.14 : undefined

  return (
    <svg
      aria-hidden
      width={size}
      height={size}
      viewBox="0 0 200 200"
      // Rewind turns the whole tile, so its corners poke out past the box as it goes round.
      className="flex-none overflow-visible"
      onAnimationIteration={() => !motion && setLast(null)}
    >
      <g className={shown === 'rewind' ? `${AROUND_SPINE} animate-rewind motion-reduce:animate-none` : undefined}>
        {small ? (
          <>
            <rect width="200" height="200" rx="34" fill={TILE} />
            <rect x="24" y="16" width="152" height="14" fill={ACCENT} />
            <rect x="24" y="170" width="152" height="14" fill={ACCENT} />
          </>
        ) : (
          <>
            <rect width="200" height="200" rx="22" fill={TILE} />
            <rect x="28" y="24" width="144" height="8" fill={ACCENT} />
            <rect x="28" y="38" width="144" height="2" fill={INK} />
            <rect x="28" y="160" width="144" height="2" fill={INK} />
            <rect x="28" y="168" width="144" height="8" fill={ACCENT} />
          </>
        )}
        <Letters scale={scale} />
      </g>

      {/* A brown copy of the right B turns over the spine to the left, like a page, and fades. */}
      {shown === 'page-back' && (
        <g fill={ACCENT} transform={lettersScale(scale)} className="motion-reduce:hidden">
          <g className={`${AROUND_SPINE} animate-page-back`}>
            <path fillRule="evenodd" d={B} />
          </g>
        </g>
      )}

      {/* A brown badge in the bottom-right corner with a white hourglass that keeps turning over. */}
      {shown === 'hourglass' && (
        <g transform="translate(166 166)" className="motion-reduce:hidden">
          <circle r="30" fill={ACCENT} stroke={TILE} strokeWidth="5" />
          <g className="transform-fill origin-center animate-hourglass">
            <path
              d="M-11 -15 H11 L0 0 L11 15 H-11 L0 0 Z"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="4"
              strokeLinejoin="round"
            />
            <path d="M-5 11 H5 L0 4 Z" fill="#FFFFFF" />
          </g>
        </g>
      )}
    </svg>
  )
}
