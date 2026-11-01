"""github sign-in: users.github_id, google_sub optional

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-01 18:00:00.000000

An account can now sign in with Google, GitHub or both, so google_sub may be empty, and a check
makes sure every account has at least one of the two. The downgrade deletes accounts that only
have GitHub, since they can't exist without it (local use only: never downgrade Neon).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("github_id", sa.BigInteger(), nullable=True))
    op.create_unique_constraint("users_github_id_key", "users", ["github_id"])
    op.alter_column("users", "google_sub", existing_type=sa.String(255), nullable=True)
    op.create_check_constraint(
        "ck_users_has_provider", "users", "google_sub IS NOT NULL OR github_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_has_provider", "users", type_="check")
    op.execute("DELETE FROM users WHERE google_sub IS NULL")
    op.alter_column("users", "google_sub", existing_type=sa.String(255), nullable=False)
    op.drop_constraint("users_github_id_key", "users", type_="unique")
    op.drop_column("users", "github_id")
