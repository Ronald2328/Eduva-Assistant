"""Inicializa el agente y registra las herramientas."""

from app.agent.agent import Agent
from app.agent.tools.time_tool import TOOL_SCHEMA, get_current_time

# Crear instancia del agente
agent = Agent()

# Registrar herramientas
agent.register_tool(
    name="get_current_time",
    schema=TOOL_SCHEMA,
    function=get_current_time,
)
