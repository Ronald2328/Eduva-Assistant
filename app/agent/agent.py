"""AI Agent for processing messages and generating responses."""

import json
import logging
from collections.abc import Callable
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class Agent:
    """AI Agent that uses OpenAI to generate responses with tool support."""

    def __init__(self) -> None:
        """Initialize the agent with OpenAI client and tools."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        self.tools: dict[str, dict[str, Any]] = {}
        self.tool_functions: dict[str, Callable[..., Any]] = {}
        self.conversation_history: dict[str, list[dict[str, Any]]] = {}

        # System prompt for the bot
        self.system_prompt = f"""Eres {settings.BOT_NAME}, un asistente virtual inteligente.
Tu objetivo es ayudar a los usuarios de manera amigable y profesional.
Responde de forma clara, concisa y útil."""

    def register_tool(
        self, name: str, schema: dict[str, Any], function: Callable[..., Any]
    ) -> None:
        """Register a new tool for the agent to use.

        Args:
            name: Tool name
            schema: OpenAI function schema
            function: Function to execute
        """
        self.tools[name] = schema
        self.tool_functions[name] = function
        logger.info(f"Tool registered: {name}")

    def get_tools_schema(self) -> list[dict[str, Any]]:
        """Get the OpenAI function schema for all registered tools.

        Returns:
            List of tool schemas in OpenAI format
        """
        return list(self.tools.values())

    def _get_conversation_history(self, user_id: str) -> list[dict[str, Any]]:
        """Get or create conversation history for a user.

        Args:
            user_id: The user identifier

        Returns:
            List of conversation messages
        """
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = [
                {"role": "system", "content": self.system_prompt}
            ]
        return self.conversation_history[user_id]

    def _add_to_history(
        self, user_id: str, role: str, content: str, name: str | None = None
    ) -> None:
        """Add a message to the conversation history.

        Args:
            user_id: The user identifier
            role: The message role (user, assistant, tool)
            content: The message content
            name: Optional name for tool messages
        """
        history = self._get_conversation_history(user_id)
        message: dict[str, Any] = {"role": role, "content": content}
        if name:
            message["name"] = name
        history.append(message)

        # Keep only last 20 messages to avoid token limits
        if len(history) > 21:  # 1 system + 20 messages
            self.conversation_history[user_id] = [history[0]] + history[-20:]

    async def process_message(self, user_id: str, message: str) -> str:
        """Process a user message and generate a response.

        Args:
            user_id: The user identifier (phone number)
            message: The user's message

        Returns:
            The agent's response
        """
        try:
            # Add user message to history
            self._add_to_history(user_id, "user", message)

            # Prepare the request
            messages = self._get_conversation_history(user_id)

            # Call OpenAI API
            if self.tools:
                # With tools
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.get_tools_schema(),
                    tool_choice="auto",
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
            else:
                # Without tools
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

            assistant_message = response.choices[0].message

            # Check if the model wants to call a tool
            if assistant_message.tool_calls:
                # Process tool calls
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(f"Calling tool: {tool_name} with args: {tool_args}")

                    if tool_name in self.tool_functions:
                        tool_result = await self.tool_functions[tool_name](**tool_args)

                        # Add tool result to history
                        self._add_to_history(
                            user_id, "tool", tool_result, name=tool_name
                        )

                # Make another API call with tool results
                messages = self._get_conversation_history(user_id)
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

                assistant_message = response.choices[0].message

            # Get the final response
            response_text = assistant_message.content or "Lo siento, no pude generar una respuesta."

            # Add assistant response to history
            self._add_to_history(user_id, "assistant", response_text)

            return response_text

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta de nuevo."

    def clear_history(self, user_id: str) -> None:
        """Clear conversation history for a user.

        Args:
            user_id: The user identifier
        """
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            logger.info(f"Cleared conversation history for user: {user_id}")
