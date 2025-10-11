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

        # Validate and parse the webhook payload structure
        webhook_payload: WebhookPayload = WebhookPayload.model_validate(obj=body)

        # Parse the incoming webhook message
        parsed_message: ParsedMessage | None = evolution_service.parse_webhook_message(
            webhook_payload=webhook_payload
        )

        if parsed_message:
            # Mark the incoming message as read
            await evolution_service.mark_message_as_read(
                phone_number=parsed_message.phone_number,
                instance_name=webhook_payload.instance,
                message_id=parsed_message.message_id,
            )

            # Show "typing" presence before processing
            await evolution_service.send_presence(
                phone_number=parsed_message.phone_number,
                instance_name=webhook_payload.instance,
                state="composing",
            )

            # Process the message with the science bot
            ai_response = await process_message(
                user_id=parsed_message.phone_number,
                message=parsed_message.text,
            )

            # Send the AI-generated response back via Evolution API
            await evolution_service.send_message(
                phone_number=parsed_message.phone_number,
                message=ai_response,
                instance_name=webhook_payload.instance,
            )

        return WebhookResponse(status="success")

    except Exception as e:
        return WebhookResponse(status="error", message=str(e))
