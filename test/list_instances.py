"""Script para listar instancias disponibles en Evolution API."""

import asyncio
import logging

import httpx

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def list_instances() -> None:
    """Listar todas las instancias en Evolution API."""
    logger.info("=" * 60)
    logger.info("LISTANDO INSTANCIAS EN EVOLUTION API")
    logger.info("=" * 60)

    logger.info(f"\n📡 Evolution API URL: {settings.EVOLUTION_API_URL}")
    logger.info(f"🔑 API Key: {settings.EVOLUTION_API_KEY[:10]}...")

    url = f"{settings.EVOLUTION_API_URL}/instance/fetchInstances"
    headers = {
        "apikey": settings.EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info(f"\n🔍 Consultando: {url}")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            instances = response.json()

            if not instances:
                logger.warning("\n⚠️  No se encontraron instancias")
                logger.info("\n💡 Para crear una nueva instancia:")
                logger.info("   Accede a: GET /instance/create")
                logger.info(f"   curl -X POST {settings.EVOLUTION_API_URL}/instance/create \\")
                logger.info(f"        -H 'apikey: {settings.EVOLUTION_API_KEY}' \\")
                logger.info("        -H 'Content-Type: application/json' \\")
                logger.info("        -d '{")
                logger.info('             "instanceName": "sciencebot_instance",')
                logger.info('             "qrcode": true,')
                logger.info('             "integration": "WHATSAPP-BAILEYS"')
                logger.info("           }'")
                return

            logger.info(f"\n✅ Encontradas {len(instances)} instancia(s):\n")

            for idx, instance in enumerate(instances, 1):
                logger.info(f"{idx}. Datos completos:")
                logger.info(f"   {instance}")
                logger.info("")

                # Intentar extraer el nombre de diferentes formas
                instance_name = None
                if isinstance(instance, dict):
                    # Probar diferentes estructuras
                    instance_name = (
                        instance.get("instance", {}).get("instanceName")
                        or instance.get("instanceName")
                        or instance.get("name")
                    )
                    status = (
                        instance.get("instance", {}).get("status")
                        or instance.get("status")
                        or "N/A"
                    )

                    logger.info(f"   Nombre extraído: {instance_name}")
                    logger.info(f"   Estado: {status}")
                    logger.info("")

            # Verificar si existe la instancia configurada
            instance_names = []
            for inst in instances:
                if isinstance(inst, dict):
                    name = (
                        inst.get("instance", {}).get("instanceName")
                        or inst.get("instanceName")
                        or inst.get("name")
                    )
                    if name:
                        instance_names.append(name)

            if settings.EVOLUTION_INSTANCE_NAME in instance_names:
                logger.info(f"✅ La instancia configurada '{settings.EVOLUTION_INSTANCE_NAME}' existe!")
            else:
                logger.warning(f"⚠️  La instancia '{settings.EVOLUTION_INSTANCE_NAME}' NO existe")
                logger.info("\n💡 Opciones:")
                logger.info(f"   1. Crear la instancia '{settings.EVOLUTION_INSTANCE_NAME}'")
                logger.info(f"   2. O actualizar .env con uno de estos nombres: {instance_names}")

        except httpx.HTTPStatusError as e:
            logger.error(f"\n❌ Error HTTP {e.response.status_code}:")
            logger.error(f"   {e.response.text}")
            logger.error("\n💡 Verifica:")
            logger.error("   1. Que la URL sea correcta")
            logger.error("   2. Que el API Key sea válido")
        except httpx.RequestError as e:
            logger.error(f"\n❌ Error de conexión:")
            logger.error(f"   {e}")
            logger.error("\n💡 Verifica:")
            logger.error("   1. Que Evolution API esté corriendo")
            logger.error("   2. Que la URL sea accesible")
        except Exception as e:
            logger.error(f"\n❌ Error inesperado: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(list_instances())
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Operación cancelada por el usuario")
