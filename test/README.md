# Test y Scripts de Configuración

Esta carpeta contiene scripts para configurar y verificar la integración con Evolution API.

## Scripts Disponibles

### `test_config.py`

Script para verificar la configuración y conexión con Evolution API.

**Uso:**
```bash
uv run python test/test_config.py
```

**Qué hace:**
- ✅ Muestra la configuración actual del `.env`
- ✅ Verifica conexión con Evolution API
- ✅ Obtiene el estado de la instancia
- ✅ Verifica la configuración del webhook
- ⚠️  Detecta problemas comunes y sugiere soluciones

**Cuándo usarlo:**
- Antes de iniciar el servidor por primera vez
- Para diagnosticar problemas de conexión
- Para verificar que Evolution API esté accesible

---

### `configure_webhook.py`

Script para configurar el webhook en Evolution API.

**Uso:**
```bash
uv run python test/configure_webhook.py
```

**Qué hace:**
- ✅ Configura la URL del webhook en Evolution API
- ✅ Configura los eventos que se van a escuchar
- ✅ Verifica que la configuración sea correcta
- ⚠️  Advierte si usas `localhost` con Evolution en Railway

**Cuándo usarlo:**
- Después de crear una instancia nueva
- Cuando cambies la URL del webhook (ej: nueva URL de ngrok o Railway)
- Para reconfigurar los eventos del webhook

**Importante:**
- Si Evolution API está en Railway, tu `WEBHOOK_URL` debe ser pública (no `localhost`)
- Usa ngrok o despliega tu servidor para que Evolution pueda enviar webhooks

---

## Flujo Recomendado

### Primera vez (desarrollo local con ngrok)

```bash
# 1. Verificar configuración
uv run python test/test_config.py

# 2. Iniciar servidor (Terminal 1)
uv run fastapi dev

# 3. Iniciar ngrok (Terminal 2)
ngrok http 8000

# 4. Actualizar .env con URL de ngrok
# WEBHOOK_URL=https://abc123.ngrok.io/webhook

# 5. Configurar webhook (Terminal 3)
uv run python test/configure_webhook.py

# 6. Probar enviando un mensaje de WhatsApp
```

### Producción (Railway)

```bash
# 1. Desplegar a Railway
# 2. Configurar variables de entorno en Railway
# 3. Esperar el deploy
# 4. Ejecutar configure_webhook con la URL de Railway

# Localmente:
# Actualizar .env con WEBHOOK_URL=https://tu-app.railway.app/webhook
uv run python test/configure_webhook.py
```

---

## Variables de Entorno Necesarias

Estos scripts usan las siguientes variables del archivo `.env`:

```env
EVOLUTION_API_URL=https://evolution-api-production-be3e.up.railway.app
EVOLUTION_API_KEY=tu_api_key
EVOLUTION_INSTANCE_NAME=sciencebot_instance
WEBHOOK_URL=https://tu-url-publica.com/webhook
WEBHOOK_ENABLED=true
```

Asegúrate de tener todas configuradas antes de ejecutar los scripts.
