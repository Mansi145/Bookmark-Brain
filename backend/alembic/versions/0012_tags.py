"""tags: the user's tags, which bookmarks have them, and the ones the user removed

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-03 12:00:00.000000

Every account made before this gets the starter tags, as new accounts do (services/tags.py). The
list is copied here rather than imported, so this migration keeps doing the same thing if the
starter tags change later. Everything is deleted with the account (ON DELETE CASCADE).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STARTER_TAGS = (
    "Programming",
    "AI",
    "Design",
    "Data",
    "Business",
    "Science",
    "Health",
    "Cooking",
    "Travel",
    "News",
)


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_user_id"), "tags", ["user_id"], unique=False)
    # One tag per name and user, whatever the case.
    op.create_index("uq_tags_user_name", "tags", ["user_id", sa.text("lower(name)")], unique=True)

    op.create_table(
        "bookmark_tags",
        sa.Column("bookmark_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.Enum("user", "ai", name="tag_source"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bookmark_id"], ["bookmarks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("bookmark_id", "tag_id"),
    )
    op.create_index(op.f("ix_bookmark_tags_tag_id"), "bookmark_tags", ["tag_id"], unique=False)

    op.create_table(
        "removed_tags",
        sa.Column("bookmark_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "removed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bookmark_id"], ["bookmarks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("bookmark_id", "tag_id"),
    )

    names = ", ".join(f"('{name}')" for name in STARTER_TAGS)
    op.execute(
        f"INSERT INTO tags (user_id, name) SELECT users.id, starter.name "
        f"FROM users CROSS JOIN (VALUES {names}) AS starter(name)"
    )


def downgrade() -> None:
    op.drop_table("removed_tags")
    op.drop_index(op.f("ix_bookmark_tags_tag_id"), table_name="bookmark_tags")
    op.drop_table("bookmark_tags")
    op.execute("DROP TYPE tag_source")
    op.drop_index("uq_tags_user_name", table_name="tags")
    op.drop_index(op.f("ix_tags_user_id"), table_name="tags")
    op.drop_table("tags")
