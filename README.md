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
# Edita .env con tu configuración
```

**Variables importantes:**

- `EVOLUTION_API_URL` - URL de Evolution API
- `EVOLUTION_API_KEY` - API Key de Evolution
- `EVOLUTION_INSTANCE_NAME` - Nombre de tu instancia
- `WEBHOOK_URL` - URL pública para recibir webhooks
- `SECRET_KEY` - Clave secreta (genera con `openssl rand -hex 32`)

### 4. Configurar webhook

```bash
# Verificar conexión
uv run python test/test_config.py

# Configurar webhook en Evolution
uv run python test/configure_webhook.py
```

### 5. Iniciar servidor

```bash
# Desarrollo
uv run fastapi dev

# Producción
uv run fastapi run
```

## 📚 Documentación

- **[RAILWAY_SETUP.md](RAILWAY_SETUP.md)** - Guía completa para configurar con Evolution API en Railway
  - Configuración con ngrok (desarrollo local)
  - Despliegue en Railway (producción)
  - Troubleshooting y comandos útiles

## 🔌 Endpoints Disponibles

- `GET /` - Estado del bot
- `POST /webhook` - Recibir mensajes de Evolution API
- `GET /instance/create` - Crear instancia de WhatsApp
- `GET /instance/qr` - Obtener código QR
- `GET /instance/status` - Estado de la instancia
- `POST /webhook/set` - Configurar webhook
- `GET /webhook/get` - Ver configuración del webhook
- `GET /health` - Health check
- `GET /docs` - Documentación interactiva (Swagger)

## 🏗️ Estructura del Proyecto

```
BOT/
├── app/
│   ├── main.py              # Aplicación FastAPI
│   ├── core/
│   │   └── config.py        # Configuración con Pydantic Settings
│   ├── models/
│   │   └── webhook.py       # Modelos de datos tipados
│   └── services/
│       └── evolution_service.py  # Servicio de Evolution API
├── test/
│   ├── configure_webhook.py # Script para configurar webhook
│   └── test_config.py       # Verificar configuración
├── pyproject.toml          # Dependencias y configuración
├── .env                    # Variables de entorno (no incluir en git)
└── RAILWAY_SETUP.md        # Guía completa de configuración
```

## 🛠️ Tecnologías

- **Python 3.13** - Última versión con tipado mejorado
- **FastAPI** - Framework web moderno y rápido
- **Pydantic** - Validación de datos con tipado estricto
- **Evolution API** - API para integración con WhatsApp
- **uv** - Gestor de paquetes rápido

## 🧪 Desarrollo

```bash
# Type checking
uv run mypy app/

# Linting
uv run ruff check app/

# Format
uv run ruff format app/
```

## 📝 Licencia

MIT
