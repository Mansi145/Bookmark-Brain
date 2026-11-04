import { useMutation } from '@tanstack/react-query'
import { useEffect, useId, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Tag, TagBulkResult } from '../api/types'
import { useSelection } from '../lib/selection'
import { LIMIT_TEXT, MAX_TAG_NAME, tagErrorCode, useRefreshTags, useTags } from '../lib/tags'

// Select mode, for tagging several bookmarks at once (boards FeedSelect, FeedSelectAdd,
// FeedSelectDone): Select in the header puts a checkbox on every story, and a sticky bar replaces
// the views bar: "3 selected", Add tag, Remove tag, Done.

/** The checkbox at the top of each story: a 22 px box in a 36 px target. */
export function SelectCheckbox({ id, title }: { id: number; title: string }) {
  const { selecting, selected, toggle } = useSelection()
  if (!selecting) return null
  const checked = selected.has(id)
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      aria-label={`Select ${title}`}
      onClick={() => toggle(id)}
      className="-m-[7px] grid size-9 flex-none cursor-pointer place-items-center border-0 bg-transparent p-0"
    >
      <span
        aria-hidden
        className={`grid size-[22px] place-items-center rounded-md border-2 ${checked ? 'border-ink bg-ink text-on-ink' : 'border-ink2 bg-surface'}`}
      >
        {checked && (
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="m5 12 4.5 4.5L19 7" />
          </svg>
        )}
      </span>
    </button>
  )
}

