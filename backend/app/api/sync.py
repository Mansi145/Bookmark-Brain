from fastapi import APIRouter

from app.auth.deps import CurrentUser
from app.db import SessionDep
from app.schemas import SyncIn, SyncOut
from app.services.sync import apply_sync

router = APIRouter(prefix="/api", tags=["sync"])


@router.post("/sync", response_model=SyncOut)
async def sync_bookmarks(body: SyncIn, user: CurrentUser, session: SessionDep):
    """Called by the browser extension with a full snapshot or incremental changes."""
    return await apply_sync(session, user.id, body)
