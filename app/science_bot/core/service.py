"""Science Bot Service for processing messages with conversation history."""

from langchain_core.messages.base import BaseMessage

from app.science_bot.agent.graph import get_graph
from app.science_bot.agent.schemas import InputState
from app.science_bot.core.conversation_manager import conversation_manager


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
        conversation_history: list[BaseMessage] = (
            conversation_manager.get_conversation_history(user_id=user_id)
        )

        # Get graph instance
        graph = get_graph()

        # Create input state with full conversation history
        state = InputState(messages=conversation_history)

        # Invoke the graph with context
        response = await graph.ainvoke(  # type: ignore
            input=state,
            config={
                "run_name": "process_webhook_message",
                "configurable": {
                    "user_id": user_id,
                    "phone_number": user_id,
                },
            },
        )

        # Extract the last message content
        last_message = response["messages"][-1]
        response_content = (
            str(object=last_message.content)
            if last_message.content
            else "I'm not sure how to respond to that."
        )

        # Add assistant response to conversation history
        conversation_manager.add_assistant_message(
            user_id, content=response_content
        )

        return response_content

    except Exception:
        error_response = "Sorry, something went wrong. Please try again later."

        # Still add the error response to history to maintain conversation flow
        conversation_manager.add_assistant_message(
            user_id=user_id, content=error_response
        )

        return error_response
