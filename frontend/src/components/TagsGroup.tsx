import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Tag, TagCount } from '../api/types'
import {
  LIMIT_TEXT,
  MAX_PER_USER,
  MAX_TAG_NAME,
  tagErrorCode,
  useRefreshTags,
  useTagFilter,
  useTags,
} from '../lib/tags'
import SidebarSection from './SidebarSection'

// The sidebar's Tags group (boards FeedTags, FeedTagMenu, FeedTagRename, FeedTagRenameTaken,
// FeedTagMerge, FeedTagDelete, FeedTagNew, FeedTagLimit, FeedTagsUnused, FeedTagsFresh). Tags in
// use, biggest first, 8 then Show all; Show unused reveals the rest so they can be renamed or
// deleted. Several can be picked: bookmarks with all of them. Each row's ⋯ menu renames, merges
// or deletes.

const FIRST = 8

export default function TagsGroup({ inUse }: { inUse: TagCount[] }) {
  const filter = useTagFilter()
  const all = useTags()
  const [adding, setAdding] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const [showUnused, setShowUnused] = useState(false)
  const [renaming, setRenaming] = useState<number | null>(null)
  const [dialog, setDialog] = useState<{
    kind: 'merge' | 'delete'
    tag: Tag
  } | null>(null)

  const unused = (all.data ?? []).filter((t) => t.count === 0)
  // Picked tags stay in view even past the first 8.
  const shown = showAll ? inUse : inUse.filter((t, i) => i < FIRST || filter.picked.includes(t.id))
  const atLimit = (all.data?.length ?? 0) >= MAX_PER_USER

  const row = (tag: TagCount) =>
    renaming === tag.id ? (
      <RenameRow key={tag.id} tag={tag} onDone={() => setRenaming(null)} />
    ) : (
      <TagRow
        key={tag.id}
        tag={tag}
        picked={filter.picked.includes(tag.id)}
        onPick={() => filter.toggle(tag.id)}
        onRename={() => setRenaming(tag.id)}
        onMerge={() => setDialog({ kind: 'merge', tag })}
        onDelete={() => setDialog({ kind: 'delete', tag })}
      />
    )

  return (
    <SidebarSection
      id="tags"
      title="Tags"
      action={
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="h-9 cursor-pointer border-0 bg-transparent px-1 text-[13px] font-medium text-ink"
        >
          + New tag
        </button>
      }
    >
      {adding &&
        (atLimit ? (
          <p role="alert" className="m-0 mb-2 text-[13px] text-dead-fg">
            {LIMIT_TEXT.account}
          </p>
        ) : (
          <NewTagForm onDone={() => setAdding(false)} />
        ))}

      {inUse.length === 0 && (
        <p className="m-0 mb-1 px-1 text-[13px] text-ink2">
          No tags on your bookmarks yet. Add one from a bookmark, or the AI adds them when it writes a summary.
        </p>
      )}
      <ul className="m-0 flex list-none flex-col gap-0.5 p-0">{shown.map(row)}</ul>

      {showUnused && unused.length > 0 && (
        <>
          <p className="m-0 mt-2.5 mb-1 px-1 text-xs font-semibold text-muted">Unused</p>
          <ul className="m-0 flex list-none flex-col gap-0.5 p-0">{unused.map(row)}</ul>
        </>
      )}
      <div className="mt-1 flex flex-wrap gap-x-3 px-1">
        {inUse.length > FIRST && (
          <LinkButton onClick={() => setShowAll(!showAll)}>
            {showAll ? 'Show fewer' : `Show all ${inUse.length}`}
          </LinkButton>
        )}
        {unused.length > 0 && (
          <LinkButton onClick={() => setShowUnused(!showUnused)}>
            {showUnused ? 'Hide unused' : `Show unused (${unused.length})`}
          </LinkButton>
        )}
      </div>

      {dialog?.kind === 'merge' && (
        <MergeDialog
          tag={dialog.tag}
          others={(all.data ?? []).filter((t) => t.id !== dialog.tag.id)}
          count={all.data?.find((t) => t.id === dialog.tag.id)?.count ?? 0}
          onClose={() => setDialog(null)}
          onMerged={() => filter.remove(dialog.tag.id)}
        />
      )}
      {dialog?.kind === 'delete' && (
        <DeleteDialog
          tag={dialog.tag}
          count={all.data?.find((t) => t.id === dialog.tag.id)?.count ?? 0}
          onClose={() => setDialog(null)}
          onDeleted={() => filter.remove(dialog.tag.id)}
        />
      )}
    </SidebarSection>
  )
}

