"""Version 1 API route registration."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(catalog_router)
