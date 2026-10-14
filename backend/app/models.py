"""ORM models. Tables are added phase by phase (users/bookmarks arrive in Phase 1).

Import every model here so Alembic autogenerate can see them.
"""

from app.db import Base  # noqa: F401
