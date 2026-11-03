"""asked questions: the first question of each Ask chat

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-01 19:29:45.050772

For the Ask tab's Recent questions. Only each chat's first question is kept, never answers, and
only the latest 3 per user (services/questions.py). Deleted with the account (ON DELETE CASCADE).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asked_questions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "asked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asked_questions_user_id"), "asked_questions", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_asked_questions_user_id"), table_name="asked_questions")
    op.drop_table("asked_questions")
