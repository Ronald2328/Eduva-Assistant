from typing import Literal

from langchain_core.messages.base import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph  # type: ignore
from langgraph.prebuilt import ToolNode
from pydantic import SecretStr

from app.core.config import settings
from app.science_bot.agent.prompts.system_prompt import get_system_prompt
from app.science_bot.agent.schemas import (
    Context,
    Graph,
    InputState,
    OutputState,
    OverallState,
)
from app.science_bot.agent.tools.search_documents.tool import TOOLS

graph_builder: StateGraph[OverallState, Context, InputState, OutputState] = StateGraph(
    state_schema=OverallState,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=Context,
)


async def chat(
    state: InputState, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    # Extract context from config
    context = Context.from_config(config)

    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=SecretStr(
            secret_value=settings.OPENAI_API_KEY,
        ),
        max_completion_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE,
    )
    model_with_tools = model.bind_tools(tools=TOOLS, strict=True)  # type: ignore

    # Get system prompt with phone number context
    system_prompt_text = get_system_prompt(phone_number=context.phone_number)

    prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(  # type: ignore
        messages=[
            (
                "system",
                system_prompt_text,
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    response: BaseMessage = await (prompt | model_with_tools).ainvoke(  # type: ignore
        input={"messages": state.messages}
    )

    return {"messages": [response]}


async def should_continue(state: OverallState) -> Literal["tools"] | Literal["__end__"]:
    messages = state.messages
    last_message: BaseMessage = messages[-1]
    if last_message.tool_calls:  # type: ignore
        return "tools"
    return "__end__"


graph_builder.add_node(node="chat", action=chat)  # type: ignore
graph_builder.add_node(node="tools", action=ToolNode(tools=TOOLS))  # type: ignore

graph_builder.set_entry_point("chat")
graph_builder.add_conditional_edges(
    source="chat", path=should_continue, path_map=["tools", "__end__"]
)
graph_builder.add_edge(start_key="tools", end_key="chat")


def get_graph() -> Graph:
    return graph_builder.compile()  # type: ignore
