"""Webhook data models for Evolution API."""

from pydantic import BaseModel, ConfigDict, Field


class MessageKey(BaseModel):
    """Message key information."""

    model_config = ConfigDict(extra="allow")

    remoteJid: str = Field(..., description="Remote JID (phone number)")
    fromMe: bool = Field(default=False, description="Whether message is from us")
    id: str = Field(..., description="Message ID")
    remoteJidAlt: str | None = Field(default=None, description="Remote JID alternative")
    participant: str | None = Field(default=None, description="Participant")
    addressingMode: str | None = Field(default=None, description="Addressing mode")


class DeviceListMetadata(BaseModel):
    """Device list metadata."""

    model_config = ConfigDict(extra="allow")

    senderKeyHash: dict[str, object] | str | None = Field(
        default=None, description="Sender key hash"
    )
    senderTimestamp: dict[str, object] | int | None = Field(
        default=None, description="Sender timestamp"
    )
    senderAccountType: int | str | None = Field(
        default=None, description="Sender account type"
    )
    receiverAccountType: int | str | None = Field(
        default=None, description="Receiver account type"
    )
    recipientKeyHash: dict[str, object] | str | None = Field(
        default=None, description="Recipient key hash"
    )
    recipientTimestamp: dict[str, object] | int | None = Field(
        default=None, description="Recipient timestamp"
    )
    senderKeyIndexes: list[object] | None = Field(default=None, description="Sender key indexes")
    recipientKeyIndexes: list[object] | None = Field(default=None, description="Recipient key indexes")


class MessageContextInfo(BaseModel):
    """Message context information."""

    model_config = ConfigDict(extra="allow")

    deviceListMetadata: DeviceListMetadata | None = Field(
        default=None, description="Device list metadata"
    )
    deviceListMetadataVersion: int | None = Field(
        default=None, description="Device list metadata version"
    )
    messageSecret: str | None = Field(default=None, description="Message secret")
    threadId: list[object] | None = Field(default=None, description="Thread ID")
    limitSharingV2: dict[str, object] | None = Field(
        default=None, description="Limit sharing v2"
    )


class ExtendedTextMessage(BaseModel):
    """Extended text message."""

    text: str = Field(..., description="Message text")


class MessageContent(BaseModel):
    """Message content."""

    model_config = ConfigDict(extra="allow")

    conversation: str | None = Field(
        default=None, description="Simple conversation text"
    )
    extendedTextMessage: ExtendedTextMessage | None = Field(
        default=None, description="Extended text message"
    )
    messageContextInfo: MessageContextInfo | dict[str, object] | None = Field(
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

    model_config = ConfigDict(extra="allow")

    key: MessageKey | None = Field(default=None, description="Message key")
    message: MessageContent | None = Field(default=None, description="Message content")
    messageTimestamp: int | None = Field(default=None, description="Message timestamp")
    pushName: str | None = Field(default=None, description="Contact name")
    messageType: str | None = Field(default=None, description="Message type")
    instanceId: str | None = Field(default=None, description="Instance ID")
    source: str | None = Field(default=None, description="Message source")
    contextInfo: dict[str, object] | None = Field(
        default=None, description="Context info"
    )
    status: str | None = Field(default=None, description="Message status")


class WebhookPayload(BaseModel):
    """Webhook payload from Evolution API."""

    model_config = ConfigDict(extra="allow")

    event: str = Field(..., description="Event type")
    instance: str = Field(..., description="Instance name")
    data: MessageData | MessageUpdateData | list[MessageData | MessageUpdateData] = Field(
        ..., description="Message data or update data"
    )
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
