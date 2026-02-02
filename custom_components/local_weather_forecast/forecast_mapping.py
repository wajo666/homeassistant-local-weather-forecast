"""
✅ UNIFIED FORECAST MAPPING SYSTEM - FINAL VERSION

This module replaces 3 different mapping systems with ONE universal approach:

OLD (3 systems):
1. forecast_models.py: Text → Condition (186 lines, multilingual)
2. const.py: ZAMBRETTI_TO_CONDITION (26 entries, letter → condition)
3. weather.py: forecast_short_term parsing (Slovak keywords)

NEW (1 system):
1. forecast_mapping.py: ANY INPUT → Internal Code → Condition

ARCHITECTURE:
┌────────────────────────────────────────────────────────────┐
│  ANY INPUT → INTERNAL CODE (0-25) → HA CONDITION          │
└────────────────────────────────────────────────────────────┘

Zambretti text (SK/DE/EN/IT/GR)  ┐
Negretti text (SK/DE/EN/IT/GR)   ├→ CODE (0-25) → HA condition
Zambretti letter (A-Z)            ┤              → (sunny/rainy/etc.)
Negretti number (0-25)            ┘

BENEFITS:
✅ Single source of truth
✅ Language-independent internal codes
✅ Easy testing (test code → condition, not text → condition)
✅ Consistent behavior across all components
✅ Less duplicate code (-70%)
"""
from __future__ import annotations

import logging
from typing import Callable

_LOGGER = logging.getLogger(__name__)


# ==============================================================================
# INTERNAL FORECAST CODE SYSTEM (0-25)
# ==============================================================================
# Universal system based on Zambretti forecast numbers
# All forecast models (Zambretti, Negretti, Combined) map to these codes

# 0-5:   Settled/Fine weather (HIGH PRESSURE, STABLE)
# 6-10:  Fair weather with possible changes
# 11-15: Unsettled/Changeable weather
# 16-19: Rainy weather
# 20-24: Very unsettled, frequent rain (HEAVY RAIN ZONE)
# 25:    Stormy weather

# Forecast code constants (for reference)
FORECAST_CODE_SETTLED_FINE = 0
FORECAST_CODE_FINE = 1
FORECAST_CODE_BECOMING_FINE = 2
FORECAST_CODE_FINE_LESS_SETTLED = 3
FORECAST_CODE_FINE_SHOWERS = 4
FORECAST_CODE_FAIRLY_FINE_IMPROVING = 5
FORECAST_CODE_FAIRLY_FINE_SHOWERS_EARLY = 6
FORECAST_CODE_FAIRLY_FINE_SHOWERY_LATER = 7
FORECAST_CODE_SHOWERY_EARLY_IMPROVING = 8
FORECAST_CODE_CHANGEABLE_MENDING = 9
FORECAST_CODE_FAIRLY_FINE_SHOWERS_LIKELY = 10
FORECAST_CODE_UNSETTLED_CLEARING = 11
FORECAST_CODE_UNSETTLED_IMPROVING = 12
FORECAST_CODE_SHOWERY_BRIGHT = 13
FORECAST_CODE_SHOWERY_MORE_UNSETTLED = 14
FORECAST_CODE_CHANGEABLE_RAIN = 15
FORECAST_CODE_UNSETTLED_SHORT_FINE = 16
FORECAST_CODE_UNSETTLED_RAIN_LATER = 17
FORECAST_CODE_UNSETTLED_RAIN_TIMES = 18
FORECAST_CODE_VERY_UNSETTLED_FINER = 19
FORECAST_CODE_RAIN_WORSE_LATER = 20
FORECAST_CODE_RAIN_VERY_UNSETTLED = 21
FORECAST_CODE_RAIN_FREQUENT = 22
FORECAST_CODE_VERY_UNSETTLED_RAIN = 23
FORECAST_CODE_STORMY_IMPROVING = 24
FORECAST_CODE_STORMY_MUCH_RAIN = 25


# ==============================================================================
# ZAMBRETTI LETTER TO INTERNAL CODE
# ==============================================================================

