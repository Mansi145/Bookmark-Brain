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
uv run alembic check                                         # models and migrations agree
uv run pytest -q                                             # tests build the schema from the models
```
Use `--rev-id` with the next number after the newest file in `alembic/versions/` (`0009` after
`0008_limit_notices.py`) so files stay ordered: `0001_…`, `0002_…`.
Never edit a migration that has already run on Neon; write a new one.
Changing a migration that has only run locally: first `alembic downgrade -1` **with the old file in
place** (its `downgrade()` knows what to undo), then edit/replace the file and `upgrade head`.
Editing first leaves the local DB with columns the new file doesn't know about.

## Things autogenerate gets wrong
- **pgvector**: the first migration must run `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`. Import `pgvector.sqlalchemy.Vector` in the migration file.
- **HNSW index** (vector search): write it by hand:
  `op.execute("CREATE INDEX ix_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops)")`
- **tsvector**: use a generated column, written by hand:
  `tsv tsvector GENERATED ALWAYS AS (setweight(to_tsvector('english', coalesce(title,'')),'A') || setweight(to_tsvector('english', coalesce(summary,'')),'B') || setweight(to_tsvector('english', coalesce(content_text,'')),'C')) STORED`
  plus `CREATE INDEX … USING gin (tsv)`.
- Enum changes (status / read_state) are not detected; add `ALTER TYPE … ADD VALUE` manually.
- **Downgrades leave enum types behind**: dropping a table doesn't drop its Postgres enum, so add
  `op.execute("DROP TYPE <name>")` after `drop_table` (e.g. `job_status` in `0003`), or the next
  upgrade fails with "type already exists".
- **Python-side `default=` isn't a database default.** If rows may be inserted with plain SQL (data
  backfills in migrations, `psql`), use `server_default` in the model *and* the migration
  (e.g. `jobs.status`, `jobs.attempts`, `jobs.payload`).
- Data backfills go in the migration with `op.execute("INSERT … SELECT …")` after the schema change.
- Autogenerate output uses old typing (`Union`, `Sequence` from `typing`); rewrite it in the house
  style (`from collections.abc import Sequence`, `str | None`), then `uv run ruff format`.

## Conventions
- Timestamps are `timestamptz`, default `now()`.
- Every user-owned table has `user_id` with `ON DELETE CASCADE`; queries always filter by it.
  **Delete account** (`DELETE /api/account`) relies on this: it deletes the user row and the
  database removes the rest. A new user-owned table without the cascade would block deleting
  accounts. If it holds the user's own data, add it to Download my data (`app/api/account.py`) too.
- Soft-delete bookmarks with `deleted_at` (the extension may resend removals).
- Unique constraints: `documents.normalized_url`, `(bookmarks.user_id, bookmarks.document_id)`.
- Embedding dimension must match the configured embedding model; store `embedding_model` alongside it.

## Neon
Run against prod with `DATABASE_URL=<neon url> uv run alembic upgrade head` (use the **direct** connection string, not the pooled one, for migrations).
