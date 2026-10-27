import { useId } from 'react'

// Same drawing as extension/assets/icon/logo.svg and logo-small.svg (see the ui-design skill):
// a brain on a bookmark ribbon, near-black line art with a radial "Mulberry" fill that stays
// inside the outline. `small` drops the fine details, which turn to mush at ~30 px.

const BRAIN =
  'M60 112 C46 110 42 94 50 86 C40 78 44 60 58 58 C58 44 74 38 86 44 C92 34 108 34 114 44 C126 38 142 44 142 58 C156 60 160 78 150 86 C158 94 154 110 140 112 C128 118 112 116 100 112 C88 116 72 118 60 112 Z'

function Aura({ id }: { id: string }) {
  return (
    <defs>
      <radialGradient id={id} gradientUnits="userSpaceOnUse" cx="100" cy="76" r="150" fx="100" fy="70">
        <stop offset="0" stopColor="#955E7D" />
        <stop offset="0.45" stopColor="#CA8FB9" />
        <stop offset="1" stopColor="#FFC0F5" />
      </radialGradient>
    </defs>
  )
}

export default function Logo({ size = 32, small = false }: { size?: number; small?: boolean }) {
  const aura = `aura-${useId()}` // each SVG on the page needs its own gradient id
  const common = {
    fill: 'none',
    stroke: '#141516',
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
  }

  if (small) {
    return (
      <svg width={size} height={size * 1.05} viewBox="8 30 184 194" strokeWidth={11} {...common}>
        <Aura id={aura} />
        <path fill={`url(#${aura})`} d={BRAIN} />
        <line x1="84" y1="82" x2="84" y2="94" strokeWidth={13} />
        <line x1="116" y1="82" x2="116" y2="94" strokeWidth={13} />
        <path
          fill={`url(#${aura})`}
          d="M62 126 H138 Q150 126 150 138 V210 Q150 220 141 215 L100 190 L59 215 Q50 220 50 210 V138 Q50 126 62 126 Z"
        />
      </svg>
    )
  }

  return (
    <svg width={size} height={size * 1.1} viewBox="0 20 200 220" strokeWidth={6} {...common}>
      <Aura id={aura} />
      <path fill={`url(#${aura})`} d={BRAIN} />
      <path d="M100 41 C95 52 105 60 100 72" />
      <path d="M64 70 C72 68 77 74 74 82" />
      <path d="M136 70 C128 68 123 74 126 82" />
      <path d="M80 50 C85 56 83 62 77 64" />
      <path d="M120 50 C115 56 117 62 123 64" />
      <line x1="86" y1="83" x2="86" y2="93" strokeWidth={8} />
      <line x1="114" y1="83" x2="114" y2="93" strokeWidth={8} />
      <path d="M93 101 Q100 107 107 101" />
      <path
        fill={`url(#${aura})`}
        d="M62 120 H138 Q150 120 150 132 V212 Q150 222 141 217 L100 192 L59 217 Q50 222 50 212 V132 Q50 120 62 120 Z"
      />
      <path d="M50 150 Q36 154 38 170" />
      <path d="M150 150 Q164 154 162 170" />
    </svg>
  )
}
