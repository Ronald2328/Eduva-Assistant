# ScienceBot WhatsApp API

Bot de WhatsApp integrado con Evolution API para respuestas automáticas.

## 🚀 Inicio Rápido

### 1. Instalar uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Instalar dependencias

```bash
uv sync
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

### 4. Iniciar servidor

```bash
# Desarrollo
uv run fastapi dev

# Producción
uv run fastapi run
```

## 🧪 Desarrollo

```bash
# Type checking
uv run mypy app/

# Linting
uv run ruff check app/

# Format
uv run ruff format app/

# Langgraph
uv run langgraph dev
```

## 📝 Licencia

MIT
