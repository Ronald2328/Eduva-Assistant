"""Conversation history manager for Science Bot."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import logfire
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database.repository import ConversationRepository

CONVERSATION_TIMEOUT_HOURS = 1


class ConversationManager:
    """Manages conversation history for users with database persistence."""

    def __init__(self) -> None:
        """Initialize the conversation manager."""
        self.session: AsyncSession | None = None
        self.repository: ConversationRepository | None = None

    def set_session(self, session: AsyncSession) -> None:
        """Set database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.repository = ConversationRepository(session=session)

    async def initialize_user_conversation(
        self, phone_number: str, user_name: str | None = None
    ) -> UUID:
        """Initialize user and conversation for new interaction.

        Args:
            phone_number: User's phone number
            user_name: Optional user name

        Returns:
            Active conversation ID for this request
        """
        if not self.repository:
            raise RuntimeError("Repository not initialized. Call set_session first.")

        try:
            # Get or create user
            user = await self.repository.get_or_create_user(
                phone_number=phone_number, name=user_name
            )

            # Get active conversation or create new one
            conversation = await self.repository.get_active_conversation(
                user_id=user.id
            )

            if conversation:
                # Check if the conversation has expired (no messages in last hour)
                last_message_time = await self.repository.get_last_message_time(
                    conversation_id=conversation.id
                )
                timeout = timedelta(hours=CONVERSATION_TIMEOUT_HOURS)
                if last_message_time and datetime.now(UTC) - last_message_time > timeout:
                    await self.repository.close_conversation(conversation.id)
                    logfire.info(
                        "Conversation expired, creating new one",
                        phone_number=phone_number,
                        last_message_time=last_message_time.isoformat(),
                    )
                    conversation = await self.repository.create_conversation(
                        user_id=user.id
                    )

            if not conversation:
                conversation = await self.repository.create_conversation(
                    user_id=user.id
                )

            logfire.info(
                "User conversation initialized",
                phone_number=phone_number,
                user_id=str(user.id),
                conversation_id=str(conversation.id),
            )
            return conversation.id

        except Exception as e:
            logfire.error(
                "Error initializing user conversation",
                phone_number=phone_number,
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_conversation_history(self, conversation_id: UUID) -> list[BaseMessage]:
        """Get recent conversation history from database.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of conversation messages (last N)
        """
        if not self.repository:
            raise RuntimeError("Conversation not initialized.")

        try:
            # Get recent messages from database
            messages_from_db = await self.repository.get_recent_messages(
                conversation_id=conversation_id,
                limit=settings.CONVERSATION_CONTEXT_WINDOW,
            )

            # Convert DB messages to LangChain messages
            messages: list[BaseMessage] = []
            for msg in messages_from_db:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))

            logfire.debug(
                "Conversation history retrieved",
                conversation_id=str(conversation_id),
                message_count=len(messages),
            )
            return messages

        except Exception as e:
            logfire.error(
                "Error retrieving conversation history",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def add_user_message(
        self, conversation_id: UUID, content: str, message_id: str | None = None
    ) -> None:
        """Add a user message to the conversation.

        Args:
            conversation_id: Conversation ID
            content: The message content
            message_id: Optional WhatsApp message ID
        """
        if not self.repository:
            raise RuntimeError("Conversation not initialized.")

        try:
            await self.repository.add_message(
                conversation_id=conversation_id,
                role="user",
                content=content,
                message_id=message_id,
            )
            logfire.debug(
                "User message added",
                conversation_id=str(conversation_id),
                content_length=len(content),
            )

        except Exception as e:
            logfire.error(
                "Error adding user message",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def add_assistant_message(self, conversation_id: UUID, content: str) -> None:
        """Add an assistant message to the conversation.

        Args:
            conversation_id: Conversation ID
            content: The message content
        """
        if not self.repository:
            raise RuntimeError("Conversation not initialized.")

        try:
            await self.repository.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
            )
            logfire.debug(
                "Assistant message added",
                conversation_id=str(conversation_id),
                content_length=len(content),
            )

        except Exception as e:
            logfire.error(
                "Error adding assistant message",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise
