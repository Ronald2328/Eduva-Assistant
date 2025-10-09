from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.base import BaseMessage

from app.science_bot.agent.schemas import Context, Graph, InputState, OutputState
from app.science_bot.schemas import (
    ChatScienceBotAssistantRequest,
    ChatScienceBotAssistantResponse,
)


class ScienceBotService:
    def __init__(
        self,
        graph: Graph,
    ) -> None:
        self.graph = graph

    async def chat(
        self, request: ChatScienceBotAssistantRequest
    ) -> ChatScienceBotAssistantResponse:
        state = InputState(messages=[HumanMessage(content=request.message)])
        response = await self.graph.ainvoke(  # type: ignore
            input=state,
            context=Context(user_id=request.context.user_id),
            config={
                "run_name": "chat_science_bot",
            },
        )
        output_state = OutputState(messages=response["messages"])
        last_message: BaseMessage = output_state.messages[-1]

        if not isinstance(last_message, AIMessage):
            raise ValueError("Last message is not an AI message")

        return ChatScienceBotAssistantResponse.model_validate(
            obj={
                "message": last_message.content,  # type: ignore
            }
        )
