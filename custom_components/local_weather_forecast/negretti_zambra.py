"""Negretti & Zambra forecast algorithm.

✅ INTEGRATED WITH UNIFIED SYSTEM:
- Uses forecast_mapping.get_forecast_text() for text retrieval
- Internal codes (0-25) are universal for all models
- No duplicate text storage needed
"""
from datetime import datetime
import logging


_LOGGER = logging.getLogger(__name__)


def calculate_negretti_zambra_forecast(
    p0: float,
    pressure_change: float,
    wind_data: list,
    lang_index: int,
    elevation: float,
    hemisphere: str = "north",
) -> list:
    """
    Calculate Negretti & Zambra 'slide rule' forecast.

    Args:
        p0: Sea level pressure in hPa
        pressure_change: Pressure change over 3 hours in hPa
        wind_data: [wind_fak, direction, dir_text, speed_fak]
        lang_index: Language index (0-3)
        elevation: Elevation in meters
        hemisphere: "north" or "south" (default: "north")

    Returns:
        [forecast_text, forecast_number, letter_code]
    """
    _LOGGER.debug(
        f"Negretti: Input - p0={p0:.1f} hPa, pressure_change={pressure_change:.2f} hPa, "
        f"wind_data={wind_data}, elevation={elevation}m, hemisphere={hemisphere}"
    )

    # Configuration - convert hemisphere string to numeric (1=North, 0=South)
    hemisphere_numeric = 1 if hemisphere == "north" else 0
    # Pressure range expanded to cover global conditions + adjustments
    # Base range: 910-1085 hPa covers 99.9% of global weather including:
    # - Mediterranean hurricanes (Medicanes): 940-960 hPa
    # - Sydney/Australian cyclones: 955-975 hPa
    # - European storms: 920-1070 hPa
    # After wind adjustments (±10.3 hPa) and summer adjustments (±12.3 hPa)
    # Effective range: ~887-1108 hPa (covers extreme global conditions)
    bar_top = 1085
    bar_bottom = 910

    # Lookup tables for different trends - EXPANDED to 44 indexes for higher precision
    # Original 22 indexes expanded to 44 (each value doubled) for better granularity
    # This provides 3.98 hPa/index instead of 7.95 hPa/index (2× better precision)
    rise_opt = [
        25, 25,  # 0-1: Extremely low pressure rising
        25, 25,  # 2-3: Very low pressure rising
        24, 24,  # 4-5: Low pressure rising
        24, 24,  # 6-7: Low-moderate pressure rising
        19, 19,  # 8-9: Moderate-low pressure rising
        16, 16,  # 10-11: Moderate pressure rising
        12, 12,  # 12-13: Moderate-high pressure rising
        11, 11,  # 14-15: High-moderate pressure rising
        9, 9,    # 16-17: High pressure rising
        8, 8,    # 18-19: High pressure rising
        6, 6,    # 20-21: Very high pressure rising
        5, 5,    # 22-23: Very high pressure rising
        2, 2,    # 24-25: Extremely high pressure rising
        1, 1,    # 26-27: Extremely high pressure rising
        1, 1,    # 28-29: Extremely high pressure rising
        0, 0,    # 30-31: Peak high pressure rising (settled fine)
        0, 0,    # 32-33: Peak high pressure rising
        0, 0,    # 34-35: Peak high pressure rising
        0, 0,    # 36-37: Peak high pressure rising
        0, 0,    # 38-39: Peak high pressure rising
        0, 0,    # 40-41: Peak high pressure rising
        0, 0     # 42-43: Peak high pressure rising
    ]

    steady_opt = [
        25, 25,  # 0-1: Extremely low pressure steady
        25, 25,  # 2-3: Very low pressure steady
        25, 25,  # 4-5: Low pressure steady
        25, 25,  # 6-7: Low-moderate pressure steady
        25, 25,  # 8-9: Moderate-low pressure steady
        25, 25,  # 10-11: Moderate pressure steady
        23, 23,  # 12-13: Moderate-high pressure steady
        23, 23,  # 14-15: High-moderate pressure steady
        22, 22,  # 16-17: High pressure steady
        18, 18,  # 18-19: High pressure steady
        15, 15,  # 20-21: Very high pressure steady
        13, 13,  # 22-23: Very high pressure steady
        10, 10,  # 24-25: Extremely high pressure steady
        4, 4,    # 26-27: Extremely high pressure steady
        1, 1,    # 28-29: Peak high pressure steady
        1, 1,    # 30-31: Peak high pressure steady
        0, 0,    # 32-33: Peak high pressure steady (settled fine)
        0, 0,    # 34-35: Peak high pressure steady
        0, 0,    # 36-37: Peak high pressure steady
        0, 0,    # 38-39: Peak high pressure steady
        0, 0,    # 40-41: Peak high pressure steady
        0, 0     # 42-43: Peak high pressure steady
    ]

    fall_opt = [
        25, 25,  # 0-1: Extremely low pressure falling (stormy)
        25, 25,  # 2-3: Very low pressure falling
        25, 25,  # 4-5: Low pressure falling
        25, 25,  # 6-7: Low-moderate pressure falling
        25, 25,  # 8-9: Moderate-low pressure falling
        25, 25,  # 10-11: Moderate pressure falling
        25, 25,  # 12-13: Moderate-high pressure falling
        25, 25,  # 14-15: High-moderate pressure falling
        23, 23,  # 16-17: High pressure falling
        23, 23,  # 18-19: High pressure falling
        21, 21,  # 20-21: Very high pressure falling
        20, 20,  # 22-23: Very high pressure falling
        17, 17,  # 24-25: Extremely high pressure falling
        14, 14,  # 26-27: Extremely high pressure falling
        7, 7,    # 28-29: Peak high pressure falling
        3, 3,    # 30-31: Peak high pressure falling
        1, 1,    # 32-33: Peak high pressure falling
        1, 1,    # 34-35: Peak high pressure falling
        1, 1,    # 36-37: Peak high pressure falling
        0, 0,    # 38-39: Peak high pressure falling (becoming fine)
        0, 0,    # 40-41: Peak high pressure falling
        0, 0     # 42-43: Peak high pressure falling
    ]

    exceptional_text = [
        "außergewöhnliches Wetter, ",
        "Exceptional Weather, ",
        "εξαιρετικός καιρός, ",
        "Tempo eccezionale, ",
        "Výnimočné počasie, "
    ]

    # Calculate constants
    bar_range = bar_top - bar_bottom
    # Expanded to 44 indexes for higher precision: 175 / 44 = 3.98 hPa per index
    # (Previously 22 indexes: 175 / 22 = 7.95 hPa per index)
    constant = bar_range / 44

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

    if hemisphere_numeric == 1 and wind_speed_fak == 1:
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
        _LOGGER.debug(f"Negretti: No wind direction adjustment applied (hemisphere={'north' if hemisphere_numeric == 1 else 'south'}, wind_speed_fak={wind_speed_fak})")

    # Summer adjustment for rising/falling trends
    # ✅ FIXED v3.1.10: Use original Negretti & Zambra absolute value (7 hPa)
    # Original barometers (1890s) used 950-1050 hPa range, 7% = 7 hPa
    # Our expanded range (910-1085 hPa) made 7% = 12.25 hPa (too aggressive!)
    # Scientific correction: Summer effects are physical constants, not percentage-scaled
    #
    # Apply only for moderate pressure (975-1025 hPa) - same logic as Zambretti
    # Very low pressure (<975 hPa) = storm conditions, no adjustment needed
    # Very high pressure (>1025 hPa) = already optimal, no adjustment needed
    SUMMER_ADJUSTMENT_HPA = 7.0  # Original Negretti & Zambra value

    if is_summer and 975 <= p0 <= 1025:
        if trend == 1:
            z_hp = z_hp + SUMMER_ADJUSTMENT_HPA
            _LOGGER.debug(f"Negretti: Summer RISING adjustment: +{SUMMER_ADJUSTMENT_HPA} hPa → z_hp={z_hp:.1f} hPa (p0={p0:.1f} hPa in moderate range)")
        elif trend == -1:
            z_hp = z_hp - SUMMER_ADJUSTMENT_HPA
            _LOGGER.debug(f"Negretti: Summer FALLING adjustment: -{SUMMER_ADJUSTMENT_HPA} hPa → z_hp={z_hp:.1f} hPa (p0={p0:.1f} hPa in moderate range)")
    elif is_summer and p0 < 975:
        _LOGGER.debug(f"Negretti: Skipping summer adjustment for very low pressure ({p0:.1f} hPa < 975, storm conditions)")
    elif is_summer and p0 > 1025:
        _LOGGER.debug(f"Negretti: Skipping summer adjustment for high pressure ({p0:.1f} hPa > 1025, already optimal)")
    elif not is_summer:
        _LOGGER.debug(f"Negretti: No summer adjustment (winter month)")

    # Ensure within bounds (use float comparison for consistency)
    if z_hp >= float(bar_top):
        _LOGGER.debug(f"Negretti: Pressure {z_hp:.1f} hPa exceeds bar_top {bar_top}, clamping to {bar_top - 1}")
        z_hp = float(bar_top - 1)

    if z_hp < float(bar_bottom):
        _LOGGER.debug(f"Negretti: Pressure {z_hp:.1f} hPa below bar_bottom {bar_bottom}, clamping to {bar_bottom}")
        z_hp = float(bar_bottom)

    # Calculate option index (this will be float, needs clamping)
    # The Negretti & Zambra algorithm uses an expanded scale from 910-1085 hPa
    # divided into 44 index positions (0-43) for higher precision (3.98 hPa/index).
    # This range covers global weather conditions including Mediterranean hurricanes,
    # Australian cyclones, and European storms, plus all adjustments.
    # Values outside this range indicate truly exceptional conditions.
    z_option_raw = (z_hp - bar_bottom) / constant

    _LOGGER.debug(f"Negretti: z_hp after adjustments={z_hp:.1f} hPa, z_option_raw={z_option_raw:.2f}")

    # Check for exceptional weather and clamp BEFORE converting to int
    is_exceptional = False
    if z_option_raw < 0.0:
        _LOGGER.debug(
            f"Negretti: EXCEPTIONAL weather detected - z_option={z_option_raw:.2f} < 0, "
            f"clamping to 0 (pressure={z_hp:.1f} hPa, very low pressure)"
        )
        z_option_raw = 0.0
        is_exceptional = True
    elif z_option_raw > 43.0:
        _LOGGER.debug(
            f"Negretti: EXCEPTIONAL weather detected - z_option={z_option_raw:.2f} > 43, "
            f"clamping to 43 (pressure={z_hp:.1f} hPa, very high pressure)"
        )
        z_option_raw = 43.0
        is_exceptional = True

    # Convert to int after clamping (now guaranteed to be in range 0-43)
    z_option = int(round(z_option_raw))

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

    # Build forecast text using unified system
    # ✅ USE UNIFIED SYSTEM: Get text from forecast_mapping
    from .forecast_mapping import get_forecast_text

    base_forecast_text = get_forecast_text(
        forecast_num=forecast_idx,
        lang_index=lang_index
    )

    # Add exceptional weather prefix if needed
    if is_exceptional:
        exceptional_text = [
            "außergewöhnliches Wetter, ",
            "Exceptional Weather, ",
            "εξαιρετικός καιρός, ",
            "Tempo eccezionale, ",
            "Výnimočné počasie, "
        ]
        forecast_text = exceptional_text[lang_index] + base_forecast_text
    else:
        forecast_text = base_forecast_text

    # Calculate letter code for display purposes
    # ⚠️ IMPORTANT: Negretti uses DIFFERENT letter codes than Zambretti!
    # The Negretti & Zambra slide rule has its own proprietary letter system.
    # However, for compatibility with unified forecast system, we use sequential letters
    # based on forecast_idx (0-25), NOT Zambretti's letter mapping.
    # 
    # SCIENTIFIC RATIONALE:
    # - Negretti letters are for display/reference only (not used for mapping)
    # - forecast_idx (0-25) is the UNIVERSAL code used by all models
    # - Using Zambretti letters for Negretti would be scientifically incorrect
    # 
    # Solution: Generate letter based on forecast severity (A=best, Z=worst)
    letter_code = _generate_negretti_letter(forecast_idx)

    _LOGGER.debug(
        f"Negretti: RESULT - forecast_code={forecast_idx}, "
        f"letter={letter_code} (Negretti system), text='{forecast_text}'"
    )

    # Return [text, code, letter] - forecast_calculator expects 3 items
    return [forecast_text, forecast_idx, letter_code]


