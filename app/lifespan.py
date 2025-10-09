from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI

from app.science_bot.agent.graph import get_graph
from app.science_bot.agent.schemas import Graph


class AppLifespan(TypedDict):
    science_bot_graph: Graph


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Initialize the graph and store it in app state
    graph = get_graph()
    app.state.science_bot_graph = graph

    yield AppLifespan(
        science_bot_graph=graph,
    )
