"""Combined (Enhanced) Forecast Model.

This module implements the Combined/Enhanced forecast model that dynamically
weights Zambretti and Negretti-Zambra forecasts based on:
- Pressure change rate
- Anticyclone detection (high pressure stability)
- Consensus between models

The weighting system gives priority to:
- Negretti (90%) during anticyclones (P > 1030 hPa) - more stable
- Zambretti (75%) during rapid pressure changes (|ΔP| ≥ 3 hPa) - more responsive
- Balanced weighting during moderate conditions

This solves the Zambretti STEADY formula bug where stable high pressure
produces wrong forecasts (e.g., 1037 hPa → "Very Unsettled").
"""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


def calculate_combined_forecast(
    zambretti_result: list,
    negretti_result: list,
    current_pressure: float,
    pressure_change: float,
    source: str = "CombinedModel"
) -> tuple[int, float, float, bool]:
    """Calculate Combined forecast using dynamic weighting.

    Args:
        zambretti_result: [text, code] from Zambretti (✅ SIMPLIFIED)
        negretti_result: [text, code] from Negretti (✅ SIMPLIFIED)
        current_pressure: Current pressure in hPa
        pressure_change: Pressure change in hPa
        source: Source identifier for logging

    Returns:
        Tuple of:
        - forecast_number: Selected forecast number/code (0-25)
        - zambretti_weight: Weight given to Zambretti (0.0-1.0)
        - negretti_weight: Weight given to Negretti (0.0-1.0)
        - consensus: Whether models agree (True/False)
    """
    # Extract forecast numbers/codes
    zambretti_num = zambretti_result[1] if len(zambretti_result) > 1 else 0
    negretti_num = negretti_result[1] if len(negretti_result) > 1 else 0

    # Calculate dynamic weights
    zambretti_weight, negretti_weight, reason = _calculate_weights(
        current_pressure, pressure_change
    )

    # Check consensus (models agree within ±1)
    consensus = abs(zambretti_num - negretti_num) <= 1

    # Select forecast based on weights and consensus
    if consensus:
        # Models agree - use Zambretti (more detailed text)
        forecast_number = zambretti_num
        decision = "CONSENSUS"
    elif zambretti_weight >= 0.6:
        # High Zambretti weight - trust Zambretti
        forecast_number = zambretti_num
        decision = f"ZAMBRETTI (weight={zambretti_weight:.0%})"
    else:
        # High Negretti weight - trust Negretti
        forecast_number = negretti_num
        decision = f"NEGRETTI (weight={negretti_weight:.0%})"

    _LOGGER.debug(
        f"🎯 {source}: P={current_pressure:.1f} hPa, ΔP={pressure_change:+.1f} hPa → "
        f"{reason} → Z:{zambretti_weight:.0%}/N:{negretti_weight:.0%} → "
        f"{decision} → forecast_code={forecast_number}"
    )

    # ✅ SIMPLIFIED: Return only forecast_number (code), no letter!
    return (
        forecast_number,
        zambretti_weight,
        negretti_weight,
        consensus
    )


