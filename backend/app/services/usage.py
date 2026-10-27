"""Per-user daily AI limit (AI_DAILY_LIMIT_PER_USER), counted per UTC day in `ai_usage`.

Only summaries that will actually call a model count. Opening a summary someone else
already made (documents are shared) is free.
"""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import AiUsage


def today() -> date:
    return datetime.now(UTC).date()


def resets_at() -> datetime:
    """Midnight UTC, when the count starts again."""
    return datetime.combine(today() + timedelta(days=1), time(), tzinfo=UTC)


async def summaries_used(session: AsyncSession, user_id: int) -> int:
    used = await session.scalar(
        select(AiUsage.summaries).where(AiUsage.user_id == user_id, AiUsage.day == today())
    )
    return used or 0


async def take_summary(session: AsyncSession, user_id: int) -> bool:
    """Count one summary for today, unless the limit is reached. True if it was counted.

    One statement does the check and the increment, so two clicks at the same moment can't
    both slip under the limit: the UPDATE only happens while the count is below it.
    """
    limit = get_settings().ai_daily_limit_per_user
    if limit <= 0:
        return False
    statement = (
        insert(AiUsage)
        .values(user_id=user_id, day=today(), summaries=1)
        .on_conflict_do_update(
            index_elements=[AiUsage.user_id, AiUsage.day],
            set_={"summaries": AiUsage.summaries + 1},
            where=AiUsage.summaries < limit,
        )
        .returning(AiUsage.summaries)
    )
    return (await session.scalar(statement)) is not None
