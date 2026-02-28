"""Conversation history manager for Science Bot."""

from uuid import UUID

import logfire
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database.repository import ConversationRepository


class ConversationManager:
    """Manages conversation history for users with database persistence."""

    def __init__(self) -> None:
        """Initialize the conversation manager."""
        self.session: AsyncSession | None = None
        self.repository: ConversationRepository | None = None
        self.current_user_id: UUID | None = None
        self.current_conversation_id: UUID | None = None

    def set_session(self, session: AsyncSession) -> None:
        """Set database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.repository = ConversationRepository(session=session)

    async def initialize_user_conversation(
        self, phone_number: str, user_name: str | None = None
    ) -> None:
        """Initialize user and conversation for new interaction.

        Args:
            phone_number: User's phone number
            user_name: Optional user name
        """
        if not self.repository:
            raise RuntimeError("Repository not initialized. Call set_session first.")

        try:
            # Get or create user
            user = await self.repository.get_or_create_user(
                phone_number=phone_number, name=user_name
            )
            self.current_user_id = user.id

            # Get active conversation or create new one
            conversation = await self.repository.get_active_conversation(
                user_id=user.id
            )

            if not conversation:
                conversation = await self.repository.create_conversation(
                    user_id=user.id
                )

            self.current_conversation_id = conversation.id
            logfire.info(
                "User conversation initialized",
                phone_number=phone_number,
                user_id=str(user.id),
                conversation_id=str(conversation.id),
            )

        except Exception as e:
            logfire.error(
                "Error initializing user conversation",
                phone_number=phone_number,
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_conversation_history(self, user_id: str) -> list[BaseMessage]:
        """Get recent conversation history from database.

        Args:
            user_id: The user identifier (phone number)

        Returns:
            List of conversation messages (last N)
        """
        if not self.repository or not self.current_conversation_id:
            raise RuntimeError("Conversation not initialized.")

        try:
            # Get recent messages from database
            messages_from_db = await self.repository.get_recent_messages(
                conversation_id=self.current_conversation_id,
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
                conversation_id=str(self.current_conversation_id),
                message_count=len(messages),
            )
            return messages

        except Exception as e:
            logfire.error(
                "Error retrieving conversation history",
                conversation_id=str(self.current_conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def add_user_message(self, user_id: str, content: str, message_id: str | None = None) -> None:
        """Add a user message to the conversation.

        Args:
            user_id: The user identifier
            content: The message content
            message_id: Optional WhatsApp message ID
        """
        if not self.repository or not self.current_conversation_id:
            raise RuntimeError("Conversation not initialized.")

        try:
            await self.repository.add_message(
                conversation_id=self.current_conversation_id,
                role="user",
                content=content,
                message_id=message_id,
            )
            logfire.debug(
                "User message added",
                conversation_id=str(self.current_conversation_id),
                content_length=len(content),
            )

        except Exception as e:
            logfire.error(
                "Error adding user message",
                conversation_id=str(self.current_conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise

    async def add_assistant_message(self, user_id: str, content: str) -> None:
        """Add an assistant message to the conversation.

        Args:
            user_id: The user identifier
            content: The message content
        """
        if not self.repository or not self.current_conversation_id:
            raise RuntimeError("Conversation not initialized.")

        try:
            await self.repository.add_message(
                conversation_id=self.current_conversation_id,
                role="assistant",
                content=content,
            )
            logfire.debug(
                "Assistant message added",
                conversation_id=str(self.current_conversation_id),
                content_length=len(content),
            )

        except Exception as e:
            logfire.error(
                "Error adding assistant message",
                conversation_id=str(self.current_conversation_id),
                error=str(e),
                exc_info=e,
            )
            raise


# Global conversation manager instance
conversation_manager = ConversationManager()
