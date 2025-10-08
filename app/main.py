import logging

from fastapi import FastAPI

from app.core.config import settings
from app.routes import health, webhook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger(name=__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Bot de WhatsApp que responde automáticamente",
    version=settings.APP_VERSION,
)

# Include routers
app.include_router(router=health.router, tags=["health"])
app.include_router(router=webhook.router, tags=["webhook"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app="app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_DEBUG,
    )
