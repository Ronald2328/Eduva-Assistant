"""Webhook routes for receiving messages from Evolution API."""

import logging

from fastapi import APIRouter, Request

from app.agent import agent
from app.models.webhook import ParsedMessage
from app.services.evolution_service import evolution_service

router = APIRouter()
logger: logging.Logger = logging.getLogger(name=__name__)


@router.post(path="/webhook")
async def receive_message(request: Request) -> dict[str, str]:
    """Recibir mensajes de Evolution API y responder con IA."""
    try:
        body = await request.json()
        logger.info(msg=f"Received webhook: {body}")

        # Parsear el mensaje usando Evolution API service
        parsed_message: ParsedMessage | None = evolution_service.parse_webhook_message(
            webhook_data=body
        )

        if parsed_message:
            logger.info(
                msg=f"Message from {parsed_message.phone_number} "
                f"({parsed_message.push_name}): {parsed_message.text}"
            )

            # Generar respuesta usando el agente de IA
            ai_response = await agent.process_message(
                user_id=parsed_message.phone_number,
                message=parsed_message.text,
            )

            # Enviar la respuesta generada por IA
            await evolution_service.send_message(
                phone_number=parsed_message.phone_number,
                message=ai_response,
            )

        return {"status": "success"}

    except Exception as e:
        logger.error(msg=f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(object=e)}
