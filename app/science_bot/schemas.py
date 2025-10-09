from pydantic import BaseModel, Field


class ScienceBotAssistantContext(BaseModel):
    user_id: str = Field(description="The user id for the science bot")


class ChatScienceBotAssistantRequest(BaseModel):
    thread_id: str = Field(description="The thread id of the chat")
    message: str = Field(description="The message to send to the science bot")
    images_urls: list[str] = Field(
        default_factory=list,
        description="The urls of the images to send to the science bot",
    )
    context: ScienceBotAssistantContext = Field(
        description="The context of the chat"
    )


class ChatScienceBotAssistantResponse(BaseModel):
    message: str = Field(description="The response message from the science bot")
