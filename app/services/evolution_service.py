import logging
from typing import Any

import httpx

from app.core.config import settings
from app.models.webhook import (
    ConnectionState,
    InstanceResponse,
    ParsedMessage,
    SendMessageRequest,
    SendMessageResponse,
    WebhookConfig,
    WebhookPayload,
)

logger = logging.getLogger(__name__)


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

    async def create_instance(self) -> dict[str, Any]:
        """Create a new WhatsApp instance."""
        url = f"{self.base_url}/instance/create"
        payload: dict[str, Any] = {
            "instanceName": self.instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                logger.info(f"Instance created: {result}")

                # Configure webhook after creating instance
                if settings.WEBHOOK_ENABLED:
                    await self.set_webhook()

                return result
            except httpx.HTTPError as e:
                logger.error(f"Error creating instance: {e}")
                return {"error": str(e)}

    async def set_webhook(self) -> dict[str, Any]:
        """Configure webhook for the instance."""
        url = f"{self.base_url}/webhook/set/{self.instance_name}"

        webhook_config = WebhookConfig(
            url=settings.WEBHOOK_URL,
            webhook_by_events=False,
            webhook_base64=False,
            events=settings.WEBHOOK_EVENTS,
        )

        payload: dict[str, Any] = {
            "url": webhook_config.url,
            "webhook_by_events": webhook_config.webhook_by_events,
            "webhook_base64": webhook_config.webhook_base64,
            "events": webhook_config.events,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                logger.info(f"Webhook configured: {result}")
                return result
            except httpx.HTTPError as e:
                logger.error(f"Error setting webhook: {e}")
                return {"error": str(e)}

    async def get_webhook(self) -> dict[str, Any]:
        """Get current webhook configuration."""
        url = f"{self.base_url}/webhook/find/{self.instance_name}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
            except httpx.HTTPError as e:
                logger.error(f"Error getting webhook: {e}")
                return {"error": str(e)}

    async def get_qr_code(self) -> dict[str, Any]:
        """Get QR code for instance connection"""
        url = f"{self.base_url}/instance/connect/{self.instance_name}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
            except httpx.HTTPError as e:
                logger.error(f"Error getting QR code: {e}")
                return {"error": str(e)}

    async def send_message(self, phone_number: str, message: str) -> dict[str, Any]:
        """Send a text message to a WhatsApp number."""
        url = f"{self.base_url}/message/sendText/{self.instance_name}"

        # Format phone number (remove + and ensure it has country code)
        formatted_number = phone_number.replace("+", "").replace(" ", "").replace("-", "")
        if not formatted_number.startswith("51"):  # Peru country code
            formatted_number = f"51{formatted_number}"

        request_data = SendMessageRequest(number=formatted_number, text=message)

        payload: dict[str, Any] = {
            "number": request_data.number,
            "text": request_data.text,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                logger.info(f"Message sent to {phone_number}: {result}")
                return result
            except httpx.HTTPError as e:
                logger.error(f"Error sending message: {e}")
                return {"error": str(e)}

    async def get_instance_status(self) -> dict[str, Any]:
        """Get instance connection status"""
        url = f"{self.base_url}/instance/connectionState/{self.instance_name}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
            except httpx.HTTPError as e:
                logger.error(f"Error getting instance status: {e}")
                return {"error": str(e)}

    def parse_webhook_message(self, webhook_data: dict[str, Any]) -> ParsedMessage | None:
        """Parse incoming webhook message from Evolution API."""
        try:
            # Validate and parse webhook payload
            webhook = WebhookPayload.model_validate(webhook_data)

            # Only process messages.upsert events
            if webhook.event != "messages.upsert":
                logger.debug(f"Ignoring event: {webhook.event}")
                return None

            # Check if there's message data
            if not webhook.data:
                logger.warning("No message data in webhook")
                return None

            message_data = webhook.data[0]

            # Don't respond to our own messages
            if message_data.key.fromMe:
                logger.debug("Ignoring message from self")
                return None

            # Extract phone number
            phone_number = message_data.key.remoteJid.replace("@s.whatsapp.net", "")

            # Get text message
            text = ""
            if message_data.message.conversation:
                text = message_data.message.conversation
            elif message_data.message.extendedTextMessage:
                text = message_data.message.extendedTextMessage.text

            if not text:
                logger.debug("No text content in message")
                return None

            # Create parsed message
            parsed = ParsedMessage(
                phone_number=phone_number,
                text=text,
                from_me=message_data.key.fromMe,
                message_id=message_data.key.id,
                push_name=message_data.pushName,
                timestamp=message_data.messageTimestamp,
            )

            return parsed

        except Exception as e:
            logger.error(f"Error parsing webhook message: {e}", exc_info=True)
            return None


# Global instance
evolution_service = EvolutionAPIService()