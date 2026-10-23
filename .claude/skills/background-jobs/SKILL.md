---
name: background-jobs
description: How Bookmark Brain's Postgres-backed job queue and in-process worker work, and how to add a new kind of job (page fetching, summaries, embeddings, tags, link checks). Use when writing anything slow that must not run in a request handler, touching backend/app/worker.py, or debugging stuck/failed jobs.
---

# Background jobs

## Why a queue
Anything slow or unreliable (downloading pages, LLM calls, embeddings, link checks) runs as a row in
the `jobs` table, never inside an HTTP request. Inside a request it would make sync take minutes, hit
browser/Render time limits, and let one slow site or a rate-limited model break the whole request.
The queue lives in Postgres (no Redis/Celery), so jobs survive restarts and need no extra service.

## How it works (`backend/app/worker.py`)
- `enqueue(session, kind, payloads)` inserts rows **in the caller's transaction**: if the caller rolls
  back, the jobs never existed. The caller commits.
- The FastAPI lifespan (`app/main.py`) starts `CONCURRENCY = 4` loops with `running_workers()`, unless
  `WORKER_ENABLED=false`. Idle loops poll every `POLL_SECONDS = 2`.
- `claim_job` picks the oldest due job with `SELECT … FOR UPDATE SKIP LOCKED` and marks it `running`
  (attempts + 1, `locked_at = now()`). SKIP LOCKED means two loops or two API instances never take the
  same job, and nobody waits on a lock.
- `run_job` calls the handler in a fresh session. The handler's writes and `status = done` commit
  together, so a job is never "done" without its result being saved.
- Failure: the handler's writes roll back; the job goes back to `queued` with `run_after` 30 s, then
  2 min later (`30 * 4 ** (attempts - 1)` seconds), and becomes `failed` after `MAX_ATTEMPTS = 3`.
  `last_error` keeps the message. Unknown kinds fail immediately.
- A job left `running` for more than `STALE_AFTER = 10 min` (the API restarted mid-job) is claimed again.

Statuses: `queued → running → done`, or `→ queued` (retry) `→ … → failed`.

## Existing job kinds
| Kind | Queued by | Does |
|---|---|---|
| `fetch_page` | `services/sync.py` for each new document; migration `0004` backfill | live page (safe fetcher) → `services/extract.py` (trafilatura) → `fetched`; private address → `failed`; needs sign-in (`services/access.py`) → `failed` + `access`, never sent to archive.org; 404/410 → `dead`; anything else → `failed`. Also stores the site logo (`services/icons.py`). Never contacts archive.org |
| `find_archive` | `POST /api/bookmarks/{id}/find-archive` (the user clicked "Find archived copy" on a dead link) | latest Wayback Machine snapshot via `services/archive.py` (throttled, private-looking URLs skipped) → `archive_status` found / none / failed (archive.org busy: reported, not retried, so the user can try again) |

## Adding a job kind
1. Write the handler in `worker.py` (or a module it imports; `fetch_page` is the reference example):
   ```python
   async def fetch_page(session: AsyncSession, job: Job, http: httpx.AsyncClient) -> None:
       document = await session.get(Document, job.payload["document_id"])
       if document is None:
           return  # deleted meanwhile: nothing to do, not an error
       ...
   ```
   - The payload is small JSON with ids (`{"document_id": 7}`), never whole objects. Load fresh state.
   - **Idempotent**: a job can run twice (stale takeover, retry after a partial failure). Check
     whether the work is already done (e.g. the summary exists) and overwrite, don't append.
   - **Raise to retry** (timeouts, 5xx). For "the other side is busy, nothing is wrong" (a 429
     from a free service), `raise RetryLater(seconds)`: the job is rescheduled without using up an
     attempt, so the handler must give up on its own eventually (e.g. compare `job.created_at`).
   - Slow or rate-limited third parties get **their own job kind** (like `find_archive`), so their
     retries don't redo the earlier work. For permanent problems (404, blocked URL,
     unparseable page) record the outcome on the document and return normally, so it isn't retried.
   - If the user needs to see "it gave up", write that state on the last attempt
     (`job.attempts >= MAX_ATTEMPTS`) before raising, or mark the document `failed`.
   - Fetch user URLs only with the `http` client passed in (built by `services/fetch.make_client()`,
     which blocks private addresses). Catch `fetch.BlockedUrl` as permanent and
     `fetch.TemporaryFetchError` as retryable.
   - To start follow-up work, `await enqueue(session, "summarise", [...])` in the same session: it
     commits only if this job succeeds.
2. Register it: `HANDLERS = {"fetch_page": fetch_page, ...}`.
3. Enqueue it where the work becomes needed, e.g. in `services/sync.py` for newly inserted documents
   (`insert(...).on_conflict_do_nothing(...).returning(Document.id)` returns only new rows), or in a
   migration as a one-off backfill (`INSERT INTO jobs (kind, payload) SELECT …`).
4. LLM handlers: also follow the `llm-patterns` skill (cache per document, quota, fallbacks).

## Testing
`tests/test_worker.py` shows the pattern:
- `monkeypatch.setattr(worker, "HANDLERS", {...})` to register fake handlers.
- `await worker.run_once(TestSession, http)` runs exactly one due job and returns `True`/`False`.
  Tests use `TestSession` (NullPool) because each test has its own event loop.
- For handlers that fetch, pass `fetch.make_client(transport=httpx.MockTransport(handler))` and use
  public IP literals like `http://93.184.216.34/` as hosts (the private-address check needs no DNS).
- The worker never starts during tests (`WORKER_ENABLED=false` in `conftest.py`).

## Debugging
```bash
docker compose exec db psql -U bb bookmark_brain -c \
  "select kind, status, count(*) from jobs group by 1, 2"
docker compose exec db psql -U bb bookmark_brain -c \
  "select id, kind, attempts, run_after, last_error from jobs where status <> 'done' order by id"
# retry everything that failed
docker compose exec db psql -U bb bookmark_brain -c \
  "update jobs set status = 'queued', attempts = 0, run_after = now() where status = 'failed'"
```
Worker failures are logged as warnings (`Job <id> (<kind>) failed, attempt n: …`) in the API output.

## Production notes
- The worker runs only while the API runs: the keep-warm ping on Render keeps both alive.
- Several API instances are safe (SKIP LOCKED), but on the free tier there is one.
- `done` rows accumulate; prune them later with a periodic job if the table grows large.
