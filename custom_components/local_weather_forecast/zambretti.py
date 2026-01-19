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
    _LOGGER.debug(
        f"Zambretti: Input - p0={p0:.1f} hPa, pressure_change={pressure_change:.2f} hPa, "
        f"wind_data={wind_data}, lang_index={lang_index}"
    )

    # Determine pressure trend
    if pressure_change <= -1.0:
        trend = -1  # Falling
    elif pressure_change >= 1.0:
        trend = 1  # Rising
    else:
        trend = 0  # Steady

    _LOGGER.debug(
        f"Zambretti: Pressure trend={'FALLING' if trend == -1 else 'RISING' if trend == 1 else 'STEADY'} "
        f"(change={pressure_change:.2f} hPa)"
    )

    # Get current month for season adjustment
    current_month = datetime.now().month
    is_summer = 2 < current_month < 11

    _LOGGER.debug(f"Zambretti: Month={current_month}, is_summer={is_summer}")

    # Calculate Zambretti number based on trend
    z_before_wind = 0
    if trend == -1:  # Falling pressure
        z_before_wind = round(127 - 0.12 * p0)
        _LOGGER.debug(f"Zambretti: FALLING formula: z = round(127 - 0.12 * {p0:.1f}) = {z_before_wind}")
    elif trend == 0:  # Steady pressure
        z_before_wind = round(144 - 0.13 * p0)
        _LOGGER.debug(f"Zambretti: STEADY formula: z = round(144 - 0.13 * {p0:.1f}) = {z_before_wind}")

        # Special handling for very low pressure (<970 hPa) with steady trend
        # Very low steady pressure = stormy conditions, should not give high z-numbers
        # Clamp to maximum z=12 to ensure unsettled forecast
        if p0 < 970 and z_before_wind > 12:
            _LOGGER.debug(
                f"Zambretti: Very low pressure ({p0:.1f} hPa < 970) with steady trend, "
                f"clamping z from {z_before_wind} to 12 (stormy conditions)"
            )
            z_before_wind = 12

        # Season adjustment
        # Winter adjustment only for moderate pressure (975-1025 hPa)
        # High stable pressure (>1025) in winter = fine weather, not unsettled
        # Very low pressure (<975) = stormy even in winter, no adjustment needed
        if not is_summer and 975 <= p0 <= 1025:
            z_before_wind = z_before_wind - 1  # Winter
            _LOGGER.debug(f"Zambretti: Winter adjustment: z = {z_before_wind} (steady winter -1)")
        elif not is_summer and p0 > 1025:
            _LOGGER.debug(f"Zambretti: Skipping winter adjustment for high pressure ({p0:.1f} hPa > 1025)")
        elif not is_summer and p0 < 975:
            _LOGGER.debug(f"Zambretti: Skipping winter adjustment for very low pressure ({p0:.1f} hPa < 975, stormy conditions)")
    else:  # Rising pressure (trend == 1)
        z_before_wind = round(185 - 0.16 * p0)
        _LOGGER.debug(f"Zambretti: RISING formula: z = round(185 - 0.16 * {p0:.1f}) = {z_before_wind}")
        # Season adjustment
        # Summer adjustment only for moderate pressure (975-1025 hPa)
        # Very low pressure (<975) = storm recovery, no adjustment needed
        # Very high pressure (>1025) = already optimistic, no adjustment needed
        if is_summer and 975 <= p0 <= 1025:
            z_before_wind = z_before_wind + 1  # Summer
            _LOGGER.debug(f"Zambretti: Summer adjustment: z = {z_before_wind} (rising summer +1)")
        elif is_summer and p0 < 975:
            _LOGGER.debug(f"Zambretti: Skipping summer adjustment for very low pressure ({p0:.1f} hPa < 975, storm recovery)")
        elif is_summer and p0 > 1025:
            _LOGGER.debug(f"Zambretti: Skipping summer adjustment for high pressure ({p0:.1f} hPa > 1025)")

    # Apply wind correction
    wind_fak = wind_data[0]
    wind_speed_fak = wind_data[3]
    wind_correction = wind_fak * wind_speed_fak
    z = z_before_wind + wind_correction

    _LOGGER.debug(
        f"Zambretti: Wind correction: wind_fak={wind_fak}, speed_fak={wind_speed_fak}, "
        f"correction={wind_correction} → z_final={z}"
    )

    # Handle extreme z-numbers with intelligent mapping
    # IMPORTANT: Clamp z BEFORE calling mapping functions to avoid "Unmapped" warnings
    z_original = z
    extreme_condition = None

    if z < 1.0:
        # Extreme high pressure with falling trend
        # This indicates breakdown of anticyclone → weather deteriorating
        _LOGGER.debug(
            f"Zambretti: EXTREME condition - Very high pressure falling rapidly "
            f"(z={z:.1f}, pressure={p0:.1f} hPa, change={pressure_change:.2f} hPa)"
        )
        extreme_condition = "high_pressure_falling"
        # Map to "Fine, Becoming Less Settled" (forecast_type=3, letter=D)
        z = 3
        _LOGGER.debug(f"Zambretti: Mapping extreme case z={z_original:.1f} → z=3 (Fine, Becoming Less Settled)")

    elif z > 33.0:
        # Extreme low pressure with rising trend
        # This indicates recovery from storm → weather improving
        _LOGGER.debug(
            f"Zambretti: EXTREME condition - Very low pressure rising rapidly "
            f"(z={z:.1f}, pressure={p0:.1f} hPa, change={pressure_change:.2f} hPa)"
        )
        extreme_condition = "low_pressure_rising"
        # Keep at z=33 (Stormy, Much Rain) - still dangerous
        z = 33
        _LOGGER.debug(f"Zambretti: Clamping extreme case z={z_original:.1f} → z=33 (Stormy, Much Rain)")

    # Convert to int for mapping (now guaranteed to be in range 1-33)
    z = int(round(z))

    # Now z is guaranteed to be in range 1-33, safe to map
    forecast_type = _map_zambretti_to_forecast(z)
    letter_code = _map_zambretti_to_letter(z)

    if forecast_type is not None:
        forecast_text = FORECAST_TEXTS[forecast_type][lang_index]

        # Add note for extreme conditions
        if extreme_condition:
            _LOGGER.debug(
                f"Zambretti: RESULT (EXTREME) - z={z} (original={z_original:.1f}), "
                f"condition={extreme_condition}, forecast_number={forecast_type}, "
                f"letter_code={letter_code}, text='{forecast_text}'"
            )
        else:
            _LOGGER.debug(
                f"Zambretti: RESULT - z={z}, forecast_number={forecast_type}, "
                f"letter_code={letter_code}, text='{forecast_text}'"
            )
    else:
        forecast_text = "Unknown"
        forecast_type = 0
        _LOGGER.warning(f"Zambretti: Failed to map z={z} to forecast, using Unknown")

    return [forecast_text, forecast_type, letter_code]


