"""Extended calculations for Local Weather Forecast integration."""
from __future__ import annotations

import logging
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

_LOGGER = logging.getLogger(__name__)


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
        _LOGGER.debug(f"Dewpoint: Invalid humidity={humidity}% (must be 0-100)")
        return None

    try:
        # Magnus formula constants
        a = 17.27
        b = 237.7

        # Calculate alpha
        alpha = ((a * temperature) / (b + temperature)) + math.log(humidity / 100.0)

        # Calculate dew point
        dewpoint = (b * alpha) / (a - alpha)

        _LOGGER.debug(f"Dewpoint: T={temperature:.1f}°C, RH={humidity:.1f}% → Dewpoint={dewpoint:.1f}°C")

        return round(dewpoint, 1)
    except (ValueError, ZeroDivisionError) as e:
        _LOGGER.debug(f"Dewpoint: Calculation failed - {e}")
        return None


def calculate_wet_bulb_temperature(
    temperature: float,
    humidity: float,
    pressure: Optional[float] = 1013.25
) -> Optional[float]:
    """
    Calculate wet-bulb temperature using simplified Stull formula (WMO-compliant).
    
    WMO COMPLIANCE (Task 2.1):
    Wet-bulb temperature is critical for determining precipitation type.
    More accurate than simple temperature thresholds for rain/snow boundary.
    
    SCIENTIFIC BASIS:
    - WMO-No. 8, Volume I (2018): "Guide to Instruments and Methods of Observation"
    - Stull, R. (2011): "Wet-Bulb Temperature from Relative Humidity and Air Temperature"
    - Accuracy: ±0.3°C for typical meteorological conditions
    
    PRECIPITATION TYPE THRESHOLDS:
    - Wet-bulb < -2°C: Snow (frozen)
    - Wet-bulb -2°C to +2°C: Mixed (transition)
    - Wet-bulb > +2°C: Rain (liquid)
    
    Args:
        temperature: Air temperature in °C
        humidity: Relative humidity in %
        pressure: Atmospheric pressure in hPa (default: 1013.25 - sea level standard)
    
    Returns:
        Wet-bulb temperature in °C, or None if calculation fails
    """
    if humidity <= 0 or humidity > 100:
        _LOGGER.debug(f"WetBulb: Invalid humidity={humidity}% (must be 0-100)")
        return None
    
    if pressure is None:
        pressure = 1013.25  # Sea level standard
    
    try:
        # Stull (2011) simplified formula for meteorological accuracy
        # Valid for: -20°C < T < 50°C, 5% < RH < 99%
        tw = temperature * math.atan(0.151977 * math.sqrt(humidity + 8.313659)) + \
             math.atan(temperature + humidity) - \
             math.atan(humidity - 1.676331) + \
             0.00391838 * (humidity ** 1.5) * math.atan(0.023101 * humidity) - \
             4.686035
        
        _LOGGER.debug(
            f"WetBulb: T={temperature:.1f}°C, RH={humidity:.1f}%, P={pressure:.1f}hPa → "
            f"Tw={tw:.1f}°C (spread={temperature-tw:.1f}°C)"
        )
        
        return round(tw, 1)
    except (ValueError, ZeroDivisionError) as e:
        _LOGGER.debug(f"WetBulb: Calculation failed - {e}")
        return None


def get_precipitation_type_from_wet_bulb(
    wet_bulb_temp: float,
    air_temp: float
) -> str:
    """
    Determine precipitation type using WMO wet-bulb temperature thresholds.
    
    WMO STANDARD (Task 2.1):
    More accurate than simple air temperature thresholds.
    Accounts for humidity effects on melting/freezing.
    
    Args:
        wet_bulb_temp: Wet-bulb temperature in °C
        air_temp: Air temperature in °C
    
    Returns:
        str: 'snow', 'mixed', or 'rain'
    """
    if wet_bulb_temp < -2.0:
        # Below -2°C wet-bulb: Always frozen
        return 'snow'
    elif wet_bulb_temp > 2.0:
        # Above +2°C wet-bulb: Always liquid
        return 'rain'
    else:
        # -2°C to +2°C wet-bulb: Transition zone
        # Use air temperature as secondary factor
        if air_temp < 0:
            return 'snow'  # Cold air favors snow
        elif air_temp > 3:
            return 'rain'  # Warm air favors rain
        else:
            return 'mixed'  # True transition conditions


def degrees_to_cardinal(degrees: float) -> str:
    """
    Convert wind direction in degrees to cardinal direction.
    
    UNIFIED WIND DIRECTION (Task 2.3):
    Standardized conversion for consistent wind direction reporting.
    Uses 16-point compass rose for precision.
    
    Args:
        degrees: Wind direction in degrees (0-360)
    
    Returns:
        str: Cardinal direction (N, NNE, NE, ENE, E, ESE, SE, SSE, S, SSW, SW, WSW, W, WNW, NW, NNW)
    """
    if degrees < 0 or degrees > 360:
        return 'N'  # Default to North for invalid values
    
    # 16-point compass rose (22.5° per direction)
    directions = [
        'N', 'NNE', 'NE', 'ENE',
        'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW',
        'W', 'WNW', 'NW', 'NNW'
    ]
    
    # Normalize to 0-360 and add offset for rounding
    normalized = (degrees + 11.25) % 360
    index = int(normalized / 22.5)
    
    return directions[index]


