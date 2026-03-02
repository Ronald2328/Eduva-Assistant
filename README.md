### 1. Instalar uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Instalar dependencias

```bash
uv sync
```

### 3. Iniciar servidor

```bash
# Desarrollo
uv run langgraph dev

# Producción
uv run fastapi run
```
