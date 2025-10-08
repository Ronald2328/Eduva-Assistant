"""Script de prueba para verificar la configuración."""

import asyncio
import logging

from app.core.config import settings
from app.services.evolution_service import evolution_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_configuration() -> None:
    """Probar la configuración."""
    logger.info("=== Verificando Configuración ===\n")

    # Mostrar configuración
    logger.info("Configuración actual:")
    logger.info(f"  - Evolution API URL: {settings.EVOLUTION_API_URL}")
    logger.info(f"  - Instance Name: {settings.EVOLUTION_INSTANCE_NAME}")
    logger.info(f"  - Webhook URL: {settings.WEBHOOK_URL}")
    logger.info(f"  - Webhook Enabled: {settings.WEBHOOK_ENABLED}")
    logger.info(f"  - Bot Name: {settings.BOT_NAME}")
    logger.info(f"  - API Host: {settings.API_HOST}")
    logger.info(f"  - API Port: {settings.API_PORT}")

    logger.info("\n=== Probando Conexión con Evolution API ===\n")

    # Probar estado de la instancia
    logger.info("1. Obteniendo estado de la instancia...")
    status = await evolution_service.get_instance_status()

    if "error" in status:
        logger.error(f"❌ Error al conectar con Evolution API: {status['error']}")
        logger.error("\nVerifica que:")
        logger.error("  1. Evolution API esté corriendo")
        logger.error(f"  2. La URL sea correcta: {settings.EVOLUTION_API_URL}")
        logger.error("  3. El API Key sea válido")
        logger.error(f"  4. La instancia '{settings.EVOLUTION_INSTANCE_NAME}' exista")
        return

    logger.info(f"✅ Estado de la instancia: {status}")

    # Probar configuración del webhook
    logger.info("\n2. Obteniendo configuración del webhook...")
    webhook_config = await evolution_service.get_webhook()

    if webhook_config and "error" in webhook_config:
        logger.warning(f"⚠️  No se pudo obtener webhook: {webhook_config['error']}")
        logger.info("\nIntentando configurar webhook...")

        webhook_result = await evolution_service.set_webhook()
        if webhook_result and "error" in webhook_result:
            logger.error(f"❌ Error al configurar webhook: {webhook_result['error']}")
        else:
            logger.info(f"✅ Webhook configurado: {webhook_result}")
    elif webhook_config:
        logger.info(f"✅ Webhook configurado: {webhook_config}")
    else:
        logger.warning("⚠️  No se recibió respuesta del webhook")

    logger.info("\n=== Verificación Completada ===")
    logger.info("\n📝 Próximos pasos:")
    logger.info("  1. Inicia el servidor: uv run fastapi dev")
    logger.info("  2. Si tu instancia no está conectada, obtén el QR: GET /instance/qr")
    logger.info("  3. Envía un mensaje de WhatsApp a tu número conectado")
    logger.info("  4. Revisa los logs para ver la respuesta automática")


if __name__ == "__main__":
    asyncio.run(test_configuration())
