# Bot con IA usando OpenAI

## Configuración

Agrega a tu archivo `.env`:

```bash
OPENAI_API_KEY=tu-api-key-aqui
```

## Cómo funciona

El bot ahora usa OpenAI para generar respuestas inteligentes en lugar de mensajes automáticos.

## Agregar nuevas herramientas

1. Crea una función async en `app/agent/tools/`:

```python
async def mi_herramienta(parametro: str) -> str:
    # Tu lógica aquí
    return "resultado"

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "mi_herramienta",
        "description": "Descripción de lo que hace",
        "parameters": {
            "type": "object",
            "properties": {
                "parametro": {
                    "type": "string",
                    "description": "Descripción del parámetro",
                }
            },
            "required": ["parametro"],
        },
    },
}
```

2. Registra en `app/agent/setup.py`:

```python
agent.register_tool(
    name="mi_herramienta",
    schema=TOOL_SCHEMA,
    function=mi_herramienta,
)
```

¡Listo! El agente la usará automáticamente cuando sea necesario.
