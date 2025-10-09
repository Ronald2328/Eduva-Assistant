from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, Request

from app.science_bot.agent.schemas import Graph
from app.science_bot.service import ScienceBotService


async def get_science_bot_service(
    request: Request,
) -> AsyncGenerator[ScienceBotService]:
    graph = cast(Graph, request.app.state.science_bot_graph)
    yield ScienceBotService(graph=graph)


ScienceBotServiceDep = Annotated[
    ScienceBotService, Depends(dependency=get_science_bot_service)
]
