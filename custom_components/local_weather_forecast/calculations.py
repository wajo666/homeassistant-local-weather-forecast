"""Extended calculations for Local Weather Forecast integration."""
from __future__ import annotations

import math
from typing import Optional

from .const import (
    COMFORT_VERY_COLD,
    COMFORT_COLD,
    COMFORT_COOL,
    COMFORT_COMFORTABLE,
    COMFORT_WARM,
    COMFORT_HOT,
    COMFORT_VERY_HOT,
    FOG_RISK_NONE,
    FOG_RISK_LOW,
    FOG_RISK_MEDIUM,
    FOG_RISK_HIGH,
)


def calculate_dewpoint(temperature: float, humidity: float) -> Optional[float]:
    """
    Calculate dew point temperature using Magnus formula.

    Args:
        temperature: Temperature in °C
        humidity: Relative humidity in %

    Returns:
        Dew point temperature in °C, or None if calculation fails
    """
    if humidity <= 0 or humidity > 100:
        return None

    try:
        # Magnus formula constants
        a = 17.27
        b = 237.7

        # Calculate alpha
        alpha = ((a * temperature) / (b + temperature)) + math.log(humidity / 100.0)

        # Calculate dew point
        dewpoint = (b * alpha) / (a - alpha)

        return round(dewpoint, 1)
    except (ValueError, ZeroDivisionError):
        return None


def calculate_heat_index(temperature: float, humidity: float) -> Optional[float]:
    """
    Calculate heat index (apparent temperature when hot).
    Based on US National Weather Service formula.

    Args:
        temperature: Temperature in °C
        humidity: Relative humidity in %

    Returns:
        Heat index in °C, or None if not applicable
    """
    # Heat index only applicable when temperature > 27°C
    if temperature <= 27 or humidity <= 0 or humidity > 100:
        return None

    try:
        # Convert to Fahrenheit for calculation
        t_f = (temperature * 9/5) + 32
        rh = humidity

        # Simplified heat index formula
        hi_f = (
            -42.379 +
            2.04901523 * t_f +
            10.14333127 * rh -
            0.22475541 * t_f * rh -
            0.00683783 * t_f * t_f -
            0.05481717 * rh * rh +
            0.00122874 * t_f * t_f * rh +
            0.00085282 * t_f * rh * rh -
            0.00000199 * t_f * t_f * rh * rh
        )

        # Convert back to Celsius
        hi_c = (hi_f - 32) * 5/9

        return round(hi_c, 1)
    except (ValueError, ZeroDivisionError):
        return None


def calculate_wind_chill(temperature: float, wind_speed: float) -> Optional[float]:
    """
    Calculate wind chill (apparent temperature when cold and windy).
    Based on US National Weather Service formula.

    Args:
        temperature: Temperature in °C
        wind_speed: Wind speed in km/h

    Returns:
        Wind chill in °C, or None if not applicable
    """
    # Wind chill only applicable when temperature < 10°C and wind > 4.8 km/h
    if temperature >= 10 or wind_speed <= 4.8:
        return None

    try:
        t = temperature
        v = wind_speed

        # Wind chill formula
        wc = (
            13.12 +
            0.6215 * t -
            11.37 * (v ** 0.16) +
            0.3965 * t * (v ** 0.16)
        )

        return round(wc, 1)
    except (ValueError, ZeroDivisionError):
        return None


def calculate_apparent_temperature(
    temperature: float,
    humidity: Optional[float] = None,
    wind_speed: Optional[float] = None
) -> float:
    """
    Calculate apparent temperature (feels like).

    Uses heat index when hot and humid,
    wind chill when cold and windy,
    or actual temperature otherwise.

    Args:
        temperature: Temperature in °C
        humidity: Relative humidity in % (optional)
        wind_speed: Wind speed in km/h (optional)

    Returns:
        Apparent temperature in °C
    """
    # Try heat index first (hot weather)
    if humidity is not None and temperature > 27:
        heat_index = calculate_heat_index(temperature, humidity)
        if heat_index is not None:
            return heat_index

    # Try wind chill (cold weather)
    if wind_speed is not None and temperature < 10:
        wind_chill = calculate_wind_chill(temperature, wind_speed)
        if wind_chill is not None:
            return wind_chill

    # Default to actual temperature
    return temperature


def get_comfort_level(apparent_temperature: float) -> str:
    """
    Get comfort level based on apparent temperature.

    Args:
        apparent_temperature: Apparent temperature in °C

    Returns:
        Comfort level string
    """
    if apparent_temperature < -10:
        return COMFORT_VERY_COLD
    elif apparent_temperature < 5:
        return COMFORT_COLD
    elif apparent_temperature < 15:
        return COMFORT_COOL
    elif apparent_temperature < 25:
        return COMFORT_COMFORTABLE
    elif apparent_temperature < 30:
        return COMFORT_WARM
    elif apparent_temperature < 35:
        return COMFORT_HOT
    else:
        return COMFORT_VERY_HOT


