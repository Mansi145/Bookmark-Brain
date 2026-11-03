"""Database engine and session.

One async engine per process (it holds the connection pool). Each request gets
its own short-lived session via the `get_session` dependency.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """All ORM models inherit from this; Alembic reads Base.metadata."""


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


# Use as a route parameter type: `async def route(session: SessionDep): ...`
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """For work that outlives the request's session, like a streamed Ask answer: it opens
    sessions as it needs them. Tests swap in their own."""
    return SessionLocal


SessionMakerDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_sessionmaker)]
