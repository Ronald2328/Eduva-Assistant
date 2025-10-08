# 🚀 Guía de Configuración - Evolution API en Railway

## Situación Actual

✅ Evolution API corriendo en Railway: `https://evolution-api-production-be3e.up.railway.app`
✅ Instancia de WhatsApp: `sciencebot_instance`
⚠️ Necesitas configurar el webhook para recibir y responder mensajes

## Opción 1: Desarrollo Local con ngrok (Recomendado para pruebas)

### Paso 1: Instalar ngrok

```bash
# En Linux/Mac
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# O descarga desde: https://ngrok.com/download
```

### Paso 2: Crear cuenta en ngrok

1. Ve a https://dashboard.ngrok.com/signup
2. Crea una cuenta gratuita
3. Copia tu authtoken
4. Ejecuta: `ngrok config add-authtoken TU_TOKEN_AQUI`

### Paso 3: Iniciar el servidor local

```bash
# Terminal 1: Inicia tu servidor FastAPI
cd /home/ronaldo/UNP/BOT
uv run fastapi dev
```

### Paso 4: Exponer con ngrok

```bash
# Terminal 2: Inicia ngrok
ngrok http 8000
```

Verás algo como:

```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

### Paso 5: Actualizar .env con la URL de ngrok

Edita `/home/ronaldo/UNP/BOT/.env`:

```env
WEBHOOK_URL=https://abc123.ngrok.io/webhook
```

**⚠️ IMPORTANTE:** Reemplaza `abc123.ngrok.io` con la URL que te dio ngrok.

### Paso 6: Configurar webhook en Evolution

```bash
# Terminal 3: Configura el webhook
uv run python test/test/configure_webhook.py
```

### Paso 7: Probar

1. Envía un mensaje de WhatsApp a tu número conectado
2. Deberías ver en los logs del servidor la recepción del mensaje
3. El bot responderá automáticamente

---

## Opción 2: Producción en Railway (Recomendado para uso real)

### Paso 1: Preparar el proyecto

Asegúrate de tener estos archivos en tu repositorio:

- `pyproject.toml` ✅
- `uv.lock` ✅
- `app/` con todo el código ✅

### Paso 2: Crear Procfile (si no existe)

```bash
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile
```

### Paso 3: Desplegar en Railway

1. Ve a https://railway.app
2. Conecta tu repositorio de GitHub
3. Railway detectará automáticamente que es un proyecto Python
4. Agrega las variables de entorno en Railway:

```
EVOLUTION_API_URL=https://evolution-api-production-be3e.up.railway.app
EVOLUTION_API_KEY=Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7
EVOLUTION_INSTANCE_NAME=sciencebot_instance
WEBHOOK_URL=https://tu-app.railway.app/webhook
WEBHOOK_ENABLED=true
BOT_NAME=ScienceBot
BOT_RESPONSE_MESSAGE=¡Hola! Soy ScienceBot 🔬. ¿En qué puedo ayudarte hoy?
API_HOST=0.0.0.0
API_PORT=$PORT
API_DEBUG=false
SECRET_KEY=Sc13nc3B0t_2024_R4ilw4y_S3cr3t_K3y_9m8x7n2p5q1w4e6r
```

**⚠️ IMPORTANTE:**

- Reemplaza `tu-app.railway.app` con la URL real que te dé Railway
- Railway automáticamente asigna la variable `$PORT`

### Paso 4: Esperar el deploy

Railway automáticamente:

- Instalará dependencias con `uv`
- Ejecutará el servidor con Uvicorn
- Te dará una URL pública

### Paso 5: Configurar webhook

Una vez desplegado, ejecuta localmente (o crea un endpoint):

```bash
# Actualiza .env con la URL de Railway
WEBHOOK_URL=https://tu-app.railway.app/webhook

# Configura el webhook
uv run python test/test/configure_webhook.py
```

O accede directamente a:

```
https://tu-app.railway.app/webhook/set
```

---

## Opción 3: Cloudflare Tunnel (Alternativa gratuita a ngrok)

### Paso 1: Instalar cloudflared

```bash
# Linux
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### Paso 2: Crear tunnel