function LinkButton(props: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      className="h-9 cursor-pointer border-0 bg-transparent p-0 text-[13px] font-medium text-ink underline"
    >
      {props.children}
    </button>
  )
}

function TagRow(props: {
  tag: TagCount
  picked: boolean
  onPick: () => void
  onRename: () => void
  onMerge: () => void
  onDelete: () => void
}) {
  const [menu, setMenu] = useState(false)
  const { tag, picked } = props
  return (
    <li className="group relative flex items-center gap-0.5">
      <button
        type="button"
        aria-pressed={picked}
        title={tag.name}
        onClick={props.onPick}
        className={`flex min-h-9 min-w-0 flex-1 cursor-pointer items-center justify-between gap-2 rounded-lg border-0 px-2.5 py-1.5 text-left text-sm ${
          picked ? 'bg-accent font-semibold text-on-accent' : 'bg-transparent text-ink hover:bg-skeleton'
        }`}
      >
        <span className="truncate">{tag.name}</span>
        <span className={`text-xs ${picked ? 'text-on-accent2' : 'text-muted'}`}>{tag.count}</span>
      </button>
      {/* On hover or focus; always on touch screens, which can't hover. */}
      <button
        type="button"
        aria-label={`More for ${tag.name}`}
        aria-haspopup="menu"
        aria-expanded={menu}
        onClick={() => setMenu(!menu)}
        className={`grid size-9 flex-none cursor-pointer place-items-center rounded-lg border-0 bg-transparent text-ink2 hover:bg-skeleton focus-visible:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100 ${menu ? 'opacity-100' : 'opacity-0'}`}
      >
        <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="5" cy="12" r="1.8" />
          <circle cx="12" cy="12" r="1.8" />
          <circle cx="19" cy="12" r="1.8" />
        </svg>
      </button>
      {menu && (
        <TagMenu
          onClose={() => setMenu(false)}
          items={[
            { label: 'Rename', icon: PENCIL, run: props.onRename },
            { label: 'Merge into another tag…', icon: MERGE, run: props.onMerge },
            { label: 'Delete tag', icon: BIN, run: props.onDelete, danger: true },
          ]}
        />
      )}
    </li>
  )
}

/** The ⋯ menu (board FeedTagMenu): closes on Escape, a click outside or a choice. */
function TagMenu(props: {
  items: { label: string; icon: React.ReactNode; run: () => void; danger?: boolean }[]
  onClose: () => void
}) {
  const menu = useRef<HTMLDivElement>(null)
  const onClose = useRef(props.onClose)
  useEffect(() => {
    onClose.current = props.onClose
  })
  useEffect(() => {
    menu.current?.querySelector('button')?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose.current()
    const onDown = (e: MouseEvent) => !menu.current?.parentElement?.contains(e.target as Node) && onClose.current()
    document.addEventListener('keydown', onKey)
    document.addEventListener('mousedown', onDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('mousedown', onDown)
    }
  }, [])
  return (
    <div
      ref={menu}
      role="menu"
      className="absolute top-full right-0 z-20 mt-1 flex w-[230px] flex-col rounded-[14px] border border-line bg-surface p-1.5 shadow-[0_12px_32px_rgba(0,0,0,0.18)]"
    >
      {props.items.map((item) => (
        <div key={item.label}>
          {item.danger && <div aria-hidden className="my-1 h-px bg-line" />}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              props.onClose()
              item.run()
            }}
            className={`flex h-10 w-full cursor-pointer items-center gap-2.5 rounded-lg border-0 bg-transparent px-3 text-left text-sm hover:bg-skeleton ${item.danger ? 'font-medium text-dead-fg' : 'text-ink'}`}
          >
            <svg
              aria-hidden
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`flex-none ${item.danger ? '' : 'text-ink2'}`}
            >
              {item.icon}
            </svg>
            {item.label}
          </button>
        </div>
      ))}
    </div>
  )
}

const PENCIL = <path d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4" />
const MERGE = (
  <>
    <path d="M6 4v4a6 6 0 0 0 6 6h6" />
    <path d="M6 20v-4" />
    <path d="m15 11 3 3-3 3" />
  </>
)
const BIN = (
  <>
    <path d="M4 7h16" />
    <path d="M10 11v6M14 11v6" />
    <path d="M6 7l1 13h10l1-13" />
    <path d="M9 7V4h6v3" />
  </>
)