ZAMBRETTI_LETTER_TO_CODE = {
    "A": 0,   # Settled fine
    "B": 1,   # Fine weather
    "C": 2,   # Becoming fine
    "D": 3,   # Fine, becoming less settled
    "E": 4,   # Fine, possible showers
    "F": 5,   # Fairly fine, improving
    "G": 6,   # Fairly fine, possible showers early
    "H": 7,   # Fairly fine, showery later
    "I": 8,   # Showery early, improving
    "J": 9,   # Changeable, mending
    "K": 10,  # Fairly fine, showers likely
    "L": 11,  # Rather unsettled clearing later
    "M": 12,  # Unsettled, probably improving
    "N": 13,  # Showery, bright intervals
    "O": 14,  # Showery, becoming more unsettled
    "P": 15,  # Changeable, some rain
    "Q": 16,  # Unsettled, short fine intervals
    "R": 17,  # Unsettled, rain later
    "S": 18,  # Unsettled, some rain
    "T": 19,  # Mostly very unsettled
    "U": 20,  # Occasional rain, worsening
    "V": 21,  # Rain at times, very unsettled
    "W": 22,  # Rain at frequent intervals
    "X": 23,  # Very unsettled, rain
    "Y": 24,  # Stormy, may improve
    "Z": 25,  # Stormy, much rain
}


# ==============================================================================
# INTERNAL CODE TO HA CONDITION MAPPING
# ==============================================================================

def forecast_code_to_condition(
    code: int,
    is_night: bool = False,
    temperature: float | None = None,
    is_current_state: bool = False
) -> str:
    """Map internal forecast code to Home Assistant weather condition.

    This is the SINGLE SOURCE OF TRUTH for code → condition mapping.

    Args:
        code: Internal forecast code (0-25)
        is_night: Whether it's nighttime (for sunny → clear-night conversion)
        temperature: Temperature in °C (for rain → snow conversion)
        is_current_state: True if this is for CURRENT state (0h), False for future forecast
                         Current state returns CLOUDINESS only (no precipitation type)
                         Future forecast returns full prediction (including precipitation)

    Returns:
        HA weather condition string
    """
    # Settled/Fine weather (0-5)
    if code <= 2:
        # 0: Settled fine, 1: Fine weather, 2: Becoming fine
        condition = "clear-night" if is_night else "sunny"
    elif code <= 5:
        # 3-5: Fine with some uncertainty
        condition = "partlycloudy"

    # Fair weather with changes (6-10)
    elif code <= 10:
        # 6-10: Fairly fine, possible showers
        condition = "partlycloudy"

    # Unsettled/Changeable (11-17)
    elif code <= 12:
        # 11-12: Unsettled but improving → cloudy (realistic for "unsettled")
        condition = "cloudy"
    elif code <= 14:
        # 13-14: Showery, bright intervals → cloudy (showers ≠ continuous rain!)
        condition = "cloudy"
    elif code <= 17:
        # 15-17: Changeable/Unsettled with "rain LATER" prediction
        # These forecasts say "neskôr dáž��" (rain later, 3-6h), NOT "dážď teraz" (rain now)
        # Example texts:
        #   15: "Changeable, some rain" (premenlivé s občasným dažďom)
        #   16: "Unsettled, short fine intervals" (nestále s krátkymi jasnými intervalmi)
        #   17: "Unsettled, rain later" (nestále, NESKÔR dážď) ← KEY!
        #
        # CORRECT MAPPING:
        # - Always map to "cloudy" (heavy clouds, rain threat, but NOT raining yet)
        # - Rain sensor determines if actually precipitating
        # - For 3-6h forecasts, these will naturally progress to rainy codes (18-23)
        condition = "cloudy"  # Heavy clouds with rain threat (but not raining yet)

    # Rainy weather (18-23)
    elif code <= 23:
        # 18-23: ACTIVE rain predictions ("rain at times", "frequent rain", "rain now")
        # These forecasts say "dážď" (rain NOW/frequent), NOT "neskôr dážď" (rain later)
        # Example texts:
        #   18: "Unsettled, rain at times" (nestále s občasným dažďom)
        #   19: "Very unsettled, finer at times" (veľmi premenlivé a daždivé)
        #   20: "Rain at times, worse later" (občasný dážď, neskôr zhoršenie)
        #   21: "Rain at times, very unsettled" (občasný dážď, veľmi nestále)
        #   22: "Rain at frequent intervals" (častý dážď)
        #   23: "Very unsettled, rain" (dážď, veľmi nestále)
        #
        # CORRECT MAPPING:
        # - For CURRENT state (0h): Show cloudiness only (rain sensor determines actual precipitation)
        # - For FORECAST (1-24h): Show predicted precipitation (rainy)
        if is_current_state:
            condition = "cloudy"  # Current: overcast (rain conditions, sensor determines if raining)
        else:
            condition = "rainy"   # Forecast: predicted active precipitation

    # Very unsettled, stormy (24-25)
    elif code == 24:
        # 24: Stormy, possibly improving
        # For CURRENT state (0h): Show cloudiness only
        # For FUTURE forecast (1-24h): Show predicted precipitation
        if is_current_state:
            condition = "cloudy"  # Current: dark clouds (storm conditions)
        else:
            condition = "pouring"  # Future: predicted heavy rain
    else:
        # 25: Stormy, much rain
        # For CURRENT state (0h): Show cloudiness only
        # For FUTURE forecast (1-24h): Show predicted precipitation
        if is_current_state:
            condition = "cloudy"  # Current: storm clouds (thunderstorm conditions)
        else:
            condition = "lightning-rainy"  # Future: predicted thunderstorm

    # ✅ ENABLED: Automatic snow/mixed precipitation conversion FOR FORECASTS ONLY
    #
    # LOGIC:
    # - For CURRENT state (0h): Skip snow conversion (rain sensor handles it)
    # - For FUTURE forecast (1-24h): Apply snow conversion based on temperature
    #
    # This allows:
    # - Hourly forecasts to show "snowy" when T ≤ 2°C
    # - Current state to remain "cloudy" (rain sensor determines actual precipitation)
    if temperature is not None and not is_current_state:
        if condition in ("rainy", "pouring", "lightning-rainy"):
            if 2.0 < temperature <= 4.0:
                condition = "snowy-rainy"
                _LOGGER.debug(f"Snow conversion: rainy → snowy-rainy (T={temperature:.1f}°C)")
            elif temperature <= 2.0:
                condition = "snowy"
                _LOGGER.debug(f"Snow conversion: rainy → snowy (T={temperature:.1f}°C)")

    _LOGGER.debug(
        f"Code→Condition: code={code} → {condition} "
        f"(night={is_night}, temp={temperature if temperature is not None else 'N/A'}°C, "
        f"current={is_current_state})"
    )

    return condition


