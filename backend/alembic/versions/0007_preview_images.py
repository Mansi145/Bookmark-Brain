"""preview images for the newspaper feed's top story

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-27 14:00:00.000000

New pages get image_url while they're fetched. Pages fetched before this get a find_image job,
which reads the page again but only stores the image URL.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("image_url", sa.Text(), nullable=True))
    # Readable or unreadable pages only: dead links are gone, and pending ones get it anyway.
    op.execute(
        """
        INSERT INTO jobs (kind, payload)
        SELECT 'find_image', jsonb_build_object('document_id', id)
        FROM documents WHERE status IN ('fetched', 'failed')
        ORDER BY id
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'find_image'")
    op.drop_column("documents", "image_url")
