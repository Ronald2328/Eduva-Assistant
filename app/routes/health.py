"""Health check route."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/ready")
async def readiness_check() -> dict[str, str | bool]:
    """Readiness check endpoint - verifica que el servicio esté listo."""
    return {
        "status": "ready",
    }


@router.get("/")
async def root() -> dict[str, str | bool]:
    """Root endpoint."""
    return {
        "message": f"¡{settings.BOT_NAME} está funcionando!",
        "status": "active",
        "ready": True,
    }