def _map_zambretti_to_forecast(z: int) -> int | None:
    """Map Zambretti number to forecast index.

    Args:
        z: Zambretti number (1-33, clamped by caller)

    Returns:
        Forecast index or None if unmapped
    """
    # Defensive clamping - should already be done by caller, but extra safety
    if z < 1:
        _LOGGER.warning(f"Zambretti: z={z} < 1, clamping to 1")
        z = 1
    elif z > 33:
        _LOGGER.warning(f"Zambretti: z={z} > 33, clamping to 33")
        z = 33

    _LOGGER.debug(f"Zambretti: Mapping z-number={z}")
    mapping = {
        1: 0, 10: 0, 20: 0,
        2: 1, 11: 1, 21: 1,
        3: 3,
        4: 7,
        5: 14,
        6: 17,
        7: 20,
        8: 21,
        9: 5, 18: 23,  # FIXED: z=9 (high pressure + steady) should be Fairly Fine (F=5), not Very Unsettled (X=23)!
        12: 4,
        13: 10,
        14: 13,
        15: 15,
        16: 18,
        17: 22,
        19: 1,  # FIXED: High pressure (~1040 hPa) + rising trend = Fine weather, not stormy!
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
        32: 25, 33: 25,  # z=32-33 is extreme rising pressure (recovery from storm)
    }
    result = mapping.get(z)
    if result is None:
        # This should never happen after clamping with valid input
        _LOGGER.error(
            f"Zambretti: UNMAPPED z-number {z} - invalid input! "
            f"Valid range is 1-31."
        )
        return None  # Return None for invalid input

    _LOGGER.debug(f"Zambretti: Mapped z={z} → forecast_index={result}")
    return result


def _map_zambretti_to_letter(z: int) -> str:
    """Map Zambretti number to letter code.

    Args:
        z: Zambretti number (1-33, clamped by caller)

    Returns:
        Letter code (A-Z) representing weather forecast
    """
    # Defensive clamping - should already be done by caller, but extra safety
    if z < 1:
        _LOGGER.warning(f"Zambretti: z={z} < 1, clamping to 1 for letter mapping")
        z = 1
    elif z > 33:
        _LOGGER.warning(f"Zambretti: z={z} > 33, clamping to 33 for letter mapping")
        z = 33

    mapping = {
        1: "A", 10: "A", 20: "A",
        2: "B", 11: "B", 21: "B",
        3: "D",
        4: "H",
        5: "O",
        6: "R",
        7: "U",
        8: "V",
        9: "F", 18: "X",  # FIXED: z=9 (high pressure + steady) should be F (Fairly Fine), not X (Very Unsettled)!
        12: "E",
        13: "K",
        14: "N",
        15: "P",
        16: "S",
        17: "W",
        19: "B",  # FIXED: High pressure (~1040 hPa) + rising trend = Fine weather (B), not stormy (Z)!
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
        32: "Z", 33: "Z",  # z=32-33 is extreme rising pressure (recovery from storm)
    }
    result = mapping.get(z, "A")
    if z not in mapping:
        # This should never happen after clamping
        _LOGGER.debug(f"Zambretti: Using default letter 'A' for z={z}")
    else:
        _LOGGER.debug(f"Zambretti: Mapped z={z} → letter '{result}'")
    return result
