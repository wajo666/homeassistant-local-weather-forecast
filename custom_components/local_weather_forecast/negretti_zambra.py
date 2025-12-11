"""Negretti & Zambra forecast algorithm."""
from datetime import datetime
import logging

from .forecast_data import FORECAST_TEXTS

_LOGGER = logging.getLogger(__name__)


def calculate_negretti_zambra_forecast(
    p0: float,
    pressure_change: float,
    wind_data: list,
    lang_index: int,
    elevation: float,
) -> list:
    """
    Calculate Negretti & Zambra 'slide rule' forecast.

    Args:
        p0: Sea level pressure in hPa
        pressure_change: Pressure change over 3 hours in hPa
        wind_data: [wind_fak, direction, dir_text, speed_fak]
        lang_index: Language index (0-3)
        elevation: Elevation in meters

    Returns:
        [forecast_text, forecast_number, letter_code]
    """
    _LOGGER.debug(
        f"Negretti: Input - p0={p0:.1f} hPa, pressure_change={pressure_change:.2f} hPa, "
        f"wind_data={wind_data}, elevation={elevation}m"
    )

    # Configuration
    hemisphere = 1  # Northern = 1, Southern = 0
    bar_top = 1050
    bar_bottom = 950

    # Lookup tables for different trends
    rise_opt = [25, 25, 25, 24, 24, 19, 16, 12, 11, 9, 8, 6, 5, 2, 1, 1, 0, 0, 0, 0, 0, 0]
    steady_opt = [25, 25, 25, 25, 25, 25, 23, 23, 22, 18, 15, 13, 10, 4, 1, 1, 0, 0, 0, 0, 0, 0]
    fall_opt = [25, 25, 25, 25, 25, 25, 25, 25, 23, 23, 21, 20, 17, 14, 7, 3, 1, 1, 1, 0, 0, 0]

    exceptional_text = [
        "außergewöhnliches Wetter, ",
        "Exceptional Weather, ",
        "εξαιρετικός καιρός, ",
        "Tempo eccezionale, "
    ]

    # Calculate constants
    bar_range = bar_top - bar_bottom
    constant = bar_range / 22

    # Determine season and trend
    current_month = datetime.now().month
    is_summer = 2 < current_month < 11

    if pressure_change <= -1.6:
        trend = -1
    elif pressure_change >= 1.6:
        trend = 1
    else:
        trend = 0

    _LOGGER.debug(
        f"Negretti: month={current_month}, is_summer={is_summer}, "
        f"trend={'RISING' if trend == 1 else 'FALLING' if trend == -1 else 'STEADY'}"
    )

    # Adjusted pressure for Northern Hemisphere
    z_hp = p0
    direction = wind_data[1]
    wind_speed_fak = wind_data[3]

    _LOGGER.debug(f"Negretti: wind direction={direction}°, wind_speed_fak={wind_speed_fak}")
    _LOGGER.debug(f"Negretti: Initial z_hp={z_hp:.1f} hPa (before wind adjustments)")

    if hemisphere == 1 and wind_speed_fak == 1:
        # Wind direction adjustments for Northern Hemisphere
        if 11.25 < direction <= 33.75:  # NNE
            z_hp = z_hp + 5 / 100 * bar_range
        elif 33.75 < direction <= 56.25:  # NE
            z_hp = z_hp + 4.6 / 100 * bar_range
        elif 56.25 < direction <= 78.75:  # ENE
            z_hp = z_hp + 2 / 100 * bar_range
        elif 78.75 < direction <= 101.25:  # E
            z_hp = z_hp - 0.5 / 100 * bar_range
        elif 101.25 < direction <= 123.75:  # ESE
            z_hp = z_hp - 5 / 100 * bar_range
        elif 123.75 < direction <= 146.25:  # SE
            z_hp = z_hp - 5 / 100 * bar_range
        elif 146.25 < direction <= 168.75:  # SSE
            z_hp = z_hp - 8.5 / 100 * bar_range
        elif 168.75 < direction <= 191.25:  # S
            z_hp = z_hp - 11.5 / 100 * bar_range
        elif 191.25 < direction <= 213.75:  # SSW
            z_hp = z_hp - 10 / 100 * bar_range
        elif 213.75 < direction <= 236.25:  # SW
            z_hp = z_hp - 6 / 100 * bar_range
        elif 236.25 < direction <= 258.75:  # WSW
            z_hp = z_hp - 4.5 / 100 * bar_range
        elif 258.75 < direction <= 281.25:  # W
            z_hp = z_hp - 3 / 100 * bar_range
        elif 281.25 < direction <= 303.75:  # WNW
            z_hp = z_hp - 0.5 / 100 * bar_range
        elif 303.75 < direction <= 326.25:  # NW
            z_hp = z_hp + 1.5 / 100 * bar_range
        elif 326.25 < direction <= 348.75:  # NNW
            z_hp = z_hp + 3 / 100 * bar_range
        elif direction > 348.75 or direction <= 11.25:  # N
            z_hp = z_hp + 6 / 100 * bar_range

        _LOGGER.debug(f"Negretti: z_hp after wind direction adjustment={z_hp:.1f} hPa")
    else:
        _LOGGER.debug(f"Negretti: No wind direction adjustment applied (hemisphere={hemisphere}, wind_speed_fak={wind_speed_fak})")

    # Summer adjustment for rising/falling trends
    if is_summer:
        if trend == 1:
            adjustment = 7 / 100 * bar_range
            z_hp = z_hp + adjustment
            _LOGGER.debug(f"Negretti: Summer RISING adjustment: +{adjustment:.1f} hPa → z_hp={z_hp:.1f} hPa")
        elif trend == -1:
            adjustment = 7 / 100 * bar_range
            z_hp = z_hp - adjustment
            _LOGGER.debug(f"Negretti: Summer FALLING adjustment: -{adjustment:.1f} hPa → z_hp={z_hp:.1f} hPa")
    else:
        _LOGGER.debug(f"Negretti: No summer adjustment (winter month)")

    # Ensure within bounds
    if z_hp >= bar_top:
        _LOGGER.debug(f"Negretti: Pressure {z_hp:.1f} hPa exceeds bar_top {bar_top}, clamping to {bar_top - 1}")
        z_hp = bar_top - 1

    if z_hp < bar_bottom:
        _LOGGER.debug(f"Negretti: Pressure {z_hp:.1f} hPa below bar_bottom {bar_bottom}, clamping to {bar_bottom}")
        z_hp = bar_bottom

    # Calculate option index
    z_option = int((z_hp - bar_bottom) / constant)

    _LOGGER.debug(f"Negretti: z_hp after adjustments={z_hp:.1f} hPa, z_option={z_option}")

    # Check for exceptional weather
    is_exceptional = False
    if z_option < 0:
        _LOGGER.warning(f"Negretti: EXCEPTIONAL weather detected - z_option={z_option} < 0, clamping to 0")
        z_option = 0
        is_exceptional = True
    elif z_option > 21:
        _LOGGER.warning(f"Negretti: EXCEPTIONAL weather detected - z_option={z_option} > 21, clamping to 21")
        z_option = 21
        is_exceptional = True

    # Select forecast based on trend
    if trend == 1:  # Rising
        forecast_idx = rise_opt[z_option]
        _LOGGER.debug(f"Negretti: Using RISING lookup table: z_option={z_option} → forecast_idx={forecast_idx}")
    elif trend == -1:  # Falling
        forecast_idx = fall_opt[z_option]
        _LOGGER.debug(f"Negretti: Using FALLING lookup table: z_option={z_option} → forecast_idx={forecast_idx}")
    else:  # Steady
        forecast_idx = steady_opt[z_option]
        _LOGGER.debug(f"Negretti: Using STEADY lookup table: z_option={z_option} → forecast_idx={forecast_idx}")

    _LOGGER.debug(
        f"Negretti: forecast_idx={forecast_idx}, is_exceptional={is_exceptional}, "
        f"z_option={z_option}"
    )

    # Build forecast text
    forecast_text = ""
    if is_exceptional:
        forecast_text = exceptional_text[lang_index]

    forecast_text += FORECAST_TEXTS[forecast_idx][lang_index]
    letter_code = _map_zambretti_to_letter(forecast_idx + 1)

    _LOGGER.info(
        f"Negretti: RESULT - forecast_number={forecast_idx}, letter_code={letter_code}, "
        f"text='{forecast_text}'"
    )

    return [forecast_text, forecast_idx, letter_code]


def _map_zambretti_to_letter(z: int) -> str:
    """Map Zambretti number to letter code.

    Args:
        z: Zambretti number (1-33)

    Returns:
        Letter code (A-Z) representing weather forecast
    """
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
        19: "Z", 32: "Z", 33: "Z",  # z=33 is extreme rising pressure
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
    result = mapping.get(z, "A")
    if z not in mapping:
        _LOGGER.debug(f"Negretti: Unknown Zambretti number {z}, using fallback letter 'A'")
    else:
        _LOGGER.debug(f"Negretti: Mapped Zambretti number {z} → letter '{result}'")
    return result

