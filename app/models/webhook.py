"""Webhook data models for Evolution API."""

from pydantic import BaseModel, Field


class TimestampInfo(BaseModel):
    """Timestamp information."""

    low: int = Field(..., description="Low timestamp value")
    high: int = Field(..., description="High timestamp value")
    unsigned: bool = Field(..., description="Unsigned flag")


class KeyHash(BaseModel):
    """Key hash as dictionary with numeric keys."""

    class Config:
        extra = "allow"


class MessageKey(BaseModel):
    """Message key information."""

    remoteJid: str = Field(..., description="Remote JID (phone number)")
    remoteJidAlt: str | None = Field(default=None, description="Alternative remote JID")
    fromMe: bool = Field(default=False, description="Whether message is from us")
    id: str = Field(..., description="Message ID")
    participant: str | None = Field(default=None, description="Participant JID")
    addressingMode: str | None = Field(default=None, description="Addressing mode")


class DeviceListMetadata(BaseModel):
    """Device list metadata."""

    senderKeyIndexes: list[int] | None = Field(default=None, description="Sender key indexes")
    recipientKeyIndexes: list[int] | None = Field(default=None, description="Recipient key indexes")
    senderKeyHash: KeyHash | None = Field(default=None, description="Sender key hash")
    senderTimestamp: TimestampInfo | None = Field(default=None, description="Sender timestamp")
    senderAccountType: int | None = Field(
        default=None, description="Sender account type"
    )
    receiverAccountType: int | None = Field(
        default=None, description="Receiver account type"
    )
    recipientKeyHash: KeyHash | None = Field(default=None, description="Recipient key hash")
    recipientTimestamp: TimestampInfo | None = Field(
        default=None, description="Recipient timestamp"
    )


class MessageSecret(BaseModel):
    """Message secret as dictionary with numeric keys."""

    class Config:
        extra = "allow"


class LimitSharingV2(BaseModel):
    """Limit sharing V2 information."""

    trigger: int | None = Field(default=None, description="Trigger value")
    initiatedByMe: bool | None = Field(default=None, description="Initiated by me flag")


class MessageContextInfo(BaseModel):
    """Message context information."""

    threadId: list[str] | None = Field(default=None, description="Thread ID")
    deviceListMetadata: DeviceListMetadata | None = Field(
        default=None, description="Device list metadata"
    )
    deviceListMetadataVersion: int | None = Field(
        default=None, description="Device list metadata version"
    )
    messageSecret: MessageSecret | None = Field(default=None, description="Message secret")
    limitSharingV2: LimitSharingV2 | None = Field(default=None, description="Limit sharing V2")


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
    messageContextInfo: MessageContextInfo | None = Field(
        default=None, description="Message context information"
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
    pushName: str | None = Field(default=None, description="Contact name")
    status: str | None = Field(default=None, description="Message status")
    message: MessageContent | None = Field(default=None, description="Message content")
    messageType: str | None = Field(default=None, description="Message type")
    messageTimestamp: int | None = Field(default=None, description="Message timestamp")
    instanceId: str | None = Field(default=None, description="Instance ID")
    source: str | None = Field(default=None, description="Message source")
    contextInfo: dict[str, object] | None = Field(
        default=None, description="Context info"
    )


class WebhookPayload(BaseModel):
    """Webhook payload from Evolution API."""

    event: str = Field(..., description="Event type")
    instance: str = Field(..., description="Instance name")
    data: (
        MessageData | MessageUpdateData | list[MessageData] | list[MessageUpdateData]
    ) = Field(..., description="Message data or update data")
    destination: str | None = Field(default=None, description="Webhook destination URL")
    date_time: str | None = Field(default=None, description="Event date and time")
    sender: str | None = Field(default=None, description="Sender JID")
    server_url: str | None = Field(default=None, description="Evolution API server URL")
    apikey: str | None = Field(default=None, description="API key")


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


class PresenceResponse(BaseModel):
    """Response from sending presence (typing, recording, etc)."""

    error: bool = Field(default=False, description="Whether there was an error")
    message: str | None = Field(default=None, description="Error message if any")


class ReadMessageResponse(BaseModel):
    """Response from marking message as read."""

    error: bool = Field(default=False, description="Whether there was an error")
    message: str | None = Field(default=None, description="Error message if any")


class ConnectionState(BaseModel):
    """Instance connection state."""

    instance: str = Field(..., description="Instance name")
    state: str = Field(..., description="Connection state")
