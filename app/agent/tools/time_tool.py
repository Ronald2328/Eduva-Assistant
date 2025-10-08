"""Tool para obtener la hora actual de un país."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)

# Mapeo de países a zonas horarias
COUNTRY_TIMEZONES = {
    "peru": "America/Lima",
    "perú": "America/Lima",
    "argentina": "America/Argentina/Buenos_Aires",
    "chile": "America/Santiago",
    "colombia": "America/Bogota",
    "mexico": "America/Mexico_City",
    "méxico": "America/Mexico_City",
    "españa": "Europe/Madrid",
    "spain": "Europe/Madrid",
    "usa": "America/New_York",
    "estados unidos": "America/New_York",
    "brasil": "America/Sao_Paulo",
    "brazil": "America/Sao_Paulo",
}


async def get_current_time(country: str) -> str:
    """Obtiene la hora actual de un país.

    Args:
        country: Nombre del país

    Returns:
        La hora actual formateada
    """
    try:
        country_lower = country.lower().strip()

        # Buscar timezone
        timezone_str = COUNTRY_TIMEZONES.get(country_lower)

        if not timezone_str:
            # Intentar obtener desde API si no está en el mapeo
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://worldtimeapi.org/api/timezone",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    zones = response.json()
                    # Buscar zona que contenga el nombre del país
                    matching_zone = next(
                        (z for z in zones if country_lower in z.lower()), None
                    )
                    if matching_zone:
                        timezone_str = matching_zone

        if not timezone_str:
            return f"No encontré la zona horaria para {country}. Países disponibles: Perú, Argentina, Chile, Colombia, México, España, USA, Brasil."

        # Obtener hora actual
        tz = ZoneInfo(timezone_str)
        current_time = datetime.now(tz)

        result = (
            f"🌍 Hora actual en {country.title()}:\n"
            f"📅 {current_time.strftime('%d/%m/%Y')}\n"
            f"🕐 {current_time.strftime('%H:%M:%S')}\n"
            f"⏰ Zona horaria: {timezone_str}"
        )

        logger.info(f"Hora obtenida para {country}: {current_time}")
        return result

    except Exception as e:
        logger.error(f"Error obteniendo hora para {country}: {e}")
        return f"Error al obtener la hora de {country}: {str(e)}"


# Schema de la tool para OpenAI
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Obtiene la fecha y hora actual de un país específico",
        "parameters": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "El nombre del país (ej: Perú, Argentina, Chile, Colombia, México, España, USA, Brasil)",
                }
            },
            "required": ["country"],
        },
    },
}
