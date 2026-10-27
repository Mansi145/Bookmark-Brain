"""Today's AI usage for the signed-in user, and "Notify the maintainer" when it runs out."""

from datetime import UTC

from fastapi import APIRouter, HTTPException, status

from app.auth.deps import CurrentUser
from app.config import get_settings
from app.db import SessionDep
from app.schemas import UsageOut
from app.services import mail, usage

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("", response_model=UsageOut)
async def get_usage(user: CurrentUser, session: SessionDep):
    return UsageOut(
        summaries_used=await usage.summaries_used(session, user.id),
        summaries_limit=get_settings().ai_daily_limit_per_user,
        resets_at=usage.resets_at(),
    )


@router.post("/notify-maintainer", status_code=status.HTTP_204_NO_CONTENT)
async def notify_maintainer(user: CurrentUser, session: SessionDep):
    """The Limit reached dialog's button: email the owner who ran out of AI today, and when.

    Sent here, not as a background job: it's one quick call, and the dialog should only say
    "Thanks, the maintainer knows" once the email has actually gone.

    Only for users who really are at the limit, and at most one email per user per day (the
    limit is per day, so that's "every time they hit it"). Pressing it again the same day
    answers 204 without sending, which keeps the free 100-a-day email quota safe.
    """
    if not mail.configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Email isn't set up")
    if not await usage.limit_reached(session, user.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "The daily limit isn't reached")

    reached_at = await usage.claim_notice(session, user.id)
    await session.commit()
    if reached_at is None:
        return  # already told today

    limit = get_settings().ai_daily_limit_per_user
    text = "\n".join(
        [
            f"{user.name or user.email} ({user.email}) reached today's AI limit in Bookmark Brain.",
            "",
            f"Hit the limit: {reached_at.astimezone(UTC):%Y-%m-%d %H:%M} UTC",
            f"Daily limit per user: {limit} summaries",
            "It resets at midnight UTC.",
            "",
            "Sent from the Limit reached dialog. Reply to this email to answer them.",
        ]
    )
    try:
        await mail.send_to_maintainer(
            subject="Bookmark Brain: a user reached the daily AI limit",
            text=text,
            reply_to=user.email,
        )
    except mail.EmailNotSent:
        await usage.release_notice(session, user.id)
        await session.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Couldn't send the email") from None
