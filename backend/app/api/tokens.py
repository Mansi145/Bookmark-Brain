"""Personal access tokens, created in the web app and pasted into the extension."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.auth.deps import CurrentUser
from app.auth.security import generate_pat, hash_pat
from app.db import SessionDep
from app.models import ApiToken
from app.schemas import TokenCreatedOut, TokenCreateIn, TokenOut

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.get("", response_model=list[TokenOut])
async def list_tokens(user: CurrentUser, session: SessionDep):
    result = await session.scalars(
        select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at.desc())
    )
    return result.all()


@router.post("", response_model=TokenCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_token(body: TokenCreateIn, user: CurrentUser, session: SessionDep):
    token = generate_pat()
    api_token = ApiToken(
        user_id=user.id, name=body.name, token_hash=hash_pat(token), prefix=token[:12]
    )
    session.add(api_token)
    await session.commit()
    out = TokenOut.model_validate(api_token)
    return TokenCreatedOut(**out.model_dump(), token=token)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(token_id: int, user: CurrentUser, session: SessionDep):
    api_token = await session.get(ApiToken, token_id)
    # Same 404 for "doesn't exist" and "belongs to someone else": don't leak which.
    if api_token is None or api_token.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token not found")
    await session.delete(api_token)
    await session.commit()
