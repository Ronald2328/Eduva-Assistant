"""Main API router."""

from fastapi import APIRouter

from app.routes.documents import router as admin_documents_router
from app.routes.webhook import router as webhook_router

router = APIRouter()

router.include_router(router=webhook_router, tags=["webhook"])
router.include_router(router=admin_documents_router, tags=["admin"])
