from dataclasses import dataclass
from typing import Annotated

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import add_messages  # type: ignore
from langgraph.graph.state import CompiledStateGraph  # type: ignore

Messages = Annotated[list[BaseMessage], add_messages]


@dataclass
class Context:
    user_id: str | None = None
    phone_number: str | None = None

    @classmethod
    def from_config(cls, config: RunnableConfig) -> "Context":
        return cls(
            user_id=config.get("configurable", {}).get("user_id"),
            phone_number=config.get("configurable", {}).get("phone_number"),
        )


@dataclass
class InputState:
    messages: Messages


@dataclass
class OutputState:
    success: bool
    messages: Messages


class OverallState(InputState, OutputState):
    pass


type Graph = CompiledStateGraph[OverallState, Context, InputState, OutputState]
