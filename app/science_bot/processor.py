"""Science Bot Agent module for processing messages."""

from langchain_core.messages import HumanMessage

from app.science_bot.agent.graph import get_graph
from app.science_bot.agent.schemas import Context, InputState

__all__: list[str] = ["process_message"]


async def process_message(user_id: str, message: str) -> str:
    """Process a message using the science bot graph.

    Args:
        user_id: The ID of the user sending the message
        message: The message content to process

    Returns:
        The AI response as a string
    """
    graph = get_graph()

    # Create input state with the user message
    state = InputState(messages=[HumanMessage(content=message)])

    # Invoke the graph with context
    response = await graph.ainvoke( # type: ignore
        input=state,
        context=Context(user_id=user_id),
        config={
            "run_name": "process_webhook_message",
        },
    )

    # Extract the last message content
    last_message = response["messages"][-1]

    # Return the content as string
    return str(last_message.content) if last_message.content else "No pude generar una respuesta."
