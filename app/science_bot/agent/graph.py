from typing import Literal

from langchain_core.messages.base import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph  # type: ignore
from langgraph.prebuilt import ToolNode
from pydantic import SecretStr

from app.core.config import settings
from app.science_bot.agent.schemas import (
    Context,
    Graph,
    InputState,
    OutputState,
    OverallState,
)
from app.science_bot.agent.tools import TOOLS

graph_builder: StateGraph[OverallState, Context, InputState, OutputState] = StateGraph(
    state_schema=OverallState,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=Context,
)


async def chat(state: InputState) -> dict[str, list[BaseMessage]]:
    model = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=SecretStr(
            secret_value=settings.OPENAI_API_KEY,
        ),
    )
    model_with_tools = model.bind_tools(tools=TOOLS, strict=True)  # type: ignore

    prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(  # type: ignore
        messages=[
            (
                "system",
                "You are a helpful assistant that can provide current time information for different countries. When users ask about time in specific countries, use the get_time_by_country tool to provide accurate information.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    response: BaseMessage = await (prompt | model_with_tools).ainvoke(input={"messages": state.messages})  # type: ignore

    return {"messages": [response]}


async def should_continue(state: OverallState) -> Literal['tools'] | Literal['__end__']:
    messages = state.messages
    last_message: BaseMessage = messages[-1]
    if last_message.tool_calls:  # type: ignore
        return "tools"
    return "__end__"


graph_builder.add_node(node="chat", action=chat)  # type: ignore
graph_builder.add_node(node="tools", action=ToolNode(tools=TOOLS))  # type: ignore

graph_builder.set_entry_point("chat")
graph_builder.add_conditional_edges(source="chat", path=should_continue, path_map=["tools", "__end__"])
graph_builder.add_edge(start_key="tools", end_key="chat")


def get_graph() -> Graph:
    return graph_builder.compile()  # type: ignore
