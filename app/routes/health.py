"""Health check route."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ok",
    }