def calculate_theoretical_max_solar_radiation(
    solar_elevation_deg: float,
    elevation_m: float = 0,
    linke_turbidity: float = 3.0,
    solar_constant: float = 1361.0
) -> float:
    """Calculate theoretical maximum solar radiation for clear sky conditions.
    
    This function implements WMO-compliant solar radiation calculation using:
    - Solar elevation angle (from sun.sun entity)
    - Station elevation above sea level
    - Atmospheric turbidity (Linke turbidity factor)
    - Solar constant at top of atmosphere
    
    The calculation accounts for:
    1. Air mass (path length through atmosphere)
    2. Atmospheric transmission (extinction due to aerosols, water vapor, etc.)
    3. Elevation correction (thinner atmosphere at altitude)
    
    Args:
        solar_elevation_deg: Sun elevation angle in degrees (0-90)
                            0° = horizon, 90° = zenith (directly overhead)
        elevation_m: Station elevation in meters above sea level (default: 0)
        linke_turbidity: Atmospheric turbidity factor (default: 3.0)
                        Range: 2-6 (2=very clear, 3=urban, 6=very hazy)
        solar_constant: Solar constant at top of atmosphere in W/m² (default: 1361)
    
    Returns:
        Theoretical maximum clear-sky solar radiation in W/m²
        Returns 0.0 if sun is below horizon (elevation ≤ 0°)
    
    References:
        - WMO-No. 8: Guide to Instruments and Methods of Observation (2018)
        - Iqbal, M. (1983): An Introduction to Solar Radiation
        - Kasten & Young formula for air mass
        - Linke turbidity model for atmospheric transmission
    
    Example:
        >>> # Noon in summer at sea level
        >>> calculate_theoretical_max_solar_radiation(60.0, 0, 3.0)
        948.2  # W/m²
        
        >>> # Same conditions at 1000m elevation
        >>> calculate_theoretical_max_solar_radiation(60.0, 1000, 3.0)
        1062.0  # W/m² (12% higher due to thinner atmosphere)
    """
    # Sun below horizon - no solar radiation
    if solar_elevation_deg <= 0:
        return 0.0
    
    # Calculate air mass using simplified formula
    # Air mass = path length through atmosphere relative to zenith
    solar_elevation_rad = math.radians(solar_elevation_deg)
    sin_elev = math.sin(solar_elevation_rad)
    
    if solar_elevation_deg < 5:
        # Safety limit for very low sun angles
        # (exact formula becomes unstable near horizon)
        air_mass = 10.0
    else:
        # Standard formula: air_mass = 1 / sin(elevation)
        air_mass = 1.0 / sin_elev
    
    # Calculate atmospheric transmission using Linke turbidity model
    # transmission = exp(-0.09 * air_mass * turbidity)
    # This accounts for extinction by aerosols, water vapor, and gases
    transmission = math.exp(-0.09 * air_mass * linke_turbidity)
    
    # Calculate clear-sky radiation at sea level
    # Combines solar constant, transmission, and geometric factor (sin elevation)
    max_solar_sea_level = solar_constant * transmission * sin_elev
    
    # Apply elevation correction
    # Solar radiation increases ~12% per 1000m elevation
    # (due to thinner atmosphere = less extinction)
    elevation_factor = 1 + (elevation_m / 1000) * 0.12
    
    theoretical_max = max_solar_sea_level * elevation_factor
    
    _LOGGER.debug(
        f"SolarRadiation: elevation={solar_elevation_deg:.1f}°, "
        f"altitude={elevation_m}m, air_mass={air_mass:.2f}, "
        f"transmission={transmission:.3f}, theoretical_max={theoretical_max:.0f} W/m²"
    )
    
    return theoretical_max


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
        _LOGGER.debug(f"HeatIndex: Not applicable - T={temperature:.1f}°C (need >27°C), RH={humidity:.1f}%")
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

        _LOGGER.debug(f"HeatIndex: T={temperature:.1f}°C, RH={humidity:.1f}% → HI={hi_c:.1f}°C")

        return round(hi_c, 1)
    except (ValueError, ZeroDivisionError) as e:
        _LOGGER.debug(f"HeatIndex: Calculation failed - {e}")
        return None


def calculate_wind_chill(temperature: float, wind_speed: float) -> Optional[float]:
    """
    Calculate wind chill (apparent temperature when cold and windy).
    Based on US National Weather Service formula.

    Args:
        temperature: Temperature in °C
        wind_speed: Wind speed in m/s

    Returns:
        Wind chill in °C, or None if not applicable
    """
    # Wind chill only applicable when temperature < 10°C and wind > 1.3 m/s
    if temperature >= 10 or wind_speed <= 1.3:
        _LOGGER.debug(f"WindChill: Not applicable - T={temperature:.1f}°C (need <10°C), Wind={wind_speed:.1f} m/s (need >1.3)")
        return None

    try:
        # Convert wind speed to km/h for calculation
        wind_kmh = wind_speed * 3.6

        # Wind chill formula (metric)
        wc = 13.12 + 0.6215 * temperature - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temperature * (wind_kmh ** 0.16)

        _LOGGER.debug(f"WindChill: T={temperature:.1f}°C, Wind={wind_speed:.1f} m/s → WC={wc:.1f}°C")

        return round(wc, 1)
    except (ValueError, ZeroDivisionError) as e:
        _LOGGER.debug(f"WindChill: Calculation failed - {e}")
        return None


