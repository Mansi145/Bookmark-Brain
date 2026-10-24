from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.auth.deps import CurrentUser
from app.auth.security import SESSION_COOKIE, create_session_token, verify_google_credential
from app.config import get_settings
from app.db import SessionDep
from app.models import User
from app.schemas import GoogleLoginIn, UserOut

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/google", response_model=UserOut)
async def login_with_google(body: GoogleLoginIn, response: Response, session: SessionDep):
    """Exchange a Google ID token for our own session cookie."""
    try:
        identity = await verify_google_credential(body.credential)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, f"Invalid Google credential: {exc}"
        ) from exc

    user = await session.scalar(select(User).where(User.google_sub == identity.sub))
    if user is None:
        user = User(google_sub=identity.sub, email=identity.email)
        session.add(user)
    # Refresh profile details on every login.
    user.email, user.name, user.avatar_url = identity.email, identity.name, identity.picture
    await session.commit()

    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id),
        max_age=settings.session_days * 24 * 3600,
        httponly=True,  # page JavaScript can't read it, so XSS can't steal it
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    settings = get_settings()
    response.delete_cookie(
        SESSION_COOKIE,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
