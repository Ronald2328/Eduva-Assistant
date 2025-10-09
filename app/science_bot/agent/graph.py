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

graph_builder = StateGraph(
    state_schema=OverallState,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=Context,
)


async def chat(state: InputState):
    model = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=SecretStr(
            settings.OPENAI_API_KEY,
        ),
    )
    model_with_tools = model.bind_tools(TOOLS, strict=True)  # type: ignore

    prompt = ChatPromptTemplate.from_messages(  # type: ignore
        [
            (
                "system",
                "You are a helpful assistant that can provide current time information for different countries. When users ask about time in specific countries, use the get_time_by_country tool to provide accurate information.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    response = await (prompt | model_with_tools).ainvoke(input={"messages": state.messages})  # type: ignore

    return {"messages": [response]}


async def should_continue(state: OverallState):
    messages = state.messages
    last_message = messages[-1]
    if last_message.tool_calls:  # type: ignore
        return "tools"
    return "__end__"


graph_builder.add_node("chat", chat)  # type: ignore
graph_builder.add_node("tools", ToolNode(TOOLS))  # type: ignore

graph_builder.set_entry_point("chat")
graph_builder.add_conditional_edges("chat", should_continue, ["tools", "__end__"])
graph_builder.add_edge("tools", "chat")


def get_graph() -> Graph:
    return graph_builder.compile()  # type: ignore
