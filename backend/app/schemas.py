"""Request/response shapes for the API (validated by FastAPI, shown in /docs)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import DocumentStatus, ReadState


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth -------------------------------------------------------------------


class GoogleLoginIn(BaseModel):
    credential: str  # the ID token Google Sign-In hands to the browser


class UserOut(ORMModel):
    id: int
    email: str
    name: str | None
    avatar_url: str | None


# --- Extension tokens -------------------------------------------------------


class TokenCreateIn(BaseModel):
    name: str = Field(default="Browser extension", min_length=1, max_length=100)


class TokenOut(ORMModel):
    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None


class TokenCreatedOut(TokenOut):
    token: str  # plaintext, returned only once at creation


# --- Sync (extension -> API) ------------------------------------------------


class SyncSource(BaseModel):
    id: str = Field(min_length=8, max_length=64)  # per-install random id
    browser: str = Field(max_length=32)


class SyncItem(BaseModel):
    node_id: str = Field(max_length=64)
    url: str = Field(max_length=8192)
    title: str = ""
    folder_path: str = ""
    added_at: datetime


class SyncIn(BaseModel):
    source: SyncSource
    # full=True: `upserts` is the complete bookmark list for this source; anything
    # missing is treated as removed. full=False: an incremental change set.
    full: bool = False
    upserts: list[SyncItem] = Field(default_factory=list, max_length=20_000)
    removed_node_ids: list[str] = Field(default_factory=list, max_length=20_000)


class SyncOut(BaseModel):
    received: int
    skipped_unsupported: int
    upserted: int
    removed_sources: int
    active_bookmarks: int


# --- Feed -------------------------------------------------------------------


class SourceOut(ORMModel):
    browser: str
    folder_path: str


class BookmarkOut(ORMModel):
    id: int
    title: str
    url: str
    site: str
    added_at: datetime
    read_state: ReadState
    status: DocumentStatus
    http_status: int | None  # e.g. 404 for a dead link
    icon_url: str | None  # the site's logo; the browser loads it from the site
    reading_minutes: int | None  # from the page's word count; None until it's fetched
    content_source: str | None  # "page" | "archive" | None (no text)
    archive_status: str | None  # dead links: None | checking | found | none | failed
    archive_url: str | None  # Wayback Machine copy, if there is one
    archived_on: datetime | None
    access: str | None  # "login" | "paywall" | None (open)
    sources: list[SourceOut]


class BookmarkPage(BaseModel):
    items: list[BookmarkOut]
    next_cursor: str | None


class FacetCount(BaseModel):
    value: str
    count: int


class ReadStateCounts(BaseModel):
    unread: int
    read: int


class FacetsOut(BaseModel):
    total: int  # bookmarks in this section
    read_states: ReadStateCounts  # for the Feed's reading-state bar
    pending: int  # of those, pages still being fetched
    folders: list[FacetCount]
    browsers: list[FacetCount]


class ArrivedBookmark(BaseModel):
    title: str
    site: str
    icon_url: str | None


class SyncSummaryOut(BaseModel):
    """What one browser has sent so far (the Connect page while syncing, and when done)."""

    bookmarks: int
    folders: int
    just_arrived: list[ArrivedBookmark]  # newest first
    other_browsers: list[str]  # the user's other browsers that have synced bookmarks
