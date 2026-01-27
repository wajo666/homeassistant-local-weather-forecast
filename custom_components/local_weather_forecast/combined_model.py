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
import math

_LOGGER = logging.getLogger(__name__)


def calculate_combined_forecast_with_time(
    zambretti_result: list,
    negretti_result: list,
    current_pressure: float,
    pressure_change: float,
    hours_ahead: int = 0,
    source: str = "CombinedModel"
) -> tuple[int, float, float, bool]:
    """Calculate Combined forecast WITH TIME DECAY.
    
    This is the enhanced version that applies TIME DECAY weighting over the
    forecast horizon. Weights dynamically adjust based on how far into the
    future we're forecasting:
    - Near term (0-6h): Trust current conditions (base weights)
    - Mid term (6-12h): Gradual transition
    - Long term (12-24h): Move toward balanced weighting (trends matter more)
    
    NEW in v3.1.12: Adds hours_ahead parameter for dynamic weighting.
    
    Args:
        zambretti_result: [text, code] from Zambretti
        negretti_result: [text, code] from Negretti
        current_pressure: Current pressure in hPa
        pressure_change: Pressure change in hPa
        hours_ahead: Hours into future (0-24+) - enables TIME DECAY
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
    
    # Calculate dynamic weights WITH TIME DECAY
    zambretti_weight, negretti_weight, reason = _calculate_weights_with_time_decay(
        current_pressure, pressure_change, hours_ahead
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
    
    return (
        forecast_number,
        zambretti_weight,
        negretti_weight,
        consensus
    )


def calculate_combined_forecast(
    zambretti_result: list,
    negretti_result: list,
    current_pressure: float,
    pressure_change: float,
    source: str = "CombinedModel"
) -> tuple[int, float, float, bool]:
    """Calculate Combined forecast using dynamic weighting.
    
    BACKWARD COMPATIBILITY: This function is kept for existing code that
    doesn't need TIME DECAY (e.g., sensor.py for current state).
    
    Internally calls calculate_combined_forecast_with_time() with hours_ahead=0,
    which means NO time decay is applied - uses base weights only.
    
    For hourly forecasts with TIME DECAY, use calculate_combined_forecast_with_time()
    directly with the appropriate hours_ahead parameter.

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
    # Call new function with hours_ahead=0 (no time decay)
    # This preserves backward compatibility while using the new TIME DECAY infrastructure
    return calculate_combined_forecast_with_time(
        zambretti_result=zambretti_result,
        negretti_result=negretti_result,
        current_pressure=current_pressure,
        pressure_change=pressure_change,
        hours_ahead=0,  # No time decay for backward compatibility
        source=source
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


def _calculate_weights_with_time_decay(
    current_pressure: float,
    pressure_change: float,
    hours_ahead: int = 0
) -> tuple[float, float, str]:
    """Calculate dynamic weights with TIME DECAY over forecast horizon.
    
    This function extends the base weighting system with exponential time decay
    to account for forecast uncertainty growth over time. Near-term forecasts
    (0-6h) trust current conditions, while long-term forecasts (12-24h) gradually
    shift toward balanced weighting as trends become more important than current state.
    
    TIME DECAY Formula:
    - time_decay = exp(-hours_ahead / 12.0)
    - final_weight = base_weight × time_decay + 0.5 × (1 - time_decay)
    
    This causes weights to:
    - Stay close to base weights for 0-6h (current conditions dominate)
    - Gradually transition toward 50/50 for 12-24h (trend importance increases)
    
    Examples:
    - Anticyclone (base Z=10%, N=90%):
      * 0h:  Z=10%, N=90% (trust Negretti - stable)
      * 6h:  Z=26%, N=74% (anticyclone weakening)
      * 12h: Z=35%, N=65% (trend developing)
      * 24h: Z=46%, N=54% (nearly balanced)
    
    - Rapid change (base Z=75%, N=25%):
      * 0h:  Z=75%, N=25% (trust Zambretti - responsive)
      * 6h:  Z=66%, N=34% (change continuing)
      * 12h: Z=59%, N=41% (new equilibrium forming)
      * 24h: Z=53%, N=47% (nearly balanced)
    
    Args:
        current_pressure: Current pressure in hPa
        pressure_change: Pressure change in hPa
        hours_ahead: Hours into future (0-24+)
        
    Returns:
        Tuple of (zambretti_weight, negretti_weight, reason)
    """
    abs_change = abs(pressure_change)
    
    # STEP 1: Calculate BASE weights (same logic as _calculate_weights)
    if current_pressure > 1030:
        # Anticyclone detection
        if abs_change >= 3.0:
            base_zambretti_weight = 0.30
            reason_base = "anticyclone moderate change"
        elif abs_change >= 1.5:
            base_zambretti_weight = 0.20
            reason_base = "anticyclone small change"
        else:
            base_zambretti_weight = 0.10
            reason_base = f"stable anticyclone (P={current_pressure:.1f})"
    else:
        # Normal pressure range
        if abs_change >= 3.0:
            base_zambretti_weight = 0.75
            reason_base = f"rapid change (ΔP={pressure_change:+.1f})"
        elif abs_change >= 1.5:
            base_zambretti_weight = 0.65
            reason_base = f"moderate change (ΔP={pressure_change:+.1f})"
        elif abs_change >= 0.5:
            base_zambretti_weight = 0.45
            reason_base = f"small change (ΔP={pressure_change:+.1f})"
        else:
            base_zambretti_weight = 0.10
            reason_base = f"stable pressure (ΔP={pressure_change:+.1f})"
    
    # STEP 2: Apply TIME DECAY
    # Exponential decay with half-life of 12 hours
    # - At 0h: decay=1.00 (100% base weight)
    # - At 6h: decay=0.61 (61% base weight, 39% balanced)
    # - At 12h: decay=0.37 (37% base weight, 63% balanced)
    # - At 24h: decay=0.14 (14% base weight, 86% balanced)
    time_decay = math.exp(-hours_ahead / 12.0)
    
    # Blend base weight toward 50/50 balance based on time
    # Near term: Trust base conditions (current state matters)
    # Long term: Move toward balanced (trend matters more)
    zambretti_weight = (
        base_zambretti_weight * time_decay +  # Current condition influence
        0.5 * (1 - time_decay)                # Balanced baseline (50/50)
    )
    
    negretti_weight = 1.0 - zambretti_weight
    
    # Build detailed reason string for logging
    reason = f"{reason_base} | h={hours_ahead} decay={time_decay:.2f}"
    
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
