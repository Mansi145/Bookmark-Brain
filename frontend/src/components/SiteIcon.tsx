import { useState } from 'react'

/**
 * A site's logo (favicon): 14 px, centred on a 20 px white chip in both themes, so dark marks
 * stay visible on dark and colourful ones don't clash with the brown accents. Falls back to a
 * letter tile on the accent colour when there's no logo or it fails to load (some guessed
 * /favicon.ico addresses don't exist). Hidden from screen readers: the site name is next to it.
 *
 * `small` is the 16 px chip inside citation chips, `brief` the 18 px one on the newspaper's
 * briefs. `light` keeps the chip border light on the signed-out pages, which are designed
 * light-only.
 */
export default function SiteIcon(props: {
  iconUrl: string | null
  site: string
  small?: boolean
  brief?: boolean
  light?: boolean
}) {
  const [broken, setBroken] = useState(false)
  const box = props.small ? 'size-4' : props.brief ? 'size-[18px]' : 'size-5'
  const logo = props.small ? 11 : props.brief ? 12 : 14

  if (props.iconUrl && !broken) {
    return (
      <span
        aria-hidden
        className={`grid flex-none place-items-center rounded-md border bg-white ${box} ${props.light ? 'border-[#E2DFDA]' : 'border-line'}`}
      >
        <img
          src={props.iconUrl}
          alt=""
          width={logo}
          height={logo}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setBroken(true)}
          className={`object-contain ${props.small ? 'size-[11px]' : props.brief ? 'size-3' : 'size-3.5'}`}
        />
      </span>
    )
  }
  return (
    <span
      aria-hidden
      className={`grid flex-none place-items-center rounded-md bg-accent font-semibold text-on-accent ${box} ${props.small ? 'text-[9px]' : props.brief ? 'text-[10px]' : 'text-[11px]'}`}
    >
      {props.site.charAt(0).toUpperCase()}
    </span>
  )
}
