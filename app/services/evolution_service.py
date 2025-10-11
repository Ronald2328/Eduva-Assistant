import re

import httpx

from app.core.config import settings
from app.models.webhook import (
    MessageData,
    MessageUpdateData,
    ParsedMessage,
    PresenceResponse,
    ReadMessageResponse,
    SendMessageResponse,
    WebhookPayload,
)


class EvolutionAPIService:
    """Service for interacting with Evolution API."""

    def __init__(self) -> None:
        self.base_url: str = settings.EVOLUTION_API_URL
        self.api_key: str = settings.EVOLUTION_API_KEY

    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for WhatsApp (remove non-digits)."""
        return re.sub(pattern=r"[^\d]", repl="", string=phone_number)

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Evolution API requests."""
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def send_message(
        self, phone_number: str, message: str, instance_name: str
    ) -> SendMessageResponse:
        """Send a text message to a WhatsApp number."""
        url: str = f"{self.base_url}/message/sendText/{instance_name}"
        payload: dict[str, str] = {
            "number": self._format_phone_number(phone_number=phone_number),
            "text": message,
        }

        async with httpx.AsyncClient() as client:
            try:
                response: httpx.Response = await client.post(
                    url=url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()

                return SendMessageResponse(
                    error=False, message="Message sent successfully"
                )

            except httpx.HTTPError as e:
                return SendMessageResponse(error=True, message=str(object=e))

    async def send_presence(
        self,
        phone_number: str,
        instance_name: str,
        state: str = "composing",
        delay: int = 1200,
    ) -> PresenceResponse:
        """Send presence status (typing, recording, etc) to a WhatsApp number.

        Args:
            phone_number: Phone number to send presence to
            instance_name: Evolution API instance name
            state: Presence state - 'composing' (typing), 'recording', 'available', etc.
            delay: Duration in milliseconds (default 1200ms)

        Returns:
            PresenceResponse with success/error status
        """
        url: str = f"{self.base_url}/chat/sendPresence/{instance_name}"

        formatted_number = self._format_phone_number(phone_number=phone_number)

        payload: dict[str, str | int] = {
            "number": formatted_number,
            "presence": state,
            "delay": delay,
        }

        async with httpx.AsyncClient() as client:
            try:
                response: httpx.Response = await client.post(
                    url=url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()

                return PresenceResponse(
                    error=False, message="Presence sent successfully"
                )

            except httpx.HTTPError as e:
                return PresenceResponse(error=True, message=str(object=e))

    async def mark_message_as_read(
        self, phone_number: str, instance_name: str, message_id: str
    ) -> ReadMessageResponse:
        """Mark a message as read in WhatsApp.

        Args:
            phone_number: Phone number (remote JID)
            instance_name: Evolution API instance name
            message_id: ID of the message to mark as read

        Returns:
            ReadMessageResponse with success/error status
        """
        url: str = f"{self.base_url}/chat/markMessageAsRead/{instance_name}"

        formatted_number = self._format_phone_number(phone_number=phone_number)
        remote_jid = f"{formatted_number}@s.whatsapp.net"

        payload: dict[str, list[dict[str, str | bool]]] = {
            "readMessages": [
                {
                    "remoteJid": remote_jid,
                    "id": message_id,
                    "fromMe": False,
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            try:
                response: httpx.Response = await client.post(
                    url=url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()

                return ReadMessageResponse(
                    error=False, message="Message marked as read"
                )

            except httpx.HTTPError as e:
                return ReadMessageResponse(error=True, message=str(object=e))

    def parse_webhook_message(
        self, webhook_payload: WebhookPayload
    ) -> ParsedMessage | None:
        """Parse incoming webhook message from Evolution API."""
        try:
            if webhook_payload.event not in ["messages.upsert", "MESSAGES_UPSERT"]:
                return None

            message_data: MessageData | MessageUpdateData = (
                webhook_payload.data[0]
                if isinstance(webhook_payload.data, list)
                else webhook_payload.data
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

        except Exception:
            return None


# Global instance
evolution_service = EvolutionAPIService()