# ==============================================================================
# TEXT TO INTERNAL CODE MAPPING (MULTILINGUAL)
# ==============================================================================

def forecast_text_to_code(
    forecast_text: str,
    forecast_num: int | None = None,
    source: str = "Unknown"
) -> int:
    """Map forecast text to internal code (language-independent).

    Uses keyword analysis to detect forecast type regardless of language.
    Falls back to forecast_num if text analysis is inconclusive.

    Args:
        forecast_text: Forecast text in any language
        forecast_num: Optional forecast number (0-25) as fallback
        source: Source of forecast (for logging)

    Returns:
        Internal forecast code (0-25)
    """
    text_lower = forecast_text.lower()

    # PRIORITY 0: Forecast number in heavy rain zone (20-24) overrides text
    # This ensures forecast_num=21 → code 21 → pouring
    if forecast_num is not None and 20 <= forecast_num <= 24:
        _LOGGER.debug(
            f"Text→Code[{source}]: num={forecast_num} in heavy rain zone, "
            f"using directly (ignoring text)"
        )
        return forecast_num

    # PRIORITY 1: Storm keywords (code 25)
    storm_keywords = [
        "storm", "thunder", "gale", "tempest",  # English
        "stürmisch", "sturm",  # German
        "θυελλώδης", "καταιγίδα", "τυφώνας",  # Greek
        "tempestoso", "tempesta", "uragano",  # Italian
        "búrlivé", "búrka", "orkán"  # Slovak
    ]
    if any(word in text_lower for word in storm_keywords):
        _LOGGER.debug(f"Text→Code[{source}]: storm → 25")
        return 25

    # PRIORITY 2: Heavy/frequent rain keywords (22)
    heavy_rain_keywords = [
        "heavy rain", "pouring", "frequent", "much rain", "torrential",  # English
        "häufiger", "viel regen",  # German
        "συχνή βροχή", "πολλές βροχές",  # Greek
        "piogge frequenti", "molta pioggia",  # Italian
        "častý", "veľa dažďom"  # Slovak
    ]
    if any(word in text_lower for word in heavy_rain_keywords):
        _LOGGER.debug(f"Text→Code[{source}]: heavy rain → 22")
        return 22

    # PRIORITY 3: Cloudy keywords (BEFORE rain check!)
    # This fixes "Zamračené" (Slovak cloudy) detection
    cloudy_keywords = [
        "cloudy", "overcast",  # English
        "wolkig", "bewölkt",  # German
        "νεφελώδης", "συννεφιασμένος",  # Greek
        "nuvoloso", "coperto",  # Italian
        "oblačn", "zamrač"  # Slovak (matches zamračené, zamračený, zamračená)
    ]
    partly_keywords = [
        "partly", "fairly",  # English
        "heiter bis", "bis wolkig",  # German
        "αίθριος έως",  # Greek
        "abbastanza",  # Italian
        "polo", "miestami"  # Slovak
    ]

    has_cloudy = any(word in text_lower for word in cloudy_keywords)
    has_partly = any(word in text_lower for word in partly_keywords)

    if has_cloudy:
        if has_partly:
            _LOGGER.debug(f"Text→Code[{source}]: partly cloudy → 3")
            return 3
        else:
            _LOGGER.debug(f"Text→Code[{source}]: cloudy → 13")
            return 13

    # PRIORITY 4: Rain keywords (but NOT "possibly") (15)
    possibly_keywords = [
        "possibly", "possible", "may", "might",  # English
        "möglich", "evtl",  # German
        "πιθανή", "πιθανώς",  # Greek
        "possibili", "possibile",  # Italian
        "možné", "možno"  # Slovak
    ]
    rain_keywords = [
        "rain", "shower",  # English
        "regen", "schauer", "regnerisch",  # German
        "βροχή", "βροχερό", "βροχόπτωση",  # Greek
        "pioggia", "piogge", "rovesci", "piovoso",  # Italian
        "dážď", "prší", "zrážk", "prehán", "dážd", "daždiv"  # Slovak
    ]

    has_possibly = any(word in text_lower for word in possibly_keywords)
    has_rain = any(word in text_lower for word in rain_keywords)

    if has_rain and not has_possibly:
        _LOGGER.debug(f"Text→Code[{source}]: rain → 15")
        return 15

    # PRIORITY 5: Unsettled/changeable (WITHOUT rain) (3)
    unsettled_keywords = [
        "unsettled", "changeable", "variable",  # English
        "unbeständig", "wechselhaft",  # German
        "ασταθής", "μεταβλητός", "άστατ",  # Greek
        "instabile", "variabile",  # Italian
        "nestále", "premenlivý", "premenlivé"  # Slovak
    ]
    if any(word in text_lower for word in unsettled_keywords):
        _LOGGER.debug(f"Text→Code[{source}]: unsettled → 3 (partlycloudy)")
        return 3

    # PRIORITY 6: Fair/fine weather (0-5)
    fine_keywords = [
        "settled", "stable", "fine", "fair",  # English
        "beständig", "schön", "schönwetter",  # German
        "σταθερός", "καλός καιρός", "ωραίος",  # Greek
        "bello", "stabile", "bel tempo",  # Italian
        "stabilne", "pekné", "jasn", "slnečn"  # Slovak
    ]
    if any(word in text_lower for word in fine_keywords):
        # Check for future problems
        future_problem_keywords = [
            "later", "becoming", "worse",  # English
            "später", "wird", "verschlechterung",  # German
            "αργό��ερα", "επιδείνωση",  # Greek
            "più tardi", "diventa", "peggiora",  # Italian
            "neskôr", "stáva sa", "zhoršenie"  # Slovak
        ] + possibly_keywords

        has_future_problems = any(word in text_lower for word in future_problem_keywords)

        if not has_future_problems or (forecast_num is not None and forecast_num == 0):
            _LOGGER.debug(f"Text→Code[{source}]: settled fine → 0")
            return 0
        else:
            _LOGGER.debug(f"Text→Code[{source}]: fine with caveats → 3")
            return 3

    # FALLBACK: Use forecast_num if provided
    if forecast_num is not None:
        code = max(0, min(25, forecast_num))
        _LOGGER.debug(f"Text→Code[{source}]: fallback to num={forecast_num} → {code}")
        return code

    # ULTIMATE FALLBACK: Partlycloudy (code 3)
    _LOGGER.debug(f"Text→Code[{source}]: ultimate fallback → 3")
    return 3


