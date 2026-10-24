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
from datetime import datetime

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Google's stable account id ("sub" claim). Emails can change; this can't.
    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)


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
    pending = "pending"  # known URL, not fetched yet (fetching arrives in Phase 2)
    fetched = "fetched"
    summarised = "summarised"
    failed = "failed"
    dead = "dead"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    normalized_url: Mapped[str] = mapped_column(Text, unique=True)
    # The URL as first seen, for opening the page (normalisation may drop bits).
    url: Mapped[str] = mapped_column(Text)
    site: Mapped[str] = mapped_column(String(255))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.pending
    )


class ReadState(enum.StrEnum):
    unread = "unread"
    read = "read"
    archived = "archived"


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
