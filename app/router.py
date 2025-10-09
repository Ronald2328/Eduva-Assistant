"""Main API router."""

from fastapi import APIRouter

from app.routes.health import router as health_router
from app.routes.webhook import router as webhook_router

router = APIRouter()

router.include_router(router=health_router, tags=["health"])
router.include_router(router=webhook_router, tags=["webhook"])