# ==============================================================================
# UNIFIED API
# ==============================================================================

def map_forecast_to_condition(
    forecast_text: str | None = None,
    forecast_num: int | None = None,
    forecast_letter: str | None = None,
    is_night_func: Callable[[], bool] | None = None,
    temperature: float | None = None,
    source: str = "Unknown",
    is_current_state: bool = False
) -> str:
    """Universal forecast mapping: ANY input → HA condition.

    This is the SINGLE ENTRY POINT for all forecast mapping.

    Accepts any combination of:
    - forecast_text: Text in any language (e.g., "Pekné počasie!")
    - forecast_num: Forecast number 0-25 (Zambretti/Negretti)
    - forecast_letter: Zambretti letter A-Z

    Returns: HA weather condition (sunny, rainy, cloudy, etc.)

    Args:
        forecast_text: Forecast text (any language)
        forecast_num: Forecast number (0-25)
        forecast_letter: Zambretti letter (A-Z)
        is_night_func: Callable returning True if nighttime
        temperature: Temperature in °C (for snow conversion)
        source: Source name for logging
        is_current_state: True if this is for CURRENT state (0h), False for future forecast

    Returns:
        HA weather condition string
    """
    # Step 1: Convert to internal code
    if forecast_letter:
        # Letter has highest priority (most precise)
        code = ZAMBRETTI_LETTER_TO_CODE.get(forecast_letter.upper(), forecast_num or 3)
        _LOGGER.debug(f"Unified[{source}]: letter={forecast_letter} → code={code}")
    elif forecast_text:
        # Text analysis
        code = forecast_text_to_code(forecast_text, forecast_num, source)
    elif forecast_num is not None:
        # Direct number
        code = max(0, min(25, forecast_num))
        _LOGGER.debug(f"Unified[{source}]: num={forecast_num} → code={code}")
    else:
        # No input - fallback
        _LOGGER.debug(f"Unified[{source}]: No input, using default code=3")
        code = 3

    # Step 2: Determine night status
    is_night = is_night_func() if is_night_func else False

    # Step 3: Map code → condition
    condition = forecast_code_to_condition(code, is_night, temperature, is_current_state)

    _LOGGER.debug(
        f"🎯 UNIFIED[{source}]: text='{forecast_text}', num={forecast_num}, "
        f"letter={forecast_letter} → code={code} → {condition}"
    )

    return condition


