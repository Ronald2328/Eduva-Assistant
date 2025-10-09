"""Science Bot Agent module for processing messages."""

from langchain_core.messages.base import BaseMessage

from app.science_bot.agent.graph import get_graph
from app.science_bot.agent.schemas import Context, InputState
from app.science_bot.conversation_manager import conversation_manager

__all__: list[str] = ["process_message"]


async def process_message(user_id: str, message: str) -> str:
    """Process a message using the science bot graph with conversation history.

    Args:
        user_id: The ID of the user sending the message
        message: The message content to process

    Returns:
        The AI response as a string
    """
    try:
        # Add user message to conversation history
        conversation_manager.add_user_message(user_id=user_id, content=message)

        # Get full conversation history for context
        conversation_history: list[BaseMessage] = conversation_manager.get_conversation_history(user_id=user_id)

        graph = get_graph()

        # Create input state with full conversation history
        state = InputState(messages=conversation_history)

        # Invoke the graph with context
        response = await graph.ainvoke(  # type: ignore
            input=state,
            context=Context(user_id=user_id),
            config={
                "run_name": "process_webhook_message",
            },
        )

        # Extract the last message content
        last_message = response["messages"][-1]
        response_content = (
            str(object=last_message.content)
            if last_message.content
            else "No pude generar una respuesta."
        )

        # Add assistant response to conversation history
        conversation_manager.add_assistant_message(user_id, content=response_content)

        return response_content

    except Exception:
        error_response = "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta de nuevo."

        # Still add the error response to history to maintain conversation flow
        conversation_manager.add_assistant_message(user_id=user_id, content=error_response)

        return error_response
