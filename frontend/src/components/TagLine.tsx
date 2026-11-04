import { Fragment } from 'react'
import { Link, useSearchParams } from 'react-router'
import type { Tag } from '../api/types'
import { withTag } from '../lib/tags'

/**
 * A story's tags, right under its headline (design boards FeedTags): a 13 px tag icon, then the
 * tags as links split by "·". A link adds that tag to the filter. No line without tags.
 */
export default function TagLine({ tags, small = false }: { tags: Tag[]; small?: boolean }) {
  const [params] = useSearchParams()
  if (tags.length === 0) return null
  return (
    <p className={`m-0 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-ink2 ${small ? 'text-xs' : 'text-[13px]'}`}>
      <TagIcon size={13} />
      <span className="sr-only">Tags:</span>
      {tags.map((tag, i) => (
        <Fragment key={tag.id}>
          {i > 0 && (
            <span aria-hidden className="text-muted">
              ·
            </span>
          )}
          <Link
            to={{ search: withTag(params, tag.id).toString() }}
            className="font-medium text-ink2 no-underline hover:underline"
          >
            {tag.name}
          </Link>
        </Fragment>
      ))}
    </p>
  )
}

export function TagIcon({ size }: { size: number }) {
  return (
    <svg
      aria-hidden
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="flex-none"
    >
      <path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z" />
      <circle cx="7.5" cy="7.5" r="1.5" />
    </svg>
  )
}
