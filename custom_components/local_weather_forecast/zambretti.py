"""Zambretti forecast algorithm."""
from datetime import datetime
import logging

from .forecast_data import FORECAST_TEXTS

_LOGGER = logging.getLogger(__name__)


def calculate_zambretti_forecast(
    p0: float,
    pressure_change: float,
    wind_data: list,
    lang_index: int,
) -> list:
    """
    Calculate Zambretti forecast.

    Args:
        p0: Sea level pressure in hPa
        pressure_change: Pressure change over 3 hours in hPa
        wind_data: [wind_fak, direction, dir_text, speed_fak]
        lang_index: Language index (0-3)

    Returns:
        [forecast_text, forecast_number, letter_code]
    """
    # Determine pressure trend
    if pressure_change <= -1.0:
        trend = -1  # Falling
    elif pressure_change >= 1.0:
        trend = 1  # Rising
    else:
        trend = 0  # Steady

    # Get current month for season adjustment
    current_month = datetime.now().month
    is_summer = 2 < current_month < 11

    # Calculate Zambretti number based on trend
    if trend == -1:  # Falling pressure
        z = round(127 - 0.12 * p0)
    elif trend == 0:  # Steady pressure
        z = round(144 - 0.13 * p0)
        # Season adjustment
        if not is_summer:
            z = z - 1  # Winter
    else:  # Rising pressure (trend == 1)
        z = round(185 - 0.16 * p0)
        # Season adjustment
        if is_summer:
            z = z + 1  # Summer

    # Apply wind correction
    wind_fak = wind_data[0]
    wind_speed_fak = wind_data[3]
    z = z + (wind_fak * wind_speed_fak)

    # Map Zambretti number to forecast index
    forecast_type = _map_zambretti_to_forecast(z)
    letter_code = _map_zambretti_to_letter(z)

    if forecast_type is not None:
        forecast_text = FORECAST_TEXTS[forecast_type][lang_index]
    else:
        forecast_text = "Unknown"
        forecast_type = 0

    return [forecast_text, forecast_type, letter_code]


def _map_zambretti_to_forecast(z: int) -> int | None:
    """Map Zambretti number to forecast index."""
    _LOGGER.debug(f"Zambretti z-number: {z}")
    mapping = {
        1: 0, 10: 0, 20: 0,
        2: 1, 11: 1, 21: 1,
        3: 3,
        4: 7,
        5: 14,
        6: 17,
        7: 20,
        8: 21,
        9: 23, 18: 23,
        12: 4,
        13: 10,
        14: 13,
        15: 15,
        16: 18,
        17: 22,
        19: 25, 32: 25,
        22: 5,  # FIXED: Missing z=22 mapping - Settling fair
        23: 5,
        24: 6,
        25: 8,
        26: 9,
        27: 11,
        28: 12,
        29: 16,
        30: 19,
        31: 24,
    }
    result = mapping.get(z)
    if result is None:
        _LOGGER.warning(f"Unmapped Zambretti number: {z} - returning None")
    return result


def _map_zambretti_to_letter(z: int) -> str:
    """Map Zambretti number to letter code."""
    mapping = {
        1: "A", 10: "A", 20: "A",
        2: "B", 11: "B", 21: "B",
        3: "D",
        4: "H",
        5: "O",
        6: "R",
        7: "U",
        8: "V",
        9: "X", 18: "X",
        12: "E",
        13: "K",
        14: "N",
        15: "P",
        16: "S",
        17: "W",
        19: "Z", 32: "Z",
        22: "F",  # FIXED: Missing z=22 letter mapping
        23: "F",
        24: "G",
        25: "I",
        26: "J",
        27: "L",
        28: "M",
        29: "Q",
        30: "T",
        31: "Y",
    }
    return mapping.get(z, "A")
