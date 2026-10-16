from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.config import get_settings

app = FastAPI(title="Bookmark Brain API")

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