def get_fog_risk(temperature: float, dewpoint: float) -> str:
    """
    Calculate fog risk based on temperature-dewpoint spread.

    Args:
        temperature: Temperature in °C
        dewpoint: Dew point in °C

    Returns:
        Fog risk level
    """
    spread = abs(temperature - dewpoint)

    if spread > 4:
        return FOG_RISK_NONE
    elif spread > 2.5:
        return FOG_RISK_LOW
    elif spread > 1.5:
        return FOG_RISK_MEDIUM
    else:
        return FOG_RISK_HIGH


def calculate_rain_probability_enhanced(
    zambretti_prob: int,
    negretti_prob: int,
    humidity: Optional[float] = None,
    cloud_coverage: Optional[float] = None,
    dewpoint_spread: Optional[float] = None,
) -> tuple[int, str]:
    """
    Calculate enhanced rain probability combining multiple factors.

    Args:
        zambretti_prob: Zambretti rain probability (0-100)
        negretti_prob: Negretti-Zambra rain probability (0-100)
        humidity: Relative humidity in % (optional)
        cloud_coverage: Cloud coverage in % (optional)
        dewpoint_spread: Temperature - Dewpoint in °C (optional)

    Returns:
        Tuple of (probability %, confidence level)
    """
    # Base probability from models
    base_prob = (zambretti_prob + negretti_prob) / 2

    # Adjustment factors
    adjustments = []

    # Humidity factor
    if humidity is not None:
        if humidity > 85:
            adjustments.append(10)  # Increase probability
        elif humidity > 70:
            adjustments.append(5)
        elif humidity < 40:
            adjustments.append(-15)  # Decrease probability
        elif humidity < 60:
            adjustments.append(-5)

    # Cloud coverage factor
    if cloud_coverage is not None:
        if cloud_coverage > 90:
            adjustments.append(10)
        elif cloud_coverage > 70:
            adjustments.append(5)
        elif cloud_coverage < 20:
            adjustments.append(-10)
        elif cloud_coverage < 40:
            adjustments.append(-5)

    # Dewpoint spread factor (saturation indicator)
    if dewpoint_spread is not None:
        if dewpoint_spread < 2:
            adjustments.append(15)  # Very humid, high rain chance
        elif dewpoint_spread < 4:
            adjustments.append(5)
        elif dewpoint_spread > 8:
            adjustments.append(-10)  # Very dry

    # Calculate final probability
    total_adjustment = sum(adjustments)
    final_prob = base_prob + total_adjustment

    # Clamp to 0-100 range
    final_prob = max(0, min(100, final_prob))

    # Determine confidence
    if len(adjustments) >= 2:
        confidence = "high"
    elif len(adjustments) == 1:
        confidence = "medium"
    else:
        confidence = "low"

    return int(final_prob), confidence


def interpolate_forecast(
    current_value: float,
    forecast_value: float,
    hours_to_forecast: int,
    total_forecast_hours: int = 12
) -> float:
    """
    Linearly interpolate between current and forecast value.

    Args:
        current_value: Current sensor value
        forecast_value: Forecast value at total_forecast_hours
        hours_to_forecast: Hours into future for this interpolation
        total_forecast_hours: Total hours for the forecast (default 12)

    Returns:
        Interpolated value
    """
    if hours_to_forecast >= total_forecast_hours:
        return forecast_value

    # Linear interpolation
    ratio = hours_to_forecast / total_forecast_hours
    interpolated = current_value + (forecast_value - current_value) * ratio

    return round(interpolated, 1)


def calculate_visibility_from_humidity(humidity: float, temperature: float) -> Optional[float]:
    """
    Estimate visibility based on humidity and temperature.
    This is a rough approximation.

    Args:
        humidity: Relative humidity in %
        temperature: Temperature in °C

    Returns:
        Estimated visibility in km, or None if not calculable
    """
    if humidity <= 0 or humidity > 100:
        return None

    try:
        # Very rough approximation
        # High humidity = lower visibility
        if humidity > 95:
            return round(1.0, 1)  # Fog/mist
        elif humidity > 85:
            return round(5.0, 1)  # Hazy
        elif humidity > 70:
            return round(10.0, 1)  # Reduced
        else:
            return round(20.0, 1)  # Good
    except (ValueError, ZeroDivisionError):
        return None

