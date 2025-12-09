"""Language handling utilities for Local Weather Forecast integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .forecast_data import (
    WIND_TYPES,
    VISIBILITY_ESTIMATES,
    COMFORT_LEVELS,
    FOG_RISK_LEVELS,
    ATMOSPHERE_STABILITY,
    ADJUSTMENT_TEMPLATES,
)

_LOGGER = logging.getLogger(__name__)

# Language mapping: HA language code → forecast_data.py array index
# forecast_data.py format: [German, English, Greek, Italian, Slovak]
LANGUAGE_MAP = {
    "de": 0,  # German
    "en": 1,  # English (default)
    "el": 2,  # Greek (HA uses 'el')
    "gr": 2,  # Greek alternative
    "it": 3,  # Italian
    "sk": 4,  # Slovak
}

DEFAULT_LANGUAGE_INDEX = 1  # English


def get_language_index(hass: HomeAssistant) -> int:
    """Get language array index from Home Assistant UI language.

    Args:
        hass: Home Assistant instance

    Returns:
        Language index (0-4) for forecast_data arrays
        Default: 1 (English)
    """
    if not hass or not hass.config:
        return DEFAULT_LANGUAGE_INDEX

    ha_language = hass.config.language
    lang_index = LANGUAGE_MAP.get(ha_language, DEFAULT_LANGUAGE_INDEX)

    _LOGGER.debug(
        f"Language detection: HA language={ha_language} → index={lang_index} "
        f"(0=de, 1=en, 2=el, 3=it, 4=sk)"
    )

    return lang_index


def get_wind_type(hass: HomeAssistant, beaufort_number: int) -> str:
    """Get wind type description in user's language.

    Args:
        hass: Home Assistant instance
        beaufort_number: Beaufort scale number (0-12)

    Returns:
        Wind type description in user's language
    """
    lang_index = get_language_index(hass)

    if 0 <= beaufort_number < len(WIND_TYPES):
        return WIND_TYPES[beaufort_number][lang_index]

    # Fallback
    return "Unknown" if lang_index == 1 else WIND_TYPES[0][lang_index]


def get_visibility_estimate(hass: HomeAssistant, fog_risk: str) -> str:
    """Get visibility estimate text in user's language.

    Args:
        hass: Home Assistant instance
        fog_risk: Fog risk level (high, medium, low, none)

    Returns:
        Visibility estimate in user's language
    """
    lang_index = get_language_index(hass)

    if fog_risk in VISIBILITY_ESTIMATES:
        return VISIBILITY_ESTIMATES[fog_risk][lang_index]

    # Fallback to "none" (very good visibility)
    return VISIBILITY_ESTIMATES["none"][lang_index]


def get_comfort_level_text(hass: HomeAssistant, comfort_level: str) -> str:
    """Get comfort level text in user's language.

    Args:
        hass: Home Assistant instance
        comfort_level: Comfort level key (very_cold, cold, cool, comfortable, warm, hot, very_hot)

    Returns:
        Comfort level text in user's language
    """
    lang_index = get_language_index(hass)

    if comfort_level in COMFORT_LEVELS:
        return COMFORT_LEVELS[comfort_level][lang_index]

    # Fallback to comfortable
    return COMFORT_LEVELS.get("comfortable", ("Angenehm", "Comfortable", "Άνετο", "Confortevole", "Príjemne"))[lang_index]


def get_fog_risk_text(hass: HomeAssistant, fog_risk: str) -> str:
    """Get fog risk level text in user's language.

    Args:
        hass: Home Assistant instance
        fog_risk: Fog risk level (none, low, medium, high, critical)

    Returns:
        Fog risk text in user's language
    """
    lang_index = get_language_index(hass)

    if fog_risk in FOG_RISK_LEVELS:
        return FOG_RISK_LEVELS[fog_risk][lang_index]

    # Fallback to none
    return FOG_RISK_LEVELS.get("none", ("Kein Nebel", "No fog", "Χωρίς ομίχλη", "Nessuna nebbia", "Žiadna hmla"))[lang_index]


def get_atmosphere_stability_text(hass: HomeAssistant, stability: str) -> str:
    """Get atmosphere stability text in user's language.

    Args:
        hass: Home Assistant instance
        stability: Stability level (stable, moderate, unstable, very_unstable, unknown)

    Returns:
        Stability text in user's language
    """
    lang_index = get_language_index(hass)

    if stability in ATMOSPHERE_STABILITY:
        return ATMOSPHERE_STABILITY[stability][lang_index]

    # Fallback to unknown
    return ATMOSPHERE_STABILITY.get("unknown", ("Unbekannt", "Unknown", "Άγνωστο", "Sconosciuto", "Neznáma"))[lang_index]


def get_adjustment_text(hass: HomeAssistant, adjustment_key: str, value: str) -> str:
    """Get adjustment detail text in user's language with unit conversion.

    Args:
        hass: Home Assistant instance
        adjustment_key: Adjustment type key (high_humidity, critical_fog_risk, etc.)
        value: Value to insert into template (formatted number as string)

    Returns:
        Adjustment text in user's language with value converted to user's unit system
    """
    lang_index = get_language_index(hass)

    if adjustment_key not in ADJUSTMENT_TEMPLATES:
        # Fallback to English-style format
        return f"{adjustment_key}: {value}"

    # Parse the numeric value
    try:
        numeric_value = float(value)
    except ValueError:
        # If can't parse, use as-is
        template = ADJUSTMENT_TEMPLATES[adjustment_key][lang_index]
        return template.replace("{value}", value)

    # Get user's temperature unit preference
    user_temp_unit = hass.config.units.temperature_unit if hass and hass.config else "°C"

    # Convert temperature SPREAD values (dewpoint spread)
    # Note: For temperature DIFFERENCES, we only scale (× 1.8), NOT add offset (+32)
    if adjustment_key in ["critical_fog_risk", "high_fog_risk", "medium_fog_risk"]:
        # Value is dewpoint spread in °C
        template = ADJUSTMENT_TEMPLATES[adjustment_key][lang_index]

        if user_temp_unit in ("°F", "F"):
            # Convert °C spread to °F spread (scale only, no offset)
            converted_value = numeric_value * 1.8
            formatted_value = f"{converted_value:.1f}°F"
            # Replace °C with °F in template
            template = template.replace("°C", "°F")
        elif user_temp_unit == "K":
            # Kelvin spread same as Celsius spread (same scale)
            formatted_value = f"{numeric_value:.1f} K"
            template = template.replace("°C", "K")
        else:
            # Metric system - use original value
            formatted_value = value
    else:
        # For humidity and gust_ratio, no conversion needed
        formatted_value = value
        template = ADJUSTMENT_TEMPLATES[adjustment_key][lang_index]

    return template.replace("{value}", formatted_value)