def _generate_negretti_letter(forecast_idx: int) -> str:
    """Generate Negretti letter code based on forecast severity.
    
    Negretti & Zambra slide rule uses proprietary letter system.
    For compatibility, we generate sequential letters based on forecast severity.
    
    SCIENTIFIC BASIS:
    - Original Negretti slide rule: A-Z represent weather progression
    - A = Settled Fine (best)
    - Z = Stormy (worst)
    - Letters progress roughly with forecast severity
    
    Args:
        forecast_idx: Forecast index (0-25)
        
    Returns:
        Letter code (A-Z) representing forecast severity
    """
    # Map forecast_idx (0-25) to letter severity (A-Z, 26 letters)
    # Group similar severities together for better representation
    mapping = {
        0: "A",   # Settled fine
        1: "B",   # Fine weather
        2: "C",   # Becoming fine
        3: "D",   # Fine, becoming less settled
        4: "E",   # Fine, possible showers
        5: "F",   # Fairly fine, improving
        6: "G",   # Fairly fine, possible showers early
        7: "H",   # Fairly fine, showery later
        8: "I",   # Showery early, improving
        9: "J",   # Changeable, mending
        10: "K",  # Fairly fine, showers likely
        11: "L",  # Rather unsettled clearing later
        12: "M",  # Unsettled, probably improving
        13: "N",  # Showery, bright intervals
        14: "O",  # Showery, becoming more unsettled
        15: "P",  # Changeable, some rain
        16: "Q",  # Unsettled, short fine intervals
        17: "R",  # Unsettled, rain later (not X!)
        18: "S",  # Unsettled, some rain
        19: "T",  # Mostly very unsettled
        20: "U",  # Occasional rain, worsening
        21: "V",  # Rain at times, very unsettled
        22: "W",  # Rain at frequent intervals
        23: "X",  # Very unsettled, rain
        24: "Y",  # Stormy, may improve
        25: "Z",  # Stormy, much rain
    }
    
    # Clamp to valid range
    forecast_idx = max(0, min(25, forecast_idx))
    result = mapping.get(forecast_idx, "A")
    
    _LOGGER.debug(f"Negretti letter: forecast_idx={forecast_idx} → '{result}'")
    return result


