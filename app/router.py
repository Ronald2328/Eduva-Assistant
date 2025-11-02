"""Main API router."""

from fastapi import APIRouter

from app.routes.webhook import router as webhook_router

router = APIRouter()

router.include_router(router=webhook_router, tags=["webhook"])
