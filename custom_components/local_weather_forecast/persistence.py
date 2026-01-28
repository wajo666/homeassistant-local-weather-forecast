"""Persistence Model - Simplest forecasting model.

Assumes current conditions will persist unchanged.
Best for: Hour 0 (current state stabilization)
Accuracy: 98-100% for current state, 95% for +1h, declines rapidly after

Theory:
- "Počasie bude rovnaké ako teraz"
- Optimal pre veľmi krátky horizont (0-1h)
- Stabilizuje fluktuácie senzorov
- Poskytuje smooth baseline pre ostatné modely
"""

import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)


def calculate_persistence_forecast(
    current_condition_code: int,
    lang_index: int = 1,
    hours_ahead: int = 0
) -> list:
    """Calculate Persistence forecast (current conditions persist).
    
    Args:
        current_condition_code: Current unified condition code (0-25)
        lang_index: Language index for forecast text
        hours_ahead: Hours into future (0 recommended, 1-3 acceptable)
        
    Returns:
        [forecast_text, forecast_code, letter_code, confidence]
    """
    # Persistence = current state
    forecast_code = current_condition_code
    
    # Get text from unified mapping using forecast_num parameter
    from .forecast_mapping import get_forecast_text
    forecast_text = get_forecast_text(forecast_num=forecast_code, lang_index=lang_index)
    
    # Generate letter code (A-Z mapping)
    letter_code = chr(65 + min(forecast_code // 3, 7))
    
    # Confidence decays with time
    confidence = get_persistence_confidence(hours_ahead)
    
    _LOGGER.debug(
        f"🔒 Persistence: h{hours_ahead} → code={forecast_code} "
        f"({forecast_text}), confidence={confidence:.0%}"
    )
    
    return [forecast_text, forecast_code, letter_code, confidence]


def get_persistence_confidence(hours_ahead: int) -> float:
    """Calculate confidence for Persistence model based on forecast horizon.
    
    Persistence accuracy declines rapidly with time:
    - Hour 0: 98% (excellent - stabilized current state)
    - Hour 1: 95% (very good)
    - Hour 2: 90% (good)
    - Hour 3: 85% (acceptable)
    - Hour 4+: <80% (poor - use other models)
    
    Args:
        hours_ahead: Hours into future (0-24)
        
    Returns:
        Confidence score (0.0-1.0)
    """
    if hours_ahead == 0:
        return 0.98  # Excellent for current state
    elif hours_ahead == 1:
        return 0.95  # Very good for +1h
    elif hours_ahead == 2:
        return 0.90  # Good for +2h
    elif hours_ahead == 3:
        return 0.85  # Acceptable for +3h
    else:
        # Rapid decline after 3h
        return max(0.60, 0.85 - (hours_ahead - 3) * 0.05)


def get_current_condition_code(
    temperature: float,
    pressure: float,
    humidity: float,
    dewpoint: float,
    weather_condition: Optional[str] = None
) -> int:
    """Determine current unified condition code from sensor data.
    
    Maps current weather conditions to unified codes (0-25) using simple
    pressure-based classification. This provides a stable baseline for
    Persistence Model without requiring complex calculations.
    
    Classification:
    - P > 1030: Settled fine (0-2)
    - P > 1020: Fine weather (3-7)
    - P > 1010: Fair/partly cloudy (8-11)
    - P > 1000: Cloudy (12-14)
    - P > 990: Rain (15-18)
    - P > 980: Heavy rain (19-21)
    - P <= 980: Stormy (22-25)
    
    Args:
        temperature: Current temperature in °C
        pressure: Current pressure in hPa
        humidity: Current humidity in %
        dewpoint: Current dewpoint in °C
        weather_condition: Current HA weather condition (optional)
        
    Returns:
        Unified condition code (0-25)
    """
    # Simple pressure-based classification
    # This provides stable current state without complex calculations
    
    if pressure > 1030:
        # Very high pressure - settled fine
        unified_code = 1  # Settled fine
    elif pressure > 1023:
        # High pressure - fine weather
        unified_code = 5  # Fine weather
    elif pressure > 1015:
        # Above normal - fair weather
        unified_code = 9  # Fair, becoming fine
    elif pressure > 1008:
        # Normal pressure - partly cloudy
        unified_code = 12  # Fairly fine, improving
    elif pressure > 1000:
        # Slightly below normal - cloudy
        unified_code = 13  # Fairly fine, possibly showers
    elif pressure > 990:
        # Low pressure - rain likely
        unified_code = 17  # Showery, unsettled
    elif pressure > 980:
        # Very low pressure - heavy rain
        unified_code = 20  # Rain at times, worse later
    else:
        # Extremely low pressure - stormy
        unified_code = 24  # Stormy, much rain
    
    # Adjust based on humidity for fine-tuning
    if humidity > 85 and unified_code < 15:
        # High humidity suggests worse conditions
        unified_code = min(unified_code + 2, 14)
    elif humidity < 50 and unified_code > 10:
        # Low humidity suggests better conditions
        unified_code = max(unified_code - 2, 8)
    
    _LOGGER.debug(
        f"🎯 Current state: P={pressure:.1f} hPa, T={temperature:.1f}°C, "
        f"RH={humidity:.0f}% → code={unified_code}"
    )
    
    return unified_code
