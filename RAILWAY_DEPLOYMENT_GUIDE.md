# 🚀 Guía Completa de Deployment en Railway

Este proyecto requiere **2 servicios separados** en Railway para funcionar correctamente.

## 📋 Arquitectura

```
┌─────────────────┐    HTTP    ┌─────────────────┐
│   Servicio 1    │◄──────────►│   Servicio 2    │
│ Evolution API   │            │ ScienceBot API  │
│   Puerto 8080   │            │   Puerto 8000   │
└─────────────────┘            └─────────────────┘
```

---

## 🔧 Servicio 1: Evolution API

### Paso 1: Crear el servicio
1. En Railway, click **"New Project"**
2. Seleccionar **"Empty Service"**
3. En **Settings** → **Source**, seleccionar **"Docker Image"**
4. Usar imagen: `atendai/evolution-api:latest`
5. Click **"Deploy"**

### Paso 2: Configurar variables de entorno

En **Settings** → **Environment**, agregar:

```env
# Authentication (OBLIGATORIO)
AUTHENTICATION_API_KEY=Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7

# Server Configuration
SERVER_TYPE=http
SERVER_PORT=8080

# CORS Configuration
CORS_ORIGIN=*
CORS_METHODS=POST,GET,PUT,DELETE
CORS_CREDENTIALS=true

# Instance Management
DEL_INSTANCE=false
QRCODE_LIMIT=30

# Disable external services (simplifica deployment)
DATABASE_ENABLED=false
REDIS_ENABLED=false
RABBITMQ_ENABLED=false
WEBSOCKET_ENABLED=false
PROVIDER_ENABLED=false

# Logging
LOG_LEVEL=ERROR,WARN,INFO
LOG_COLOR=true
LOG_BAILEYS=false

# Session Configuration
CONFIG_SESSION_PHONE_CLIENT=Evolution API
CONFIG_SESSION_PHONE_NAME=Chrome

# WhatsApp Business (opcional)
WA_BUSINESS_TOKEN_WEBHOOK=evolution
WA_BUSINESS_URL=https://graph.facebook.com
WA_BUSINESS_VERSION=v20.0
WA_BUSINESS_LANGUAGE=pt_BR

# Webhook Configuration
WEBHOOK_GLOBAL_URL=
WEBHOOK_GLOBAL_ENABLED=false

# Language
LANGUAGE=en
```

### Paso 3: Obtener URL del servicio
1. Una vez deployado, ir a **Settings** → **Domains**
2. Copiar la URL (ej: `https://evolution-api-xyz.up.railway.app`)
3. **GUARDAR ESTA URL** - la necesitarás para el Servicio 2

---

## 🤖 Servicio 2: ScienceBot FastAPI

### Paso 1: Crear el servicio
1. En Railway, click **"New Service"** (en el mismo proyecto)
2. Seleccionar **"GitHub Repo"**
3. Conectar: `https://github.com/Ronald2328/ScienceBotUNP.git`
4. Railway detectará automáticamente el `Dockerfile`

### Paso 2: Configurar variables de entorno

En **Settings** → **Environment**, agregar:

```env
# Evolution API Configuration (ACTUALIZAR URL)
EVOLUTION_API_URL=https://[URL-DEL-SERVICIO-1].up.railway.app
EVOLUTION_API_KEY=Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7
EVOLUTION_INSTANCE_NAME=sciencebot_instance

# Bot Configuration
BOT_NAME=ScienceBot
BOT_RESPONSE_MESSAGE=¡Hola! Soy ScienceBot 🔬. ¿En qué puedo ayudarte hoy?

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# App Configuration
APP_NAME=ScienceBot WhatsApp API
APP_VERSION=1.0.0
ENVIRONMENT=production

# Security
SECRET_KEY=Sc13nc3B0t_2024_R4ilw4y_S3cr3t_K3y_9m8x7n2p5q1w4e6r

# Debug (false en producción)
API_DEBUG=false
```

⚠️ **IMPORTANTE**: Reemplazar `[URL-DEL-SERVICIO-1]` con la URL real del Servicio 1.

