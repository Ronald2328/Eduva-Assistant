# 🚀 Guía Rápida - Railway Deployment

## 📋 Opción más Simple: Docker Hub Direct

### Servicio 1: Evolution API

1. **New Project** → **Empty Service**
2. **Settings** → **Source** → **Docker Image**
3. **Image:** `atendai/evolution-api:latest`
4. **Environment Variables:**
   ```
   AUTHENTICATION_API_KEY=Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7
   SERVER_PORT=8080
   DATABASE_ENABLED=false
   REDIS_ENABLED=false
   WEBSOCKET_ENABLED=false
   ```
5. **Deploy**

### Servicio 2: Tu Bot

1. **New Service** (mismo proyecto)
2. **GitHub Repo:** `https://github.com/Ronald2328/ScienceBotUNP.git`
3. **Environment Variables:**
   ```
   EVOLUTION_API_URL=https://[URL-SERVICIO-1].up.railway.app
   EVOLUTION_API_KEY=Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7
   EVOLUTION_INSTANCE_NAME=sciencebot_instance
   BOT_NAME=ScienceBot
   BOT_RESPONSE_MESSAGE=¡Hola! Soy ScienceBot 🔬. ¿En qué puedo ayudarte hoy?
   API_HOST=0.0.0.0
   API_PORT=8000
   SECRET_KEY=Sc13nc3B0t_2024_R4ilw4y_S3cr3t_K3y_9m8x7n2p5q1w4e6r
   API_DEBUG=false
   ```

## 🔗 Conectar WhatsApp

1. **Crear instancia:** `GET https://[BOT-URL]/instance/create`
2. **Obtener QR:** `GET https://[BOT-URL]/instance/qr`
3. **Escanear** con WhatsApp
4. **Probar** enviando mensaje

## 🆘 Si Evolution API no funciona

**Alternativa - Render.com:**
1. Crear cuenta en Render.com
2. **New** → **Web Service**
3. **Docker Image:** `atendai/evolution-api:latest`
4. **Environment Variables:** (mismas que arriba)
5. Usar URL de Render en `EVOLUTION_API_URL`

¡Listo! 🎉