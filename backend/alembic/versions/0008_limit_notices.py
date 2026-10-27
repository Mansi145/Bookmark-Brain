"""when users hit the daily AI limit and told the maintainer

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-27 18:00:00.000000

The Limit reached dialog's "Notify the maintainer" emails the owner. ai_usage records when
each user was first refused that day and when they sent the email (once a day per user).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_usage", sa.Column("limit_reached_at", sa.DateTime(timezone=True)))
    op.add_column("ai_usage", sa.Column("maintainer_notified_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("ai_usage", "maintainer_notified_at")
    op.drop_column("ai_usage", "limit_reached_at")
