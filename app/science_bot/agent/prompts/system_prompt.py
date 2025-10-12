"""System prompt configuration for the Science Bot."""

from datetime import datetime
from zoneinfo import ZoneInfo

import phonenumbers
from phonenumbers import timezone as phone_timezone


def get_country_timezone(phone_number: str) -> str:
    """Get timezone based on phone number country code.

    Args:
        phone_number: Phone number (may include country code)

    Returns:
        IANA timezone identifier
    """
    try:
        parsed_number: phonenumbers.PhoneNumber = phonenumbers.parse(
            number=phone_number, region=None
        )
        timezones: tuple[str, ...] = phone_timezone.time_zones_for_number(
            numobj=parsed_number
        )

        if timezones:
            return timezones[0]
    except Exception:
        pass

    return "UTC"


def get_current_time_for_phone(phone_number: str) -> str:
    """Get current time formatted for the phone number's timezone.

    Args:
        phone_number: Phone number (may include country code)

    Returns:
        Formatted current time string
    """
    timezone: str = get_country_timezone(phone_number=phone_number)

    try:
        tz = ZoneInfo(key=timezone)
        current_time: datetime = datetime.now(tz=tz)
        return current_time.strftime(format="%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        current_time = datetime.now(tz=ZoneInfo(key="UTC"))
        return current_time.strftime(format="%Y-%m-%d %H:%M:%S UTC")


def get_system_prompt(phone_number: str | None = None) -> str:
    """Generate the system prompt with current time information.

    Args:
        phone_number: User's phone number to determine timezone

    Returns:
        Complete system prompt string
    """
    time_info = ""
    if phone_number:
        current_time: str = get_current_time_for_phone(phone_number=phone_number)
        time_info: str = f"\n\nCurrent time for this user: {current_time}"

    return f"""You are a helpful assistant that can provide current time information for different countries.
When users ask about time in specific countries, use the get_time_by_country tool to provide accurate information.{time_info}"""
