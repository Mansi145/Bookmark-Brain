"""ORM models.

Import every model here so Alembic autogenerate can see them.

Shape of the bookmark data:
    users 1──* bookmarks *──1 documents
                  │
                  1──* bookmark_sources   (one per browser that has it)

`documents` are shared across users (one row per normalised URL), so the
expensive AI work done in later phases is cached once per URL.

`jobs` is the background work queue (see app/worker.py).
"""

import enum
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "google_sub IS NOT NULL OR github_id IS NOT NULL", name="ck_users_has_provider"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # How the account signs in: Google's stable account id ("sub" claim) and/or GitHub's numeric
    # user id. Emails can change; these can't. One account can have both (same verified email,
    # owner's decision), and always has at least one.
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    github_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)

    @property
    def providers(self) -> list[str]:
        """How this account can sign in, e.g. ["google", "github"] (shown in Settings)."""
        linked = (("google", self.google_sub), ("github", self.github_id))
        return [name for name, account_id in linked if account_id is not None]


class ApiToken(TimestampMixin, Base):
    """Personal access token used by the browser extension."""

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    # SHA-256 of the token. The plaintext is shown to the user once and never stored.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # First characters of the token, so the UI can show which one is which.
    prefix: Mapped[str] = mapped_column(String(16))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentStatus(enum.StrEnum):
    pending = "pending"  # known URL, a fetch_page job is queued
    fetched = "fetched"  # article text extracted
    summarised = "summarised"  # unused: summaries have their own summary_status
    failed = "failed"  # couldn't get readable text (not HTML, blocked, gave up retrying)
    dead = "dead"  # the page is gone (404 / 410)


# How many numbers each page's embedding has. gemini-embedding-2 makes 3,072 by default; 768 is
# Google's recommended smaller size: a quarter of the storage and faster comparisons for almost the
# same quality. The model is asked for exactly this many (app/ai/llm.py), and changing it needs a
# migration and re-embedding every page.
EMBEDDING_DIMENSIONS = 768

# Keyword search: the page's words, weighted so a match in the title (A) ranks above one in the
# description, summary or key points (B), which ranks above one in the page text (C). The page
# text is capped because a tsvector must stay under 1 MB.
DOCUMENT_TSV = """
setweight(to_tsvector('english', coalesce(title, '')), 'A')
|| setweight(to_tsvector('english', coalesce(description, '') || ' ' || coalesce(summary, '')
    || ' ' || coalesce(key_points::text, '')), 'B')
|| setweight(to_tsvector('english', left(coalesce(content_text, ''), 100000)), 'C')
"""


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tsv", "tsv", postgresql_using="gin"),
        # HNSW: a graph index that finds the nearest vectors without comparing every row.
        # vector_cosine_ops makes it serve the cosine distance operator (<=>).
        Index(
            "ix_documents_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    normalized_url: Mapped[str] = mapped_column(Text, unique=True)
    # The URL as first seen, for opening the page (normalisation may drop bits).
    url: Mapped[str] = mapped_column(Text)
    site: Mapped[str] = mapped_column(String(255))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.pending
    )

    # Filled in by the fetch_page job (app/worker.py).
    title: Mapped[str | None] = mapped_column(Text)  # the page's own title
    description: Mapped[str | None] = mapped_column(Text)  # <meta name="description">
    content_text: Mapped[str | None] = mapped_column(Text)  # main article text, no nav/ads
    word_count: Mapped[int | None] = mapped_column(Integer)
    http_status: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Where content_text came from: "page" (the live page) or "archive" (a Wayback Machine
    # copy of a dead link, looked up when a user asks). Null = no text.
    content_source: Mapped[str | None] = mapped_column(String(16))
    # Wayback Machine lookup for dead links, only when a user clicks "Find archived copy":
    # null (never asked) | "checking" | "found" | "none" (no copy) | "failed" (unreachable).
    archive_status: Mapped[str | None] = mapped_column(String(16))
    archive_url: Mapped[str | None] = mapped_column(Text)  # the snapshot, for people to open
    archived_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Why we can't read it anonymously: "login" (sign-in page / logged-in app) or
    # "paywall" (subscribers only). Null = open. See app/services/access.py.
    access: Mapped[str | None] = mapped_column(String(16))
    # The site's logo (favicon), as declared by the page or the usual /favicon.ico guess.
    # The browser loads it straight from the site; we don't store images.
    icon_url: Mapped[str | None] = mapped_column(Text)
    # The page's preview image (og:image), shown only on the newspaper feed's top story. The
    # browser loads it from the site; we store the URL only. See app/services/preview.py.
    image_url: Mapped[str | None] = mapped_column(Text)

    # The AI summary, made on demand by the summarise job (app/ai/chains.py) and shared by
    # everyone who saved this URL. summary_status: null (never asked) | "working" | "done" |
    # "failed". summary_source records what it was made from: "page", "archive" (a Wayback
    # copy) or "metadata" (only the title and description); stored, never shown (owner).
    summary: Mapped[str | None] = mapped_column(Text)
    key_points: Mapped[list[str] | None] = mapped_column(JSONB)
    summary_status: Mapped[str | None] = mapped_column(String(16))
    summary_source: Mapped[str | None] = mapped_column(String(16))
    summary_model: Mapped[str | None] = mapped_column(String(64))  # which model answered
    summarised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Meaning search: the page's embedding (app/ai/embedding.py decides which text), written by
    # the embed_pages job and shared by everyone who saved this URL. Vectors from different
    # models can't be compared, so the model is recorded. embedded_at null = waiting for the
    # job; set with no embedding = nothing worth embedding (a sign-in page).
    # Deferred: loaded only when asked for, so the feed doesn't carry 768 numbers per story.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), deferred=True
    )
    embedding_model: Mapped[str | None] = mapped_column(String(64))
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Keyword search (DOCUMENT_TSV): Postgres keeps it up to date whenever the row changes.
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed(DOCUMENT_TSV, persisted=True), deferred=True
    )


