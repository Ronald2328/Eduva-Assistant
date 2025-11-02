from typing import Literal

import logfire
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


@logfire.instrument("chat_node")
async def chat(
    state: InputState, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    # Extract context from config
    with logfire.span("extract_context"):
        context = Context.from_config(config)
        logfire.info("Context extracted", phone_number=context.phone_number)

    # Initialize OpenAI model
    with logfire.span("initialize_model"):
        model = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=SecretStr(
                secret_value=settings.OPENAI_API_KEY,
            ),
            max_completion_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
        )
        logfire.info(
            "Model initialized",
            model=settings.OPENAI_MODEL,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
        )

    # Bind tools to model
    with logfire.span("bind_tools"):
        try:
            model_with_tools = model.bind_tools(tools=TOOLS, strict=True)  # type: ignore
            logfire.info("Tools bound successfully", tool_count=len(TOOLS))
        except Exception as e:
            logfire.error(
                "Failed to bind tools to model",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=e,
            )
            raise

    # Get system prompt with phone number context
    with logfire.span("prepare_prompt"):
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
        logfire.info("Prompt prepared", message_count=len(state.messages))

    # Invoke the model
    with logfire.span("invoke_model"):
        try:
            response: BaseMessage = await (prompt | model_with_tools).ainvoke(  # type: ignore
                input={"messages": state.messages}
            )
            logfire.info(
                "Model invocation successful",
                has_tool_calls=bool(response.tool_calls),  # type: ignore
                tool_call_count=len(response.tool_calls) if response.tool_calls else 0,  # type: ignore
            )
            return {"messages": [response]}
        except Exception as e:
            logfire.error(
                "Model invocation failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=e,
            )
            raise


@logfire.instrument("should_continue")
async def should_continue(state: OverallState) -> Literal["tools"] | Literal["__end__"]:
    messages = state.messages
    last_message: BaseMessage = messages[-1]

    has_tool_calls = bool(last_message.tool_calls)  # type: ignore

    if has_tool_calls:
        tool_call_count = len(last_message.tool_calls)  # type: ignore
        logfire.info(
            "Routing to tools",
            tool_call_count=tool_call_count,
        )
        return "tools"

    logfire.info("Routing to end - no tool calls")
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