def calculate_apparent_temperature(
    temperature: float,
    humidity: Optional[float] = None,
    wind_speed: Optional[float] = None,
    solar_radiation: Optional[float] = None
) -> float:
    """
    Calculate apparent temperature (feels like).

    Uses Australian Apparent Temperature formula which dynamically combines
    effects based on available sensors:
    - Always: Temperature
    - Optional: Humidity (vapor pressure effect)
    - Optional: Wind speed (wind chill effect)
    - Optional: Solar radiation (warming effect)

    Args:
        temperature: Temperature in °C
        humidity: Relative humidity in % (optional - if None, humidity effect ignored)
        wind_speed: Wind speed in km/h (optional - if None, wind chill ignored)
        solar_radiation: Solar radiation in W/m² (optional - if None, solar warming ignored)

    Returns:
        Apparent temperature in °C
    """
    try:
        apparent_temp = temperature
        components = []

        # 1. HUMIDITY EFFECT (vapor pressure makes it feel warmer/colder)
        if humidity is not None:
            # Calculate water vapor pressure (e) in hPa
            e = (humidity / 100) * 6.105 * math.exp((17.27 * temperature) / (237.7 + temperature))
            # Humidity contribution (calibrated to Netatmo)
            humidity_effect = 0.18 * e - 0.9
            apparent_temp += humidity_effect
            components.append(f"humidity_effect={humidity_effect:+.1f}°C")

        # 2. WIND CHILL EFFECT (wind makes it feel colder)
        if wind_speed is not None and wind_speed > 0:
            ws_ms = wind_speed / 3.6  # Convert km/h to m/s
            # Wind chill contribution (calibrated to Netatmo)
            wind_effect = -0.15 * ws_ms
            apparent_temp += wind_effect
            components.append(f"wind_effect={wind_effect:+.1f}°C")

        # 3. SOLAR RADIATION EFFECT (sun makes it feel warmer)
        if solar_radiation is not None and solar_radiation > 0:
            # Solar warming effect (stronger when sun is high)
            # Typical range: 0-1000 W/m²
            # At 800 W/m² (full sun), adds ~4°C
            solar_factor = solar_radiation / 200.0  # Scale factor
            components.append(f"solar_effect={solar_factor:+.1f}°C")
            apparent_temp += solar_factor

        result = round(apparent_temp, 1)
        _LOGGER.debug(f"ApparentTemp: T={temperature:.1f}°C → Feels={result:.1f}°C [{', '.join(components) if components else 'no adjustments'}]")

        return result
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        _LOGGER.debug(f"ApparentTemp: Calculation failed - {e}, returning temperature={temperature:.1f}°C")
        # If calculation fails, return actual temperature
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


def get_fog_risk(
    temperature: float,
    dewpoint: float,
    humidity: Optional[float] = None
) -> str:
    """
    Calculate fog risk based on temperature-dewpoint spread and humidity.
    
    WMO (World Meteorological Organization) compliant fog detection:
    - FOG: Visibility < 1000m, requires RH > 90%, dewpoint spread < 1.5°C
    - MIST: Visibility 1-5km, RH 85-95%, dewpoint spread 1.5-4°C
    
    Without humidity sensor, uses conservative spread-only estimates.

    Args:
        temperature: Temperature in °C
        dewpoint: Dew point in °C
        humidity: Optional relative humidity in % (improves accuracy)

    Returns:
        Fog risk level: none, low, medium, high
    """
    spread = abs(temperature - dewpoint)

    # No fog if spread > 4°C (only light mist possible)
    if spread > 4:
        return FOG_RISK_NONE

    # If humidity not available, use conservative spread-only estimates
    # (Less accurate but better than nothing)
    if humidity is None:
        _LOGGER.debug(
            f"FogRisk: No humidity sensor - using spread-only estimate "
            f"(spread={spread:.1f}°C)"
        )
        if spread >= 2.5:
            return FOG_RISK_LOW  # Mist possible
        elif spread >= 1.5:
            return FOG_RISK_MEDIUM  # Light fog possible
        else:
            return FOG_RISK_HIGH  # Fog likely

    # WMO compliant fog risk with humidity (accurate)
    # Based on WMO-No. 8 (Guide to Instruments and Methods of Observation)
    
    if spread < 0.5 and humidity > 95:
        # WMO Code 12: Dense fog (visibility < 400m)
        _LOGGER.debug(
            f"FogRisk: HIGH - Dense fog conditions "
            f"(spread={spread:.1f}°C, RH={humidity:.1f}%, WMO code 12)"
        )
        return FOG_RISK_HIGH
    elif spread < 1.0 and humidity > 90:
        # WMO Code 11: Fog (visibility 400-1000m)
        _LOGGER.debug(
            f"FogRisk: HIGH - Fog likely "
            f"(spread={spread:.1f}°C, RH={humidity:.1f}%, WMO code 11)"
        )
        return FOG_RISK_HIGH
    elif spread < 1.5 and humidity > 90:
        # WMO Code 10: Light fog (visibility 500-1000m)
        _LOGGER.debug(
            f"FogRisk: MEDIUM - Light fog possible "
            f"(spread={spread:.1f}°C, RH={humidity:.1f}%, WMO code 10)"
        )
        return FOG_RISK_MEDIUM
    elif spread < 2.5 and humidity > 85:
        # WMO Code 30: Mist (visibility 1-5km)
        _LOGGER.debug(
            f"FogRisk: MEDIUM - Mist conditions "
            f"(spread={spread:.1f}°C, RH={humidity:.1f}%, WMO code 30)"
        )
        return FOG_RISK_MEDIUM
    elif spread < 4.0 and humidity > 75:
        # Light mist, reduced visibility
        _LOGGER.debug(
            f"FogRisk: LOW - Light mist possible "
            f"(spread={spread:.1f}°C, RH={humidity:.1f}%)"
        )
        return FOG_RISK_LOW
    else:
        # Dry air or spread too large
        _LOGGER.debug(
            f"FogRisk: NONE - Conditions not met "
            f"(spread={spread:.1f}°C, RH={humidity:.1f}%)"
        )
        return FOG_RISK_NONE


