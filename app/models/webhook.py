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


class MessageUpdateData(BaseModel):
    """Message update data from webhook (for status updates)."""

    messageId: str = Field(..., description="Message ID")
    keyId: str | None = Field(default=None, description="Key ID")
    remoteJid: str | None = Field(default=None, description="Remote JID")
    fromMe: bool | None = Field(default=None, description="Whether message is from us")
    participant: str | None = Field(default=None, description="Participant")
    status: str | None = Field(
        default=None, description="Message status (READ, DELIVERED, etc)"
    )
    instanceId: str | None = Field(default=None, description="Instance ID")


class MessageData(BaseModel):
    """Message data from webhook."""

    key: MessageKey | None = Field(default=None, description="Message key")
    message: MessageContent | None = Field(default=None, description="Message content")
    messageTimestamp: int | None = Field(default=None, description="Message timestamp")
    pushName: str | None = Field(default=None, description="Contact name")


class WebhookPayload(BaseModel):
    """Webhook payload from Evolution API."""

    event: str = Field(..., description="Event type")
    instance: str = Field(..., description="Instance name")
    data: (
        MessageData | MessageUpdateData | list[MessageData] | list[MessageUpdateData]
    ) = Field(..., description="Message data or update data")


class ParsedMessage(BaseModel):
    """Parsed message from webhook."""

    phone_number: str = Field(..., description="Phone number without @s.whatsapp.net")
    text: str = Field(..., description="Message text")
    from_me: bool = Field(default=False, description="Whether message is from us")
    message_id: str = Field(..., description="Message ID")
    push_name: str | None = Field(default=None, description="Contact name")
    timestamp: int | None = Field(default=None, description="Message timestamp")


class SendMessageResponseData(BaseModel):
    """Response data from sending a message."""

    key: MessageKey = Field(..., description="Message key")
    message: MessageContent = Field(..., description="Message content")
    messageTimestamp: int = Field(..., description="Message timestamp")
    status: str | None = Field(default=None, description="Message status")


class SendMessageResponse(BaseModel):
    """Response from sending a message."""

    error: bool = Field(default=False, description="Whether there was an error")
    message: str | None = Field(default=None, description="Error message if any")
    data: SendMessageResponseData | None = Field(
        default=None, description="Response data"
    )


class ConnectionState(BaseModel):
    """Instance connection state."""

    instance: str = Field(..., description="Instance name")
    state: str = Field(..., description="Connection state")
