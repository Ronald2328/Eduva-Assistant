import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EvolutionAPIService:
    def __init__(self) -> None:
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance_name = settings.EVOLUTION_INSTANCE_NAME
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    async def create_instance(self) -> dict[str, Any]:
        """Create a new WhatsApp instance"""
        url = f"{self.base_url}/instance/create"
        payload: dict[str, Any] = {
            "instanceName": self.instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                logger.info(f"Instance created: {result}")
                return result
            except httpx.HTTPError as e:
                logger.error(f"Error creating instance: {e}")
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
        """Send a text message to a WhatsApp number"""
        url = f"{self.base_url}/message/sendText/{self.instance_name}"

        # Format phone number (remove + and ensure it has country code)
        formatted_number = phone_number.replace("+", "").replace(" ", "")
        if not formatted_number.startswith("51"):  # Peru country code
            formatted_number = f"51{formatted_number}"

        payload: dict[str, Any] = {
            "number": formatted_number,
            "text": message
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

    def parse_webhook_message(self, webhook_data: dict[str, Any]) -> tuple[str, str] | None:
        """Parse incoming webhook message from Evolution API"""
        try:
            # Evolution API webhook structure
            if webhook_data.get("event") == "messages.upsert":
                data = webhook_data.get("data", [])
                if isinstance(data, list) and len(data) > 0:
                    message_data: dict[str, Any] = data[0]

                    # Get message info
                    key: dict[str, Any] = message_data.get("key", {})
                    message: dict[str, Any] = message_data.get("message", {})

                    # Extract phone number and text
                    phone_number: str = key.get("remoteJid", "").replace("@s.whatsapp.net", "")

                    # Get text message
                    text = ""
                    if "conversation" in message:
                        text = message["conversation"]
                    elif "extendedTextMessage" in message:
                        text = message["extendedTextMessage"].get("text", "")

                    if phone_number and text:
                        return phone_number, text

            return None
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing webhook message: {e}")
            return None


# Global instance
evolution_service = EvolutionAPIService()