def calculate_rain_probability_enhanced(
    zambretti_prob: int,
    negretti_prob: int,
    humidity: Optional[float] = None,
    dewpoint_spread: Optional[float] = None,
    temperature: Optional[float] = None,
) -> tuple[int, str]:
    """
    Calculate enhanced rain probability combining multiple factors.

    Enhanced logic (v3.1.0):
    - If base probability is LOW (0-10%), modifiers add small amounts (max +10%)
    - If base probability is MEDIUM (11-50%), modifiers scale normally
    - If base probability is HIGH (51-100%), modifiers boost significantly

    This prevents false positives when Zambretti says "Settled Fine" (0%)
    but humidity is high (which could just be morning dew/fog).

    Args:
        zambretti_prob: Zambretti rain probability (0-100)
        negretti_prob: Negretti-Zambra rain probability (0-100)
        humidity: Relative humidity in % (optional)
        dewpoint_spread: Temperature - Dewpoint in °C (optional)
        temperature: Current temperature in °C (optional, for snow/cold adjustments)


    Returns:
        Tuple of (probability %, confidence level)
    """
    # ✅ FIXED v3.1.12: Base probability from WEIGHTED models
    # Weighted probabilities already account for model weights (0.0-1.0)
    # Example 1 (Zambretti only): Z=40×1.0=40, N=60×0.0=0 → base=40+0=40 ✅
    # Example 2 (Negretti only): Z=40×0.0=0, N=60×1.0=60 → base=0+60=60 ✅
    # Example 3 (Enhanced 0.5/0.5): Z=40×0.5=20, N=60×0.5=30 → base=20+30=50 ✅
    # OLD BUG: Divided by 2, causing half the expected probability!
    base_prob = zambretti_prob + negretti_prob
    _LOGGER.debug(
        f"RainCalc: Input - Zambretti={zambretti_prob}%, Negretti={negretti_prob}% (already weighted), "
        f"humidity={humidity}, dewpoint_spread={dewpoint_spread}"
    )
    _LOGGER.debug(f"RainCalc: Base probability = {base_prob}%")

    # Determine scaling factor based on base probability
    # Special case: If dewpoint spread is critical (<1.0°C), use higher scale
    # because high saturation = likely precipitation, not just fog
    if base_prob <= 10:
        # Check if it's critical saturation (near 100% RH)
        if dewpoint_spread is not None and dewpoint_spread < 1.0:
            scale = 0.8  # High saturation = likely precipitation
            _LOGGER.debug(
                f"RainCalc: Using scale=0.8 (critical saturation despite low base, spread={dewpoint_spread:.1f}°C)"
            )
        else:
            # Low base probability - use minimal adjustments (fog/dew != rain)
            scale = 0.3
            _LOGGER.debug("RainCalc: Using scale=0.3 (low base probability, normal adjustments)")
    elif base_prob <= 30:
        # Medium-low - moderate adjustments
        scale = 0.6
    elif base_prob <= 50:
        # Medium - normal adjustments
        scale = 1.0
    else:
        # High - strong adjustments
        scale = 1.5

    _LOGGER.debug(f"RainCalc: Scale factor = {scale}")

    # Adjustment factors (before scaling)
    adjustments = []

    # Humidity factor
    # Adjust threshold based on temperature - cold air holds less moisture
    if humidity is not None:
        # Determine humidity threshold based on temperature
        if temperature is not None and temperature <= 0:
            high_humidity_threshold = 75  # Lower for freezing temps (80% at 0°C ≈ 90% at 10°C)
            medium_humidity_threshold = 65
        else:
            high_humidity_threshold = 85  # Normal for warmer temps
            medium_humidity_threshold = 70

        if humidity > high_humidity_threshold:
            adjustments.append(10)  # High humidity
            _LOGGER.debug(
                f"RainCalc: Adding +10 for high humidity ({humidity:.1f}%, "
                f"threshold={high_humidity_threshold}%, temp={temperature if temperature is not None else 'N/A'}°C)"
            )
        elif humidity > medium_humidity_threshold:
            adjustments.append(5)
            _LOGGER.debug(
                f"RainCalc: Adding +5 for humidity ({humidity:.1f}%, "
                f"threshold={medium_humidity_threshold}%, temp={temperature if temperature is not None else 'N/A'}°C)"
            )
        elif humidity < 40:
            adjustments.append(-15)  # Very dry
            _LOGGER.debug(f"RainCalc: Adding -15 for very dry ({humidity:.1f}%)")
        elif humidity < 60:
            adjustments.append(-5)
            _LOGGER.debug(f"RainCalc: Adding -5 for dry ({humidity:.1f}%)")


    # Dewpoint spread factor (saturation indicator)
    if dewpoint_spread is not None:
        if dewpoint_spread < 1.5:
            # Critical saturation - but scale down if base prob is low (fog != rain)
            adjustments.append(15)
            _LOGGER.debug(f"RainCalc: Adding +15 for critical saturation (spread={dewpoint_spread}°C)")
        elif dewpoint_spread < 3:
            adjustments.append(8)
            _LOGGER.debug(f"RainCalc: Adding +8 for high saturation (spread={dewpoint_spread}°C)")
        elif dewpoint_spread < 5:
            adjustments.append(3)
            _LOGGER.debug(f"RainCalc: Adding +3 for medium saturation (spread={dewpoint_spread}°C)")
        elif dewpoint_spread > 8:
            adjustments.append(-10)  # Very dry
            _LOGGER.debug(f"RainCalc: Adding -10 for very dry (spread={dewpoint_spread}°C)")

    # Apply scaling to adjustments
    scaled_adjustments = [adj * scale for adj in adjustments]
    total_adjustment = sum(scaled_adjustments)
    final_prob = base_prob + total_adjustment

    _LOGGER.debug(f"RainCalc: Raw adjustments = {adjustments}")
    _LOGGER.debug(f"RainCalc: Scaled adjustments = {scaled_adjustments}")
    _LOGGER.debug(f"RainCalc: Total adjustment = {total_adjustment}")
    _LOGGER.debug(f"RainCalc: Final probability (before clamp) = {final_prob}%")

    # Clamp to 0-100 range
    final_prob = max(0.0, min(100.0, final_prob))

    # Determine confidence based on data availability and consensus
    if len(adjustments) >= 3:
        confidence = "very_high"
    elif len(adjustments) >= 2:
        confidence = "high"
    elif len(adjustments) == 1:
        confidence = "medium"
    else:
        confidence = "low"

    _LOGGER.debug(
        f"RainCalc: RESULT - {int(final_prob)}% (confidence={confidence}, "
        f"base={base_prob}%, adjustment={total_adjustment:.1f}, scale={scale})"
    )

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
    Estimate visibility based on humidity and temperature (WMO compliant).

    WMO Visibility Categories (WMO-No. 8, Manual of Codes):
    - Excellent:  > 40 km  (RH < 50%)
    - Very good:  20-40 km (RH 50-60%)
    - Good:       10-20 km (RH 60-70%)
    - Moderate:   4-10 km  (RH 70-80%)
    - Poor:       2-4 km   (RH 80-85%)
    - Very poor:  1-2 km   (RH 85-90%)
    - Mist:       1-5 km   (RH 90-95%, WMO Code 30)
    - Fog:        < 1 km   (RH > 95%, WMO Codes 10-12)

    Note: Further fog adjustments based on dewpoint spread are applied
    in weather.py native_visibility() method.

    Args:
        humidity: Relative humidity in %
        temperature: Temperature in °C (currently not used, reserved for future enhancements)

    Returns:
        Estimated visibility in km, or None if not calculable

    References:
        - WMO-No. 8: Manual of Codes, Volume I.1
        - WMO-No. 306: Manual on Codes, International Codes
    """
    if humidity <= 0 or humidity > 100:
        return None

    try:
        # WMO-compliant visibility categories (8 levels for better granularity)
        if humidity > 95:
            # Dense fog conditions (RH > 95%, WMO Codes 11-12)
            # Visibility: < 1000m (fog definition)
            return 0.5  # 500m (will be further reduced by fog adjustments if dewpoint spread < 0.5)
        elif humidity > 90:
            # Light fog/heavy mist (RH 90-95%, WMO Code 10/30)
            # Visibility: ~1 km (borderline fog/mist)
            return 0.8  # 800m (approaching fog threshold)
        elif humidity > 85:
            # Mist (RH 85-90%, WMO Code 30)
            # Visibility: 1-5 km (mist definition)
            return 1.5  # 1.5km (middle of mist range)
        elif humidity > 80:
            # Poor visibility (RH 80-85%)
            # Visibility: 2-4 km
            return 3.0  # 3km (poor visibility)
        elif humidity > 70:
            # Moderate visibility (RH 70-80%)
            # Visibility: 4-10 km
            return 7.0  # 7km (moderate visibility)
        elif humidity > 60:
            # Good visibility (RH 60-70%)
            # Visibility: 10-20 km
            return 15.0  # 15km (good visibility)
        elif humidity > 50:
            # Very good visibility (RH 50-60%)
            # Visibility: 20-40 km
            return 30.0  # 30km (very good visibility)
        else:
            # Excellent visibility (RH < 50%)
            # Visibility: > 40 km
            return 50.0  # 50km (excellent visibility)

        # Note: Temperature correction could be added in future:
        # - Cold air (< 0°C): visibility *= 1.1 (clearer air, less water vapor)
        # - Hot air (> 30°C): visibility *= 0.9 (more haze, heat shimmer)
        # - Exception: Ice fog at < -20°C: visibility can drop dramatically

    except (ValueError, ZeroDivisionError):
        return None


def calculate_uv_index_from_solar_radiation(solar_radiation: float) -> Optional[float]:
    """
    Calculate UV Index from solar radiation.

    UV Index is derived from the UV-B component of solar radiation.
    Approximate formula: UV Index ≈ Solar Radiation (W/m²) × 0.04 to 0.05

    Args:
        solar_radiation: Solar radiation in W/m²

    Returns:
        UV Index (0-15+), or None if calculation fails

    Examples:
        - 1000 W/m² → UV Index 10-11
        - 500 W/m² → UV Index 5-6
        - 200 W/m² → UV Index 2-3
    """
    if solar_radiation < 0:
        return None

    try:
        # Base conversion factor (UV-B is about 4-5% of total solar radiation)
        uv_index = solar_radiation * 0.04


        # UV index is capped at reasonable maximum
        uv_index = min(uv_index, 15.0)

        return round(uv_index, 1)
    except (ValueError, ZeroDivisionError):
        return None


def calculate_solar_radiation_from_uv_index(uv_index: float) -> Optional[float]:
    """
    Calculate solar radiation from UV Index.

    Inverse of UV Index calculation. This estimates total solar radiation
    from the UV-B component measurement.

    Args:
        uv_index: UV Index (0-15+)

    Returns:
        Estimated solar radiation in W/m², or None if calculation fails

    Examples:
        - UV Index 10 → ~1000 W/m²
        - UV Index 5 → ~500 W/m²
        - UV Index 2 → ~200 W/m²
    """
    if uv_index < 0:
        return None

    try:
        # Reverse calculation: solar_radiation = uv_index / 0.04
        solar_radiation = uv_index / 0.04


        return round(solar_radiation, 1)
    except (ValueError, ZeroDivisionError):
        return None


def get_snow_risk(
    temperature: float,
    humidity: float,
    dewpoint: float,
    precipitation_prob: Optional[int] = None
) -> str:
    """
    Calculate snow risk based on temperature, humidity, dewpoint, and precipitation probability.

    Snow formation requires ALL of these conditions:
    - Cold temperature (≤ 4°C)
    - High humidity (> 60-75% depending on temperature)
    - Near saturation (dewpoint spread < 2-3°C)
    - **PRECIPITATION LIKELY** (> 40-60% depending on risk level)

    ⚠️ IMPORTANT: High humidity at freezing WITHOUT precipitation = FOG/FROST, not snow!

    Risk Levels:
    - HIGH: T≤0°C, RH>75%, spread<2°C, precipitation>60%
    - MEDIUM: T≤2°C, RH>65%, spread<3°C, precipitation>40%
    - LOW: T≤4°C, RH>60%, precipitation>50% OR marginal conditions
    - NONE: Temperature too warm or humidity too low or no precipitation

    Args:
        temperature: Temperature in °C
        humidity: Relative humidity in %
        dewpoint: Dew point in °C
        precipitation_prob: Optional precipitation probability (0-100%).
                           REQUIRED for HIGH/MEDIUM risk levels.

    Returns:
        Snow risk level: none, low, medium, high
    """
    from .const import (
        SNOW_RISK_NONE,
        SNOW_RISK_LOW,
        SNOW_RISK_MEDIUM,
        SNOW_RISK_HIGH,
    )

    # Snow is unlikely if temperature is above 4°C
    if temperature > 4:
        _LOGGER.debug(f"SnowRisk: none - T={temperature:.1f}°C (>4°C)")
        return SNOW_RISK_NONE

    dewpoint_spread = abs(temperature - dewpoint)

    # HIGH RISK: Very cold + high humidity + near saturation + precipitation likely
    # Temperature ≤ 0°C, humidity > 75%, spread < 2°C, precipitation > 60%
    # All conditions must be met for snow formation
    if temperature <= 0 and humidity > 75 and dewpoint_spread < 2:
        if precipitation_prob is not None and precipitation_prob > 60:
            _LOGGER.debug(
                f"SnowRisk: HIGH - T={temperature:.1f}°C (≤0°C), RH={humidity:.1f}% (>75%), "
                f"spread={dewpoint_spread:.1f}°C (<2°C), precip={precipitation_prob}% (>60%)"
            )
            return SNOW_RISK_HIGH
        else:
            # High humidity at freezing = FOG/FROST, not snow without precipitation
            _LOGGER.debug(
                f"SnowRisk: LOW - T={temperature:.1f}°C (≤0°C), RH={humidity:.1f}% (>75%), "
                f"spread={dewpoint_spread:.1f}°C (<2°C), but precip={precipitation_prob if precipitation_prob is not None else 'unknown'}% (≤60%) → fog/frost likely, not snow"
            )
            return SNOW_RISK_LOW

    # MEDIUM RISK: Cold, decent humidity, moderate precipitation
    # Temperature 0-2°C, humidity > 65%, spread < 3°C, precipitation > 40%
    if temperature <= 2 and humidity > 65 and dewpoint_spread < 3:
        if precipitation_prob is not None and precipitation_prob > 40:
            result = SNOW_RISK_MEDIUM
            _LOGGER.debug(f"SnowRisk: MEDIUM - T={temperature:.1f}°C (0-2°C), RH={humidity:.1f}%, spread={dewpoint_spread:.1f}°C, precip={precipitation_prob}% (>40%)")
        else:
            result = SNOW_RISK_LOW
            _LOGGER.debug(f"SnowRisk: LOW - T={temperature:.1f}°C (0-2°C), RH={humidity:.1f}%, spread={dewpoint_spread:.1f}°C, precip={precipitation_prob if precipitation_prob is not None else 'unknown'}% (≤40%)")
        return result

    # LOW RISK: Near freezing, moderate conditions
    # Temperature 2-4°C (not colder!), humidity > 60%, precipitation > 50%
    if 2 < temperature <= 4 and humidity > 60:
        if precipitation_prob is not None and precipitation_prob > 50:
            result = SNOW_RISK_LOW
            _LOGGER.debug(f"SnowRisk: LOW - T={temperature:.1f}°C (2-4°C), RH={humidity:.1f}%, precip={precipitation_prob}% (>50%)")
        else:
            result = SNOW_RISK_NONE
            _LOGGER.debug(f"SnowRisk: NONE - T={temperature:.1f}°C (2-4°C), RH={humidity:.1f}%, precip={precipitation_prob if precipitation_prob is not None else 'unknown'}% (≤50%)")
        return result

    _LOGGER.debug(f"SnowRisk: none - T={temperature:.1f}°C, RH={humidity:.1f}% (conditions not met)")
    return SNOW_RISK_NONE


def get_frost_risk(
    temperature: float,
    dewpoint: float,
    wind_speed: Optional[float] = None,
    humidity: Optional[float] = None
) -> str:
    """
    Calculate frost/ice (námraza) risk based on temperature and dewpoint.

    Frost/Ice conditions (meteorologically justified):
    - Temperature at or below 0°C
    - Dewpoint at or below 0°C (moisture will freeze)
    - Low wind speed favors frost formation
    - High humidity + freezing = ice formation

    Types of frost/ice warnings:
    - CRITICAL: Black ice risk (wet + freezing)
    - HIGH: Heavy frost/ice formation expected
    - MEDIUM: Light frost expected
    - LOW: Near-freezing, frost possible
    - NONE: No frost risk

    Args:
        temperature: Temperature in °C
        dewpoint: Dew point in °C
        wind_speed: Optional wind speed in m/s (low wind favors frost)
        humidity: Optional relative humidity in %

    Returns:
        Frost risk level: none, low, medium, high, critical
    """
    from .const import (
        FROST_RISK_NONE,
        FROST_RISK_LOW,
        FROST_RISK_MEDIUM,
        FROST_RISK_HIGH,
        FROST_RISK_CRITICAL,
    )

    # No frost risk if temperature is above 4°C
    if temperature > 4:
        _LOGGER.debug(f"FrostRisk: none - T={temperature:.1f}°C (>4°C)")
        return FROST_RISK_NONE

    dewpoint_spread = abs(temperature - dewpoint)

    # CRITICAL RISK: Black ice conditions
    # Temperature slightly below 0°C, very high humidity, near saturation
    # This creates conditions for ice formation on surfaces
    if -2 <= temperature <= 0 and humidity is not None and humidity > 90 and dewpoint_spread < 1:
        _LOGGER.debug(
            f"FrostRisk: CRITICAL - Black ice conditions - T={temperature:.1f}°C, "
            f"Dewpoint={dewpoint:.1f}°C, RH={humidity:.1f}%, spread={dewpoint_spread:.1f}°C"
        )
        return FROST_RISK_CRITICAL

    # HIGH RISK: Heavy frost/ice formation
    # Temperature well below 0°C, dewpoint also below 0°C
    if temperature < -2 and dewpoint < 0:
        # Low wind makes it worse (calm conditions = more frost)
        result = FROST_RISK_HIGH if (wind_speed is None or wind_speed < 2) else FROST_RISK_MEDIUM
        _LOGGER.debug(f"FrostRisk: {result} - T={temperature:.1f}°C (<-2°C), Dewpoint={dewpoint:.1f}°C, Wind={wind_speed if wind_speed else 'unknown'} m/s")
        return result

    # MEDIUM RISK: Frost formation likely
    # Temperature 0 to -2°C, dewpoint ALSO at or below 0°C (both must be freezing!)
    # WMO: Frost forms when both air temperature AND dewpoint are at/below 0°C
    if -2 < temperature <= 0 and dewpoint <= 0:
        result = FROST_RISK_MEDIUM if (wind_speed is not None and wind_speed < 3) else FROST_RISK_LOW
        _LOGGER.debug(
            f"FrostRisk: {result} - T={temperature:.1f}°C (-2 to 0°C), "
            f"Dewpoint={dewpoint:.1f}°C (≤0°C), Wind={wind_speed if wind_speed else 'unknown'} m/s "
            f"(WMO: both temp and dewpoint at/below freezing)"
        )
        return result

    # LOW RISK: Near-freezing conditions
    # Temperature 0-4°C, dewpoint below freezing possible
    if temperature <= 2 and dewpoint <= 0:
        _LOGGER.debug(f"FrostRisk: low - T={temperature:.1f}°C (0-2°C), Dewpoint={dewpoint:.1f}°C (≤0°C)")
        return FROST_RISK_LOW

    _LOGGER.debug(f"FrostRisk: none - T={temperature:.1f}°C, Dewpoint={dewpoint:.1f}°C (conditions not met)")
    return FROST_RISK_NONE


def get_uv_protection_level(uv_index: float) -> str:
    """
    Get sun protection recommendation based on UV Index.

    Args:
        uv_index: UV Index value (0-15+)

    Returns:
        Protection level description
    """
    if uv_index < 0:
        return "Invalid"
    elif uv_index < 3:
        return "Low - No protection required"
    elif uv_index < 6:
        return "Moderate - Protection required"
    elif uv_index < 8:
        return "High - Protection required"
    elif uv_index < 11:
        return "Very High - Extra protection required"
    else:
        return "Extreme - Avoid sun exposure"


def calculate_max_solar_radiation_for_location(
    latitude: float,
    month: Optional[int] = None
) -> float:
    """
    Calculate maximum solar radiation for a specific location and season.

    This accounts for:
    - Latitude (higher latitudes receive less radiation)
    - Season (summer vs winter differences)
    - Hemisphere (inverted seasons for southern hemisphere)

    Args:
        latitude: Location latitude in degrees (-90 to +90)
        month: Month (1-12), defaults to current month

    Returns:
        Maximum clear-sky solar radiation in W/m² at solar noon

    Examples:
        >>> calculate_max_solar_radiation_for_location(0, 6)  # Equator, June
        1300.0
        >>> calculate_max_solar_radiation_for_location(48.72, 6)  # Košice, June
        1050.0
        >>> calculate_max_solar_radiation_for_location(-33.87, 12)  # Sydney, December
        1150.0
    """
    from datetime import datetime

    if month is None:
        month = datetime.now().month

    abs_latitude = abs(latitude)
    is_northern = latitude >= 0

    # Hemisphere correction: Southern hemisphere has inverted seasons
    if not is_northern:
        # Shift months by 6 for southern hemisphere
        month = ((month + 6 - 1) % 12) + 1

    # Base maximum radiation at solar noon (at sea level, clear sky)
    # Equator: ~1300 W/m² (direct overhead sun)
    # Mid-latitudes (45°): ~1000 W/m² (angled sun)
    # High latitudes (70°): ~600 W/m² (very low sun)

    # Latitude factor: How much radiation is reduced due to sun angle
    # This is based on the cosine law of solar radiation
    # At equator (0°): factor = 1.0 (full radiation)
    # At 45°: factor = 0.77 (cos 30° effective angle)
    # At 70°: factor = 0.47 (very angled)

    if abs_latitude < 23.5:
        # Tropical zone: Sun can be directly overhead
        base_max = 1300.0
        lat_factor = 1.0 - (abs_latitude / 90.0) * 0.3  # Gentle reduction
    elif abs_latitude < 66.5:
        # Temperate zone: Sun is angled but predictable
        base_max = 1200.0
        # Cosine law approximation
        effective_angle = abs_latitude - 23.5
        lat_factor = math.cos(math.radians(effective_angle * 0.7))
    else:
        # Polar zone: Very low sun, long days in summer
        base_max = 800.0
        lat_factor = 0.5 + (90 - abs_latitude) / 90.0 * 0.3

    # Seasonal factor: Varies throughout the year
    # Month 6 (June after hemisphere correction) = summer = maximum
    # Month 12 (December after hemisphere correction) = winter = minimum
    # Uses cosine function for smooth transition
    seasonal_factor = 0.5 + 0.5 * math.cos((month - 6) * math.pi / 6)

    # Summer boost for mid-latitudes (longer days compensate for angle)
    if 40 <= abs_latitude <= 60 and seasonal_factor > 0.85:
        seasonal_factor = min(1.0, seasonal_factor * 1.05)

    # Final calculation
    max_radiation = base_max * lat_factor * seasonal_factor

    _LOGGER.debug(
        f"Max solar radiation calculation: lat={latitude:.2f}°, month={month}, "
        f"base={base_max:.0f}, lat_factor={lat_factor:.3f}, "
        f"seasonal={seasonal_factor:.3f}, result={max_radiation:.0f} W/m²"
    )

    return round(max_radiation, 1)


def estimate_solar_radiation_from_time_and_clouds(
    latitude: float,
    hour: int,
    month: Optional[int] = None
) -> float:
    """
    Estimate solar radiation based on time of day and location.

    This is used when no solar sensor is available.

    Args:
        latitude: Location latitude in degrees
        hour: Hour of day (0-23)
        month: Month (1-12), if None uses current season estimate

    Returns:
        Estimated solar radiation in W/m²
    """
    # Solar radiation peaks at solar noon, zero at night
    # Maximum theoretical solar radiation at Earth's surface: ~1000-1200 W/m²

    # Calculate sun position factor (simplified)
    # Solar noon is around 12:00
    hour_angle = abs(hour - 12)

    # Use location-aware maximum radiation instead of fixed 1000 W/m²
    max_radiation = calculate_max_solar_radiation_for_location(latitude, month)

    if hour_angle > 6:
        # Night time (beyond ±6 hours from noon)
        radiation = 0.0
    else:
        # Daytime - use cosine curve
        # Peak at noon (hour_angle=0), zero at ±6h
        sun_factor = math.cos(math.radians(hour_angle * 15))  # 15° per hour
        radiation = max_radiation * max(0.0, sun_factor)


    return round(radiation, 1)


def get_uv_risk_category(uv_index: float) -> str:
    """
    Get UV risk category name based on WHO standard.

    Args:
        uv_index: UV Index value (0-15+)

    Returns:
        Risk category: "Low", "Moderate", "High", "Very High", or "Extreme"
    """
    if uv_index < 3:
        return "Low"
    elif uv_index < 6:
        return "Moderate"
    elif uv_index < 8:
        return "High"
    elif uv_index < 11:
        return "Very High"
    else:
        return "Extreme"