const input =
  'h-9 w-full min-w-0 rounded-lg border border-line bg-surface px-2.5 text-sm text-ink placeholder:text-muted'
const smallInk =
  'h-9 cursor-pointer rounded-lg border-0 bg-ink px-3 text-[13px] font-semibold text-on-ink disabled:opacity-50'
const smallOutline = 'h-9 cursor-pointer rounded-lg border border-line bg-surface px-3 text-[13px] font-medium text-ink'

/** "+ New tag" (board FeedTagNew): an input at the top of the list. */
function NewTagForm({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState('')
  const refresh = useRefreshTags()
  const create = useMutation({
    mutationFn: () => api.post<Tag>('/api/tags', { name }),
    onSuccess: () => {
      refresh()
      onDone()
    },
  })
  const code = tagErrorCode(create.error)
  const error =
    code === 'tag_name_taken'
      ? `There's already a tag called “${name.trim()}”.`
      : code === 'tag_limit'
        ? LIMIT_TEXT.account
        : create.isError
          ? "Couldn't add the tag. Check your connection and try again."
          : null
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (name.trim()) create.mutate()
      }}
      className="mb-2 flex flex-col gap-2 px-1"
    >
      <input
        autoFocus
        aria-label="New tag name"
        value={name}
        maxLength={MAX_TAG_NAME}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === 'Escape' && onDone()}
        className={input}
      />
      <div className="flex gap-2">
        <button type="submit" disabled={!name.trim() || create.isPending} className={smallInk}>
          Add tag
        </button>
        <button type="button" onClick={onDone} className={smallOutline}>
          Cancel
        </button>
      </div>
      {error ? (
        <p role="alert" className="m-0 text-[13px] text-dead-fg">
          {error}
        </p>
      ) : (
        <p className="m-0 text-xs text-muted">Up to {MAX_TAG_NAME} characters. The AI can use it from now on.</p>
      )}
    </form>
  )
}

/** Rename (boards FeedTagRename, FeedTagRenameTaken): the row becomes an input. */
function RenameRow({ tag, onDone }: { tag: Tag; onDone: () => void }) {
  const [name, setName] = useState(tag.name)
  const refresh = useRefreshTags()
  const rename = useMutation({
    mutationFn: () => api.patch<Tag>(`/api/tags/${tag.id}`, { name }),
    onSuccess: () => {
      refresh()
      onDone()
    },
  })
  const error =
    tagErrorCode(rename.error) === 'tag_name_taken'
      ? `There's already a tag called “${name.trim()}”. To combine the two, use Merge.`
      : rename.isError
        ? "Couldn't rename it. Check your connection and try again."
        : null
  return (
    <li>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (name.trim() === tag.name) onDone()
          else if (name.trim()) rename.mutate()
        }}
        className="flex flex-col gap-2 px-1 py-1"
      >
        <input
          autoFocus
          aria-label={`New name for ${tag.name}`}
          value={name}
          maxLength={MAX_TAG_NAME}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Escape' && onDone()}
          className={input}
        />
        <div className="flex gap-2">
          <button type="submit" disabled={!name.trim() || rename.isPending} className={smallInk}>
            Save
          </button>
          <button type="button" onClick={onDone} className={smallOutline}>
            Cancel
          </button>
        </div>
        {error && (
          <p role="alert" className="m-0 text-[13px] text-dead-fg">
            {error}
          </p>
        )}
      </form>
    </li>
  )
}

function plural(n: number) {
  return `${n} ${n === 1 ? 'bookmark' : 'bookmarks'}`
}

