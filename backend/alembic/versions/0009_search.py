"""search: embeddings and keyword search on documents

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-30 18:00:00.000000

- embedding (768 numbers from gemini-embedding-2), the model that made it and when: meaning
  search. An HNSW index finds the nearest vectors without comparing every row.
- tsv, a generated column Postgres keeps up to date: keyword search, with a GIN index.
Every page fetched before this is waiting to be embedded (embedded_at null), so one
embed_pages job is queued to work through them.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A copy of models.DOCUMENT_TSV as it was when this ran (migrations must not change later).
TSV = """
setweight(to_tsvector('english', coalesce(title, '')), 'A')
|| setweight(to_tsvector('english', coalesce(description, '') || ' ' || coalesce(summary, '')
    || ' ' || coalesce(key_points::text, '')), 'B')
|| setweight(to_tsvector('english', left(coalesce(content_text, ''), 100000)), 'C')
"""


def upgrade() -> None:
    op.add_column("documents", sa.Column("embedding", Vector(768), nullable=True))
    op.add_column("documents", sa.Column("embedding_model", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "documents", sa.Column("tsv", TSVECTOR(), sa.Computed(TSV, persisted=True), nullable=True)
    )
    op.create_index("ix_documents_tsv", "documents", ["tsv"], postgresql_using="gin")
    op.execute(
        "CREATE INDEX ix_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        """
        INSERT INTO jobs (kind, payload)
        SELECT 'embed_pages', '{}'::jsonb
        WHERE EXISTS (SELECT 1 FROM documents WHERE status <> 'pending')
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'embed_pages'")
    op.drop_index("ix_documents_embedding", table_name="documents")
    op.drop_index("ix_documents_tsv", table_name="documents")
    op.drop_column("documents", "tsv")
    op.drop_column("documents", "embedded_at")
    op.drop_column("documents", "embedding_model")
    op.drop_column("documents", "embedding")
