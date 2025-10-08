import logging
from typing import Any

from fastapi import FastAPI, Request

from app.core.config import settings
from app.services.evolution_service import evolution_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Bot de WhatsApp que responde automáticamente",
    version=settings.APP_VERSION,
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": f"¡{settings.BOT_NAME} está funcionando!", "status": "active"}


@app.post("/webhook")
async def receive_message(request: Request) -> dict[str, str]:
    """Recibir mensajes de Evolution API"""
    try:
        body = await request.json()
        logger.info(f"Received webhook: {body}")

        # Parsear el mensaje usando Evolution API service
        parsed_message = evolution_service.parse_webhook_message(body)

        if parsed_message:
            phone_number, text = parsed_message
            logger.info(f"Message from {phone_number}: {text}")

            # Responder automáticamente con el mensaje configurado
            await evolution_service.send_message(phone_number, settings.BOT_RESPONSE_MESSAGE)

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/instance/create")
async def create_instance() -> dict[str, Any]:
    """Crear instancia de WhatsApp"""
    result = await evolution_service.create_instance()
    return result


@app.get("/instance/qr")
async def get_qr_code() -> dict[str, Any]:
    """Obtener código QR para conectar WhatsApp"""
    result = await evolution_service.get_qr_code()
    return result


@app.get("/instance/status")
async def get_instance_status() -> dict[str, Any]:
    """Obtener estado de la instancia"""
    result = await evolution_service.get_instance_status()
    return result


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "bot": settings.BOT_NAME}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_DEBUG,
    )
