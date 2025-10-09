"""Conversation history manager for Science Bot."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


class ConversationManager:
    """Manages conversation history for users."""

    def __init__(self) -> None:
        """Initialize the conversation manager."""
        self.conversations: dict[str, list[BaseMessage]] = {}

        # System message for the science bot
        self.system_message = SystemMessage(
            content="Eres ScienceBot, un asistente virtual inteligente especializado en ciencia. "
            "Tu objetivo es ayudar a los usuarios de manera amigable y profesional. "
            "Responde de forma clara, concisa y útil, especialmente en temas científicos."
        )

    def get_conversation_history(self, user_id: str) -> list[BaseMessage]:
        """Get or create conversation history for a user.

        Args:
            user_id: The user identifier (phone number)

        Returns:
            List of conversation messages
        """
        if user_id not in self.conversations:
            self.conversations[user_id] = [self.system_message]

        return self.conversations[user_id]

    def add_message(self, user_id: str, message: BaseMessage) -> None:
        """Add a message to the conversation history.

        Args:
            user_id: The user identifier
            message: The message to add
        """
        history: list[BaseMessage] = self.get_conversation_history(user_id=user_id)
        history.append(message)

        # Limit history to last 20 messages (10 user + 10 assistant)
        user_messages: list[HumanMessage] = [msg for msg in history if isinstance(msg, HumanMessage)]
        assistant_messages: list[AIMessage] = [msg for msg in history if isinstance(msg, AIMessage)]

        # Keep last 10 of each type
        if len(user_messages) > 10:
            excess_user = len(user_messages) - 10
            for _ in range(excess_user):
                for i, msg in enumerate(history):
                    if isinstance(msg, HumanMessage):
                        history.pop(i)
                        break

        if len(assistant_messages) > 10:
            excess_assistant = len(assistant_messages) - 10
            for _ in range(excess_assistant):
                for i, msg in enumerate(history):
                    if isinstance(msg, AIMessage):
                        history.pop(i)
                        break

        # Update the stored conversation
        self.conversations[user_id] = history

    def add_user_message(self, user_id: str, content: str) -> None:
        """Add a user message to the conversation.

        Args:
            user_id: The user identifier
            content: The message content
        """
        message = HumanMessage(content=content)
        self.add_message(user_id, message)

    def add_assistant_message(self, user_id: str, content: str) -> None:
        """Add an assistant message to the conversation.

        Args:
            user_id: The user identifier
            content: The message content
        """
        message = AIMessage(content=content)
        self.add_message(user_id, message)


# Global conversation manager instance
conversation_manager = ConversationManager()
