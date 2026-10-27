import type { Bookmark } from '../api/types'

// The feed's date groups: Today / This week / Earlier, by when the bookmark was saved. The
// newspaper feed calls them editions.

export type EditionKey = 'today' | 'week' | 'earlier'
export type Edition = { key: EditionKey; title: string; items: Bookmark[] }

const DAY = 24 * 60 * 60 * 1000

function startOfToday() {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return today
}

/**
 * Where This week ends and Earlier begins: the start of the day six days ago (local time). The
 * feed sends it to the server as an exact moment, so both sides split at the same instant.
 */
export function startOfWeek() {
  return new Date(startOfToday().getTime() - 6 * DAY)
}

/** Rows arrive newest first, so each group keeps that order. Empty groups are left out. */
export function groupBySaveDate(bookmarks: Bookmark[]): Edition[] {
  const today = startOfToday().getTime()
  const weekAgo = startOfWeek().getTime()
  const groups: Edition[] = [
    { key: 'today', title: 'Today', items: [] },
    { key: 'week', title: 'This week', items: [] },
    { key: 'earlier', title: 'Earlier', items: [] },
  ]
  for (const b of bookmarks) {
    const saved = new Date(b.added_at).getTime()
    groups[saved >= today ? 0 : saved >= weekAgo ? 1 : 2].items.push(b)
  }
  return groups.filter((g) => g.items.length > 0)
}

const dayMonth = new Intl.DateTimeFormat(undefined, {
  day: 'numeric',
  month: 'long',
})
const weekday = new Intl.DateTimeFormat(undefined, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})

/** The masthead's date: "Tuesday 27 October", "21–26 October", "Before 21 October". */
export function editionDate(key: EditionKey) {
  const today = startOfToday()
  const weekStart = startOfWeek()
  if (key === 'today') return weekday.format(today)
  if (key === 'earlier') return `Before ${dayMonth.format(weekStart)}`
  const yesterday = new Date(today.getTime() - DAY)
  return dayMonth.formatRange(weekStart, yesterday)
}
