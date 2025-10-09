import logging
import re

import httpx

from app.core.config import settings
from app.models.webhook import (
    MessageData,
    MessageUpdateData,
    ParsedMessage,
    SendMessageResponse,
    WebhookPayload,
)

logger: logging.Logger = logging.getLogger(name=__name__)


class EvolutionAPIService:
    """Service for interacting with Evolution API."""

    def __init__(self) -> None:
        self.base_url: str = settings.EVOLUTION_API_URL
        self.api_key: str = settings.EVOLUTION_API_KEY
        self.instance_name: str = settings.EVOLUTION_INSTANCE_NAME
        self.headers: dict[str, str] = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for WhatsApp (remove non-digits)."""
        return re.sub(pattern=r"[^\d]", repl="", string=phone_number)

    async def send_message(
        self, phone_number: str, message: str
    ) -> SendMessageResponse:
        """Send a text message to a WhatsApp number."""
        url: str = f"{self.base_url}/message/sendText/{self.instance_name}"
        payload: dict[str, str] = {
            "number": self._format_phone_number(phone_number=phone_number),
            "text": message,
        }

        async with httpx.AsyncClient() as client:
            try:
                response: httpx.Response = await client.post(
                    url=url, json=payload, headers=self.headers
                )
                response.raise_for_status()
                logger.info(msg=f"Message sent to {phone_number}")

                return SendMessageResponse(
                    error=False, message="Message sent successfully"
                )

            except httpx.HTTPError as e:
                logger.error(msg=f"Error sending message: {e}")
                return SendMessageResponse(error=True, message=str(object=e))

    def parse_webhook_message(
        self, webhook_data: dict[str, object]
    ) -> ParsedMessage | None:
        """Parse incoming webhook message from Evolution API."""
        try:
            webhook: WebhookPayload = WebhookPayload.model_validate(obj=webhook_data)

            if webhook.event not in ["messages.upsert", "MESSAGES_UPSERT"]:
                return None

            message_data: MessageData | MessageUpdateData = (
                webhook.data[0] if isinstance(webhook.data, list) else webhook.data
            )

            if (
                isinstance(message_data, MessageUpdateData)
                or not message_data.key
                or not message_data.message
                or message_data.key.fromMe
            ):
                return None

            text: str = (
                message_data.message.conversation
                or (
                    message_data.message.extendedTextMessage
                    and message_data.message.extendedTextMessage.text
                )
                or ""
            )

            if not text:
                return None

            return ParsedMessage(
                phone_number=message_data.key.remoteJid.replace("@s.whatsapp.net", ""),
                text=text,
                from_me=message_data.key.fromMe,
                message_id=message_data.key.id,
                push_name=message_data.pushName,
                timestamp=message_data.messageTimestamp,
            )

        except Exception as e:
            logger.error(msg=f"Error parsing webhook message: {e}")
            return None


# Global instance
evolution_service = EvolutionAPIService()
