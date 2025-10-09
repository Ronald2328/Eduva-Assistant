import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool  # type: ignore
from pydantic import BaseModel


class CountryTimeInfo(BaseModel):
    country: str
    timezone: str
    current_time: str
    formatted_time: str


@tool
async def get_time_by_country(country: str) -> dict[str, str]:
    """Get the current time for a specific country.

    Args:
        country: The name of the country to get the time for (e.g., 'Spain', 'USA', 'Japan', 'Mexico', 'Colombia')

    Returns:
        Dictionary with country, timezone, current_time, and formatted_time
    """

    # Common country to timezone mappings
    country_timezones = {
        "spain": "Europe/Madrid",
        "usa": "America/New_York",
        "united states": "America/New_York",
        "japan": "Asia/Tokyo",
        "mexico": "America/Mexico_City",
        "colombia": "America/Bogota",
        "argentina": "America/Argentina/Buenos_Aires",
        "brazil": "America/Sao_Paulo",
        "chile": "America/Santiago",
        "peru": "America/Lima",
        "venezuela": "America/Caracas",
        "france": "Europe/Paris",
        "germany": "Europe/Berlin",
        "italy": "Europe/Rome",
        "uk": "Europe/London",
        "united kingdom": "Europe/London",
        "china": "Asia/Shanghai",
        "india": "Asia/Kolkata",
        "australia": "Australia/Sydney",
        "canada": "America/Toronto",
        "ecuador": "America/Guayaquil",
        "bolivia": "America/La_Paz",
        "uruguay": "America/Montevideo",
        "paraguay": "America/Asuncion"
    }

    country_lower = country.lower().strip()
    timezone_str = country_timezones.get(country_lower)

    if not timezone_str:
        # If country not found, return UTC time
        timezone_str = "UTC"
        country = f"{country} (usando UTC como predeterminado)"

    try:
        # Get timezone and current time
        tz = ZoneInfo(timezone_str)
        current_time = datetime.datetime.now(tz)

        time_info = CountryTimeInfo(
            country=country,
            timezone=timezone_str,
            current_time=current_time.isoformat(),
            formatted_time=current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        )

        return time_info.model_dump()

    except Exception:
        # Fallback to UTC if there's any error
        utc_time = datetime.datetime.now(datetime.UTC)
        time_info = CountryTimeInfo(
            country=f"{country} (error, usando UTC)",
            timezone="UTC",
            current_time=utc_time.isoformat(),
            formatted_time=utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        )

        return time_info.model_dump()


TOOLS = [get_time_by_country]
