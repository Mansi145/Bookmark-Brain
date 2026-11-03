"""Ask your bookmarks: the agent's answer, streamed as Server-Sent Events, and Recent questions.

POST /api/chat answers with `text/event-stream`: one event per line pair, "event: <kind>" and
"data: <json>", in this order:
- chat   {"chat_id"}: send it back with follow-ups to stay in this chat
- step   {"id", "status": "running", "tool", "args"} when the agent starts a tool, then
         {"id", "status": "done", "found", "title"?} when it's done (title: read_bookmark's page)
- token  {"text"}: the answer as it's written (only text after the last step is the answer)
- done   ChatSourcesOut: the final answer and its bookmarks, as the feed shows them
- error  {"message"}: no answer this time (every model failed); the question still counted

Only the web app may ask (the session cookie, never an extension token), and each question
counts once towards the daily AI limit, before anything runs. Only a new chat's first question
is kept, for Recent questions; follow-ups and answers live in memory (ai/agent/chat.py).
"""

import json
import logging
import secrets

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.agent import chat
from app.api.bookmarks import bookmark_out
from app.auth.deps import WebUser
from app.db import SessionDep, SessionMakerDep
from app.models import Bookmark
from app.schemas import AskedQuestionOut, ChatIn, ChatSourcesOut
from app.services import questions, usage

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def ask(body: ChatIn, user: WebUser, session: SessionDep, sessions: SessionMakerDep):
    question = body.message.strip()
    if not question:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Ask a question")
    if not await usage.take_ai_use(session, user.id):
        # The app opens the Limit reached dialog, as for Summarise.
        await usage.note_limit_reached(session, user.id)
        await session.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Daily AI limit reached")
    chat_id = body.chat_id or secrets.token_urlsafe(16)
    if body.chat_id is None:
        await questions.remember(session, user.id, question)
    await session.commit()

    return StreamingResponse(
        _events(question, user.id, chat_id, sessions),
        media_type="text/event-stream",
        # Don't let a proxy hold the events back until the end.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/recent", response_model=list[AskedQuestionOut])
async def recent_questions(user: WebUser, session: SessionDep):
    """The Ask tab's Recent questions: the first questions of the latest chats."""
    return await questions.recent(session, user.id)


async def _events(question: str, user_id: int, chat_id: str, sessions: async_sessionmaker):
    """The stream. It runs after the request's own session has closed, so it opens its own."""
    yield _event("chat", {"chat_id": chat_id})
    try:
        async for kind, data in chat.turn(
            question, user_id=user_id, chat_id=chat_id, sessions=sessions
        ):
            if kind == "answer":
                async with sessions() as session:
                    done = await _with_bookmarks(session, user_id, data)
                yield _event("done", done.model_dump(mode="json"))
            else:
                yield _event(kind, data)
    except Exception:
        log.exception("Ask failed for user %s", user_id)
        yield _event("error", {"message": "Couldn't answer right now"})


async def _with_bookmarks(session: AsyncSession, user_id: int, answer: dict) -> ChatSourcesOut:
    """The answer with its bookmarks as the feed shows them. Only the user's own bookmarks: an
    id the model made up, or someone else's, is left out."""
    ids = answer["cited"] + answer["found"]
    rows = await session.scalars(
        select(Bookmark).where(
            Bookmark.id.in_(ids), Bookmark.user_id == user_id, Bookmark.deleted_at.is_(None)
        )
    )
    mine = {bookmark.id: bookmark_out(bookmark) for bookmark in rows}
    return ChatSourcesOut(
        answer=answer["text"],
        sources=[mine[i] for i in answer["cited"] if i in mine],
        also_found=[mine[i] for i in answer["found"] if i in mine],
    )


def _event(kind: str, data: dict) -> str:
    return f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
