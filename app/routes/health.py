"""Health check route."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ReadyResponse(BaseModel):
    status: str
    ready: bool = True


@router.get("/ready")
async def readiness_check() -> ReadyResponse:
    """Readiness check endpoint - verifica que el servicio esté listo."""
    return ReadyResponse(status="Service is ready", ready=True)
