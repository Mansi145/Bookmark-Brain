from fastapi import APIRouter
from sqlalchemy import text

from app.db import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check. Kept free of DB/LLM calls: the keep-warm ping hits it every 10 min."""
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(session: SessionDep) -> dict[str, str]:
    """Readiness check: confirms Postgres is reachable and pgvector is installed."""
    version = await session.scalar(
        text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    )
    return {"status": "ok", "pgvector": version or "missing"}
