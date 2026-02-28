"""Authentication utilities for admin endpoints."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

security = HTTPBasic()


async def verify_admin(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """Verify admin credentials.

    Args:
        credentials: HTTP Basic credentials from request

    Returns:
        Admin username if credentials are valid

    Raises:
        HTTPException: If credentials are invalid
    """
    if (
        credentials.username != settings.ADMIN_USERNAME
        or credentials.password != settings.ADMIN_PASSWORD
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
