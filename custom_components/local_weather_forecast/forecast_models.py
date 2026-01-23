"""
Legacy wrapper for Universal Forecast Mapping System.

⚠️ DEPRECATED: This module is kept for backward compatibility only.
✅ NEW: Use forecast_mapping.py for all forecast mapping operations.

The new system provides:
- Unified internal code system (0-25)
- Language-independent mapping
- Single source of truth
- Better maintainability
"""
from __future__ import annotations

import logging
from typing import Callable

_LOGGER = logging.getLogger(__name__)

# Import new unified system
from .forecast_mapping import map_forecast_to_condition as _new_map_forecast


def map_forecast_to_condition(
    forecast_text: str,
    forecast_num: int | None = None,
    is_night_func: Callable[[], bool] | None = None,
    source: str = "Unknown"
) -> str:
    """Universal function to map any forecast to Home Assistant weather condition.

    ⚠️ DEPRECATED: This is a legacy wrapper. Use forecast_mapping.map_forecast_to_condition() directly.

    Works for Zambretti, Negretti-Zambra, and Combined forecasts.
    Uses text analysis and optional forecast number for reliable mapping.

    Args:
        forecast_text: Forecast text (e.g., "Fair weather", "Rain at times")
        forecast_num: Optional forecast number (0-25 for Zambretti, 0-10 for Negretti)
        is_night_func: Optional callable that returns True if nighttime
        source: Source of forecast ("Zambretti", "Negretti", "Combined") for logging

    Returns:
        HA condition: sunny, cloudy, rainy, partlycloudy, etc.
    """
    _LOGGER.debug(
        f"⚠️ DEPRECATED: map_forecast_to_condition() called from forecast_models.py. "
        f"Please use forecast_mapping.py directly."
    )

    # Delegate to new unified system
    return _new_map_forecast(
        forecast_text=forecast_text,
        forecast_num=forecast_num,
        forecast_letter=None,  # Not provided in old API
        is_night_func=is_night_func,
        temperature=None,  # Not provided in old API
        source=source
    )

