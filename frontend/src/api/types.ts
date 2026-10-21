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

export type ReadState = 'unread' | 'read' | 'archived'
export type DocumentStatus = 'pending' | 'fetched' | 'summarised' | 'failed' | 'dead'

export type Bookmark = {
  id: number
  title: string
  url: string
  site: string
  added_at: string
  read_state: ReadState
  status: DocumentStatus
  sources: { browser: string; folder_path: string }[]
}

export type BookmarkPage = {
  items: Bookmark[]
  next_cursor: string | null
}

export type FacetCount = { value: string; count: number }
export type Facets = { folders: FacetCount[]; browsers: FacetCount[] }
