"""Science Bot Service for processing messages with conversation history."""

import logfire
from langchain_core.messages.base import BaseMessage

from app.science_bot.agent.graph import get_graph
from app.science_bot.agent.schemas import InputState
from app.science_bot.core.conversation_manager import conversation_manager


@logfire.instrument("process_message")
async def process_message(user_id: str, message: str) -> str:
    """Process a message using the science bot graph with conversation history.

    Args:
        user_id: The ID of the user sending the message
        message: The message content to process

    Returns:
        The AI response as a string
    """
    try:
        logfire.info(
            "Processing message",
            user_id=user_id,
            message_length=len(message),
        )

        # Add user message to conversation history
        with logfire.span("add_user_message_to_history"):
            conversation_manager.add_user_message(user_id=user_id, content=message)

        # Get full conversation history for context
        with logfire.span("get_conversation_history"):
            conversation_history: list[BaseMessage] = (
                conversation_manager.get_conversation_history(user_id=user_id)
            )
            logfire.info(
                "Conversation history retrieved",
                history_length=len(conversation_history),
            )

        # Get graph instance
        with logfire.span("get_graph_instance"):
            graph = get_graph()

        # Create input state with full conversation history
        with logfire.span("create_input_state"):
            state = InputState(messages=conversation_history)

        # Invoke the graph with context
        with logfire.span("invoke_langgraph"):
            logfire.info("Invoking LangGraph agent", user_id=user_id)
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
        with logfire.span("extract_response"):
            last_message = response["messages"][-1]
            response_content = (
                str(object=last_message.content)
                if last_message.content
                else "I'm not sure how to respond to that."
            )
            logfire.info(
                "Response generated",
                response_length=len(response_content),
                user_id=user_id,
            )

        # Add assistant response to conversation history
        with logfire.span("add_assistant_message_to_history"):
            conversation_manager.add_assistant_message(
                user_id, content=response_content
            )

        logfire.info("Message processed successfully", user_id=user_id)
        return response_content

    except Exception as e:
        logfire.error(
            "Error processing message",
            user_id=user_id,
            error=str(e),
            exc_info=e,
        )
        error_response = "Sorry, something went wrong. Please try again later."

        # Still add the error response to history to maintain conversation flow
        conversation_manager.add_assistant_message(
            user_id=user_id, content=error_response
        )

        return error_response