def _calculate_weights(
    current_pressure: float,
    pressure_change: float
) -> tuple[float, float, str]:
    """Calculate dynamic weights for Zambretti vs Negretti.

    Weighting strategy:
    1. ANTICYCLONE (P > 1030 hPa): Trust Negretti 90%
       - Zambretti STEADY formula has bugs at high pressure
       - Negretti is more stable and accurate

    2. RAPID CHANGE (|ΔP| ≥ 3 hPa): Trust Zambretti 75%
       - Zambretti responds faster to pressure changes
       - Negretti is more conservative

    3. MODERATE CONDITIONS: Proportional weighting
       - Balanced approach based on change rate

    Args:
        current_pressure: Current pressure in hPa
        pressure_change: Pressure change in hPa

    Returns:
        Tuple of (zambretti_weight, negretti_weight, reason)
    """
    abs_change = abs(pressure_change)

    # SPECIAL CASE 1: Anticyclone (high pressure)
    # Zambretti STEADY formula gives wrong results at high pressure
    # Example: 1037 hPa → z=9 → "Very Unsettled" (WRONG!)
    # Negretti handles high pressure correctly
    if current_pressure > 1030:
        if abs_change >= 3.0:
            zambretti_weight = 0.30  # Even moderate changes in anticyclone
            reason = f"anticyclone moderate change"
        elif abs_change >= 1.5:
            zambretti_weight = 0.20  # Small change in anticyclone
            reason = f"anticyclone small change"
        else:
            zambretti_weight = 0.10  # Stable anticyclone - trust Negretti 90%
            reason = f"stable anticyclone (P={current_pressure:.1f})"

    # NORMAL PRESSURE RANGE: Standard weighting
    elif abs_change >= 3.0:
        zambretti_weight = 0.75  # Rapid change - trust Zambretti more
        reason = f"rapid change (ΔP={pressure_change:+.1f})"
    elif abs_change >= 1.5:
        zambretti_weight = 0.65  # Moderate change
        reason = f"moderate change (ΔP={pressure_change:+.1f})"
    elif abs_change >= 0.5:
        zambretti_weight = 0.45  # Small change
        reason = f"small change (ΔP={pressure_change:+.1f})"
    else:
        zambretti_weight = 0.10  # Stable - trust Negretti 90%
        reason = f"stable pressure (ΔP={pressure_change:+.1f})"

    negretti_weight = 1.0 - zambretti_weight

    return (zambretti_weight, negretti_weight, reason)


def get_combined_forecast_text(
    zambretti_result: list,
    negretti_result: list,
    forecast_number: int,
    zambretti_weight: float,
    lang_index: int = 1
) -> str:
    """Get forecast text from selected model.

    Args:
        zambretti_result: [text, code] from Zambretti (✅ SIMPLIFIED)
        negretti_result: [text, code] from Negretti (✅ SIMPLIFIED)
        forecast_number: Selected forecast code (0-25)
        zambretti_weight: Weight given to Zambretti
        lang_index: Language index

    Returns:
        Forecast text from selected model
    """
    # Determine which model was selected by comparing codes
    zambretti_num = zambretti_result[1] if len(zambretti_result) > 1 else 0
    negretti_num = negretti_result[1] if len(negretti_result) > 1 else 0

    # Return text from selected model
    if forecast_number == zambretti_num:
        return zambretti_result[0] if len(zambretti_result) > 0 else "Unknown"
    elif forecast_number == negretti_num:
        return negretti_result[0] if len(negretti_result) > 0 else "Unknown"
    else:
        # Fallback: use unified system
        from .forecast_mapping import get_forecast_text
        return get_forecast_text(forecast_num=forecast_number, lang_index=lang_index)


def calculate_combined_rain_probability(
    zambretti_letter: str,
    negretti_letter: str,
    zambretti_weight: float,
    negretti_weight: float
) -> float:
    """Calculate weighted rain probability from both models.

    Args:
        zambretti_letter: Zambretti letter code (A-Z)
        negretti_letter: Negretti letter code (A-Z)
        zambretti_weight: Weight for Zambretti (0.0-1.0)
        negretti_weight: Weight for Negretti (0.0-1.0)

    Returns:
        Combined rain probability (0-100)
    """
    # Import rain probability mapping
    try:
        from .forecast_calculator import RainProbabilityCalculator

        zambretti_rain = RainProbabilityCalculator.LETTER_RAIN_PROB.get(
            zambretti_letter, 50
        )
        negretti_rain = RainProbabilityCalculator.LETTER_RAIN_PROB.get(
            negretti_letter, 50
        )

        # Weighted average
        combined_rain = (
            zambretti_rain * zambretti_weight +
            negretti_rain * negretti_weight
        )

        _LOGGER.debug(
            f"Combined rain probability: "
            f"Z:{zambretti_letter}({zambretti_rain}%) × {zambretti_weight:.0%} + "
            f"N:{negretti_letter}({negretti_rain}%) × {negretti_weight:.0%} = "
            f"{combined_rain:.0f}%"
        )

        return combined_rain

    except ImportError:
        _LOGGER.warning("RainProbabilityCalculator not available, returning 50%")
        return 50.0
