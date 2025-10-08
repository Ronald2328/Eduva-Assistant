"""Script de prueba para el agente de IA."""

import asyncio

from app.agent import agent


async def main() -> None:
    """Prueba el agente con algunos mensajes."""
    print("🤖 Probando el agente de IA...\n")

    # Test 1: Mensaje simple
    print("Test 1: Saludo")
    response = await agent.process_message("test_user", "Hola, ¿cómo estás?")
    print(f"Bot: {response}\n")

    # Test 2: Pregunta que debería activar la tool
    print("Test 2: Pregunta sobre la hora")
    response = await agent.process_message(
        "test_user", "¿Qué hora es en Perú?"
    )
    print(f"Bot: {response}\n")

    # Test 3: Otro país
    print("Test 3: Pregunta sobre otro país")
    response = await agent.process_message(
        "test_user", "¿Y en México qué hora es?"
    )
    print(f"Bot: {response}\n")

    print("✅ Pruebas completadas")


if __name__ == "__main__":
    asyncio.run(main())
