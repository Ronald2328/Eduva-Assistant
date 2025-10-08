"""Script para configurar el webhook en Evolution API de Railway."""

import asyncio
import logging

from app.core.config import settings
from app.services.evolution_service import evolution_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def configure_webhook_railway() -> None:
    """Configurar webhook en Evolution API alojado en Railway."""
    logger.info("=" * 60)
    logger.info("CONFIGURACIÓN DE WEBHOOK EN EVOLUTION API (RAILWAY)")
    logger.info("=" * 60)

    logger.info("\n📋 Configuración actual:")
    logger.info(f"  • Evolution API URL: {settings.EVOLUTION_API_URL}")
    logger.info(f"  • Instancia: {settings.EVOLUTION_INSTANCE_NAME}")
    logger.info(f"  • Webhook URL: {settings.WEBHOOK_URL}")
    logger.info(f"  • Webhook Enabled: {settings.WEBHOOK_ENABLED}")

    # Verificar conexión
    logger.info("\n🔍 Paso 1: Verificando conexión con Evolution API...")
    status = await evolution_service.get_instance_status()

    if "error" in status:
        logger.error(f"\n❌ Error al conectar con Evolution API:")
        logger.error(f"   {status['error']}")
        logger.error("\n💡 Verifica que:")
        logger.error("   1. Evolution API esté corriendo en Railway")
        logger.error("   2. La URL sea correcta en .env")
        logger.error("   3. El API Key sea válido")
        logger.error(f"   4. La instancia '{settings.EVOLUTION_INSTANCE_NAME}' exista")
        return

    logger.info(f"✅ Conexión exitosa!")
    logger.info(f"   Estado: {status.get('state', 'unknown')}")

    # Configurar webhook
    logger.info("\n⚙️  Paso 2: Configurando webhook...")

    if not settings.WEBHOOK_ENABLED:
        logger.warning("⚠️  WEBHOOK_ENABLED está en False en .env")
        return

    # Importante: Verificar que la URL del webhook sea accesible desde Railway
    if settings.WEBHOOK_URL.startswith("http://localhost"):
        logger.warning("\n⚠️  ADVERTENCIA IMPORTANTE:")
        logger.warning("   Tu WEBHOOK_URL es 'localhost', Evolution API en Railway NO podrá acceder.")
        logger.warning("\n   Para que funcione, necesitas:")
        logger.warning("   1. Desplegar este servicio en Railway, Render, o similar")
        logger.warning("   2. O usar ngrok/cloudflare tunnel para exponer localhost")
        logger.warning("\n   Ejemplo con ngrok:")
        logger.warning("   - Instalar: brew install ngrok (Mac) o descargar de ngrok.com")
        logger.warning("   - Ejecutar: ngrok http 8000")
        logger.warning("   - Copiar la URL https:// que te da ngrok")
        logger.warning("   - Actualizar WEBHOOK_URL en .env con esa URL + /webhook")
        logger.warning("\n   ¿Deseas continuar de todos modos? (configurará localhost)")

    webhook_result = await evolution_service.set_webhook()

    if "error" in webhook_result:
        logger.error(f"\n❌ Error al configurar webhook:")
        logger.error(f"   {webhook_result['error']}")
        return

    logger.info("✅ Webhook configurado exitosamente!")

    # Verificar configuración
    logger.info("\n🔍 Paso 3: Verificando configuración del webhook...")
    webhook_config = await evolution_service.get_webhook()

    if "error" not in webhook_config:
        logger.info("✅ Configuración del webhook:")
        logger.info(f"   URL: {webhook_config.get('url', 'N/A')}")
        logger.info(f"   Eventos: {len(webhook_config.get('events', []))} configurados")
        logger.info(f"   Webhook by Events: {webhook_config.get('webhook_by_events', False)}")
        logger.info(f"   Webhook Base64: {webhook_config.get('webhook_base64', False)}")

    logger.info("\n" + "=" * 60)
    logger.info("✅ CONFIGURACIÓN COMPLETADA")
    logger.info("=" * 60)

    logger.info("\n📝 Próximos pasos:")
    logger.info("   1. Inicia este servidor: uv run fastapi dev")

    if settings.WEBHOOK_URL.startswith("http://localhost"):
        logger.info("   2. Configura ngrok o despliega a producción")
        logger.info("   3. Actualiza WEBHOOK_URL en .env con la URL pública")
        logger.info("   4. Ejecuta este script nuevamente")
    else:
        logger.info("   2. Envía un mensaje de WhatsApp a tu instancia")
        logger.info("   3. Verifica los logs para ver la respuesta automática")

    logger.info("\n💡 Comandos útiles:")
    logger.info("   • Ver webhook actual: curl {}/webhook/get".format(
        f"http://localhost:{settings.API_PORT}"
    ))
    logger.info("   • Estado instancia: curl {}/instance/status".format(
        f"http://localhost:{settings.API_PORT}"
    ))


if __name__ == "__main__":
    try:
        asyncio.run(configure_webhook_railway())
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Configuración cancelada por el usuario")
    except Exception as e:
        logger.error(f"\n❌ Error inesperado: {e}", exc_info=True)