### Paso 3: Verificar deployment
El `railway.yml` maneja la configuración automáticamente:
- ✅ **Build**: Usa `Dockerfile`
- ✅ **Health Check**: `/health`
- ✅ **Port**: 8000

---

## 🔗 Conectar los servicios

### Paso 1: Verificar comunicación
1. Acceder a: `https://[SERVICIO-2-URL]/health`
2. Debe retornar: `{"status": "healthy", "bot": "ScienceBot"}`

### Paso 2: Probar Evolution API
1. Acceder a: `https://[SERVICIO-2-URL]/instance/status`
2. Si muestra conexión exitosa, todo está bien

---

## 📱 Configurar WhatsApp

### Paso 1: Crear instancia
```bash
GET https://[SERVICIO-2-URL]/instance/create
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "instance": {
    "instanceName": "sciencebot_instance",
    "status": "created"
  }
}
```

### Paso 2: Obtener código QR
```bash
GET https://[SERVICIO-2-URL]/instance/qr
```

**Respuesta esperada:**
```json
{
  "qrcode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "status": "qrcode_generated"
}
```

### Paso 3: Escanear QR con WhatsApp
1. Abrir **WhatsApp** en tu teléfono
2. Ir a **⚙️ Configuración** → **Dispositivos vinculados**
3. Tocar **"Vincular dispositivo"**
4. Escanear el código QR mostrado

### Paso 4: Verificar conexión
```bash
GET https://[SERVICIO-2-URL]/instance/status
```

**Respuesta cuando está conectado:**
```json
{
  "status": "open",
  "instance": "sciencebot_instance"
}
```

---

## 🧪 Probar el bot

1. **Enviar mensaje** a tu número de WhatsApp
2. **Respuesta automática**: "¡Hola! Soy ScienceBot 🔬. ¿En qué puedo ayudarte hoy?"
3. **Verificar logs** en Railway para confirmar que el mensaje fue procesado

---

## 🔧 Troubleshooting

### Error: "All connection attempts failed"
**Causa**: Servicio 2 no puede conectar al Servicio 1
**Solución**:
1. Verificar que ambos servicios estén funcionando
2. Confirmar que `EVOLUTION_API_URL` tenga la URL correcta del Servicio 1
3. Verificar que `EVOLUTION_API_KEY` sea igual en ambos servicios

### Error: "Instance not found"
**Causa**: La instancia no ha sido creada
**Solución**: Ejecutar `GET /instance/create` primero

### Error: "QR code expired"
**Causa**: El código QR tiene tiempo límite (30 seg por defecto)
**Solución**: Generar nuevo QR con `GET /instance/qr`

### Error 500 en endpoints
**Causa**: Variables de entorno incorrectas
**Solución**:
1. Verificar todas las variables en Railway
2. Redeploy el servicio después de cambios
3. Revisar logs en Railway Dashboard

---

## 📊 Monitoreo

### Logs importantes a revisar:
```bash
# En Servicio 1 (Evolution API)
- "WhatsApp connection established"
- "QR code generated"
- "Instance created successfully"

# En Servicio 2 (ScienceBot)
- "Message from [número]: [texto]"
- "Message sent successfully"
- "Webhook verification successful"
```

### Endpoints de salud:
- **Servicio 1**: `https://[SERVICIO-1-URL]/`
- **Servicio 2**: `https://[SERVICIO-2-URL]/health`

---

## 🔄 Actualizaciones

### Para actualizar el código:
1. Hacer `git push` al repositorio
2. Railway redeploy automáticamente el Servicio 2
3. El Servicio 1 (Evolution API) no necesita actualizaciones

### Para cambiar configuración:
1. Actualizar variables en Railway Dashboard
2. Restart el servicio correspondiente
3. Verificar que los cambios surtan efecto

---

## 💡 Tips importantes

- ✅ **Mantén las claves API iguales** en ambos servicios
- ✅ **Usa HTTPS** para todas las URLs
- ✅ **El Servicio 1 debe estar online** antes que el Servicio 2
- ✅ **Guarda las URLs** de ambos servicios para referencia
- ✅ **Revisa logs regularmente** para detectar problemas temprano

---

¡Tu ScienceBot ya está listo para funcionar en Railway! 🎉