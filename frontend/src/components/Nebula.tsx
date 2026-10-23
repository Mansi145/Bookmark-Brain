import { useId } from 'react'

// The brand texture: a base gradient, heavily blurred overlapping ellipses, and film grain.
// Recipes come from the ui-design skill / design canvas.
//
// Render it as the first child of a `relative overflow-hidden` element; put the content in a
// `relative` sibling after it so it sits on top.
//
// "nude" (dark Nude, white text on it) is used everywhere; the old light Cloudlifter texture was
// retired (owner: "looked unprofessional"). Kept as a variant map in case another texture comes.

type Blob = [left: number, top: number, width: number, height: number, color: string, opacity: number]

const NUDE: Blob[] = [
  [4, 8, 36, 52, '#48332C', 0.85],
  [28, -3, 31, 45, '#624D46', 0.7],
  [35, 35, 38, 55, '#534336', 0.85],
  [60, 11, 35, 50, '#564D3A', 0.95],
  [72, 51, 28, 40, '#4C4433', 0.8],
  [13, 55, 30, 43, '#59433B', 0.8],
  [51, -8, 26, 37, '#675F4E', 0.7],
  [43, 23, 21, 30, '#FFFFFF', 0.06],
]

const VARIANTS = {
  nude: { base: 'linear-gradient(90deg, #503931 0%, #564D3A 100%)', blobs: NUDE, grain: { blend: 'screen', opacity: 0.12 } },
} as const

// A tall hero needs a bigger, blurrier layer than a short bar.
const SIZES = {
  hero: { inset: '-240px -16%', blur: 140 },
  band: { inset: '-160px -12%', blur: 110 },
  bar: { inset: '-60px -8%', blur: 60 },
}

export default function Nebula({
  variant = 'nude',
  size = 'band',
}: {
  variant?: keyof typeof VARIANTS
  size?: keyof typeof SIZES
}) {
  const grainId = `grain-${useId()}`
  const v = VARIANTS[variant]
  const s = SIZES[size]

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0" style={{ background: v.base }}>
      <div className="absolute" style={{ inset: s.inset, filter: `blur(${s.blur}px)` }}>
        {v.blobs.map(([left, top, width, height, color, opacity]) => (
          <div
            key={`${left}-${top}`}
            className="absolute rounded-full"
            style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%`, background: color, opacity }}
          />
        ))}
      </div>
      <svg
        width="100%"
        height="100%"
        className="absolute inset-0"
        style={{ mixBlendMode: v.grain.blend, opacity: v.grain.opacity }}
      >
        <filter id={grainId} x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="11" stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#${grainId})`} />
      </svg>
    </div>
  )
}
