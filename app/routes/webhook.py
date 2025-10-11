"""Webhook routes for receiving messages from Evolution API."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.models.webhook import ParsedMessage, WebhookPayload
from app.science_bot.core.service import process_message
from app.services.evolution_service import evolution_service

router = APIRouter()


class WebhookResponse(BaseModel):
    status: str
    message: str | None = None


@router.post(path="/webhook")
async def receive_message(request: Request) -> WebhookResponse:
    """Receive and process incoming webhook messages from Evolution API."""
    try:
        body = await request.json()
        print(f"\n{'=' * 60}")
        print(f"📨 WEBHOOK RECIBIDO - Evento: {body.get('event')}")
        print(f"{'=' * 60}")

        # Validate and parse the webhook payload structure
        webhook_payload: WebhookPayload = WebhookPayload.model_validate(obj=body)

        # Parse the incoming webhook message
        parsed_message: ParsedMessage | None = evolution_service.parse_webhook_message(
            webhook_payload=webhook_payload
        )

        if parsed_message:
            print(
                f"✅ Mensaje parseado: '{parsed_message.text}' de {parsed_message.phone_number}"
            )

            # Mark the incoming message as read
            print("👀 Marcando mensaje como VISTO...")
            read_response = await evolution_service.mark_message_as_read(
                phone_number=parsed_message.phone_number,
                instance_name=webhook_payload.instance,
                message_id=parsed_message.message_id,
            )
            print(
                f"   ✓ Visto: {'✅ OK' if not read_response.error else f'❌ Error: {read_response.message}'}"
            )

            # Show "typing..." indicator
            print("✍️  Enviando indicador 'escribiendo...'")
            typing_response = await evolution_service.send_presence(
                phone_number=parsed_message.phone_number,
                instance_name=webhook_payload.instance,
                state="composing",
            )
            print(
                f"   ✓ Typing: {'✅ OK' if not typing_response.error else f'❌ Error: {typing_response.message}'}"
            )

            # Process the message with the science bot
            print("🤖 Procesando mensaje con el bot...")
            ai_response = await process_message(
                user_id=parsed_message.phone_number,
                message=parsed_message.text,
            )
            print(f"   ✓ Respuesta generada: '{ai_response[:50]}...'")

            # Send the AI-generated response back via Evolution API
            # (El indicador "escribiendo" se detiene automáticamente al enviar)
            print("💬 Enviando respuesta...")
            send_response = await evolution_service.send_message(
                phone_number=parsed_message.phone_number,
                message=ai_response,
                instance_name=webhook_payload.instance,
            )
            print(
                f"   ✓ Envío: {'✅ OK' if not send_response.error else f'❌ Error: {send_response.message}'}"
            )
            print(f"{'=' * 60}\n")
        else:
            print("⏭️  Mensaje ignorado (puede ser propio o sin texto)")

        return WebhookResponse(status="success")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        return WebhookResponse(status="error", message=str(e))
