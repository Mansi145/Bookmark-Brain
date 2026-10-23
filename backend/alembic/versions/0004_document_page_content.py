"""document page content

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-23 16:28:43.735755

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = (
    "title",
    "description",
    "content_text",
    "word_count",
    "http_status",
    "fetched_at",
    "content_source",
    "archive_url",
    "archived_on",
    "access",
    "icon_url",
    "archive_status",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("documents", sa.Column("title", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("content_text", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("word_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("http_status", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("content_source", sa.String(length=16), nullable=True))
    op.add_column("documents", sa.Column("archive_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("archived_on", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("access", sa.String(length=16), nullable=True))
    op.add_column("documents", sa.Column("icon_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("archive_status", sa.String(length=16), nullable=True))

    # Backfill: documents that already exist were never fetched, so queue them.
    op.execute(
        "INSERT INTO jobs (kind, payload) "
        "SELECT 'fetch_page', jsonb_build_object('document_id', id) "
        "FROM documents WHERE status = 'pending'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM jobs WHERE kind IN ('fetch_page', 'find_archive')")
    op.execute("UPDATE documents SET status = 'pending'")
    for column in reversed(COLUMNS):
        op.drop_column("documents", column)
