import type { Bookmark } from '../api/types'

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' })

export default function BookmarkCard({ bookmark }: { bookmark: Bookmark }) {
  const folders = [...new Set(bookmark.sources.map((s) => s.folder_path).filter(Boolean))]
  const browsers = [...new Set(bookmark.sources.map((s) => s.browser))]

  return (
    <article className="flex flex-col rounded-xl border border-stone-200 bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="flex items-center gap-2 text-xs text-stone-500">
        <img
          src={`https://www.google.com/s2/favicons?domain=${bookmark.site}&sz=32`}
          alt=""
          className="h-4 w-4"
          loading="lazy"
        />
        <span className="truncate">{bookmark.site}</span>
        <span className="ml-auto shrink-0">{dateFormat.format(new Date(bookmark.added_at))}</span>
      </div>

      <a
        href={bookmark.url}
        target="_blank"
        rel="noreferrer"
        className="mt-2 line-clamp-2 font-semibold text-stone-900 hover:underline"
      >
        {bookmark.title}
      </a>

      {/* The AI summary goes here in Phase 2. */}
      <p className="mt-2 text-sm italic text-stone-400">Summary coming soon</p>

      <div className="mt-auto flex flex-wrap gap-1.5 pt-4">
        {folders.map((f) => (
          <span key={f} className="rounded bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
            {f}
          </span>
        ))}
        {browsers.map((b) => (
          <span key={b} className="rounded bg-sky-50 px-2 py-0.5 text-xs capitalize text-sky-700">
            {b}
          </span>
        ))}
      </div>
    </article>
  )
}
