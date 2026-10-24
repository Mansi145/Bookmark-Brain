from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, bookmarks, health, sync, tokens
from app.config import get_settings
from app.worker import running_workers


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Runs once at startup/shutdown. The job worker lives inside the API process, so
    # there's no separate worker service to host (Render's free tier has none).
    if get_settings().worker_enabled:
        async with running_workers():
            yield
    else:
        yield


app = FastAPI(title="Bookmark Brain API", lifespan=lifespan)

# The React app runs on a different origin (localhost:5173, later vercel.app),
# so the browser needs CORS headers before it lets the frontend call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tokens.router)
app.include_router(sync.router)
app.include_router(bookmarks.router)
