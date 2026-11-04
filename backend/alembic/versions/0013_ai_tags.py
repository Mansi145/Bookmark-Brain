"""ai tags: when the AI last picked a bookmark's tags, and tags for bookmarks summarised already

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-04 12:00:00.000000

New summaries queue a tag_bookmark job themselves (worker.py). Bookmarks summarised before AI
tags existed get one now, once each (owner, 2026-11-03: tag them once, no new UI).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bookmarks", sa.Column("ai_tagged_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        INSERT INTO jobs (kind, payload)
        SELECT 'tag_bookmark', jsonb_build_object('bookmark_id', bookmarks.id)
        FROM bookmarks JOIN documents ON documents.id = bookmarks.document_id
        WHERE documents.summary_status = 'done' AND bookmarks.deleted_at IS NULL
        ORDER BY bookmarks.id
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'tag_bookmark' AND status = 'queued'")
    op.drop_column("bookmarks", "ai_tagged_at")
