"""Science Bot Service for processing messages with conversation history."""

import logfire
from langchain_core.messages.base import BaseMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import AsyncSessionLocal
from app.science_bot.agent.graph import get_graph
from app.science_bot.agent.schemas import InputState
from app.science_bot.core.conversation_manager import ConversationManager


@logfire.instrument("process_message")
async def process_message(
    user_id: str,
    message: str,
    phone_number: str | None = None,
    user_name: str | None = None,
    message_id: str | None = None,
) -> str:
    """Process a message using the science bot graph with conversation history.

    Args:
        user_id: The ID of the user sending the message (typically phone_number)
        message: The message content to process
        phone_number: User's phone number (if different from user_id)
        user_name: Optional user name from WhatsApp
        message_id: Optional WhatsApp message ID

    Returns:
        The AI response as a string
    """
    # Use phone_number if provided, otherwise use user_id
    phone_number = phone_number or user_id

    async_session: AsyncSession | None = None
    manager = ConversationManager()
    conversation_id = None

    try:
        logfire.info(
            "Processing message",
            user_id=user_id,
            phone_number=phone_number,
            message_length=len(message),
        )

        # Create database session
        with logfire.span("create_db_session"):
            async_session = AsyncSessionLocal()
            manager.set_session(session=async_session)

        # Initialize user and conversation
        with logfire.span("initialize_user_conversation"):
            conversation_id = await manager.initialize_user_conversation(
                phone_number=phone_number, user_name=user_name
            )

        # Add user message to conversation history
        with logfire.span("add_user_message_to_history"):
            await manager.add_user_message(
                conversation_id=conversation_id, content=message, message_id=message_id
            )

        # Get full conversation history for context
        with logfire.span("get_conversation_history"):
            conversation_history: list[BaseMessage] = (
                await manager.get_conversation_history(conversation_id=conversation_id)
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
                        "phone_number": phone_number,
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
            await manager.add_assistant_message(
                conversation_id=conversation_id, content=response_content
            )

        # Commit database transaction
        with logfire.span("commit_transaction"):
            if async_session:
                await async_session.commit()
                logfire.debug("Database transaction committed")

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

        try:
            # Try to save error response to history
            if conversation_id:
                await manager.add_assistant_message(
                    conversation_id=conversation_id, content=error_response
                )
            if async_session and conversation_id:
                await async_session.commit()
        except Exception as db_error:
            logfire.error(
                "Failed to save error response",
                error=str(db_error),
                exc_info=db_error,
            )

        return error_response

    finally:
        # Close database session
        if async_session:
            await async_session.close()
            logfire.debug("Database session closed")