/** Merge into another tag (board FeedTagMerge). */
function MergeDialog(props: {
  tag: Tag
  others: TagCount[]
  count: number
  onClose: () => void
  onMerged: () => void
}) {
  const [into, setInto] = useState<TagCount | null>(null)
  const refresh = useRefreshTags()
  const merge = useMutation({
    mutationFn: () => api.post<Tag>(`/api/tags/${props.tag.id}/merge`, { into: into!.id }),
    onSuccess: () => {
      props.onMerged()
      refresh()
      props.onClose()
    },
  })
  const its = props.count === 1 ? 'Its bookmark gets' : `Its ${props.count} bookmarks get`
  return (
    <Dialog title={`Merge “${props.tag.name}”`} onClose={props.onClose}>
      <p className="m-0 text-ink2">
        {its} the tag you pick, then “{props.tag.name}” is deleted.
      </p>
      <div role="radiogroup" aria-label="Merge into" className="flex max-h-[280px] flex-col gap-0.5 overflow-auto">
        {props.others.map((t) => (
          <label
            key={t.id}
            className="flex min-h-10 cursor-pointer items-center gap-3 rounded-lg px-2.5 hover:bg-skeleton"
          >
            <input type="radio" name="merge-into" checked={into?.id === t.id} onChange={() => setInto(t)} />
            <span className="flex-1 truncate">{t.name}</span>
            <span className="text-xs text-muted">{t.count}</span>
          </label>
        ))}
      </div>
      <div className="flex flex-wrap gap-2.5">
        <button
          type="button"
          disabled={!into || merge.isPending}
          onClick={() => merge.mutate()}
          className="h-11 cursor-pointer rounded-[10px] border-0 bg-ink px-[18px] font-semibold text-on-ink disabled:cursor-default disabled:opacity-50"
        >
          {into ? `Merge into ${into.name}` : 'Merge'}
        </button>
        <button type="button" onClick={props.onClose} className={dialogCancel}>
          Cancel
        </button>
      </div>
      {merge.isError && (
        <p role="alert" className="m-0 text-[13px] text-dead-fg">
          Couldn't merge the tags. Check your connection and try again.
        </p>
      )}
    </Dialog>
  )
}

/** Delete tag (board FeedTagDelete): an alert dialog like Delete account. */
function DeleteDialog(props: { tag: Tag; count: number; onClose: () => void; onDeleted: () => void }) {
  const refresh = useRefreshTags()
  const remove = useMutation({
    mutationFn: () => api.delete<void>(`/api/tags/${props.tag.id}`),
    onSuccess: () => {
      props.onDeleted()
      refresh()
      props.onClose()
    },
  })
  return (
    <Dialog title={`Delete the tag “${props.tag.name}”?`} onClose={props.onClose} alert>
      <p className="m-0 text-ink2">
        {props.count > 0
          ? `It comes off ${plural(props.count)}. The bookmarks stay, and so do their other tags.`
          : "It isn't on any bookmarks."}
      </p>
      <div className="flex flex-wrap gap-2.5">
        <button
          type="button"
          disabled={remove.isPending}
          onClick={() => remove.mutate()}
          className="h-11 cursor-pointer rounded-[10px] border-0 bg-dead-fg px-[18px] font-semibold text-on-dead disabled:opacity-50"
        >
          Delete tag
        </button>
        <button type="button" onClick={props.onClose} className={dialogCancel}>
          Cancel
        </button>
      </div>
      {remove.isError && (
        <p role="alert" className="m-0 text-[13px] text-dead-fg">
          Couldn't delete the tag. Check your connection and try again.
        </p>
      )}
    </Dialog>
  )
}

const dialogCancel = 'h-11 cursor-pointer rounded-[10px] border border-line bg-surface px-4 font-medium text-ink'

/** A modal card on a dimmed page; Escape or the backdrop closes it, focus returns afterwards. */
function Dialog(props: { title: string; alert?: boolean; onClose: () => void; children: React.ReactNode }) {
  const card = useRef<HTMLDivElement>(null)
  const onClose = useRef(props.onClose)
  useEffect(() => {
    onClose.current = props.onClose
  })
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null
    card.current?.querySelector<HTMLElement>('input, button')?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose.current()
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      before?.focus()
    }
  }, [])
  return (
    <div className="fixed inset-0 z-40 grid place-items-start justify-center overflow-auto p-4 pt-[150px]">
      <div aria-hidden className="fixed inset-0 bg-[rgba(20,21,22,0.55)]" onClick={props.onClose} />
      <div
        ref={card}
        role={props.alert ? 'alertdialog' : 'dialog'}
        aria-modal="true"
        aria-label={props.title}
        className="relative flex w-full max-w-[460px] flex-col gap-3 rounded-2xl bg-surface p-7 text-ink shadow-[0_24px_60px_rgba(0,0,0,0.35)]"
      >
        {props.alert && (
          <span aria-hidden className="grid size-12 place-items-center rounded-full bg-dead-bg text-dead-fg">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 7h16" />
              <path d="M10 11v6M14 11v6" />
              <path d="M6 7l1 13h10l1-13" />
              <path d="M9 7V4h6v3" />
            </svg>
          </span>
        )}
        <h2 className="mt-1 font-serif text-2xl leading-[1.2] font-bold">{props.title}</h2>
        {props.children}
      </div>
    </div>
  )
}
