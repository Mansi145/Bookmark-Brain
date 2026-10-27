"""drop the archived read state

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-23 20:10:00.000000

Reading states are only unread and read now (owner's decision). Postgres can't remove a
value from an enum type, so the type is rebuilt; archived bookmarks become read.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rebuild(values: str) -> None:
    op.execute("ALTER TYPE read_state RENAME TO read_state_old")
    op.execute(f"CREATE TYPE read_state AS ENUM ({values})")
    op.execute(
        "ALTER TABLE bookmarks ALTER COLUMN read_state TYPE read_state "
        "USING read_state::text::read_state"
    )
    op.execute("DROP TYPE read_state_old")


def upgrade() -> None:
    op.execute("UPDATE bookmarks SET read_state = 'read' WHERE read_state = 'archived'")
    _rebuild("'unread', 'read'")


def downgrade() -> None:
    _rebuild("'unread', 'read', 'archived'")
