---
name: db-migrations
description: Alembic migration workflow for Bookmark Brain, including pgvector and tsvector caveats. Use when changing SQLAlchemy models, adding tables/columns/indexes, or running migrations locally or on Neon.
---

# Database migrations

## Workflow
```bash
cd backend
# 1. edit app/models.py
uv run alembic revision --autogenerate -m "short description"
# 2. READ the generated file in alembic/versions/ and fix it (autogenerate misses things, see below)
uv run alembic upgrade head
uv run alembic downgrade -1 && uv run alembic upgrade head   # check downgrade works
```
Never edit a migration that has already run on Neon; write a new one.

## Things autogenerate gets wrong
- **pgvector**: the first migration must run `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`. Import `pgvector.sqlalchemy.Vector` in the migration file.
- **HNSW index** (vector search): write it by hand:
  `op.execute("CREATE INDEX ix_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops)")`
- **tsvector**: use a generated column, written by hand:
  `tsv tsvector GENERATED ALWAYS AS (setweight(to_tsvector('english', coalesce(title,'')),'A') || setweight(to_tsvector('english', coalesce(summary,'')),'B') || setweight(to_tsvector('english', coalesce(content_text,'')),'C')) STORED`
  plus `CREATE INDEX … USING gin (tsv)`.
- Enum changes (status / read_state) are not detected; add `ALTER TYPE … ADD VALUE` manually.

## Conventions
- Timestamps are `timestamptz`, default `now()`.
- Soft-delete bookmarks with `deleted_at` (the extension may resend removals).
- Unique constraints: `documents.normalized_url`, `(bookmarks.user_id, bookmarks.document_id)`.
- Embedding dimension must match the configured embedding model; store `embedding_model` alongside it.

## Neon
Run against prod with `DATABASE_URL=<neon url> uv run alembic upgrade head` (use the **direct** connection string, not the pooled one, for migrations).