# ==============================================================================
# TEXT RETRIEVAL - UNIFIED SYSTEM
# ==============================================================================

def get_forecast_text(
    forecast_num: int | None = None,
    forecast_letter: str | None = None,
    lang_index: int = 1
) -> str:
    """Get forecast text from forecast number or letter using unified system.

    This is the SINGLE function for retrieving forecast text from any model:
    - Zambretti: Can use forecast_num (0-25) OR forecast_letter (A-Z)
    - Negretti: Uses forecast_num (0-25)
    - Both return SAME text for same code!

    Args:
        forecast_num: Forecast number (0-25) - used by Negretti, optional for Zambretti
        forecast_letter: Forecast letter (A-Z) - used by Zambretti, maps to same codes
        lang_index: Language index (0=DE, 1=EN, 2=GR, 3=IT, 4=SK)

    Returns:
        Forecast text in selected language

    Examples:
        >>> get_forecast_text(forecast_num=0, lang_index=4)
        "Stabilne pekné počasie!"

        >>> get_forecast_text(forecast_letter="A", lang_index=4)
        "Stabilne pekné počasie!"  # SAME TEXT!

        >>> get_forecast_text(forecast_num=25, lang_index=1)
        "Stormy, much rain"
    """
    # Import here to avoid circular dependency
    from .forecast_data import FORECAST_TEXTS

    # Determine forecast code
    if forecast_letter:
        # Convert letter to code
        code = ZAMBRETTI_LETTER_TO_CODE.get(forecast_letter.upper(), 0)
        _LOGGER.debug(f"get_forecast_text: letter={forecast_letter} → code={code}")
    elif forecast_num is not None:
        # Use number directly
        code = max(0, min(25, forecast_num))
        _LOGGER.debug(f"get_forecast_text: num={forecast_num} → code={code}")
    else:
        # No input - default
        _LOGGER.debug("get_forecast_text: No input, using default code=0")
        code = 0

    # Get text from FORECAST_TEXTS
    try:
        text = FORECAST_TEXTS[code][lang_index]
        _LOGGER.debug(f"get_forecast_text: code={code}, lang={lang_index} → '{text}'")
        return text
    except (IndexError, KeyError) as e:
        _LOGGER.error(
            f"get_forecast_text: Failed to get text for code={code}, lang={lang_index}: {e}"
        )
        return "Unknown"

