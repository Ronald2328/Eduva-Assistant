"""Webhook routes for receiving messages from Evolution API."""

import logging

from fastapi import APIRouter, Request

from app.core.config import settings
from app.services.evolution_service import evolution_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook")
async def receive_message(request: Request) -> dict[str, str]:
    """Recibir mensajes de Evolution API y responder automáticamente."""
    try:
        body = await request.json()
        logger.info(f"Received webhook: {body}")

        # Parsear el mensaje usando Evolution API service
        parsed_message = evolution_service.parse_webhook_message(body)

        if parsed_message:
            logger.info(
                f"Message from {parsed_message.phone_number} "
                f"({parsed_message.push_name}): {parsed_message.text}"
            )

            # Responder automáticamente con el mensaje configurado
            await evolution_service.send_message(
                parsed_message.phone_number, settings.BOT_RESPONSE_MESSAGE
            )

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
