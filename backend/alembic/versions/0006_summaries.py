"""AI summaries and the per-user daily limit

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-27 10:00:00.000000

Summaries are made on demand (the Summarise button) and cached on documents, so everyone who
saved a URL shares one summary. ai_usage counts summaries started per user per UTC day.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("key_points", postgresql.JSONB(), nullable=True))
    op.add_column("documents", sa.Column("summary_status", sa.String(16), nullable=True))
    op.add_column("documents", sa.Column("summary_source", sa.String(16), nullable=True))
    op.add_column("documents", sa.Column("summary_model", sa.String(64), nullable=True))
    op.add_column(
        "documents", sa.Column("summarised_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "ai_usage",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("summaries", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("user_id", "day"),
    )


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'summarise'")
    op.drop_table("ai_usage")
    for column in (
        "summarised_at",
        "summary_model",
        "summary_source",
        "summary_status",
        "key_points",
        "summary",
    ):
        op.drop_column("documents", column)
