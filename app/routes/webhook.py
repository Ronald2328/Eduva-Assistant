"""Webhook routes for receiving messages from Evolution API."""

from fastapi import APIRouter, Request

from app.models.webhook import ParsedMessage
from app.science_bot import process_message
from app.services.evolution_service import evolution_service

router = APIRouter()


@router.post(path="/webhook")
async def receive_message(request: Request) -> dict[str, str]:
    """Recibir mensajes de Evolution API y responder con IA."""
    try:
        body = await request.json()

        # Parsear el mensaje usando Evolution API service
        parsed_message: ParsedMessage | None = evolution_service.parse_webhook_message(
            webhook_data=body
        )

        if parsed_message:
            # Generar respuesta usando el agente de IA con historial
            ai_response = await process_message(
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
        return {"status": "error", "message": str(object=e)}
