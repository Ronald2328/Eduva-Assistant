"""Webhook routes for receiving messages from Evolution API."""

import logfire
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
@logfire.instrument("receive_webhook_message")
async def receive_message(request: Request) -> WebhookResponse:
    """Receive and process incoming webhook messages from Evolution API."""
    try:
        body = await request.json()
        logfire.info("Webhook received", payload_size=len(str(body)))

        # Validate and parse the webhook payload structure
        with logfire.span("validate_webhook_payload"):
            webhook_payload: WebhookPayload = WebhookPayload.model_validate(obj=body)
            logfire.info("Webhook payload validated", instance=webhook_payload.instance)

        # Parse the incoming webhook message
        with logfire.span("parse_webhook_message"):
            parsed_message: ParsedMessage | None = evolution_service.parse_webhook_message(
                webhook_payload=webhook_payload
            )

        if parsed_message:
            logfire.info(
                "Message parsed successfully",
                phone_number=parsed_message.phone_number,
                message_length=len(parsed_message.text),
                message_id=parsed_message.message_id,
            )

            # Mark the incoming message as read
            with logfire.span("mark_message_as_read"):
                await evolution_service.mark_message_as_read(
                    phone_number=parsed_message.phone_number,
                    instance_name=webhook_payload.instance,
                    message_id=parsed_message.message_id,
                )

            # Show "typing" presence before processing
            with logfire.span("send_typing_presence"):
                await evolution_service.send_presence(
                    phone_number=parsed_message.phone_number,
                    instance_name=webhook_payload.instance,
                    state="composing",
                )

            # Process the message with the science bot
            with logfire.span("process_message_with_ai"):
                ai_response = await process_message(
                    user_id=parsed_message.phone_number,
                    message=parsed_message.text,
                )
                logfire.info("AI response generated", response_length=len(ai_response))

            # Send the AI-generated response back via Evolution API
            with logfire.span("send_response_message"):
                await evolution_service.send_message(
                    phone_number=parsed_message.phone_number,
                    message=ai_response,
                    instance_name=webhook_payload.instance,
                )

            logfire.info("Message processed successfully", phone_number=parsed_message.phone_number)
        else:
            logfire.warn("Message could not be parsed or was ignored")

        return WebhookResponse(status="success")

    except Exception as e:
        logfire.error("Webhook processing failed", error=str(e), exc_info=e)
        return WebhookResponse(status="error", message=str(e))
