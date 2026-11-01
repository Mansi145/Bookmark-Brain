"""Test fixtures: a real Postgres test database, wiped between tests.

Requires the docker-compose database to be running (`docker compose up -d db`).
"""

import os
import random

TEST_DB = "bookmark_brain_test"
# Must be set before the app is imported: settings and the engine read it at import.
os.environ["DATABASE_URL"] = f"postgresql+asyncpg://bb:bb@localhost:5432/{TEST_DB}"
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 32
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
os.environ["WORKER_ENABLED"] = "false"  # tests run jobs explicitly with run_once()

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.ai import llm  # noqa: E402
from app.auth.security import SESSION_COOKIE, create_session_token  # noqa: E402
from app.db import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import EMBEDDING_DIMENSIONS, User  # noqa: E402

# NullPool: open a fresh connection each time. TestClient runs the app in its own
# event loop, and pooled asyncpg connections can't be shared across loops.
engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


async def _override_session():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_session] = _override_session


@pytest.fixture(scope="session", autouse=True)
async def _create_schema():
    admin = await asyncpg.connect("postgresql://bb:bb@localhost:5432/postgres")
    if not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB):
        await admin.execute(f'CREATE DATABASE "{TEST_DB}"')
    await admin.close()

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


class FakeEmbedder:
    """Stands in for llm.get_embedder(): the same text always gives the same vector, offline.

    Records each request's texts in `calls` (pages) and `queries` (searches); set `error` to
    make the next requests fail.
    """

    model = "fake-embedding"

    def __init__(self):
        self.calls: list[list[str]] = []
        self.queries: list[str] = []
        self.error: Exception | None = None

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if self.error:
            raise self.error
        return [self._vector(text) for text in texts]

    async def aembed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        if self.error:
            raise self.error
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        numbers = random.Random(text)  # seeded by the text, so it's always the same vector
        return [numbers.uniform(-1, 1) for _ in range(EMBEDDING_DIMENSIONS)]


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch) -> FakeEmbedder:
    """Every test: fetching a page queues embeddings, and .env may hold a real Google key."""
    fake = FakeEmbedder()
    monkeypatch.setattr(llm, "get_embedder", lambda: fake)
    return fake


@pytest.fixture(autouse=True)
async def _clean_tables():
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def _make_user(sub: str, email: str) -> User:
    async with TestSession() as session:
        user = User(google_sub=sub, email=email, name=email.split("@")[0])
        session.add(user)
        await session.commit()
        return user


@pytest.fixture
async def user() -> User:
    return await _make_user("google-sub-1", "ada@example.com")


@pytest.fixture
async def other_user() -> User:
    return await _make_user("google-sub-2", "grace@example.com")


@pytest.fixture
def anon_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def client(user) -> TestClient:
    """A client signed in as `user` via the session cookie."""
    c = TestClient(app)
    c.cookies.set(SESSION_COOKIE, create_session_token(user.id))
    return c


@pytest.fixture
def client_for():
    def make(u: User) -> TestClient:
        c = TestClient(app)
        c.cookies.set(SESSION_COOKIE, create_session_token(u.id))
        return c

    return make
