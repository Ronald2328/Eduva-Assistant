# Railway Deployment Setup

Este proyecto usa **2 servicios separados** en Railway:

## 🚀 Servicio 1: Evolution API

**Configuración:**
- **Template:** `atendai/evolution-api:latest`
- **Custom Start Command:** `./start-evolution.sh`
- **Port:** `8080`

**Variables de entorno:**
```
EVOLUTION_API_KEY=Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7
SERVER_PORT=8080
SERVER_TYPE=http
CORS_ORIGIN=*
AUTHENTICATION_TYPE=apikey
AUTHENTICATION_API_KEY=Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7
QRCODE_LIMIT=30
```

## 🤖 Servicio 2: ScienceBot FastAPI

**Configuración:**
- **GitHub Repo:** `https://github.com/Ronald2328/ScienceBotUNP.git`
- **Custom Start Command:** `uv run python -m app.main`
- **Port:** `8000`

**Variables de entorno:**
```
EVOLUTION_API_URL=https://[SERVICIO-1-URL].up.railway.app
EVOLUTION_API_KEY=Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7
EVOLUTION_INSTANCE_NAME=sciencebot_instance
BOT_NAME=ScienceBot
BOT_RESPONSE_MESSAGE=¡Hola! Soy ScienceBot 🔬. ¿En qué puedo ayudarte hoy?
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=Sc13nc3B0t_2024_R4ilw4y_S3cr3t_K3y_9m8x7n2p5q1w4e6r
```

## 🔗 Conectar servicios

1. **Primero:** Deploy Servicio 1 (Evolution API)
2. **Copiar:** URL del Servicio 1
3. **Actualizar:** `EVOLUTION_API_URL` en Servicio 2
4. **Deploy:** Servicio 2 (Bot)

## 📱 Uso

1. **Crear instancia:** `GET https://[SERVICIO-2-URL]/instance/create`
2. **Obtener QR:** `GET https://[SERVICIO-2-URL]/instance/qr`
3. **Escanear** con WhatsApp
4. **Probar** enviando mensaje a tu número