/** The sticky bar that replaces the views bar while selecting. */
export function SelectBar({ selected, onDone }: { selected: Set<number>; onDone: () => void }) {
  const [picker, setPicker] = useState<'add' | 'remove' | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const refresh = useRefreshTags()
  const ids = [...selected]

  const apply = useMutation({
    mutationFn: async ({ action, tag }: { action: 'add' | 'remove'; tag: Tag | string }) => {
      // A typed name with no match is created first (Add tag only).
      const target = typeof tag === 'string' ? await api.post<Tag>('/api/tags', { name: tag }) : tag
      const result = await api.post<TagBulkResult>(`/api/tags/${target.id}/${action}`, { bookmark_ids: ids })
      return { action, tag: target, result }
    },
    onSuccess: ({ action, tag, result }) => {
      setStatus(resultLine(action, tag.name, result))
      setPicker(null)
      refresh()
    },
    onError: (error) => {
      setStatus(
        tagErrorCode(error) === 'tag_limit'
          ? LIMIT_TEXT.account
          : "That didn't work. Check your connection and try again.",
      )
    },
  })

  const outline =
    'flex h-10 cursor-pointer items-center gap-1.5 rounded-full border border-line bg-surface px-4 text-sm font-medium text-ink disabled:cursor-default disabled:opacity-50'
  return (
    <div className="sticky top-3 z-10 mb-[22px] flex flex-col gap-2 rounded-[14px] border border-line bg-surface py-2 pr-2 pl-4 shadow-[0_10px_30px_rgba(0,0,0,0.10)]">
      <div className="flex flex-wrap items-center gap-2">
        <span className="mr-1 text-sm font-semibold" aria-live="polite">
          {selected.size} selected
        </span>
        {(['add', 'remove'] as const).map((action) => (
          <div key={action} className="relative">
            <button
              type="button"
              disabled={selected.size === 0}
              aria-expanded={picker === action}
              onClick={() => setPicker(picker === action ? null : action)}
              className={outline}
            >
              <svg
                aria-hidden
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
              >
                {action === 'add' ? <path d="M12 5v14M5 12h14" /> : <path d="M5 12h14" />}
              </svg>
              {action === 'add' ? 'Add tag' : 'Remove tag'}
            </button>
            {picker === action && (
              <TagPicker
                canCreate={action === 'add'}
                onPick={(tag) => apply.mutate({ action, tag })}
                onClose={() => setPicker(null)}
              />
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={onDone}
          className="ml-auto h-10 cursor-pointer rounded-full border-0 bg-ink px-4 text-sm font-semibold text-on-ink"
        >
          Done
        </button>
      </div>
      {status && (
        <p role="status" className="m-0 text-sm text-ink2">
          {status}
        </p>
      )}
    </div>
  )
}

function plural(n: number) {
  return `${n} ${n === 1 ? 'bookmark' : 'bookmarks'}`
}

/** "Added Programming to 2 bookmarks. 1 already had 5 tags, so it was skipped." */
function resultLine(action: 'add' | 'remove', name: string, { changed, skipped }: TagBulkResult) {
  if (action === 'remove') return `Removed ${name} from ${plural(changed)}.`
  const added = `Added ${name} to ${plural(changed)}.`
  if (!skipped) return added
  return `${added} ${skipped} already had 5 tags, so ${skipped === 1 ? 'it was' : 'they were'} skipped.`
}

/** The 300 px picker under Add tag / Remove tag: find a tag (or, for Add, create one). */
function TagPicker(props: { canCreate: boolean; onPick: (tag: Tag | string) => void; onClose: () => void }) {
  const all = useTags()
  const [text, setText] = useState('')
  const box = useRef<HTMLDivElement>(null)
  const onClose = useRef(props.onClose)
  useEffect(() => {
    onClose.current = props.onClose
  })
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose.current()
    const onDown = (e: MouseEvent) => !box.current?.parentElement?.contains(e.target as Node) && onClose.current()
    document.addEventListener('keydown', onKey)
    document.addEventListener('mousedown', onDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('mousedown', onDown)
    }
  }, [])

  const [active, setActive] = useState(0)
  const listId = useId()
  const typed = text.trim().replace(/\s+/g, ' ')
  const matching = (all.data ?? []).filter((t) => t.name.toLowerCase().includes(typed.toLowerCase()))
  const exists = (all.data ?? []).some((t) => t.name.toLowerCase() === typed.toLowerCase())
  // The highlighted option (the first, to start with) is what Enter picks.
  const options: { key: string; pick: Tag | string; label: string; count?: number }[] = [
    ...matching.map((tag) => ({ key: String(tag.id), pick: tag, label: tag.name, count: tag.count })),
    ...(props.canCreate && typed && !exists ? [{ key: 'new', pick: typed, label: `+ Create tag “${typed}”` }] : []),
  ]
  return (
    <div
      ref={box}
      className="absolute top-full left-0 z-20 mt-1.5 flex w-[300px] max-w-[calc(100vw-32px)] flex-col gap-2 rounded-[14px] border border-line bg-surface p-2.5 shadow-[0_12px_32px_rgba(0,0,0,0.18)]"
    >
      <input
        autoFocus
        role="combobox"
        aria-label={props.canCreate ? 'Find or create a tag' : 'Find a tag'}
        aria-expanded={options.length > 0}
        aria-controls={listId}
        aria-activedescendant={options[active] && `${listId}-${options[active].key}`}
        placeholder={props.canCreate ? 'Find or create a tag' : 'Find a tag'}
        value={text}
        maxLength={MAX_TAG_NAME}
        onChange={(e) => {
          setText(e.target.value)
          setActive(0)
        }}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') setActive((a) => Math.min(a + 1, options.length - 1))
          else if (e.key === 'ArrowUp') setActive((a) => Math.max(a - 1, 0))
          else if (e.key === 'Enter' && options[active]) props.onPick(options[active].pick)
          else return
          e.preventDefault()
        }}
        className="h-10 rounded-[10px] border border-line bg-surface px-3 text-sm text-ink placeholder:text-muted"
      />
      <ul id={listId} role="listbox" className="m-0 flex max-h-[240px] list-none flex-col overflow-auto p-0">
        {options.map((option, i) => (
          <li
            key={option.key}
            id={`${listId}-${option.key}`}
            role="option"
            aria-selected={i === active}
            onMouseEnter={() => setActive(i)}
            onMouseDown={(e) => e.preventDefault()} // keep focus in the input
            onClick={() => props.onPick(option.pick)}
            className={`flex min-h-9 cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 text-sm text-ink ${i === active ? 'bg-line' : ''}`}
          >
            <span className="truncate">{option.label}</span>
            {option.count !== undefined && <span className="text-xs text-muted">{option.count}</span>}
          </li>
        ))}
      </ul>
      {props.canCreate && <p className="m-0 text-xs text-muted">Bookmarks that already have 5 tags are skipped.</p>}
    </div>
  )
}
