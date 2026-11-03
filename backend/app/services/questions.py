"""The Ask tab's Recent questions: the first question of each of the user's latest chats.

Only first questions are kept (owner): picking one asks it again for a fresh answer, so nothing
else of a chat needs keeping. Asking the same question again moves it to the top instead of
listing it twice, and only the latest RECENT_QUESTIONS are kept at all.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AskedQuestion

RECENT_QUESTIONS = 3


async def remember(session: AsyncSession, user_id: int, question: str) -> None:
    """Add a chat's first question at the top. The caller commits."""
    mine = AskedQuestion.user_id == user_id
    same = func.lower(AskedQuestion.question) == question.lower()
    await session.execute(delete(AskedQuestion).where(mine, same))
    session.add(AskedQuestion(user_id=user_id, question=question))
    await session.flush()
    keep = select(AskedQuestion.id).where(mine).order_by(AskedQuestion.id.desc())
    await session.execute(
        delete(AskedQuestion).where(mine, AskedQuestion.id.not_in(keep.limit(RECENT_QUESTIONS)))
    )


async def recent(session: AsyncSession, user_id: int) -> list[AskedQuestion]:
    """The latest first questions, newest first."""
    rows = await session.scalars(
        select(AskedQuestion)
        .where(AskedQuestion.user_id == user_id)
        .order_by(AskedQuestion.id.desc())
        .limit(RECENT_QUESTIONS)
    )
    return list(rows)
