from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.messages.base import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph  # type: ignore
from pydantic import SecretStr

from app.core.config import settings
from app.science_bot.agent.prompts.agro_system_prompt import get_system_prompt
from app.science_bot.agent.schemas import (
    Graph,
    InputState,
    OutputState,
    OverallState,
)

graph_builder = StateGraph(
    state_schema=OverallState,
    input_schema=InputState,
    output_schema=OutputState,
)


def get_peru_time() -> str:
    """Get current time in Peru timezone (America/Lima).

    Returns:
        Formatted current time string in Peru timezone
    """
    try:
        peru_tz = ZoneInfo(key="America/Lima")
        current_time: datetime = datetime.now(tz=peru_tz)
        return current_time.strftime(format="%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        # Fallback to UTC if timezone fails
        current_time = datetime.now(tz=ZoneInfo(key="UTC"))
        return current_time.strftime(format="%Y-%m-%d %H:%M:%S UTC")


async def chat(state: InputState) -> dict[str, list[BaseMessage]]:
    # Initialize OpenAI model
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=SecretStr(
            secret_value=settings.OPENAI_API_KEY,
        ),
        max_completion_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE,
    )

    # Get system prompt with Peru time
    current_time = get_peru_time()
    system_prompt_text = get_system_prompt(current_time=current_time)
    prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(  # type: ignore
        messages=[
            (
                "system",
                system_prompt_text,
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    # Invoke the model
    response: BaseMessage = await (prompt | model).ainvoke(  # type: ignore
        input={"messages": state.messages}
    )
    return {"messages": [response]}


graph_builder.add_node(node="chat", action=chat)  # type: ignore
graph_builder.set_entry_point("chat")
graph_builder.set_finish_point("chat")


def get_graph() -> Graph:
    return graph_builder.compile()  # type: ignore
