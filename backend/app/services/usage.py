"""Per-user daily AI limit (AI_DAILY_LIMIT_PER_USER), counted per UTC day in `ai_usage`.

Only summaries that will actually call a model count. Opening a summary someone else
already made (documents are shared) is free.

The same row records when the user was first refused that day and when they told the
maintainer about it (the Limit reached dialog), so the owner can see who runs out and when.
"""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, func, select, update
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


async def limit_reached(session: AsyncSession, user_id: int) -> bool:
    return await summaries_used(session, user_id) >= get_settings().ai_daily_limit_per_user


async def note_limit_reached(session: AsyncSession, user_id: int) -> None:
    """Remember when a Summarise was first refused today (the time goes in the email)."""
    statement = (
        insert(AiUsage)
        .values(user_id=user_id, day=today(), limit_reached_at=func.now())
        .on_conflict_do_update(
            index_elements=[AiUsage.user_id, AiUsage.day],
            set_={"limit_reached_at": func.now()},
            where=AiUsage.limit_reached_at.is_(None),
        )
    )
    await session.execute(statement)


async def claim_notice(session: AsyncSession, user_id: int) -> datetime | None:
    """Mark today's maintainer email as sent, if it isn't yet. Returns when the user hit the
    limit (now, if that wasn't recorded), or None if they already told the maintainer today.

    Like take_summary, one statement checks and sets, so a double click sends one email.
    """
    statement = (
        insert(AiUsage)
        .values(user_id=user_id, day=today(), maintainer_notified_at=func.now())
        .on_conflict_do_update(
            index_elements=[AiUsage.user_id, AiUsage.day],
            set_={"maintainer_notified_at": func.now()},
            where=AiUsage.maintainer_notified_at.is_(None),
        )
        .returning(func.coalesce(AiUsage.limit_reached_at, func.now()))
    )
    return await session.scalar(statement)


async def set_used_up(session: AsyncSession, user_id: int) -> None:
    """Dev tools: count today as fully used, as if the user had made every summary."""
    limit = get_settings().ai_daily_limit_per_user
    statement = (
        insert(AiUsage)
        .values(user_id=user_id, day=today(), summaries=limit)
        .on_conflict_do_update(
            index_elements=[AiUsage.user_id, AiUsage.day], set_={"summaries": limit}
        )
    )
    await session.execute(statement)


async def forget_today(session: AsyncSession, user_id: int) -> None:
    """Dev tools: wipe today's count, refusal time and maintainer email, like a new day."""
    await session.execute(delete(AiUsage).where(AiUsage.user_id == user_id, AiUsage.day == today()))


async def release_notice(session: AsyncSession, user_id: int) -> None:
    """The email didn't go: let the user try again."""
    await session.execute(
        update(AiUsage)
        .where(AiUsage.user_id == user_id, AiUsage.day == today())
        .values(maintainer_notified_at=None)
    )
