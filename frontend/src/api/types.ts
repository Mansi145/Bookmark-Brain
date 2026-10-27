// Mirrors backend/app/schemas.py. Keep the two in sync.

export type User = {
  id: number
  email: string
  name: string | null
  avatar_url: string | null
}

export type ApiToken = {
  id: number
  name: string
  prefix: string
  created_at: string
  last_used_at: string | null
}

export type CreatedApiToken = ApiToken & { token: string }

export type ReadState = 'unread' | 'read'
export type DocumentStatus = 'pending' | 'fetched' | 'summarised' | 'failed' | 'dead'

export type Bookmark = {
  id: number
  title: string
  url: string
  site: string
  added_at: string
  read_state: ReadState
  status: DocumentStatus
  http_status: number | null // e.g. 404 for a dead link
  icon_url: string | null // the site's logo, loaded straight from the site
  image_url: string | null // the page's preview image, for the newspaper feed's top story
  reading_minutes: number | null // from the page's word count; null until fetched
  content_source: 'page' | 'archive' | null // where the text came from
  // Dead links: Wayback Machine lookup, only when the user clicks "Find archived copy".
  archive_status: 'checking' | 'found' | 'none' | 'failed' | null
  archive_url: string | null // Wayback Machine copy
  archived_on: string | null
  access: 'login' | 'paywall' | null // needs an account / subscription to read
  description: string | null // the site's own description, shown when there's no summary
  // The on-demand AI summary, shared by everyone who saved this URL.
  summary: string | null
  key_points: string[]
  summary_status: 'working' | 'done' | 'failed' | null
  sources: { browser: string; folder_path: string }[]
}

// Each bookmark is in exactly one section (see backend/app/api/bookmarks.py).
export type FeedSection = 'main' | 'sign_in' | 'dead'

export type BookmarkPage = {
  items: Bookmark[]
  next_cursor: string | null
}

export type FacetCount = { value: string; count: number }
export type Facets = {
  total: number // bookmarks in this section
  read_states: { unread: number; read: number } // for the feed's views bar
  pending: number // of those, pages still being fetched
  folders: FacetCount[]
  browsers: FacetCount[]
}

export type ArrivedBookmark = {
  title: string
  site: string
  icon_url: string | null
}

/** GET /api/bookmarks/sync-summary?browser=: what one browser has sent so far (Connect page). */
export type SyncSummary = {
  bookmarks: number
  folders: number
  just_arrived: ArrivedBookmark[] // newest first
  other_browsers: string[]
}

/** GET /api/usage: today's AI summaries for the signed-in user. */
export type Usage = {
  summaries_used: number
  summaries_limit: number
  resets_at: string // midnight UTC
}
