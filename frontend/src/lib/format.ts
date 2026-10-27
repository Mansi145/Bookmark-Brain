// Small text helpers shared by the feed rows and the detail panel.

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' })

export function formatDate(iso: string) {
  return dateFormat.format(new Date(iso))
}

export function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/** "just now", "5 min ago", "3 h ago", "2d ago", "3w ago", "4mo ago", then a date. */
export function age(iso: string) {
  const minutes = (Date.now() - new Date(iso).getTime()) / 60_000
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${Math.floor(minutes)} min ago`
  const hours = minutes / 60
  if (hours < 24) return `${Math.floor(hours)} h ago`
  const days = hours / 24
  if (days < 7) return `${Math.floor(days)}d ago`
  if (days < 30) return `${Math.floor(days / 7)}w ago`
  if (days < 365) return `${Math.floor(days / 30)}mo ago`
  return formatDate(iso)
}
