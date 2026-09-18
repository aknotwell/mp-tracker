"""FastAPI application entry point.

Only an operational health endpoint belongs in the Milestone 1 scaffold.
Domain routes are added in later, explicitly approved milestones.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings.frontend_origin).rstrip("/")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
app.include_router(api_v1_router, prefix=settings.api_prefix)


@app.get("/health", tags=["operations"])
async def health_check() -> dict[str, str]:
    """Report that the API process is ready to accept requests."""

    return {"status": "ok"}
