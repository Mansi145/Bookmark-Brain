"""Today's AI usage for the signed-in user."""

from fastapi import APIRouter

from app.auth.deps import CurrentUser
from app.config import get_settings
from app.db import SessionDep
from app.schemas import UsageOut
from app.services import usage

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("", response_model=UsageOut)
async def get_usage(user: CurrentUser, session: SessionDep):
    return UsageOut(
        summaries_used=await usage.summaries_used(session, user.id),
        summaries_limit=get_settings().ai_daily_limit_per_user,
        resets_at=usage.resets_at(),
    )