```bash
# Inicia el servidor
uv run fastapi dev

# En otra terminal
cloudflared tunnel --url http://localhost:8000
```

Te dará una URL como: `https://random-name.trycloudflare.com`

### Paso 3: Actualizar .env

```env
WEBHOOK_URL=https://random-name.trycloudflare.com/webhook
```

### Paso 4: Configurar webhook

```bash
uv run python test/test/configure_webhook.py
```

---

## 🔧 Comandos Útiles

```bash
# Verificar configuración actual
uv run python test/test/test_config.py

# Configurar webhook
uv run python test/test/configure_webhook.py

# Iniciar servidor en desarrollo
uv run fastapi dev

# Iniciar servidor en producción
uv run fastapi run

# Ver logs en tiempo real (cuando esté corriendo)
# Los verás en la terminal donde ejecutaste fastapi dev

# Verificar webhook configurado
curl http://localhost:8000/webhook/get

# Ver estado de la instancia
curl http://localhost:8000/instance/status

# Ver documentación interactiva
# http://localhost:8000/docs
```

---

## 📝 Eventos de Webhook Disponibles

Actualmente configurado para escuchar:

- ✅ `QRCODE_UPDATED` - Cuando se genera un nuevo QR
- ✅ `MESSAGES_UPSERT` - Cuando llega un mensaje nuevo
- ✅ `MESSAGES_UPDATE` - Cuando se actualiza un mensaje
- ✅ `SEND_MESSAGE` - Cuando se envía un mensaje
- ✅ `CONNECTION_UPDATE` - Cuando cambia el estado de conexión

Otros eventos disponibles en Evolution:

- `APPLICATION_STARTUP`
- `CALL`
- `CHATS_DELETE`, `CHATS_SET`, `CHATS_UPDATE`, `CHATS_UPSERT`
- `CONTACTS_SET`, `CONTACTS_UPDATE`, `CONTACTS_UPSERT`
- `GROUP_PARTICIPANTS_UPDATE`, `GROUP_UPDATE`, `GROUPS_UPSERT`
- `LABELS_ASSOCIATION`, `LABELS_EDIT`
- `LOGOUT_INSTANCE`, `REMOVE_INSTANCE`
- `MESSAGES_DELETE`, `MESSAGES_SET`
- `PRESENCE_UPDATE`
- `TYPEBOT_CHANGE_STATUS`, `TYPEBOT_START`

---

## ❓ Troubleshooting

### "Invalid URL format" en Evolution

➡️ Asegúrate que `WEBHOOK_URL` sea una URL pública válida (https://)
➡️ No uses `localhost` o `127.0.0.1` cuando Evolution está en Railway

### No llegan mensajes al webhook

1. Verifica que el webhook esté configurado: `curl http://localhost:8000/webhook/get`
2. Verifica que tu servidor esté accesible desde internet
3. Revisa los logs de Evolution API en Railway
4. Asegúrate que `MESSAGES_UPSERT` esté en los eventos

### Evolution API no responde

1. Verifica que la URL sea correcta
2. Verifica el API Key
3. Chequea que la instancia exista y esté conectada

---

## 🎯 Flujo Completo

1. **Mensaje entrante** → WhatsApp
2. **Evolution API** detecta el mensaje
3. **Webhook** envía el mensaje a tu servidor (`/webhook`)
4. **Tu servidor** procesa el mensaje con `evolution_service.parse_webhook_message()`
5. **Tu servidor** envía respuesta con `evolution_service.send_message()`
6. **Evolution API** envía la respuesta a WhatsApp
7. **Usuario** recibe la respuesta automática

---

## 🚀 Empezar Ahora

```bash
# 1. Elige tu opción (ngrok para desarrollo, Railway para producción)

# 2. Si usas ngrok:
uv run fastapi dev          # Terminal 1
ngrok http 8000             # Terminal 2
# Actualiza WEBHOOK_URL en .env con la URL de ngrok
uv run python test/test/configure_webhook.py  # Terminal 3

# 3. Si despliegas a Railway:
# - Sube tu código a GitHub
# - Despliega en Railway
# - Configura las variables de entorno
# - Ejecuta test/configure_webhook.py con la URL de Railway

# 4. Prueba enviando un mensaje de WhatsApp
```
