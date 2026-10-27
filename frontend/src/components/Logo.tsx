// "Masthead BB" (design board LogoFinal, see the ui-design skill): a backwards B and a B drawn as
// shapes, sharing one spine, between newspaper rules on a cream tile. Same colours in both themes.
// Same drawing as extension/assets/icon/logo.svg and logo-small.svg.
//
// Full version (64 px and up): a thick accent rule and a thin ink rule above and below. `small`
// (under 64 px: top bars, popup, favicon) keeps only the thick rules, with bigger letters and a
// rounder tile, because the thin rules disappear at ~30 px.

// One B; the other is the same path mirrored, so the two share the vertical stroke in the middle.
const B =
  'M91 52 H128 C147 52 155 62 155 75 C155 86 148 94 138 97 C151 100 159 110 159 123 C159 139 148 148 129 148 H91 Z M109 64 H126 C134 64 138 69 138 75 C138 82 134 87 125 87 H109 Z M109 99 H128 C137 99 142 106 142 115 C142 126 136 136 127 136 H109 Z'

const TILE = '#F4EDE4'
const RULE = '#503931'
const INK = '#141516'

function Letters({ scale }: { scale?: number }) {
  return (
    <g fill={INK} transform={scale ? `translate(100 100) scale(${scale}) translate(-100 -100)` : undefined}>
      <path fillRule="evenodd" d={B} />
      <path fillRule="evenodd" transform="translate(200 0) scale(-1 1)" d={B} />
    </g>
  )
}

export default function Logo({ size = 32, small = false }: { size?: number; small?: boolean }) {
  if (small) {
    return (
      <svg aria-hidden width={size} height={size} viewBox="0 0 200 200" className="flex-none">
        <rect width="200" height="200" rx="34" fill={TILE} />
        <rect x="24" y="16" width="152" height="14" fill={RULE} />
        <rect x="24" y="170" width="152" height="14" fill={RULE} />
        <Letters scale={1.14} />
      </svg>
    )
  }

  return (
    <svg aria-hidden width={size} height={size} viewBox="0 0 200 200" className="flex-none">
      <rect width="200" height="200" rx="22" fill={TILE} />
      <rect x="28" y="24" width="144" height="8" fill={RULE} />
      <rect x="28" y="38" width="144" height="2" fill={INK} />
      <rect x="28" y="160" width="144" height="2" fill={INK} />
      <rect x="28" y="168" width="144" height="8" fill={RULE} />
      <Letters />
    </svg>
  )
}
