import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { api } from '../api/client'
import type { Bookmark } from '../api/types'
import { updateCachedBookmark } from '../lib/cache'
import { canSummarise } from '../lib/summaries'
import { LIMIT_TEXT, MAX_PER_BOOKMARK, MAX_TAG_NAME, refreshAfterTagChange, tagErrorCode, useTags } from '../lib/tags'

// The detail panel's tags (boards FeedDetailNoTags, FeedDetailTagAdd, FeedDetailTagCreate,
// FeedDetailTagsFull, FeedDetailTagError): outlined pills with a remove ×, then Add tag, which
// opens a combobox of the user's other tags; a typed name with no match offers "+ Create tag".

export default function DetailTags({ bookmark }: { bookmark: Bookmark }) {
  const queryClient = useQueryClient()
  const all = useTags()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [active, setActive] = useState(0)
  const listId = useId()

  const done = (updated: Bookmark) => {
    updateCachedBookmark(queryClient, updated)
    refreshAfterTagChange(queryClient)
  }
  const add = useMutation({
    mutationFn: (name: string) => api.post<Bookmark>(`/api/bookmarks/${bookmark.id}/tags`, { name }),
    onSuccess: (updated) => {
      done(updated)
      setText('')
      setOpen(false)
    },
  })
  const remove = useMutation({
    mutationFn: (tagId: number) => api.delete<Bookmark>(`/api/bookmarks/${bookmark.id}/tags/${tagId}`),
    onSuccess: done,
  })

  const full = bookmark.tags.length >= MAX_PER_BOOKMARK
  const has = new Set(bookmark.tags.map((t) => t.id))
  const typed = text.trim().replace(/\s+/g, ' ')
  const matching = (all.data ?? []).filter((t) => !has.has(t.id) && t.name.toLowerCase().includes(typed.toLowerCase()))
  const exists = (all.data ?? []).some((t) => t.name.toLowerCase() === typed.toLowerCase())
  const options = [
    ...matching.map((t) => ({ id: `${listId}-${t.id}`, name: t.name, label: t.name, count: t.count })),
    ...(typed && !exists ? [{ id: `${listId}-new`, name: typed, label: `+ Create tag “${typed}”`, count: null }] : []),
  ]
  const creating = typed !== '' && !exists
  const pick = (name: string) => !add.isPending && add.mutate(name)

  const code = tagErrorCode(add.error)
  const addError =
    code === 'bookmark_tag_limit'
      ? LIMIT_TEXT.bookmark
      : code === 'tag_limit'
        ? LIMIT_TEXT.account
        : add.isError
          ? `Couldn't add “${add.variables}”. Check your connection and try again.`
          : null
  const left = MAX_PER_BOOKMARK - bookmark.tags.length

  return (
    <section aria-labelledby="detail-tags" className="flex flex-col gap-2.5">
      <h3 id="detail-tags" className="text-xs font-semibold tracking-[0.06em] text-ink2 uppercase">
        Tags
      </h3>

      {bookmark.tags.length === 0 && (
        <p className="m-0 text-sm text-ink2">
          {canSummarise(bookmark) && bookmark.summary_status !== 'done'
            ? 'No tags yet. When you summarise this page, the AI adds up to 2 of your tags.'
            : 'No tags yet.'}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {bookmark.tags.map((tag) => (
          <span
            key={tag.id}
            className="flex h-8 items-center gap-0.5 rounded-full border border-line bg-surface pr-1 pl-3 text-sm text-ink"
          >
            {tag.name}
            <button
              type="button"
              aria-label={`Remove tag ${tag.name}`}
              disabled={remove.isPending}
              onClick={() => remove.mutate(tag.id)}
              className="grid size-6 cursor-pointer place-items-center rounded-full border-0 bg-transparent text-ink2 hover:bg-skeleton"
            >
              <svg
                aria-hidden
                width="11"
                height="11"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.6"
                strokeLinecap="round"
              >
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </span>
        ))}
        {!full && !open && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="h-8 cursor-pointer border-0 bg-transparent px-1 text-sm font-medium text-ink underline"
          >
            Add tag
          </button>
        )}
      </div>

      {full && <p className="m-0 text-[13px] text-ink2">{LIMIT_TEXT.bookmark}</p>}

      {open && !full && (
        <div className="relative flex flex-col gap-2">
          <input
            autoFocus
            role="combobox"
            aria-label="Find or create a tag"
            aria-expanded={options.length > 0}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={options[active]?.id}
            placeholder="Find or create a tag"
            value={text}
            maxLength={MAX_TAG_NAME}
            onChange={(e) => {
              setText(e.target.value)
              setActive(0)
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') setActive((a) => Math.min(a + 1, options.length - 1))
              else if (e.key === 'ArrowUp') setActive((a) => Math.max(a - 1, 0))
              else if (e.key === 'Escape') setOpen(false)
              else if (e.key === 'Enter' && options[active]) pick(options[active].name)
              else return
              e.preventDefault()
            }}
            className="h-10 rounded-[10px] border border-line bg-surface px-3 text-sm text-ink placeholder:text-muted"
          />
          {options.length > 0 && (
            <ul
              id={listId}
              role="listbox"
              aria-label="Tags"
              className="m-0 flex max-h-[220px] list-none flex-col overflow-auto rounded-[10px] border border-line bg-surface p-1"
            >
              {options.map((option, i) => (
                <li
                  key={option.id}
                  id={option.id}
                  role="option"
                  aria-selected={i === active}
                  onMouseEnter={() => setActive(i)}
                  onMouseDown={(e) => e.preventDefault()} // keep focus in the input
                  onClick={() => pick(option.name)}
                  className={`flex min-h-9 cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 text-sm ${i === active ? 'bg-line' : ''}`}
                >
                  <span className="truncate">{option.label}</span>
                  {option.count !== null && <span className="text-xs text-muted">{option.count}</span>}
                </li>
              ))}
            </ul>
          )}
          {!addError && (
            <p className="m-0 text-[13px] text-ink2">
              {creating
                ? 'New tags join your list, and the AI can use them too.'
                : `${left} more ${left === 1 ? 'tag fits' : 'tags fit'} on this bookmark.`}
            </p>
          )}
        </div>
      )}

      {addError && (
        <div role="alert" className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <span className="text-[13px] text-dead-fg">{addError}</span>
          {!code && (
            <button
              type="button"
              onClick={() => add.mutate(add.variables!)}
              className="h-8 cursor-pointer rounded-lg border border-line bg-surface px-3 text-[13px] font-medium text-ink"
            >
              Try again
            </button>
          )}
        </div>
      )}
      {remove.isError && (
        <p role="alert" className="m-0 text-[13px] text-dead-fg">
          Couldn't remove the tag. Check your connection and try again.
        </p>
      )}
    </section>
  )
}