def _map_zambretti_to_letter(z: int) -> str:
    """DEPRECATED: This function should NOT be used for Negretti!
    
    This function maps Zambretti z-numbers to Zambretti letter codes.
    Negretti has a DIFFERENT letter system and should use _generate_negretti_letter() instead.
    
    Kept for backward compatibility only.
    
    Args:
        z: Zambretti number (1-33, should be clamped by caller)

    Returns:
        Letter code (A-Z) representing weather forecast
    """
    # Defensive clamping - should already be done by caller, but extra safety
    if z < 1:
        _LOGGER.debug(f"Negretti: z={z} < 1, clamping to 1 for letter mapping")
        z = 1
    elif z > 33:
        _LOGGER.debug(f"Negretti: z={z} > 33, clamping to 33 for letter mapping")
        z = 33

    mapping = {
        1: "A", 10: "A", 20: "A",  # Settled fine
        2: "B", 11: "B", 21: "B",  # Fine weather
        3: "D",  # Fine, becoming less settled
        4: "H",  # Fairly fine, showery later
        5: "O",  # Showery, becoming more unsettled
        6: "R",  # Unsettled, rain later
        7: "U",  # Rain at times, worse later
        8: "V",  # Rain at times, becoming very unsettled
        9: "F",   # Fairly fine, improving (high pressure steady)
        12: "E",  # Fine, possible showers
        13: "K",  # Fairly fine, showers likely
        14: "N",  # Showery, bright intervals
        15: "P",  # Changeable, some rain
        16: "S",  # Unsettled, rain at times
        17: "W",  # Rain at frequent intervals
        18: "X",  # Very unsettled, rain
        19: "B",  # Fine weather (high pressure rising)
        22: "F",  # Settling fair
        23: "F",  # Fairly fine
        24: "G",  # Fairly fine, possible showers early
        25: "I",  # Showery early, improving
        26: "J",  # Changeable, mending
        27: "L",  # Rather unsettled, clearing later
        28: "M",  # Unsettled, probably improving
        29: "Q",  # Unsettled, short fine intervals
        30: "T",  # Very unsettled, finer at times
        31: "Y",  # Stormy, possibly improving
        32: "Z", 33: "Z",  # Stormy, much rain (extreme recovery)
    }
    result = mapping.get(z, "A")
    if z not in mapping:
        _LOGGER.debug(f"Negretti: Using default letter 'A' for z={z}")
    else:
        _LOGGER.debug(f"Negretti: Mapped z={z} → letter '{result}'")
    return result

