"""FastAPI application entry point.

Only an operational health endpoint belongs in the Milestone 1 scaffold.
Domain routes are added in later, explicitly approved milestones.
"""

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)


@app.get("/health", tags=["operations"])
async def health_check() -> dict[str, str]:
    """Report that the API process is ready to accept requests."""

    return {"status": "ok"}
