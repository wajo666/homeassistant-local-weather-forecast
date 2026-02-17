"""Advanced Forecast Calculator for Local Weather Forecast.

This module implements sophisticated meteorological forecasting models:
- Pressure trend forecasting with exponential smoothing
- Temperature modeling with diurnal cycle
- Zambretti algorithm for hourly conditions
- Rain probability based on pressure evolution
- Daily aggregation from hourly predictions
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import math
from typing import TypedDict

from homeassistant.core import HomeAssistant

from .const import (
    FORECAST_MODEL_ZAMBRETTI,
    FORECAST_MODEL_NEGRETTI,
    FORECAST_MODEL_ENHANCED,
)
from .zambretti import calculate_zambretti_forecast
from .forecast_mapping import map_forecast_to_condition, ZAMBRETTI_LETTER_TO_CODE


class Forecast(TypedDict, total=False):
    """Typed dictionary for forecast data."""
    datetime: str
    condition: str
    temperature: float
    native_temperature: float
    templow: float | None  # Daily low temperature
    native_templow: float | None
    precipitation: float | None
    native_precipitation: float | None
    precipitation_probability: int | None
    is_daytime: bool | None  # Whether forecast is for daytime or nighttime
    # Extended forecast data (added v3.2.0)
    pressure: float | None  # Sea-level pressure in hPa
    native_pressure: float | None  # Native unit pressure
    humidity: float | None  # Relative humidity in % (using float for consistency with round())
    dew_point: float | None  # Dew point in °C
    native_dew_point: float | None  # Native unit dew point
    apparent_temperature: float | None  # Feels-like temperature in °C
    native_apparent_temp: float | None  # Native unit apparent temperature

_LOGGER = logging.getLogger(__name__)


class PressureModel:
    """Model atmospheric pressure trends with exponential smoothing.

    Uses:
    - Current pressure
    - 3-hour pressure change rate
    - Exponential smoothing to simulate natural pressure evolution
    - Damping factor to prevent unrealistic extremes
    """

    def __init__(
        self,
        current_pressure: float,
        pressure_change_3h: float,
        smoothing_factor: float = 0.3,
        damping_factor: float = 0.95
    ):
        """Initialize pressure model.

        Args:
            current_pressure: Current pressure in hPa
            pressure_change_3h: Pressure change over last 3 hours in hPa
            smoothing_factor: Exponential smoothing (0-1, higher = more responsive)
            damping_factor: Rate decay factor (0-1, closer to 1 = slower decay)
        """
        self.current_pressure = current_pressure
        self.change_rate_3h = pressure_change_3h
        self.change_rate_1h = pressure_change_3h / 3.0  # Convert to hourly rate
        self.smoothing_factor = smoothing_factor
        self.damping_factor = damping_factor

        # Backwards compatibility aliases for old tests
        self.current = current_pressure
        self.change_3h = pressure_change_3h
        self.change_per_hour = pressure_change_3h / 3.0

    def predict(self, hours_ahead: int) -> float:
        """Predict pressure N hours ahead.

        Uses exponential smoothing with damping to simulate natural pressure evolution.
        Formula: P(t+h) = P(t) + Σ(rate * damping^i)

        Args:
            hours_ahead: Hours into the future

        Returns:
            Predicted pressure in hPa
        """
        if hours_ahead == 0:
            return self.current_pressure

        # Apply exponentially damped change rate
        total_change = 0.0
        current_rate = self.change_rate_1h

        for hour in range(hours_ahead):
            total_change += current_rate
            # Dampen the rate for next hour
            current_rate *= self.damping_factor

        # Apply realistic limits to prevent unrealistic forecasts
        # Maximum change: ±20 hPa over 24 hours (scales proportionally)
        max_change = 20.0 * (hours_ahead / 24.0)  # Scale linearly with time
        total_change = max(-max_change, min(max_change, total_change))

        predicted = self.current_pressure + total_change

        # Constrain to realistic absolute pressure range (910-1085 hPa)
        # Matches Negretti-Zambra global range for consistency
        predicted = max(910.0, min(1085.0, predicted))

        # Clamp to realistic atmospheric pressure range (910-1085 hPa)
        result = max(910.0, min(1085.0, predicted))

        _LOGGER.debug(
            f"PressureModel: {hours_ahead}h → {result:.1f} hPa "
            f"(current={self.current_pressure:.1f}, change={total_change:+.1f}, rate={self.change_rate_3h:+.1f}/3h)"
        )

        return result

    def get_trend(self, hours_ahead: int) -> str:
        """Get pressure trend description.

        Args:
            hours_ahead: Hours into the future

        Returns:
            Trend string: 'rising', 'falling', or 'steady'
        """
        future_pressure = self.predict(hours_ahead)
        change = future_pressure - self.current_pressure

        if change > 1.0:
            return "rising"
        elif change < -1.0:
            return "falling"
        else:
            return "steady"


class TemperatureModel:
    """Model temperature with diurnal (daily) cycle and solar radiation effects.

    Combines:
    - Current temperature
    - Temperature trend (hourly change rate with exponential decay)
    - Solar-aware diurnal cycle (based on sun position with astral library)
    - Solar radiation warming (when sensor available)
    - Cloud cover reduction (when sensor available)
    - Seasonal amplitude adjustments
    - Hemisphere support
    """

    def __init__(
        self,
        current_temp: float,
        change_rate_1h: float,
        diurnal_amplitude: float | None = None,
        trend_damping: float = 0.75,
        solar_radiation: float | None = None,
        cloud_cover: float | None = None,
        humidity: float | None = None,
        wind_speed: float | None = None,
        hass: HomeAssistant | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        hemisphere: str = "north",
        elevation: float | None = None
    ):
        """Initialize temperature model.

        Args:
            current_temp: Current temperature in °C
            change_rate_1h: Temperature change rate per hour
            diurnal_amplitude: Daily temperature swing amplitude (None = auto-calculate from season/sun)
            trend_damping: Exponential decay factor for trend (0.75 = trend halves in ~3 hours)
            solar_radiation: Current solar radiation in W/m² (None = solar effect ignored, only works during daylight)
            cloud_cover: Current cloud cover in % (None = estimated from humidity if available)
            humidity: Relative humidity in % (used to estimate cloud cover if sensor unavailable)
            wind_speed: Current wind speed in m/s (None = assume calm conditions for radiative cooling)
            hass: Home Assistant instance for location fallback
            latitude: Station latitude (-90 to +90, None = use HA config)
            longitude: Station longitude (-180 to +180, None = use HA config)
            hemisphere: "north" or "south"
            elevation: Station elevation in meters (None = use HA config or 0)
        """
        self.current_temp = current_temp
        self.change_rate_1h = change_rate_1h
        self.trend_damping = trend_damping
        self.current_hour = datetime.now(timezone.utc).hour
        self.solar_radiation = solar_radiation
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.hemisphere = hemisphere
        self.hass = hass

        # Get location coordinates
        if latitude is not None and longitude is not None:
            self.latitude = latitude
            self.longitude = longitude
        elif hass is not None:
            self.latitude = hass.config.latitude
            self.longitude = hass.config.longitude
        else:
            # Fallback to Košice, Slovakia (example location)
            self.latitude = 48.72
            self.longitude = 21.25
            _LOGGER.debug(
                f"TempModel: No location specified, using fallback: "
                f"{self.latitude}°N, {self.longitude}°E"
            )
        
        # Get elevation (affects diurnal amplitude)
        if elevation is not None:
            self.elevation = float(elevation)
        elif hass is not None and hasattr(hass.config, 'elevation'):
            try:
                self.elevation = float(hass.config.elevation)
            except (TypeError, ValueError):
                self.elevation = 0.0  # Fallback if elevation is Mock or invalid
        else:
            self.elevation = 0.0  # Sea level fallback
        
        # Calculate continentality (0 = ocean, 1 = deep interior)
        # Based on distance from coast - approximated by longitude position
        # This is a simplification: proper method would need actual distance to coast
        # For Europe/Asia: center of continent ~60-90°E, coasts at edges
        # For Americas: center ~100°W, coasts at edges
        self.continentality = self._estimate_continentality(self.latitude, self.longitude)

        # Auto-calculate diurnal amplitude if not specified
        if diurnal_amplitude is None:
            current_month = datetime.now(timezone.utc).month
            self.diurnal_amplitude = self._get_seasonal_amplitude(current_month)
            _LOGGER.debug(
                f"TempModel: Auto-calculated seasonal amplitude: {self.diurnal_amplitude}°C "
                f"(lat={self.latitude:.1f}°, elev={self.elevation:.0f}m, "
                f"continent={self.continentality:.2f}, month={current_month}, hemisphere={hemisphere})"
            )
        else:
            self.diurnal_amplitude = diurnal_amplitude

        # Cloud cover estimation: If sensor not available, estimate from humidity
        # This is critical for radiative cooling calculations at night
        if cloud_cover is not None:
            self.cloud_cover = cloud_cover
            _LOGGER.debug(f"Cloud cover from sensor: {self.cloud_cover:.0f}%")
        elif humidity is not None:
            # Empirical relationship: high humidity correlates with clouds
            # Based on typical RH-cloud relationships:
            # RH < 50%: mostly clear (0-20% clouds)
            # RH 50-70%: partly cloudy (20-50% clouds)
            # RH 70-85%: mostly cloudy (50-80% clouds)
            # RH > 85%: overcast (80-100% clouds)
            if humidity < 50:
                self.cloud_cover = humidity * 0.4  # 0-20%
            elif humidity < 70:
                self.cloud_cover = 20 + (humidity - 50) * 1.5  # 20-50%
            elif humidity < 85:
                self.cloud_cover = 50 + (humidity - 70) * 2.0  # 50-80%
            else:
                self.cloud_cover = 80 + (humidity - 85) * 1.33  # 80-100%
            _LOGGER.debug(
                f"Cloud cover estimated from humidity: {self.cloud_cover:.0f}% "
                f"(RH={humidity:.1f}%)"
            )
        else:
            # No cloud/humidity data: assume moderate conditions (50% clouds)
            # This is conservative - neither full cooling nor full blocking
            self.cloud_cover = 50.0
            _LOGGER.debug(
                "Cloud cover unknown: assuming 50% (moderate conditions) for radiative calculations"
            )

    def predict(self, hours_ahead: int) -> float:
        """Predict temperature N hours ahead.

        Combines exponentially damped trend with sinusoidal diurnal cycle
        and solar radiation warming effect.
        Peak at 14:00, minimum at 04:00.

        Args:
            hours_ahead: Hours into the future

        Returns:
            Predicted temperature in °C
        """
        if hours_ahead == 0:
            return self.current_temp

        # Exponentially damped trend component with cap
        # Trend influence decreases over time to prevent unrealistic long-term accumulation
        # Cap maximum trend contribution to ±5°C to avoid unrealistic extremes
        trend_change = 0.0
        current_rate = self.change_rate_1h

        for hour in range(hours_ahead):
            # Apply diurnal damping: warming trends are moderated during natural cooling periods
            # This prevents unrealistic temperature rise after natural cooling should occur
            future_hour_temp = (self.current_hour + hour + 1) % 24
            
            # Moderate warming trends during cooling period (18:00-06:00)
            # Changed from 16:00 to 18:00 to allow natural afternoon cooling from 14:00-18:00
            if 18 <= future_hour_temp or future_hour_temp < 6:
                if current_rate > 0:  # Only moderate warming, not cooling
                    # Reduce warming trend by 50% during evening/night
                    # This allows some trend influence but prevents unrealistic warming
                    trend_change += current_rate * 0.5
                else:
                    # Cooling trends work normally
                    trend_change += current_rate
            else:
                # Daytime (06:00-18:00): normal trend influence
                trend_change += current_rate
            
            current_rate *= self.trend_damping  # Decay the trend influence

        # Cap trend contribution to realistic limits (±5°C over forecast period)
        trend_change = max(-5.0, min(5.0, trend_change))

        # Diurnal cycle component - USE REAL SUN POSITION
        # Get actual sunrise/sunset times to calculate proper diurnal cycle
        diurnal_change = 0.0
        
        if self.hass is not None:
            sun_entity = self.hass.states.get("sun.sun")
            if sun_entity:
                try:
                    from homeassistant.util import dt as dt_util
                    
                    # Get sunrise and sunset times for accurate diurnal calculation
                    next_rising_str = sun_entity.attributes.get("next_rising")
                    next_setting_str = sun_entity.attributes.get("next_setting")
                    
                    if next_rising_str and next_setting_str:
                        next_rising = dt_util.parse_datetime(next_rising_str)
                        next_setting = dt_util.parse_datetime(next_setting_str)
                        
                        if next_rising and next_setting:
                            # Calculate for current and future hour
                            sunrise_hour = next_rising.hour + next_rising.minute / 60.0
                            sunset_hour = next_setting.hour + next_setting.minute / 60.0
                            
                            # Daylight duration - needed for temperature maximum calculation
                            daylight_duration = sunset_hour - sunrise_hour
                            if daylight_duration < 0:
                                daylight_duration += 24
                            
                            # Temperature minimum: ~30min before sunrise
                            temp_min_hour = sunrise_hour - 0.5
                            if temp_min_hour < 0:
                                temp_min_hour += 24
                            
                            # Temperature maximum: varies by season/daylength
                            # References:
                            # - WMO (2017): "Maximum temperature typically occurs at 14:00-15:00 local time"
                            # - Oke (1987): "Peak surface temperature lags solar noon by 2-3 hours"
                            # Winter (short days < 10h): earlier peak ~13:00-13:30
                            # Spring/Autumn (10-14h): standard peak ~14:00-14:30
                            # Summer (long days > 14h): later peak ~15:00-15:30
                            solar_noon = (sunrise_hour + sunset_hour) / 2.0
                            if daylight_duration < 10.0:
                                # Winter: peak 1.5-2h after solar noon
                                temp_max_hour = solar_noon + 1.5
                            elif daylight_duration < 14.0:
                                # Spring/Autumn: peak 2-2.5h after solar noon
                                temp_max_hour = solar_noon + 2.0
                            else:
                                # Summer: peak 2.5-3h after solar noon
                                temp_max_hour = solar_noon + 2.5
                            
                            # Scale amplitude by daylight duration (winter = less warming)
                            # Standard day = 12h, winter day = 8-9h, summer = 15-16h
                            # In winter, shorter days mean smaller temperature swings
                            daylight_factor = min(1.0, daylight_duration / 12.0)
                            
                            # Additional winter damping for short days (< 10h daylight)
                            # This prevents abrupt temperature changes in winter afternoons
                            if daylight_duration < 10.0:
                                # Extra reduction: 10-20% less for very short days
                                extra_winter_damping = 0.8 + (daylight_duration - 8.0) * 0.1
                                daylight_factor *= extra_winter_damping
                            
                            effective_amplitude = self.diurnal_amplitude * daylight_factor
                            
                            # Calculate diurnal position for current and future hour
                            def get_diurnal_temp(hour: float, min_hour: float, max_hour: float, amplitude: float) -> float:
                                """Calculate diurnal temperature offset at given hour.
                                
                                Uses radiative cooling model for nighttime based on:
                                - Cloud cover (clouds trap heat, reduce cooling)
                                - Humidity (water vapor absorbs IR, slows cooling)
                                
                                References:
                                - Oke (1987): "Boundary Layer Climates"
                                - Clear sky: 5-7°C cooling, Overcast: 1-2°C cooling
                                """
                                # Night time (after sunset or before sunrise): cooling toward minimum
                                if hour < sunrise_hour or hour >= sunset_hour:
                                    # Night length: from sunset to sunrise
                                    night_length = (24 - sunset_hour) + sunrise_hour
                                    
                                    # Calculate hours from sunset
                                    if hour >= sunset_hour:
                                        # After sunset (same day)
                                        hours_from_sunset = hour - sunset_hour
                                    else:
                                        # Before sunrise (next day)
                                        hours_from_sunset = (24 - sunset_hour) + hour
                                    
                                    # === RADIATIVE COOLING MODEL ===
                                    # Nighttime cooling rate depends on atmospheric conditions
                                    
                                    # Base cooling rate (clear sky, dry air, calm wind)
                                    radiative_cooling_rate = 1.0
                                    
                                    # Cloud cover STRONGLY reduces radiative cooling
                                    # Empirical: 100% clouds reduces cooling by ~70%
                                    # Physical: clouds emit IR back to surface
                                    if self.cloud_cover is not None:
                                        cloud_factor = 1.0 - (self.cloud_cover / 100.0) * 0.7
                                        radiative_cooling_rate *= cloud_factor
                                        _LOGGER.debug(
                                            f"Radiative cooling - cloud_cover={self.cloud_cover:.0f}%, "
                                            f"cloud_factor={cloud_factor:.2f}"
                                        )
                                    
                                    # High humidity reduces cooling (water vapor absorbs IR)
                                    # Empirical: RH > 80% reduces cooling by up to ~30%
                                    if self.humidity is not None and self.humidity > 80:
                                        humidity_factor = 1.0 - (self.humidity - 80) / 20.0 * 0.3
                                        radiative_cooling_rate *= humidity_factor
                                        _LOGGER.debug(
                                            f"Radiative cooling - humidity={self.humidity:.0f}%, "
                                            f"humidity_factor={humidity_factor:.2f}"
                                        )
                                    
                                    # Wind mixing prevents temperature inversion and reduces surface cooling
                                    # Calm night (0 m/s): max radiative cooling (strong inversion)
                                    # Breezy night (3-5 m/s): reduced cooling (~20-40% less)
                                    # Windy night (>8 m/s): minimal cooling (~60% less, well-mixed atmosphere)
                                    # Based on: Oke (1987), Geiger et al. (2009)
                                    if self.wind_speed is not None:
                                        if self.wind_speed < 1.0:
                                            # Calm: full radiative cooling (factor = 1.0)
                                            wind_factor = 1.0
                                        elif self.wind_speed < 3.0:
                                            # Light breeze: slight mixing (factor = 0.9-1.0)
                                            wind_factor = 1.0 - (self.wind_speed - 1.0) / 2.0 * 0.1
                                        elif self.wind_speed < 5.0:
                                            # Moderate breeze: noticeable mixing (factor = 0.7-0.9)
                                            wind_factor = 0.9 - (self.wind_speed - 3.0) / 2.0 * 0.2
                                        elif self.wind_speed < 8.0:
                                            # Fresh breeze: strong mixing (factor = 0.5-0.7)
                                            wind_factor = 0.7 - (self.wind_speed - 5.0) / 3.0 * 0.2
                                        else:
                                            # Strong wind: well-mixed, minimal surface cooling (factor = 0.4)
                                            wind_factor = 0.4
                                        
                                        radiative_cooling_rate *= wind_factor
                                        _LOGGER.debug(
                                            f"Radiative cooling - wind_speed={self.wind_speed:.1f}m/s, "
                                            f"wind_factor={wind_factor:.2f}"
                                        )
                                    
                                    # === COOLING CURVE ===
                                    # Cooling curve: gradual cooling from 0 at sunset to -amplitude at minimum
                                    # Use gentler exponential to avoid unrealistic rapid cooling
                                    if night_length > 0:
                                        progress = hours_from_sunset / night_length  # 0 at sunset, 1 at sunrise
                                        
                                        # Modified cosine for more realistic cooling
                                        # At sunset (progress=0): offset = 0
                                        # At midnight-ish (progress=0.5): offset ≈ -amplitude * 0.3
                                        # At minimum before sunrise: offset ≈ -amplitude * 0.5
                                        # Using (1 - cos) / 2 gives smooth S-curve
                                        cooling_factor = (1 - math.cos(progress * math.pi)) / 2.0
                                        
                                        # Apply radiative cooling rate
                                        # Clear sky: full cooling (rate=1.0)
                                        # Cloudy: reduced cooling (rate=0.3-0.7)
                                        # Very cloudy + humid: minimal cooling (rate=0.2)
                                        max_cooling = amplitude * 0.5  # Base maximum cooling
                                        actual_cooling = max_cooling * radiative_cooling_rate
                                        
                                        return -actual_cooling * cooling_factor
                                    return -amplitude * 0.25 * radiative_cooling_rate
                                
                                # Daytime: warming from minimum to maximum
                                else:
                                    # Hours from minimum to maximum
                                    hours_from_min = hour - min_hour
                                    if hours_from_min < 0:
                                        hours_from_min += 24
                                    
                                    hours_min_to_max = max_hour - min_hour
                                    if hours_min_to_max < 0:
                                        hours_min_to_max += 24
                                    
                                    if hours_from_min <= hours_min_to_max:
                                        # Warming phase: sine curve from -amplitude to +amplitude
                                        progress = hours_from_min / hours_min_to_max
                                        return amplitude * (math.sin(progress * math.pi - math.pi/2))
                                    else:
                                        # Cooling phase after maximum: logarithmic decay (smoother transition)
                                        # Temperature drops gradually from peak toward evening minimum
                                        # This creates a realistic afternoon cooling pattern
                                        # References: Oke (1987) - surface temperature response
                                        hours_from_max = hour - max_hour
                                        # Handle day wrap-around: if negative, it's actually next day
                                        if hours_from_max < 0:
                                            hours_from_max += 24
                                        
                                        # Logarithmic cooling with gradual initial drop
                                        # At +0.5h after max (14:30): ~97% remaining
                                        # At +1h after max (15:00): ~93% remaining  
                                        # At +2h after max (16:00): ~86% remaining
                                        # At +4h after max (18:00): ~73% remaining
                                        # At +8h after max (22:00): ~53% remaining
                                        # Formula: amplitude * (1 - k * log(1 + t))
                                        # where k controls cooling rate (increased from 0.12 to 0.18)
                                        k = 0.18
                                        fraction = max(0.1, 1.0 - k * math.log(1.0 + hours_from_max))
                                        return amplitude * fraction
                            
                            current_diurnal = get_diurnal_temp(
                                float(self.current_hour), temp_min_hour, temp_max_hour, effective_amplitude
                            )
                            future_hour = (self.current_hour + hours_ahead) % 24
                            future_diurnal = get_diurnal_temp(
                                float(future_hour), temp_min_hour, temp_max_hour, effective_amplitude
                            )
                            
                            diurnal_change = future_diurnal - current_diurnal
                            
                            _LOGGER.debug(
                                f"Sun-based diurnal: current_hour={self.current_hour}, future_hour={future_hour}, "
                                f"sunrise={sunrise_hour:.1f}, sunset={sunset_hour:.1f}, "
                                f"temp_min={temp_min_hour:.1f}, temp_max={temp_max_hour:.1f}, "
                                f"daylight={daylight_duration:.1f}h, daylight_factor={daylight_factor:.2f}, "
                                f"current_offset={current_diurnal:+.1f}°C, future_offset={future_diurnal:+.1f}°C, "
                                f"change={diurnal_change:+.1f}°C"
                            )
                        else:
                            _LOGGER.debug("Could not parse sunrise/sunset times, using fallback")
                    else:
                        _LOGGER.debug("Sunrise/sunset times not available, using fallback")
                except Exception as err:
                    _LOGGER.debug(f"Error calculating sun-based diurnal: {err}, using fallback")
            else:
                _LOGGER.debug("sun.sun entity not available, using fallback")
        
        # Fallback: simple fixed-time diurnal cycle (old behavior)
        if diurnal_change == 0.0:
            # Current cycle position (peak at 14:00, min at 04:00)
            current_phase = (self.current_hour - 14) / 24.0 * 2 * math.pi
            future_hour = (self.current_hour + hours_ahead) % 24
            future_phase = (future_hour - 14) / 24.0 * 2 * math.pi

            # Diurnal contribution (sinusoidal)
            # cos(0) = 1 at 14:00 = maximum
            # cos(π) = -1 at 04:00 = minimum
            current_diurnal = self.diurnal_amplitude * math.cos(current_phase)
            future_diurnal = self.diurnal_amplitude * math.cos(future_phase)
            diurnal_change = future_diurnal - current_diurnal

        # Solar radiation warming component (if sensor available)
        solar_change = 0.0
        if self.solar_radiation is not None and self.solar_radiation > 0:
            # Calculate sun angle factor for future time
            # Assumption: Solar radiation peaks at solar noon (~13:00 local)
            # and is zero at night (18:00-06:00)

            # Current sun angle factor (0 at night, 1 at solar noon)
            current_sun_factor = self._get_sun_angle_factor(self.current_hour)
            future_sun_factor = self._get_sun_angle_factor(future_hour)

            # Scale solar radiation by cloud cover
            cloud_reduction = 1.0 - (self.cloud_cover / 100.0)
            effective_solar = self.solar_radiation * cloud_reduction

            # Solar warming: +2°C per 400 W/m² at solar noon
            # Scale by sun angle (higher sun = more warming)
            max_solar_warming = (effective_solar / 400.0) * 2.0

            current_solar_warming = max_solar_warming * current_sun_factor
            future_solar_warming = max_solar_warming * future_sun_factor

            solar_change = future_solar_warming - current_solar_warming

            _LOGGER.debug(
                f"Solar temp adjustment: {solar_change:.1f}°C "
                f"(radiation={effective_solar:.0f}W/m², "
                f"sun_factor={future_sun_factor:.2f})"
            )

        # Combine all components: damped trend + diurnal cycle + solar warming
        predicted_ideal = self.current_temp + trend_change + diurnal_change + solar_change
        
        # === THERMAL INERTIA (THERMAL TIME CONSTANT) ===
        # Temperature changes are not instantaneous - surface has thermal capacity
        # Different surfaces respond at different rates:
        # - Water/ocean: very slow (tau = 6-12 hours) - high thermal capacity
        # - Soil/vegetation: medium (tau = 1.5-2 hours)
        # - Urban/pavement: fast (tau = 0.5-1 hour) - low thermal capacity
        # - Snow/ice: medium (tau = 2-3 hours)
        #
        # We use a composite time constant based on continentality:
        # - Maritime (0.0): tau = 3.0h (ocean influence)
        # - Continental (1.0): tau = 1.0h (land dominates)
        #
        # Formula: T(t) = T_ideal * (1 - e^(-t/tau))
        # This means temperature approaches ideal value exponentially
        
        # Calculate thermal time constant
        # Maritime areas: slow response (high tau)
        # Continental areas: fast response (low tau)
        thermal_tau = 3.0 - (2.0 * self.continentality)  # 1.0h to 3.0h
        
        # For short timescales (< 1 hour), apply thermal inertia
        # For longer timescales, response approaches 100%
        if hours_ahead > 0:
            # Exponential response factor
            # At t=0: response = 0 (no change yet)
            # At t=tau: response = 0.63 (63% of ideal change)
            # At t=3*tau: response = 0.95 (95% of ideal change)
            thermal_response = 1 - math.exp(-hours_ahead / thermal_tau)
            
            # Apply thermal inertia to temperature change
            total_change = predicted_ideal - self.current_temp
            damped_change = total_change * thermal_response
            predicted = self.current_temp + damped_change
            
            _LOGGER.debug(
                f"Thermal inertia: tau={thermal_tau:.1f}h, response={thermal_response:.2f}, "
                f"ideal_change={total_change:+.1f}°C, damped_change={damped_change:+.1f}°C"
            )
        else:
            predicted = predicted_ideal

        # Apply realistic seasonal constraints
        # For multi-day forecasts, temperature should stay within reasonable bounds
        # relative to current temperature
        if hours_ahead > 24:
            # For forecasts beyond 24 hours, limit deviation from current temp
            max_deviation = 10.0  # ±10°C max deviation over 3 days
            predicted = max(
                self.current_temp - max_deviation,
                min(self.current_temp + max_deviation, predicted)
            )

        # Absolute realistic temperature limits (-40 to +50°C)
        result = max(-40.0, min(50.0, predicted))

        _LOGGER.debug(
            f"TempModel: {hours_ahead}h → {result:.1f}°C "
            f"(current={self.current_temp:.1f}, trend={trend_change:+.1f}, "
            f"diurnal={diurnal_change:+.1f}, solar={solar_change:+.1f})"
        )

        return result

    def _get_seasonal_amplitude(self, month: int) -> float:
        """Get base diurnal amplitude for given month.

        Accounts for:
        - Hemisphere (seasons are reversed in southern hemisphere)
        - Latitude (tropical vs temperate vs polar)
        - Month/season (winter vs summer diurnal range)

        Based on:
        - Makowski et al. (2008): "Diurnal temperature range variability and trends"
        - WMO (2017): "Guidelines on the Calculation of Climate Normals"

        Args:
            month: Month (1-12)

        Returns:
            Base amplitude in °C
        """
        # Adjust for hemisphere
        if self.hemisphere == "south":
            # Southern hemisphere: shift by 6 months
            month = ((month + 5) % 12) + 1

        # Get absolute latitude for climate zone classification
        abs_lat = abs(self.latitude) if self.latitude is not None else 45.0
        
        # Classify climate zone by latitude
        # Tropics (0-15°): minimal seasonal variation, constant ~8°C DTR
        # Subtropics (15-40°): moderate seasonal variation
        # Temperate (40-60°): large seasonal variation
        # Polar (60-90°): extreme seasonal variation, but limited by sun angle
        
        if abs_lat < 15:  # Tropical zone
            # Minimal seasonal variation
            base_summer = 8.0
            base_winter = 7.0
        elif abs_lat < 40:  # Subtropical zone
            # Moderate seasonal variation
            base_summer = 10.0
            base_winter = 5.0
        elif abs_lat < 60:  # Temperate zone
            # Large seasonal variation
            base_summer = 12.0
            base_winter = 2.0  # Reduced from 3.0 for smoother winter transitions
        else:  # Polar zone (60-90°)
            # Extreme light/dark but limited by low sun angle
            base_summer = 8.0   # Continuous daylight but low sun angle
            base_winter = 1.5   # Reduced from 2.0 for smoother transitions

        # Seasonal interpolation (northern hemisphere reference after adjustment)
        # Winter (Dec-Feb): Low sun, short days → small amplitude
        # Summer (Jun-Aug): High sun, long days → large amplitude
        if month in [12, 1, 2]:  # Winter
            seasonal_amp = base_winter
        elif month in [6, 7, 8]:  # Summer
            seasonal_amp = base_summer
        elif month in [3, 4, 5]:  # Spring (transition)
            seasonal_amp = (base_winter + base_summer) / 2.0
        else:  # Autumn (9, 10, 11) (transition)
            seasonal_amp = (base_summer + base_winter) / 2.0
        
        _LOGGER.debug(
            f"Seasonal amplitude: lat={abs_lat:.1f}°, month={month}, "
            f"base_winter={base_winter}°C, base_summer={base_summer}°C, "
            f"result={seasonal_amp:.1f}°C"
        )
        
        # Apply continentality factor
        # Maritime climate (0.0): smaller DTR due to ocean's thermal inertia
        # Continental climate (1.0): larger DTR due to land's low thermal capacity
        # Typical: maritime = 0.7x, continental = 1.3x
        continentality_factor = 0.7 + (0.6 * self.continentality)
        seasonal_amp *= continentality_factor
        
        # Apply elevation factor
        # Higher elevations have larger DTR due to:
        # - Thinner atmosphere (less heat retention)
        # - Lower absolute humidity (enhanced radiative cooling)
        # Empirical: +10% per 1000m (up to 3000m)
        elevation_factor = 1.0 + min(0.3, self.elevation / 1000.0 * 0.1)
        seasonal_amp *= elevation_factor
        
        _LOGGER.debug(
            f"Final amplitude after adjustments: {seasonal_amp:.1f}°C "
            f"(continent_factor={continentality_factor:.2f}, elev_factor={elevation_factor:.2f})"
        )
        
        return seasonal_amp
    
    def _estimate_continentality(self, latitude: float, longitude: float) -> float:
        """Estimate continentality (0 = ocean, 1 = deep interior) from coordinates.
        
        This is a simplified heuristic based on known continental interiors:
        - Europe/Asia: continental interior around 60-90°E
        - Americas: continental interior around 90-110°W
        - Coastal areas: edges of continents
        
        Note: This is an approximation. Proper calculation would require
        actual distance to nearest coast, but that requires geographic database.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees (-180 to +180)
            
        Returns:
            Continentality factor (0.0 to 1.0)
        """
        abs_lat = abs(latitude)
        
        # Polar regions and small islands: assume maritime (low continentality)
        if abs_lat > 70:
            return 0.3  # Polar oceans and ice
        
        # Normalize longitude to 0-360
        lon = longitude if longitude >= 0 else longitude + 360
        
        # Define continental interiors (simplified)
        # These are rough approximations of major land masses
        continental_cores = [
            # (lon_min, lon_max, lat_min, lat_max, continentality)
            (20, 140, 25, 65, 0.9),   # Eurasia interior
            (240, 280, 25, 50, 0.8),  # North America interior
            (290, 320, -35, -15, 0.7), # South America interior
            (10, 50, -30, 30, 0.7),   # Africa interior
            (110, 155, -45, -10, 0.6), # Australia interior
        ]
        
        # Check if location is in any continental interior
        max_continentality = 0.3  # Default: assume near coast
        
        for lon_min, lon_max, lat_min, lat_max, continent_val in continental_cores:
            if lon_min <= lon <= lon_max and lat_min <= latitude <= lat_max:
                # Calculate distance from center of continental region
                center_lon = (lon_min + lon_max) / 2
                center_lat = (lat_min + lat_max) / 2
                
                # Normalize distance (0 = center, 1 = edge)
                lon_dist = abs(lon - center_lon) / ((lon_max - lon_min) / 2)
                lat_dist = abs(latitude - center_lat) / ((lat_max - lat_min) / 2)
                distance_from_center = (lon_dist + lat_dist) / 2
                
                # Continentality decreases linearly from center to edge
                local_continentality = continent_val * (1 - distance_from_center * 0.5)
                max_continentality = max(max_continentality, local_continentality)
        
        _LOGGER.debug(
            f"Estimated continentality: {max_continentality:.2f} "
            f"(lat={latitude:.1f}°, lon={longitude:.1f}°)"
        )
        
        return max_continentality

    def _get_sun_angle_factor(self, hour: int) -> float:
        """Calculate sun angle factor (0-1) for given hour.

        Uses real sun.sun entity if available for accurate sunrise/sunset times,
        otherwise falls back to simple sine curve simulation.

        Args:
            hour: Hour of day (0-23)

        Returns:
            Sun angle factor (0.0 = night, 1.0 = solar noon)
        """
        # Try to use real sun entity if hass available
        if self.hass is not None:
            sun_entity = self.hass.states.get("sun.sun")

            if sun_entity:
                try:
                    from homeassistant.util import dt as dt_util

                    # Get sunrise and sunset times
                    next_rising_str = sun_entity.attributes.get("next_rising")
                    next_setting_str = sun_entity.attributes.get("next_setting")

                    if next_rising_str and next_setting_str:
                        next_rising = dt_util.parse_datetime(next_rising_str)
                        next_setting = dt_util.parse_datetime(next_setting_str)

                        if next_rising and next_setting:
                            # Calculate for the target hour
                            now = datetime.now(timezone.utc)
                            target_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)

                            # If target hour is in the past today, move to tomorrow
                            if target_time < now:
                                target_time = target_time + timedelta(days=1)

                            # Ensure timezone awareness
                            if target_time.tzinfo is None:
                                target_time = target_time.replace(tzinfo=timezone.utc)
                            if next_rising.tzinfo is None:
                                next_rising = next_rising.replace(tzinfo=timezone.utc)
                            if next_setting.tzinfo is None:
                                next_setting = next_setting.replace(tzinfo=timezone.utc)

                            # If time is before sunrise or after sunset, sun factor = 0
                            sunrise_hour = next_rising.hour + next_rising.minute / 60.0
                            sunset_hour = next_setting.hour + next_setting.minute / 60.0

                            if hour < sunrise_hour or hour >= sunset_hour:
                                return 0.0

                            # Calculate solar noon (midpoint between sunrise and sunset)
                            solar_noon = (sunrise_hour + sunset_hour) / 2.0
                            daylight_duration = sunset_hour - sunrise_hour

                            # Sun angle factor: sine curve from sunrise to sunset, peaking at solar noon
                            # Map hour to 0-π phase (0 at sunrise, π at sunset)
                            time_from_sunrise = hour - sunrise_hour
                            phase = (time_from_sunrise / daylight_duration) * math.pi

                            sun_factor = math.sin(phase)

                            _LOGGER.debug(
                                f"Sun factor for hour {hour}: {sun_factor:.2f} "
                                f"(sunrise={sunrise_hour:.1f}, sunset={sunset_hour:.1f}, "
                                f"solar_noon={solar_noon:.1f})"
                            )

                            return max(0.0, min(1.0, sun_factor))

                except (ValueError, AttributeError) as err:
                    _LOGGER.debug(f"Could not use sun entity, falling back to simulation: {err}")

        # Fallback: Simple sine curve simulation
        # Night time (no solar warming)
        if hour >= 18 or hour < 6:
            return 0.0

        # Daytime: sine curve peaking at 13:00
        # Map 6:00-18:00 to 0-π for half sine wave
        time_from_sunrise = hour - 6  # 0 at 6:00, 12 at 18:00
        phase = (time_from_sunrise / 12.0) * math.pi  # 0 to π

        # Sine curve: 0 at sunrise/sunset, 1 at solar noon
        # Shift peak to 13:00 instead of 12:00 (7 hours after 6:00 sunrise)
        peak_offset = (13 - 6) / 12.0 * math.pi
        adjusted_phase = phase - (math.pi / 2 - peak_offset)

        sun_factor = math.sin(adjusted_phase)

        # Clamp to 0-1 range
        return max(0.0, min(1.0, sun_factor))

    def get_daily_range(self, hours_ahead: int = 24) -> tuple[float, float]:
        """Get predicted temperature range for next N hours.

        Args:
            hours_ahead: Hours to look ahead (default 24)

        Returns:
            Tuple of (min_temp, max_temp) in °C
        """
        temps = [self.predict(h) for h in range(hours_ahead + 1)]
        return (min(temps), max(temps))


class ZambrettiForecaster:
    """Hourly Zambretti forecast calculator.

    Runs Zambretti algorithm for each hour using predicted pressure
    to determine evolving weather conditions.
    """

    def __init__(
        self,
        hass: HomeAssistant | None = None,
        latitude: float = 50.0,
        solar_radiation: float | None = None
    ):
        """Initialize Zambretti forecaster.

        Args:
            hass: Home Assistant instance for sun entity access
            latitude: Location latitude for seasonal adjustment
            solar_radiation: Current solar radiation in W/m² for cloud cover correction
        """
        self.hass = hass
        self.latitude = latitude
        self.solar_radiation = solar_radiation

    def forecast_hour(
        self,
        pressure: float,
        wind_direction: int,
        pressure_change: float,
        wind_speed: float = 0.0
    ) -> tuple[str, int, str]:
        """Calculate Zambretti forecast for specific conditions.

        Args:
            pressure: Atmospheric pressure in hPa
            wind_direction: Wind direction in degrees
            pressure_change: Pressure change over 3 hours in hPa
            wind_speed: Wind speed in m/s

        Returns:
            Tuple of (forecast_text, forecast_number, letter_code)
        """
        # Calculate wind factor (0-2 based on direction)
        # North (0): 2, East (90): 0, South (180): 1, West (270): 0
        if 315 <= wind_direction or wind_direction < 45:
            wind_fak = 2  # North
        elif 135 <= wind_direction < 225:
            wind_fak = 1  # South
        else:
            wind_fak = 0  # East/West

        # Wind speed factor (0-2 based on beaufort scale approximation)
        # 0-1 m/s: 0, 1-3 m/s: 1, >3 m/s: 2
        if wind_speed < 1.0:
            speed_fak = 0
        elif wind_speed < 3.0:
            speed_fak = 1
        else:
            speed_fak = 2

        # Wind direction text (not used in calculation but needed for API)
        if 315 <= wind_direction or wind_direction < 45:
            dir_text = "N"
        elif 45 <= wind_direction < 135:
            dir_text = "E"
        elif 135 <= wind_direction < 225:
            dir_text = "S"
        else:
            dir_text = "W"

        wind_data = [wind_fak, wind_direction, dir_text, speed_fak]

        # Run Zambretti algorithm
        result = calculate_zambretti_forecast(
            p0=pressure,
            pressure_change=pressure_change,
            wind_data=wind_data,
            lang_index=1  # English
        )

        # Result is [forecast_text, forecast_number, letter_code]
        # Convert to typed tuple
        return (str(result[0]), int(result[1]), str(result[2]))

    def get_condition(self, letter_code: str, forecast_time: datetime) -> str:
        """Map Zambretti letter code to Home Assistant weather condition.

        Uses UV index and solar radiation to correct cloud cover estimates:
        - High UV during daytime + Zambretti "cloudy" → downgrade to partlycloudy
        - Low UV during daytime + Zambretti "sunny" → upgrade to cloudy
        - UV index provides real-time atmospheric transparency

        Args:
            letter_code: Zambretti letter (A-Z)
            forecast_time: Datetime to check for day/night

        Returns:
            HA weather condition string
        """
        # Use new unified mapping system
        is_night = self._is_night(forecast_time)
        condition = map_forecast_to_condition(
            forecast_letter=letter_code,
            is_night_func=lambda: is_night,
            source="ZambrettiForecaster"
        )

        _LOGGER.debug(
            f"Zambretti condition mapping: letter={letter_code} → "
            f"base={condition}, time={forecast_time.hour:02d}:00"
        )

        # UV INDEX CLOUD COVER CORRECTION (daytime only)
        # UV index scale: 0-2 (low), 3-5 (moderate), 6-7 (high), 8-10 (very high), 11+ (extreme)
        # Only apply during daylight hours (6:00-18:00)
        hour = forecast_time.hour
        is_daytime = 6 <= hour <= 18

        # SOLAR RADIATION CLOUD COVER CORRECTION
        # Solar radiation scale: 0-1000+ W/m²
        # Clear sky at solar noon: ~800-1000 W/m² (varies by season)
        if is_daytime and self.solar_radiation is not None:
            # Use solar radiation if UV index not available
            sun_factor = self._get_sun_angle_factor_for_condition(hour)

            # Expected clear-sky solar radiation with location-aware maximum
            month = forecast_time.month
            original_month = month

            # Import the new function for calculating max radiation
            from .calculations import calculate_max_solar_radiation_for_location

            # Calculate location-specific maximum radiation
            # This replaces the fixed 1000 W/m² with a value based on latitude and season
            max_solar_location = calculate_max_solar_radiation_for_location(
                latitude=self.latitude,
                month=month
            )

            # Hemisphere correction is now handled in calculate_max_solar_radiation_for_location
            # No need to manually shift months here

            # Seasonal factor: peaks in June (northern) or December (southern after shift)
            # Range: 0.5 (winter minimum) to 1.0 (summer maximum)
            # Note: This is now redundant as calculate_max_solar_radiation_for_location
            # already includes seasonal adjustment, but we keep it for time-of-day variation
            seasonal_factor = 1.0  # Use full location-specific maximum

            expected_clear_sky_solar = max_solar_location * sun_factor

            _LOGGER.debug(
                f"Location-aware solar calculation: lat={self.latitude:.2f}°, "
                f"month={month}, max_for_location={max_solar_location:.0f} W/m², "
                f"sun_factor={sun_factor:.3f}, expected={expected_clear_sky_solar:.0f} W/m²"
            )

            if expected_clear_sky_solar > 100:
                solar_ratio = self.solar_radiation / expected_clear_sky_solar
                cloud_cover_percent = max(0.0, min(100.0, (1.0 - solar_ratio) * 100))

                _LOGGER.debug(
                    f"Solar cloud correction: radiation={self.solar_radiation:.0f}W/m², "
                    f"expected={expected_clear_sky_solar:.0f}W/m², "
                    f"clouds={cloud_cover_percent:.0f}%"
                )

                # Apply same corrections as UV
                if condition in ("sunny", "clear-night") and cloud_cover_percent > 70:
                    _LOGGER.debug(f"Solar correction: {condition} → cloudy")
                    condition = "cloudy"
                elif condition in ("sunny", "clear-night") and cloud_cover_percent > 40:
                    _LOGGER.debug(f"Solar correction: {condition} → partlycloudy")
                    condition = "partlycloudy"
                elif condition == "cloudy" and cloud_cover_percent < 30:
                    _LOGGER.debug(f"Solar correction: cloudy → partlycloudy")
                    condition = "partlycloudy"
                elif condition == "cloudy" and cloud_cover_percent < 10:
                    _LOGGER.debug(f"Solar correction: cloudy → sunny")
                    condition = "sunny"

        # Convert sunny to clear-night during night hours
        if condition == "sunny" and self._is_night(forecast_time):
            _LOGGER.debug(f"Night time detected, converting sunny → clear-night")
            return "clear-night"

        return condition

    def _get_sun_angle_factor_for_condition(self, hour: int) -> float:
        """Calculate sun angle factor for condition correction.

        Simplified version for cloud cover correction.

        Args:
            hour: Hour of day (0-23)

        Returns:
            Sun angle factor (0.0 = night, 1.0 = solar noon)
        """
        # Night time
        if hour >= 18 or hour < 6:
            return 0.0

        # Daytime: sine curve peaking at 13:00
        time_from_sunrise = hour - 6
        phase = (time_from_sunrise / 12.0) * math.pi
        peak_offset = (13 - 6) / 12.0 * math.pi
        adjusted_phase = phase - (math.pi / 2 - peak_offset)
        sun_factor = math.sin(adjusted_phase)

        return max(0.0, min(1.0, sun_factor))

    def _is_night(self, check_time: datetime) -> bool:
        """Check if it's night time based on sun position.

        Args:
            check_time: Time to check

        Returns:
            True if sun is below horizon
        """
        # For daily forecasts (around noon), always return False (daytime)
        if check_time.hour >= 11 and check_time.hour <= 13:
            return False

        if self.hass is None:
            # Fallback to simple time check if hass not available
            return check_time.hour >= 19 or check_time.hour < 7

        # Get sun entity
        sun_entity = self.hass.states.get("sun.sun")

        if not sun_entity:
            # Fallback to simple time check if sun entity not available
            return check_time.hour >= 19 or check_time.hour < 7

        # For current time (within 1 minute), just check state
        now = datetime.now(timezone.utc)

        # Make check_time timezone aware first if needed
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=timezone.utc)

        time_diff = abs((check_time - now).total_seconds())

        if time_diff < 60:
            return sun_entity.state == "below_horizon"

        # For future times, calculate sunrise/sunset for the specific forecast date
        try:
            from homeassistant.helpers.sun import get_astral_event_date
            from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET

            # Get sunrise/sunset for the specific forecast date
            forecast_date = check_time.date()

            sunrise = get_astral_event_date(self.hass, SUN_EVENT_SUNRISE, forecast_date)
            sunset = get_astral_event_date(self.hass, SUN_EVENT_SUNSET, forecast_date)

            if sunrise and sunset:
                # Make check_time timezone-aware if it isn't already
                if check_time.tzinfo is None:
                    check_time = check_time.replace(tzinfo=timezone.utc)

                # Check if time is before sunrise or after sunset
                is_night = check_time < sunrise or check_time > sunset

                _LOGGER.debug(
                    f"Future time check: "
                    f"check={check_time.strftime('%Y-%m-%d %H:%M')}, "
                    f"sunset={sunset.strftime('%Y-%m-%d %H:%M')}, "
                    f"sunrise={sunrise.strftime('%Y-%m-%d %H:%M')} → "
                    f"is_night={is_night}"
                )

                return is_night

        except (ImportError, ValueError, AttributeError) as err:
            _LOGGER.debug(f"Could not calculate sun times, using fallback: {err}")

        # Fallback: Night is between 19:00 and 07:00
        hour = check_time.hour
        return hour >= 19 or hour < 7



class RainProbabilityCalculator:
    """Calculate rain probability based on pressure evolution and weather conditions.
    
    UNIVERSAL for all forecast models (Zambretti, Negretti, Enhanced).
    Uses forecast code (0-25) which is model-independent.
    """

    # Universal forecast code to base rain probability mapping (0-25)
    # Based on forecast conditions: 0-5 (fine) = low, 6-15 (mixed) = medium, 16-25 (poor) = high
    # Same mapping applies to Zambretti, Negretti, and Enhanced models
    CODE_RAIN_PROB = {
        0: 5, 1: 10, 2: 15, 3: 20, 4: 25, 5: 30,           # 0-5: Settled fine to fairly fine
        6: 35, 7: 40, 8: 45, 9: 50, 10: 50,                # 6-10: Fair weather, possible showers
        11: 55, 12: 55, 13: 60, 14: 60, 15: 65,            # 11-15: Unsettled, changeable
        16: 70, 17: 75, 18: 80, 19: 85, 20: 85,            # 16-20: Rain at times
        21: 90, 22: 90, 23: 95, 24: 95, 25: 95             # 21-25: Very wet, stormy
    }

    @staticmethod
    def calculate(
        current_pressure: float,
        future_pressure: float,
        pressure_trend: str,
        forecast_code: int,
        forecast_letter: str = 'A'  # Deprecated, kept for compatibility
    ) -> int:
        """Calculate rain probability percentage.

        UNIVERSAL calculation for all forecast models (Zambretti/Negretti/Enhanced).
        
        Based on:
        - Forecast code (0-25) - MODEL INDEPENDENT
        - Pressure level and change
        - Pressure trend direction

        Args:
            current_pressure: Current pressure in hPa
            future_pressure: Forecasted pressure in hPa
            pressure_trend: Trend string (not used currently)
            forecast_code: Universal forecast code (0-25)
            forecast_letter: Letter code (deprecated, for backward compatibility)

        Returns:
            Rain probability 0-100%
        """
        # Base probability from forecast code (0-25)
        # Works for ALL models: Zambretti, Negretti, Enhanced
        base_prob = RainProbabilityCalculator.CODE_RAIN_PROB.get(
            forecast_code,
            50  # Default middle value if code unknown
        )

        # Adjust for absolute pressure level
        # Very low pressure = unstable, high rain likelihood
        # High pressure = anticyclone = stable, dry weather
        if future_pressure < 990:
            base_prob = min(100, base_prob + 25)
        elif future_pressure < 1000:
            base_prob = min(100, base_prob + 15)
        elif future_pressure < 1010:
            base_prob = min(100, base_prob + 5)
        elif future_pressure > 1035:  # Strong anticyclone
            base_prob = max(0, base_prob - 25)  # Very dry
        elif future_pressure > 1030:  # Anticyclone
            base_prob = max(0, base_prob - 20)
        elif future_pressure > 1025:  # High pressure
            base_prob = max(0, base_prob - 15)

        # Adjust for pressure change (trend)
        pressure_change = future_pressure - current_pressure

        # Rapidly falling pressure = incoming bad weather
        if pressure_change < -5:
            base_prob = min(100, base_prob + 20)
        elif pressure_change < -3:
            base_prob = min(100, base_prob + 15)
        elif pressure_change < -1:
            base_prob = min(100, base_prob + 5)
        # Stable pressure in anticyclone = very dry
        elif pressure_change > 5:
            base_prob = max(0, base_prob - 20)
        elif pressure_change > 3:
            base_prob = max(0, base_prob - 15)
        elif pressure_change > 1:
            base_prob = max(0, base_prob - 5)
        # Very stable anticyclone (minimal change, high pressure)
        elif abs(pressure_change) < 0.5 and future_pressure > 1030:
            base_prob = max(0, base_prob - 15)  # Additional reduction for stable anticyclone

        # Clamp to 0-100
        result = max(0, min(100, base_prob))

        _LOGGER.debug(
            f"RainProb: code={forecast_code} → {result}% "
            f"(P={future_pressure:.1f}hPa, ΔP={pressure_change:+.1f}, base={RainProbabilityCalculator.CODE_RAIN_PROB.get(forecast_code, 50)}%)"
        )

        return result


def get_beaufort_scale(wind_speed_ms: float) -> int:
    """Convert wind speed (m/s) to Beaufort scale factor.
    
    Args:
        wind_speed_ms: Wind speed in meters per second
        
    Returns:
        Beaufort factor (0-2):
        - 0: Calm to light breeze (0-5.5 m/s, Beaufort 0-3)
        - 1: Moderate breeze (5.5-10.8 m/s, Beaufort 4-5)
        - 2: Strong breeze+ (>10.8 m/s, Beaufort 6+)
    """
    if wind_speed_ms < 5.5:
        return 0
    elif wind_speed_ms < 10.8:
        return 1
    else:
        return 2


def get_wind_dir_text(wind_direction: int) -> str:
    """Convert wind direction degrees to text.
    
    Args:
        wind_direction: Wind direction in degrees (0-360)
        
    Returns:
        Wind direction text (N, NE, E, SE, S, SW, W, NW)
    """
    if 315 <= wind_direction or wind_direction < 45:
        return "N"
    elif 45 <= wind_direction < 135:
        return "E"
    elif 135 <= wind_direction < 225:
        return "S"
    else:
        return "W"


class HourlyForecastGenerator:
    """Generate hourly weather forecasts using advanced models."""

    def __init__(
        self,
        hass: HomeAssistant,
        pressure_model: PressureModel,
        temperature_model: TemperatureModel,
        zambretti: ZambrettiForecaster,
        wind_direction: int = 0,
        wind_speed: float = 0.0,
        latitude: float = 50.0,
        current_rain_rate: float = 0.0,
        forecast_model: str = FORECAST_MODEL_ENHANCED,
        elevation: float = 0.0,
        current_condition: str | None = None
    ):
        """Initialize hourly forecast generator.

        Args:
            hass: Home Assistant instance
            pressure_model: Pressure forecasting model
            temperature_model: Temperature forecasting model
            zambretti: Zambretti forecaster
            wind_direction: Current wind direction in degrees
            wind_speed: Current wind_speed in m/s
            latitude: Location latitude
            current_rain_rate: Current precipitation rate in mm/h
            forecast_model: Which model to use (FORECAST_MODEL_ZAMBRETTI, FORECAST_MODEL_NEGRETTI, FORECAST_MODEL_ENHANCED)
            elevation: Elevation in meters above sea level
            current_condition: Current weather condition from weather entity (e.g., 'snowy', 'rainy', 'cloudy')
        """
        self.hass = hass
        self.pressure_model = pressure_model
        self.temperature_model = temperature_model
        self.zambretti = zambretti
        self.wind_direction = wind_direction
        self.wind_speed = wind_speed
        self.latitude = latitude
        self.current_rain_rate = current_rain_rate
        self.forecast_model = forecast_model
        self.elevation = elevation
        self.current_condition = current_condition

    def generate(
        self,
        hours_count: int = 24,
        interval_hours: int = 1
    ) -> list[Forecast]:
        """Generate hourly forecasts.

        Args:
            hours_count: Number of hours to forecast
            interval_hours: Interval between forecasts in hours

        Returns:
            List of Forecast objects
        """
        # ═══════════════════════════════════════════════════════════════
        # v3.1.12: Use ENHANCED ORCHESTRATION if ENHANCED model selected
        # ═══════════════════════════════════════════════════════════════
        if self.forecast_model == FORECAST_MODEL_ENHANCED and interval_hours == 1:
            _LOGGER.debug("🎯 Using ENHANCED orchestration: Persistence → WMO Simple → TIME DECAY")
            return self._generate_with_orchestration(hours_count)
        
        # ═══════════════════════════════════════════════════════════════
        # LEGACY PATH: Classic Zambretti/Negretti without orchestration
        # ═══════════════════════════════════════════════════════════════
        forecasts = []
        now = datetime.now(timezone.utc)
        rain_calc = RainProbabilityCalculator()

        for hour_offset in range(0, hours_count + 1, interval_hours):
            future_time = now + timedelta(hours=hour_offset)

            # Predict atmospheric conditions
            future_pressure = self.pressure_model.predict(hour_offset)
            pressure_trend = self.pressure_model.get_trend(hour_offset)
            
            # ═══════════════════════════════════════════════════════════════
            # v3.1.12: Use weather-aware temperature model for ALL models
            # ═══════════════════════════════════════════════════════════════
            # Calculate pressure change for forecast code determination
            pressure_change = future_pressure - self.pressure_model.current_pressure

            # Predict atmospheric conditions
            future_pressure = self.pressure_model.predict(hour_offset)
            pressure_trend = self.pressure_model.get_trend(hour_offset)
            
            # ═══════════════════════════════════════════════════════════════
            # v3.1.12: Use weather-aware temperature model for ALL models
            # ═══════════════════════════════════════════════════════════════
            # Calculate pressure change for forecast code determination
            pressure_change = future_pressure - self.pressure_model.current_pressure

            # Get Zambretti forecast for this hour
            zambretti_result = self.zambretti.forecast_hour(
                pressure=future_pressure,
                wind_direction=self.wind_direction,
                pressure_change=pressure_change,
                wind_speed=self.wind_speed
            )

            zambretti_text, zambretti_num, zambretti_letter = zambretti_result

            # Get Negretti-Zambra forecast if needed
            negretti_letter = None
            negretti_num = None

            if self.forecast_model in (FORECAST_MODEL_NEGRETTI, FORECAST_MODEL_ENHANCED):
                try:
                    from .negretti_zambra import calculate_negretti_zambra_forecast
                    from .language import get_language_index
                    from .const import CONF_HEMISPHERE, DEFAULT_HEMISPHERE

                    lang_index = get_language_index(self.hass)

                    # Get hemisphere from config
                    hemisphere = DEFAULT_HEMISPHERE
                    if hasattr(self, 'config_entry') and hasattr(self, 'config_entry') and getattr(self, 'config_entry', None):
                        hemisphere = getattr(self, 'config_entry').data.get(CONF_HEMISPHERE, DEFAULT_HEMISPHERE)

                    negretti_result = calculate_negretti_zambra_forecast(
                        future_pressure,
                        pressure_change,
                        [self.wind_speed, self.wind_direction, "N", 0],  # wind_data
                        lang_index,
                        self.elevation,
                        hemisphere
                    )
                    negretti_text, negretti_num, negretti_letter = negretti_result
                except Exception as e:
                    _LOGGER.debug(f"Negretti-Zambra calculation failed: {e}, using Zambretti")
                    negretti_letter = zambretti_letter
                    negretti_num = zambretti_num

            # Select forecast code based on model preference
            if self.forecast_model == FORECAST_MODEL_ZAMBRETTI:
                forecast_letter = zambretti_letter
                forecast_num = zambretti_num
                _LOGGER.debug(f"Using Zambretti forecast: {zambretti_letter}")
            elif self.forecast_model == FORECAST_MODEL_NEGRETTI and negretti_letter:
                forecast_letter = negretti_letter
                forecast_num = negretti_num
                _LOGGER.debug(f"Using Negretti-Zambra forecast: {negretti_letter}")
            else:  # FORECAST_MODEL_ENHANCED - use combined_model.py
                if hour_offset == 0:
                    # ═══════════════════════════════════════
                    # NEW v3.1.12: Use Persistence for hour 0
                    # ═══════════════════════════════════════
                    from .persistence import calculate_persistence_forecast, get_current_condition_code
                    from .language import get_language_index
                    
                    lang_index = get_language_index(self.hass)
                    
                    # Get current dewpoint (estimate if not available)
                    current_dewpoint = self.temperature_model.current_temp - 5.0  # Rough estimate
                    current_humidity = getattr(self, 'current_humidity', None)
                    if current_humidity is not None:
                        # Better estimate using humidity
                        current_dewpoint = self.temperature_model.current_temp - (
                            (100 - current_humidity) / 5.0
                        )
                    
                    # Get current condition code from sensors
                    current_code = get_current_condition_code(
                        temperature=self.temperature_model.current_temp,
                        pressure=self.pressure_model.current_pressure,
                        humidity=getattr(self, 'current_humidity', 70.0),
                        dewpoint=current_dewpoint,
                        weather_condition=self.current_condition
                    )
                    
                    # Calculate Persistence forecast
                    forecast_result = calculate_persistence_forecast(
                        current_condition_code=current_code,
                        lang_index=lang_index,
                        hours_ahead=0
                    )
                    
                    forecast_num = forecast_result[1]
                    
                    # Get letter code for rain probability
                    from .forecast_mapping import ZAMBRETTI_LETTER_TO_CODE
                    forecast_letter = None
                    for letter, code in ZAMBRETTI_LETTER_TO_CODE.items():
                        if code == forecast_num:
                            forecast_letter = letter
                            break
                    if not forecast_letter:
                        forecast_letter = "A"  # Fallback
                    
                    _LOGGER.debug(
                        f"🔒 Hour 0: PERSISTENCE → code={forecast_num}, "
                        f"letter={forecast_letter}, confidence=98%"
                    )
                    
                elif negretti_letter:
                    # ✅ USE COMBINED MODEL MODULE WITH TIME DECAY (v3.1.12)
                    from .combined_model import (
                        calculate_combined_forecast_with_time,
                        calculate_combined_rain_probability
                    )

                    (
                        forecast_num,
                        zambretti_weight,
                        negretti_weight,
                        consensus
                    ) = calculate_combined_forecast_with_time(
                        zambretti_result=["", zambretti_num],  # ✅ SIMPLIFIED: [text, code]
                        negretti_result=["", negretti_num],    # ✅ SIMPLIFIED: [text, code]
                        current_pressure=future_pressure,
                        pressure_change=pressure_change,
                        hours_ahead=hour_offset,  # ✅ NEW: TIME DECAY based on forecast horizon
                        source=f"HourlyForecast_h{hour_offset}"
                    )

                    # forecast_letter determined from code for rain probability
                    from .forecast_mapping import ZAMBRETTI_LETTER_TO_CODE
                    # Reverse lookup: code → letter (for rain probability calculation)
                    forecast_letter = None
                    for letter, code in ZAMBRETTI_LETTER_TO_CODE.items():
                        if code == forecast_num:
                            forecast_letter = letter
                            break
                    if not forecast_letter:
                        forecast_letter = "A"  # Fallback

                    # ✅ FIXED: Ensure letter codes are not None before calculating probability
                    # If either letter is None, use fallback values
                    safe_zambretti_letter = zambretti_letter if zambretti_letter else "M"
                    safe_negretti_letter = negretti_letter if negretti_letter else "M"

                    # Calculate combined rain probability
                    combined_rain = calculate_combined_rain_probability(
                        zambretti_letter=safe_zambretti_letter,
                        negretti_letter=safe_negretti_letter,
                        zambretti_weight=zambretti_weight,
                        negretti_weight=negretti_weight
                    )
                else:
                    # Fallback to Zambretti if Negretti unavailable
                    forecast_letter = zambretti_letter
                    forecast_num = zambretti_num
                    _LOGGER.debug(f"Combined forecast (Zambretti fallback): {zambretti_letter}")

            # ═══════════════════════════════════════════════════════════════
            # v3.1.12: Calculate temperature using weather-aware model
            # NOW available for ALL forecast models (Zambretti/Negretti/Enhanced)
            # ═══════════════════════════════════════════════════════════════
            from .combined_model import calculate_weather_aware_temperature
            
            future_temp = calculate_weather_aware_temperature(
                hour=hour_offset,
                current_temp=self.temperature_model.current_temp,
                temp_trend=self.temperature_model.change_rate_1h,
                forecast_code=forecast_num if forecast_num is not None else 13,  # Use selected forecast code
                current_hour=now.hour,
                latitude=self.latitude,
                longitude=getattr(self.hass.config, 'longitude', 21.25) if self.hass and self.hass.config else 21.25,
                humidity=getattr(self.temperature_model, 'humidity', None),
                cloud_cover=getattr(self.temperature_model, 'cloud_cover', None),
                solar_radiation=self.zambretti.solar_radiation if hasattr(self.zambretti, 'solar_radiation') else None,
            )
            
            _LOGGER.debug(
                f"🌡️ {self.forecast_model} h{hour_offset}: {future_temp:.1f}°C "
                f"(code={forecast_num}, weather-aware)"
            )

            # Determine if it's daytime using sun entity (if available)
            is_night = self._is_night(future_time)
            is_daytime = not is_night

            # ✅ FIX: Hourly forecasts are PREDICTIONS, not current state
            # Logic:
            # - ALL hourly forecasts (0-24h): Show PREDICTED precipitation
            # - Rain sensor is ONLY for weather entity (current state)
            # - Hour 0 is still a FORECAST (what's expected), not current state
            #
            # NOTE: Hourly forecasts use ONLY forecast model (Zambretti/Negretti/Enhanced)
            #       Rain sensor is used ONLY for current weather (weather entity state)
            # For all forecasts, is_current_state should be False to show predicted precipitation
            is_current_state = False
            
            # Normal forecast mapping for ALL hours (including hour 0)
            condition = map_forecast_to_condition(
                forecast_letter=forecast_letter,
                forecast_num=forecast_num,
                is_night_func=lambda: is_night,
                temperature=future_temp,
                source=f"HourlyForecast_{self.forecast_model}",
                is_current_state=is_current_state
            )

            _LOGGER.debug(
                f"Final condition for {future_time.strftime('%H:%M')}: "
                f"model={self.forecast_model}, letter={forecast_letter}, "
                f"code={forecast_num}, is_current={is_current_state} → {condition}"
            )

            # ═══════════════════════════════════════════════════════════════
            # HUMIDITY PREDICTION FOR DERIVED PARAMETERS
            # Calculate future humidity for dewpoint and apparent temperature
            # NO condition adjustments - trust the barometric models!
            # ═══════════════════════════════════════════════════════════════
            humidity = None  # Default if no humidity data available
            
            if hasattr(self.temperature_model, 'humidity') and self.temperature_model.humidity is not None:
                current_humidity = self.temperature_model.humidity
                current_temp = self.temperature_model.current_temp
                
                # Only proceed if current data is valid
                if 0 <= current_humidity <= 100 and current_temp is not None:
                    # Calculate future humidity based on temperature change (Clausius-Clapeyron)
                    from .calculations import calculate_future_humidity
                    
                    pressure_change = future_pressure - self.pressure_model.current_pressure
                    predicted_humidity = calculate_future_humidity(
                        current_temperature=current_temp,
                        current_humidity=current_humidity,
                        future_temperature=future_temp,
                        pressure_change=pressure_change
                    )
                    
                    # Use predicted humidity if available, otherwise fall back to current
                    humidity = predicted_humidity if predicted_humidity is not None else current_humidity
                    
                    if predicted_humidity is not None:
                        _LOGGER.debug(
                            f"💧 Forecast h{hour_offset}: RH prediction "
                            f"{current_humidity:.1f}% → {predicted_humidity:.1f}% "
                            f"(T: {current_temp:.1f}°C → {future_temp:.1f}°C, ΔP={pressure_change:+.1f}hPa)"
                        )

            # Calculate rain probability from selected model (Zambretti/Negretti/Enhanced)
            # NOTE: Rain override is NOT applied to forecasts - only to current weather display
            # Forecasts always use model predictions, regardless of current rain
            rain_prob = rain_calc.calculate(
                current_pressure=self.pressure_model.current_pressure,
                future_pressure=future_pressure,
                pressure_trend=pressure_trend,
                forecast_code=forecast_num if forecast_num is not None else 13,
                forecast_letter=forecast_letter
            )

            # ═══════════════════════════════════════════════════════════════
            # ✅ v3.1.15: Rain probability COMPLEMENTS forecast, does not override
            # Scientific basis: WMO (2018) - probability supplements deterministic forecast
            # 
            # Forecast condition from code mapping is AUTHORITATIVE
            # - Code 13 "cloudy" already implies rain possibility (showers)
            # - Code 19 "rainy" means rain is primary condition
            # Rain probability provides additional QUANTITATIVE info but doesn't change icon
            # The Zambretti/Negretti code already captured the weather condition correctly!
            # ═══════════════════════════════════════════════════════════════

            # Barometric models don't predict exact precipitation amounts
            # Only probability and conditions are predicted
            precipitation_amount = None

            # Calculate dew point from predicted temperature and humidity
            dewpoint_temp = None
            if humidity is not None and 0 < humidity <= 100:
                from .calculations import calculate_dewpoint
                dewpoint_temp = calculate_dewpoint(future_temp, humidity)

            # Calculate apparent temperature (feels-like) from predicted conditions
            apparent_temp = None
            if humidity is not None:
                from .calculations import calculate_apparent_temperature
                # Estimate future wind speed (currently use current, could be improved)
                future_wind_speed = self.wind_speed  # TODO: Add wind speed prediction
                apparent_temp = calculate_apparent_temperature(
                    future_temp,
                    humidity,
                    future_wind_speed
                )

            # Create forecast entry
            forecast: Forecast = {
                "datetime": future_time.isoformat(),
                "condition": condition,
                "temperature": round(future_temp, 1),
                "native_temperature": round(future_temp, 1),
                "precipitation_probability": rain_prob,
                "precipitation": precipitation_amount,  # Model doesn't predict exact mm
                "native_precipitation": precipitation_amount,
                "is_daytime": is_daytime,
                # ✅ NEW: Additional forecast data
                "pressure": round(future_pressure, 1) if future_pressure else None,
                "native_pressure": round(future_pressure, 1) if future_pressure else None,
                "humidity": round(humidity, 1) if humidity is not None else None,
                "dew_point": round(dewpoint_temp, 1) if dewpoint_temp is not None else None,
                "native_dew_point": round(dewpoint_temp, 1) if dewpoint_temp is not None else None,
                "apparent_temperature": round(apparent_temp, 1) if apparent_temp is not None else None,
                "native_apparent_temp": round(apparent_temp, 1) if apparent_temp is not None else None,
            }

            forecasts.append(forecast)

        _LOGGER.debug(
            f"Generated {len(forecasts)} hourly forecasts "
            f"(interval: {interval_hours}h)"
        )

        return forecasts

    def _is_night(self, check_time: datetime) -> bool:
        """Check if it's night time based on sun position.

        Args:
            check_time: Time to check

        Returns:
            True if sun is below horizon
        """
        if self.hass is None:
            # Fallback to simple time check if hass not available
            return check_time.hour >= 19 or check_time.hour < 7

        # Get sun entity
        sun_entity = self.hass.states.get("sun.sun")

        if not sun_entity:
            # Fallback to simple time check if sun entity not available
            _LOGGER.debug(f"Sun entity not available, using fallback time check for hour={check_time.hour}")
            return check_time.hour >= 19 or check_time.hour < 7

        # For current time (within 1 minute), just check state
        now = datetime.now(timezone.utc)

        # Make check_time timezone aware first if needed
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=timezone.utc)

        time_diff = abs((check_time - now).total_seconds())

        if time_diff < 60:
            is_night = sun_entity.state == "below_horizon"
            _LOGGER.debug(f"Current time check: is_night={is_night} (sun.sun state={sun_entity.state})")
            return is_night

        # For future times, calculate sunrise/sunset for the specific forecast date
        try:
            from homeassistant.helpers.sun import get_astral_event_date
            from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET

            # Get sunrise/sunset for the specific forecast date
            forecast_date = check_time.date()

            sunrise = get_astral_event_date(self.hass, SUN_EVENT_SUNRISE, forecast_date)
            sunset = get_astral_event_date(self.hass, SUN_EVENT_SUNSET, forecast_date)

            if sunrise and sunset:
                # Make check_time timezone-aware if it isn't already
                if check_time.tzinfo is None:
                    check_time = check_time.replace(tzinfo=timezone.utc)

                # Check if time is before sunrise or after sunset
                is_night = check_time < sunrise or check_time > sunset

                _LOGGER.debug(
                    f"Future time check: "
                    f"check={check_time.strftime('%Y-%m-%d %H:%M')}, "
                    f"sunset={sunset.strftime('%Y-%m-%d %H:%M')}, "
                    f"sunrise={sunrise.strftime('%Y-%m-%d %H:%M')} → "
                    f"is_night={is_night}"
                )

                return is_night

        except (ImportError, ValueError, AttributeError) as err:
            _LOGGER.debug(f"Could not calculate sun times, using fallback: {err}")

        # Fallback: Night is between 19:00 and 07:00
        hour = check_time.hour
        is_night = hour >= 19 or hour < 7
        _LOGGER.debug(f"Fallback time check: hour={hour} → is_night={is_night}")
        return is_night

    def _generate_with_orchestration(self, hours_count: int) -> list[Forecast]:
        """Generate forecast using ENHANCED orchestration (v3.1.12).
        
        Orchestration Strategy:
        - Hour 0: Persistence (98% accuracy)
        - Hours 1-3: WMO Simple nowcasting (90% accuracy)
        - Hours 4-6: Blended WMO→TIME DECAY transition
        - Hours 7+: Zambretti/Negretti with TIME DECAY
        
        Args:
            hours_count: Number of hours to forecast
            
        Returns:
            List of Forecast objects
        """
        from .combined_model import generate_enhanced_hourly_forecast
        from .language import get_language_index
        from .const import CONF_HEMISPHERE, DEFAULT_HEMISPHERE
        
        # Get language index
        lang_index = get_language_index(self.hass)
        
        # Get hemisphere from config
        hemisphere = DEFAULT_HEMISPHERE
        try:
            config_entries = self.hass.config_entries.async_entries("local_weather_forecast")
            if config_entries:
                hemisphere = config_entries[0].data.get(CONF_HEMISPHERE, DEFAULT_HEMISPHERE)
        except (AttributeError, TypeError, IndexError):
            # In tests, config_entries might be a Mock or unavailable
            pass
        
        # Get Zambretti and Negretti forecasts for the orchestration
        zambretti_result = self.zambretti.forecast_hour(
            pressure=self.pressure_model.current_pressure,
            wind_direction=self.wind_direction,
            pressure_change=0.0,  # Current state
            wind_speed=self.wind_speed
        )
        
        # Get Negretti forecast
        negretti_result = ["", 13]  # Default
        try:
            from .negretti_zambra import calculate_negretti_zambra_forecast
            
            negretti_data = calculate_negretti_zambra_forecast(
                p0=self.pressure_model.current_pressure,
                pressure_change=0.0,
                wind_data=[
                    get_beaufort_scale(self.wind_speed),
                    self.wind_direction,
                    get_wind_dir_text(self.wind_direction),
                    0
                ],
                elevation=self.elevation,
                hemisphere=hemisphere,
                lang_index=lang_index
            )
            negretti_result = [negretti_data[0], negretti_data[1]]
        except Exception as e:
            _LOGGER.debug(f"Could not get Negretti forecast: {e}")
        
        # Prepare weather data dict
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "temperature": self.temperature_model.current_temp,
            "pressure": self.pressure_model.current_pressure,
            "pressure_change": self.pressure_model.change_rate_3h,  # Use change_rate_3h
            "humidity": getattr(self.temperature_model, 'humidity', None) or 70.0,
            "dewpoint": self.temperature_model.current_temp - 3.0,  # Approximation
            "condition": self.current_condition or "unknown",
            "zambretti_result": [zambretti_result[0], zambretti_result[1]],
            "negretti_result": negretti_result,
            "temperature_trend": self.temperature_model.change_rate_1h,  # Use change_rate_1h
            "latitude": self.latitude,  # NEW: For sun-based temperature model
            "longitude": getattr(self.hass.config, 'longitude', 21.25) if self.hass and self.hass.config else 21.25,  # NEW
            "solar_radiation": self.zambretti.solar_radiation if hasattr(self.zambretti, 'solar_radiation') else None,  # NEW
            "cloud_cover": None,  # TODO: Add if available from sensors
        }
        
        # Generate forecasts using enhanced orchestration
        # Note: generate_enhanced_hourly_forecast uses range(hours + 1), so pass hours_count - 1
        _LOGGER.debug(f"🎯 Calling generate_enhanced_hourly_forecast with {hours_count} hours")
        hourly_forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=hours_count - 1,  # Function generates hours 0 to hours (inclusive)
            lang_index=lang_index
        )
        
        # Convert to Home Assistant Forecast format
        forecasts = []
        rain_calc = RainProbabilityCalculator()
        
        for forecast_data in hourly_forecasts:
            future_time = forecast_data["datetime"]
            condition_code = forecast_data["condition_code"]
            temperature = forecast_data["temperature"]
            pressure = forecast_data["pressure"]
            confidence = forecast_data.get("confidence", 0.85)
            
            # Determine if it's night
            is_night = self._is_night(future_time)
            
            # For forecasts, is_current_state should always be False
            # (we want to show predicted precipitation, not just cloudiness)
            # is_current_state=True is only for weather.entity current condition
            is_current_state = False
            
            # Map condition code to HA condition
            from .forecast_mapping import ZAMBRETTI_LETTER_TO_CODE
            forecast_letter = None
            for letter, code in ZAMBRETTI_LETTER_TO_CODE.items():
                if code == condition_code:
                    forecast_letter = letter
                    break
            if not forecast_letter:
                forecast_letter = "A"
            
            condition = map_forecast_to_condition(
                forecast_letter=forecast_letter,
                forecast_num=condition_code,
                is_night_func=lambda: is_night,
                temperature=temperature,
                source=f"Enhanced_orchestration",
                is_current_state=is_current_state
            )
            
            # ═══════════════════════════════════════════════════════════════
            # HUMIDITY PREDICTION FOR DERIVED PARAMETERS
            # Calculate future humidity for dewpoint and apparent temperature
            # NO condition adjustments - trust the orchestrated models!
            # ═══════════════════════════════════════════════════════════════
            humidity = None
            hour_offset = (future_time - datetime.now(timezone.utc)).total_seconds() / 3600
            
            if hasattr(self.temperature_model, 'humidity') and self.temperature_model.humidity is not None:
                current_humidity = self.temperature_model.humidity
                current_temp = self.temperature_model.current_temp
                
                if 0 <= current_humidity <= 100 and current_temp is not None:
                    # Calculate future humidity based on temperature change (Clausius-Clapeyron)
                    from .calculations import calculate_future_humidity
                    
                    pressure_change = pressure - self.pressure_model.current_pressure
                    predicted_humidity = calculate_future_humidity(
                        current_temperature=current_temp,
                        current_humidity=current_humidity,
                        future_temperature=temperature,
                        pressure_change=pressure_change
                    )
                    
                    # Use predicted humidity if available, otherwise fall back to current
                    humidity = predicted_humidity if predicted_humidity is not None else current_humidity
                    
                    if predicted_humidity is not None:
                        _LOGGER.debug(
                            f"💧 Enhanced h{hour_offset:.0f}: RH prediction "
                            f"{current_humidity:.1f}% → {predicted_humidity:.1f}% "
                            f"(T: {current_temp:.1f}°C → {temperature:.1f}°C, ΔP={pressure_change:+.1f}hPa)"
                        )
            
            # Calculate rain probability
            rain_prob = rain_calc.calculate(
                current_pressure=self.pressure_model.current_pressure,
                future_pressure=pressure,
                pressure_trend="steady",  # Already in forecast
                forecast_code=condition_code,
                forecast_letter=forecast_letter
            )
            
            # ═══════════════════════════════════════════════════════════════
            # ✅ v3.1.15: Rain probability COMPLEMENTS forecast, does not override
            # Scientific basis: WMO (2018) - probability supplements deterministic forecast
            # 
            # Forecast condition from code mapping is AUTHORITATIVE
            # - "cloudy" (code 13) already implies rain possibility
            # - "partlycloudy" (code 6) implies scattered showers possible
            # Rain_prob provides additional QUANTITATIVE context (e.g., 75%)
            # but DOES NOT change the icon - the icon is already correct!
            # ═══════════════════════════════════════════════════════════════
            
            # Log for transparency
            _LOGGER.debug(
                f"Enhanced h{hour_offset:.0f}: condition={condition}, rain_prob={rain_prob}% "
                f"(code={condition_code})"
            )
            
            # Calculate dew point from predicted temperature and humidity
            dewpoint_temp = None
            if humidity is not None and 0 < humidity <= 100:
                from .calculations import calculate_dewpoint
                dewpoint_temp = calculate_dewpoint(temperature, humidity)

            # Calculate apparent temperature (feels-like) from predicted conditions
            apparent_temp = None
            if humidity is not None:
                from .calculations import calculate_apparent_temperature
                # Estimate future wind speed (currently use current, could be improved)
                future_wind_speed = self.wind_speed  # TODO: Add wind speed prediction
                apparent_temp = calculate_apparent_temperature(
                    temperature,
                    humidity,
                    future_wind_speed
                )
            
            forecast: Forecast = {
                "datetime": future_time.isoformat(),
                "condition": condition,
                "temperature": round(temperature, 1),
                "native_temperature": round(temperature, 1),
                "precipitation_probability": rain_prob,
                "precipitation": None,
                "native_precipitation": None,
                "is_daytime": not is_night,
                # ✅ NEW: Additional forecast data (same as legacy path)
                "pressure": round(pressure, 1) if pressure else None,
                "native_pressure": round(pressure, 1) if pressure else None,
                "humidity": round(humidity, 1) if humidity is not None else None,
                "dew_point": round(dewpoint_temp, 1) if dewpoint_temp is not None else None,
                "native_dew_point": round(dewpoint_temp, 1) if dewpoint_temp is not None else None,
                "apparent_temperature": round(apparent_temp, 1) if apparent_temp is not None else None,
                "native_apparent_temp": round(apparent_temp, 1) if apparent_temp is not None else None,
            }
            
            forecasts.append(forecast)
        
        _LOGGER.debug(
            f"🎯 Generated {len(forecasts)} forecasts via enhanced orchestration "
            f"(Persistence → WMO Simple → TIME DECAY)"
        )
        
        return forecasts


class DailyForecastGenerator:
    """Generate daily forecasts by aggregating hourly data."""

    def __init__(self, hourly_generator: HourlyForecastGenerator):
        """Initialize daily forecast generator.

        Args:
            hourly_generator: Hourly forecast generator instance
        """
        self.hourly_generator = hourly_generator

    def generate(self, days: int = 3) -> list[Forecast]:
        """Generate daily forecasts.

        Args:
            days: Number of days to forecast

        Returns:
            List of daily Forecast objects
        """
        # Generate detailed hourly forecasts
        # ✅ IMPROVED: Use 1-hour intervals for better daily aggregation accuracy
        # Previous 3-hour intervals could miss important weather changes
        total_hours = days * 24
        hourly_forecasts = self.hourly_generator.generate(
            hours_count=total_hours,
            interval_hours=1  # 1-hour intervals for accurate daily aggregation
        )

        if not hourly_forecasts:
            return []

        # Group by day and aggregate
        daily_forecasts = []
        now = datetime.now(timezone.utc)

        for day_offset in range(days):
            day_start = now + timedelta(days=day_offset)
            # Set to 12:00 (noon) for daily forecast time
            day_time = day_start.replace(hour=12, minute=0, second=0, microsecond=0)

            # Get hourly forecasts for this day
            day_hours = [
                f for f in hourly_forecasts
                if f.get("datetime") and datetime.fromisoformat(f.get("datetime", "")).date() == day_start.date()
            ]

            if not day_hours:
                continue

            # Aggregate temperature: use maximum as daily high, minimum as daily low
            temps = [f.get("temperature", 0.0) for f in day_hours]
            daily_temp_max = round(max(temps), 1)
            daily_temp_min = round(min(temps), 1)

            # ═══════════════════════════════════════════════════════════════
            # ✅ IMPROVED: Weighted condition selection for daily forecast
            # Strategy:
            # 1. Priority-based: Precipitation always wins (rainy > cloudy > clear)
            # 2. Time-weighted: Afternoon (12-16) has 2× weight vs morning/evening
            # 3. Trend-aware: If conditions worsen, use worse condition
            # ═══════════════════════════════════════════════════════════════
            daytime_hours = [
                f for f in day_hours
                if f.get("datetime") and 7 <= datetime.fromisoformat(f.get("datetime", "")).hour <= 19
            ]
            if daytime_hours:
                # Priority system: precipitation > cloudiness > clear
                # Higher number = worse weather = higher priority
                CONDITION_PRIORITY = {
                    "lightning-rainy": 8,  # Worst: Thunderstorms
                    "pouring": 7,          # Very bad: Heavy rain
                    "rainy": 6,            # Bad: Rain
                    "snowy-rainy": 6,      # Bad: Mixed precipitation
                    "snowy": 6,            # Bad: Snow
                    "hail": 6,             # Bad: Hail
                    "cloudy": 4,           # Moderate: Overcast
                    "fog": 3,              # Moderate: Fog
                    "partlycloudy": 2,     # Good: Partly cloudy
                    "sunny": 1,            # Best: Sunny
                    "clear-night": 1,      # Best: Clear night
                    "windy": 3,            # Moderate: Windy
                    "windy-variant": 4,    # Moderate: Windy with clouds
                    "exceptional": 9,      # Exceptional conditions
                }

                # ✅ STEP 1: Check for ANY precipitation - it takes absolute priority
                precipitation_conditions = ["lightning-rainy", "pouring", "rainy", "snowy-rainy", "snowy", "hail"]
                has_precipitation = [
                    f.get("condition") for f in daytime_hours
                    if f.get("condition") in precipitation_conditions
                ]
                
                if has_precipitation:
                    # Use the most severe precipitation condition
                    daily_condition = max(has_precipitation, key=lambda c: CONDITION_PRIORITY.get(c, 0))
                    _LOGGER.debug(
                        f"Daily condition (precipitation priority): {daily_condition} "
                        f"(found {len(has_precipitation)} precip hours out of {len(daytime_hours)} daytime)"
                    )
                else:
                    # ✅ STEP 2: Check for WORSENING TREND
                    # If conditions worsen significantly during the day, use worse condition
                    # Compare morning (7-12) vs afternoon (12-19)
                    morning_hours = [
                        f for f in daytime_hours
                        if 7 <= datetime.fromisoformat(f.get("datetime", "")).hour < 12
                    ]
                    afternoon_hours = [
                        f for f in daytime_hours
                        if 12 <= datetime.fromisoformat(f.get("datetime", "")).hour <= 19
                    ]
                    
                    trend_adjusted = False
                    if morning_hours and afternoon_hours:
                        # Get worst condition in each period
                        morning_worst = max(
                            [f.get("condition", "sunny") for f in morning_hours],
                            key=lambda c: CONDITION_PRIORITY.get(c, 0)
                        )
                        afternoon_worst = max(
                            [f.get("condition", "sunny") for f in afternoon_hours],
                            key=lambda c: CONDITION_PRIORITY.get(c, 0)
                        )
                        
                        # If afternoon is significantly worse (≥2 priority levels)
                        morning_priority = CONDITION_PRIORITY.get(morning_worst, 0)
                        afternoon_priority = CONDITION_PRIORITY.get(afternoon_worst, 0)
                        
                        if afternoon_priority - morning_priority >= 2:
                            # Worsening trend detected - use afternoon condition
                            daily_condition = afternoon_worst
                            trend_adjusted = True
                            _LOGGER.debug(
                                f"Daily condition (worsening trend): {daily_condition} "
                                f"(morning={morning_worst}[{morning_priority}] → "
                                f"afternoon={afternoon_worst}[{afternoon_priority}])"
                            )
                    
                    if not trend_adjusted:
                        # ✅ STEP 3: No precipitation, no trend - use WEIGHTED voting
                        # Afternoon (12-16) gets 2× weight
                        weighted_conditions = []
                        for f in daytime_hours:
                            hour = datetime.fromisoformat(f.get("datetime", "")).hour
                            condition = f.get("condition", "cloudy")
                            
                            # Afternoon hours (12-16) have 2× weight
                            weight = 2.0 if 12 <= hour <= 16 else 1.0
                            
                            # Add condition multiple times based on weight
                            weighted_conditions.extend([condition] * int(weight))
                        
                        # Count weighted frequencies
                        from collections import Counter
                        condition_counts = Counter(weighted_conditions)
                        
                        # Find maximum frequency
                        max_count = max(condition_counts.values())
                        
                        # Get all conditions with maximum frequency (potential tie)
                        tied_conditions = [
                            cond for cond, count in condition_counts.items()
                            if count == max_count
                        ]
                        
                        if len(tied_conditions) == 1:
                            # No tie - use the most frequent (weighted)
                            daily_condition = tied_conditions[0]
                            _LOGGER.debug(
                                f"Daily condition (weighted vote): {daily_condition} "
                                f"(weight={max_count} out of {len(weighted_conditions)} weighted)"
                            )
                        else:
                            # Tie detected - select the worst (highest priority)
                            daily_condition = max(
                                tied_conditions,
                                key=lambda c: CONDITION_PRIORITY.get(c, 0)
                            )
                            _LOGGER.debug(
                                f"Daily condition (tie-break): {daily_condition} "
                                f"(tied with {tied_conditions} at weight={max_count}, "
                                f"selected worst with priority={CONDITION_PRIORITY.get(daily_condition, 0)})"
                            )
            else:
                daily_condition = day_hours[len(day_hours) // 2].get("condition", "cloudy")

            # Convert clear-night to sunny for daily forecasts (daily forecasts are always daytime)
            if daily_condition == "clear-night":
                daily_condition = "sunny"

            # ✅ IMPROVED: Weighted rain probability for daily forecast
            # Strategy:
            # 1. Use MAXIMUM probability during daytime hours (most relevant for planning)
            # 2. Alternative: Weighted average with afternoon (12-16) having 2× weight
            # Using maximum is more conservative and useful for planning
            daytime_rain_probs = [
                f.get("precipitation_probability", 0)
                for f in daytime_hours
                if f.get("precipitation_probability") is not None
            ]
            
            if daytime_rain_probs:
                # Use maximum daytime probability (most conservative, best for planning)
                daily_rain_prob = max(daytime_rain_probs)
                _LOGGER.debug(
                    f"Daily rain probability: max={daily_rain_prob}% "
                    f"(from {len(daytime_rain_probs)} daytime hours, "
                    f"avg={sum(daytime_rain_probs)/len(daytime_rain_probs):.0f}%)"
                )
            else:
                # Fallback: use all day hours
                all_rain_probs = [
                    f.get("precipitation_probability", 0)
                    for f in day_hours
                    if f.get("precipitation_probability") is not None
                ]
                daily_rain_prob = max(all_rain_probs) if all_rain_probs else 0

            # SNOW CONVERSION for daily forecasts
            # Convert rainy/pouring to snowy when daily average temperature is at or below freezing
            # Use average of high and low for decision
            daily_avg_temp = (daily_temp_max + daily_temp_min) / 2.0
            if daily_avg_temp <= 2.0 and daily_condition in ("rainy", "pouring"):
                _LOGGER.debug(
                    f"Daily forecast snow conversion: {daily_condition} → snowy "
                    f"(avg_temp={daily_avg_temp:.1f}°C ≤ 2°C, high={daily_temp_max:.1f}, low={daily_temp_min:.1f}, "
                    f"day={day_time.strftime('%Y-%m-%d')})"
                )
                daily_condition = "snowy"

            # Create daily forecast
            forecast: Forecast = {
                "datetime": day_time.isoformat(),
                "condition": daily_condition,
                "temperature": daily_temp_max,
                "native_temperature": daily_temp_max,
                "templow": daily_temp_min,
                "native_templow": daily_temp_min,
                "precipitation_probability": daily_rain_prob,
                "precipitation": None,  # Not predicted by Zambretti
                "native_precipitation": None,
                "is_daytime": True,  # Daily forecasts always represent daytime
            }

            daily_forecasts.append(forecast)

        _LOGGER.debug(
            f"Aggregated {len(daily_forecasts)} daily forecasts "
            f"from {len(hourly_forecasts)} hourly points"
        )

        return daily_forecasts


class ForecastCalculator:
    """Main facade for forecast calculation.

    This class provides a simple interface to generate forecasts
    using all the advanced models.
    """

    @staticmethod
    def generate_daily_forecast(
        hass: HomeAssistant,
        current_pressure: float,
        current_temp: float,
        pressure_change_3h: float,
        temp_change_1h: float,
        wind_direction: int,
        wind_speed: float,
        latitude: float,
        days: int = 3,
        solar_radiation: float | None = None,
        cloud_cover: float | None = None,
        humidity: float | None = None,
        current_rain_rate: float = 0.0,
        forecast_model: str = FORECAST_MODEL_ENHANCED,
        elevation: float | None = None
    ) -> list[Forecast]:
        """Generate daily forecast.

        Args:
            hass: Home Assistant instance
            current_pressure: Current pressure in hPa
            current_temp: Current temperature in °C
            pressure_change_3h: 3-hour pressure change
            temp_change_1h: 1-hour temperature change
            wind_direction: Wind direction in degrees
            wind_speed: Wind speed in m/s (used for temperature and weather prediction)
            latitude: Location latitude
            days: Number of days to forecast
            solar_radiation: Current solar radiation in W/m² (optional, only works during daylight)
            cloud_cover: Current cloud cover in % (optional)
            humidity: Relative humidity in % (optional, used to estimate cloud cover)
            current_rain_rate: Current rain rate in mm/h (optional)
            forecast_model: Which model to use (FORECAST_MODEL_ZAMBRETTI, FORECAST_MODEL_NEGRETTI, FORECAST_MODEL_ENHANCED)

        Returns:
            List of daily Forecast objects
        """
        # Create models
        pressure_model = PressureModel(current_pressure, pressure_change_3h)
        temp_model = TemperatureModel(
            current_temp,
            temp_change_1h,
            hass=hass,
            solar_radiation=solar_radiation,
            cloud_cover=cloud_cover,
            humidity=humidity,
            wind_speed=wind_speed,
            elevation=elevation
        )
        zambretti = ZambrettiForecaster(hass=hass, latitude=latitude)

        # Create generators
        hourly_gen = HourlyForecastGenerator(
            hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction,
            wind_speed,
            latitude,
            current_rain_rate,
            forecast_model
        )

        daily_gen = DailyForecastGenerator(hourly_gen)

        return daily_gen.generate(days)

    @staticmethod
    def generate_hourly_forecast(
        hass: HomeAssistant,
        current_pressure: float,
        current_temp: float,
        pressure_change_3h: float,
        temp_change_1h: float,
        wind_direction: int,
        wind_speed: float,
        latitude: float,
        hours: int = 24,
        solar_radiation: float | None = None,
        cloud_cover: float | None = None,
        humidity: float | None = None,
        current_rain_rate: float = 0.0,
        forecast_model: str = FORECAST_MODEL_ENHANCED,
        elevation: float | None = None
    ) -> list[Forecast]:
        """Generate hourly forecast.

        Args:
            hass: Home Assistant instance
            current_pressure: Current pressure in hPa
            current_temp: Current temperature in °C
            pressure_change_3h: 3-hour pressure change
            temp_change_1h: 1-hour temperature change
            wind_direction: Wind direction in degrees
            wind_speed: Wind speed in m/s (used for temperature and weather prediction)
            latitude: Location latitude
            hours: Number of hours to forecast
            solar_radiation: Current solar radiation in W/m² (optional, only works during daylight)
            cloud_cover: Current cloud cover in % (optional)
            humidity: Relative humidity in % (optional, used to estimate cloud cover)
            current_rain_rate: Current rain rate in mm/h (optional)
            forecast_model: Which model to use (FORECAST_MODEL_ZAMBRETTI, FORECAST_MODEL_NEGRETTI, FORECAST_MODEL_ENHANCED)

        Returns:
            List of hourly Forecast objects
        """
        # Create models
        pressure_model = PressureModel(current_pressure, pressure_change_3h)
        temp_model = TemperatureModel(
            current_temp,
            temp_change_1h,
            hass=hass,
            solar_radiation=solar_radiation,
            cloud_cover=cloud_cover,
            humidity=humidity,
            wind_speed=wind_speed,
            elevation=elevation
        )
        zambretti = ZambrettiForecaster(hass=hass, latitude=latitude)

        # Create generator
        hourly_gen = HourlyForecastGenerator(
            hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction,
            wind_speed,
            latitude,
            current_rain_rate,
            forecast_model
        )

        return hourly_gen.generate(hours_count=hours, interval_hours=1)