class ReadState(enum.StrEnum):
    unread = "unread"
    read = "read"


class Bookmark(TimestampMixin, Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "document_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    # Earliest date any browser says it was bookmarked.
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    read_state: Mapped[ReadState] = mapped_column(
        Enum(ReadState, name="read_state"), default=ReadState.unread
    )
    # Set when no browser has this bookmark any more (soft delete keeps AI work and read state).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[Document] = relationship(lazy="joined")
    sources: Mapped[list["BookmarkSource"]] = relationship(
        back_populates="bookmark", lazy="selectin"
    )


class BookmarkSource(TimestampMixin, Base):
    """Where a bookmark lives in one browser install."""

    __tablename__ = "bookmark_sources"
    # A browser's node id is only unique within that browser install.
    __table_args__ = (UniqueConstraint("user_id", "source_id", "node_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    bookmark_id: Mapped[int] = mapped_column(
        ForeignKey("bookmarks.id", ondelete="CASCADE"), index=True
    )
    # Random id the extension generates per install (two Chrome profiles = two sources).
    source_id: Mapped[str] = mapped_column(String(64))
    browser: Mapped[str] = mapped_column(String(32))  # chrome | edge | brave | firefox | ...
    node_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    folder_path: Mapped[str] = mapped_column(Text, default="")  # e.g. "Bookmarks bar/Reading"
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    bookmark: Mapped[Bookmark] = relationship(back_populates="sources")


class JobStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"  # gave up after max attempts


class Job(TimestampMixin, Base):
    """A unit of slow background work, e.g. {"kind": "fetch_page", "payload": {"document_id": 7}}.

    Request handlers only insert rows here; app/worker.py picks them up. Keeping the
    queue in Postgres means no Redis/Celery, and a job survives the API restarting.
    """

    __tablename__ = "jobs"
    # The worker's "next job" query: queued jobs whose time has come, oldest first.
    __table_args__ = (Index("ix_jobs_status_run_after", "status", "run_after"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), server_default=JobStatus.queued.value
    )
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    # Not before this time (used for retry back-off).
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # When a worker took it. A "running" job with an old locked_at belongs to a worker
    # that died (e.g. the API restarted), so it's safe to hand out again.
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class AiUsage(Base):
    """How many AI summaries a user started on a day (UTC), for AI_DAILY_LIMIT_PER_USER.

    The free Gemini and Groq quotas are per API key, so every user shares them; a per-user
    limit stops one person from using up everyone's day.
    """

    __tablename__ = "ai_usage"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    summaries: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # When a Summarise was first refused that day, and when the user emailed the maintainer
    # about it from the Limit reached dialog (at most once a day; see api/usage.py).
    limit_reached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    maintainer_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
