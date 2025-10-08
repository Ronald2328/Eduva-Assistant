"""Webhook data models for Evolution API."""

from pydantic import BaseModel, Field


class MessageKey(BaseModel):
    """Message key information."""

    remoteJid: str = Field(..., description="Remote JID (phone number)")
    fromMe: bool = Field(default=False, description="Whether message is from us")
    id: str = Field(..., description="Message ID")


class ExtendedTextMessage(BaseModel):
    """Extended text message."""

    text: str = Field(..., description="Message text")


class MessageContent(BaseModel):
    """Message content."""

    conversation: str | None = Field(
        default=None, description="Simple conversation text"
    )
    extendedTextMessage: ExtendedTextMessage | None = Field(
        default=None, description="Extended text message"
    )


class MessageData(BaseModel):
    """Message data from webhook."""

    key: MessageKey = Field(..., description="Message key")
    message: MessageContent = Field(..., description="Message content")
    messageTimestamp: int | None = Field(default=None, description="Message timestamp")
    pushName: str | None = Field(default=None, description="Contact name")


class WebhookPayload(BaseModel):
    """Webhook payload from Evolution API."""

    event: str = Field(..., description="Event type")
    instance: str = Field(..., description="Instance name")
    data: MessageData | list[MessageData] = Field(..., description="Message data")


class ParsedMessage(BaseModel):
    """Parsed message from webhook."""

    phone_number: str = Field(..., description="Phone number without @s.whatsapp.net")
    text: str = Field(..., description="Message text")
    from_me: bool = Field(default=False, description="Whether message is from us")
    message_id: str = Field(..., description="Message ID")
    push_name: str | None = Field(default=None, description="Contact name")
    timestamp: int | None = Field(default=None, description="Message timestamp")


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    number: str = Field(..., description="Phone number to send message to")
    text: str = Field(..., description="Message text to send")


class ConnectionState(BaseModel):
    """Instance connection state."""

    instance: str = Field(..., description="Instance name")
    state: str = Field(..., description="Connection state")


class WebhookConfig(BaseModel):
    """Webhook configuration for Evolution API."""

    url: str = Field(..., description="Webhook URL")
    webhook_by_events: bool = Field(
        default=False, description="Whether to send webhooks by event type"
    )
    webhook_base64: bool = Field(
        default=False, description="Whether to send media as base64"
    )
    events: list[str] = Field(
        default_factory=lambda: [
            "MESSAGES_UPSERT",
            "MESSAGES_UPDATE",
            "SEND_MESSAGE",
        ],
        description="Events to listen to",
    )
