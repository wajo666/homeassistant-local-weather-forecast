"""
Advanced forecast models for Local Weather Forecast integration.

Provides scientific weather forecasting models based on pressure trends,
temperature cycles, and barometric algorithms.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .forecast_calculator import ZambrettiForecaster

_LOGGER = logging.getLogger(__name__)


def map_forecast_to_condition(
    forecast_text: str,
    forecast_num: int | None = None,
    is_night_func: Callable[[], bool] | None = None,
    source: str = "Unknown"
) -> str:
    """Universal function to map any forecast to Home Assistant weather condition.

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
    text_lower = forecast_text.lower()
    is_night = is_night_func() if is_night_func else False

    # Priority 1: Strong weather (storms, thunder) - 25
    if any(word in text_lower for word in ["storm", "thunder", "gale", "tempest"]):
        _LOGGER.debug(f"ConditionMap[{source}]: '{forecast_text}' → lightning-rainy (storm keywords)")
        return "lightning-rainy"

    # Priority 2: Heavy rain / Pouring - 20-24
    # These are "Rain at times" / "Frequent rain" conditions
    if forecast_num is not None and forecast_num >= 20:
        _LOGGER.debug(f"ConditionMap[{source}]: '{forecast_text}' (num={forecast_num}) → pouring (heavy rain zone)")
        return "pouring"

    if any(word in text_lower for word in ["heavy rain", "pouring", "frequent", "much rain", "torrential"]):
        _LOGGER.debug(f"ConditionMap[{source}]: '{forecast_text}' → pouring (heavy rain keywords)")
        return "pouring"

    # Priority 3: Rain (includes showers) - 7-19
    # Look for explicit rain/shower mentions, but NOT "possibly showers" (that's partlycloudy)
    has_possible_showers = any(word in text_lower for word in ["possibly", "possible", "may", "might", "možné"])
    has_rain_keywords = any(word in text_lower for word in ["rain", "shower", "wet", "dážď", "prší", "zrážk"])

    if has_rain_keywords and not has_possible_showers:
        _LOGGER.debug(f"ConditionMap[{source}]: '{forecast_text}' (num={forecast_num}) → rainy")
        return "rainy"

    # Priority 4: Poor/unsettled weather (cloudy/changeable) - 15-19 but without explicit rain
    # "Unsettled" without rain mention = partlycloudy
    is_unsettled = any(word in text_lower for word in ["unsettled", "changeable", "variable", "premenlivý", "nestále"])
    if is_unsettled:
        _LOGGER.debug(
            f"ConditionMap[{source}]: '{forecast_text}' (num={forecast_num}) → partlycloudy "
            f"(unsettled, night={is_night})"
        )
        return "partlycloudy"

    # Priority 5: Cloudy weather
    if any(word in text_lower for word in ["cloudy", "overcast", "oblačn", "zamračen"]):
        # Check if it's "partly cloudy" vs "fully cloudy"
        if any(word in text_lower for word in ["partly", "polo", "miestami", "fairly"]):
            _LOGGER.debug(f"ConditionMap[{source}]: '{forecast_text}' → partlycloudy (partly cloudy, night={is_night})")
            return "partlycloudy"
        else:
            _LOGGER.debug(f"ConditionMap[{source}]: '{forecast_text}' → cloudy (fully cloudy)")
            return "cloudy"

    # Priority 6: Fair/fine weather (truly clear/sunny conditions) - 0-5
    # Model-specific fair weather thresholds
    is_fair_by_number = False
    if forecast_num is not None:
        if source == "Zambretti" or source == "Enhanced (Dynamic)":
            # Zambretti 0-5: "Settled fine" to "Fairly fine, improving"
            is_fair_by_number = forecast_num <= 5
        elif source == "Negretti":
            # Negretti 0-2: "Stabilne pekné počasie!" to "Polooblačno..."
            is_fair_by_number = forecast_num <= 2
        else:
            # Combined/other: use conservative threshold
            is_fair_by_number = forecast_num <= 5

    # Check for "fine" / "fair" keywords
    is_fine_text = any(word in text_lower for word in [
        "settled", "stable", "fine", "fair", "stabilne", "pekné", "jasn", "slnečn"
    ])

    if is_fair_by_number or is_fine_text:
        # But check if text mentions problems (later rain, showers, becoming unsettled)
        has_problems = any(word in text_lower for word in [
            "later", "becoming", "shower", "rain", "unsettled", "changeable",
            "neskôr", "prehán", "dážď", "nestál"
        ])

        if not has_problems or forecast_num == 0:
            # Truly fair: no problems mentioned OR forecast=0 (settled fine)
            condition = "clear-night" if is_night else "sunny"
            _LOGGER.debug(
                f"ConditionMap[{source}]: '{forecast_text}' (num={forecast_num}) → {condition} "
                f"(truly fair weather, night={is_night})"
            )
            return condition
        else:
            # Fine but with caveats → partlycloudy
            _LOGGER.debug(
                f"ConditionMap[{source}]: '{forecast_text}' (num={forecast_num}) → partlycloudy "
                f"(fair with caveats, night={is_night})"
            )
            return "partlycloudy"

    # Default: partly cloudy (safe fallback)
    _LOGGER.debug(
        f"ConditionMap[{source}]: '{forecast_text}' (num={forecast_num}) → partlycloudy "
        f"(default fallback, night={is_night})"
    )
    return "partlycloudy"


class PressureModel:
    """Advanced pressure trend forecasting model."""

    def __init__(self, current_pressure: float, pressure_change_3h: float):
        """Initialize pressure model.

        Args:
            current_pressure: Current sea level pressure (hPa)
            pressure_change_3h: Pressure change over last 3 hours (hPa)
        """
        self.current = current_pressure
        self.change_3h = pressure_change_3h
        self.change_per_hour = pressure_change_3h / 3.0 if pressure_change_3h else 0.0

    def predict(self, hours_ahead: int) -> float:
        """Predict pressure N hours ahead using exponential decay model.

        Uses meteorologically proven model:
        - Linear trend for first 6 hours
        - Exponential decay for 6-24 hours (trends don't continue indefinitely)
        - Maximum change limit: ±20 hPa

        Args:
            hours_ahead: Number of hours to predict ahead

        Returns:
            Predicted pressure in hPa
        """
        if hours_ahead <= 0:
            return self.current

        # Linear trend for short term (0-6 hours)
        if hours_ahead <= 6:
            predicted_change = self.change_per_hour * hours_ahead
        else:
            # Exponential decay for long term (6-24 hours)
            # Change slows down over time
            decay_factor = 0.85 ** (hours_ahead - 6)  # 15% decay per hour after 6h
            linear_6h = self.change_per_hour * 6
            additional = self.change_per_hour * (hours_ahead - 6) * decay_factor
            predicted_change = linear_6h + additional

        # Realistic limits: pressure doesn't change more than ±20 hPa in 24h
        predicted_change = max(-20.0, min(20.0, predicted_change))

        predicted_pressure = self.current + predicted_change

        # Absolute limits: 910-1085 hPa (matches Negretti-Zambra global range)
        # Covers global conditions including Medicanes, Australian cyclones, European storms
        result = max(910.0, min(1085.0, predicted_pressure))

        _LOGGER.debug(
            f"PressureModel: {hours_ahead}h → {result:.1f} hPa "
            f"(current={self.current:.1f}, change={predicted_change:+.1f}, rate={self.change_3h:+.1f}/3h)"
        )

        return result

    def get_trend(self, hours_ahead: int) -> str:
        """Get pressure trend description.

        Args:
            hours_ahead: Hours to look ahead

        Returns:
            "rising", "falling", or "steady"
        """
        future_pressure = self.predict(hours_ahead)
        change = future_pressure - self.current

        if change > 1.0:
            trend = "rising"
        elif change < -1.0:
            trend = "falling"
        else:
            trend = "steady"

        _LOGGER.debug(
            f"PressureTrend: {hours_ahead}h → {trend} "
            f"(current={self.current:.1f}, future={future_pressure:.1f}, Δ={change:+.1f})"
        )

        return trend


class TemperatureModel:
    """Advanced temperature forecasting with diurnal cycle."""

    def __init__(
        self,
        current_temp: float,
        temp_change_1h: float,
        current_time: datetime | None = None
    ):
        """Initialize temperature model.

        Args:
            current_temp: Current temperature (°C)
            temp_change_1h: Temperature change over last 1 hour (°C)
            current_time: Current datetime (default: now)
        """
        self.current = current_temp
        self.change_1h = temp_change_1h
        self.time = current_time or datetime.now(timezone.utc)

    def predict(self, hours_ahead: int) -> float:
        """Predict temperature N hours ahead using diurnal cycle model.

        Combines:
        1. Current trend (temp_change_1h)
        2. Diurnal (daily) cycle - warmer during day, cooler at night
        3. Realistic limits

        Args:
            hours_ahead: Number of hours to predict ahead

        Returns:
            Predicted temperature in °C
        """
        if hours_ahead <= 0:
            return self.current

        future_time = self.time + timedelta(hours=hours_ahead)

        # Current hour of day (0-23)
        current_hour = self.time.hour
        future_hour = future_time.hour

        # Diurnal cycle adjustment
        # Peak at 14:00 (~+2°C), minimum at 04:00 (~-1.5°C)
        diurnal_adjustment = self._calculate_diurnal_effect(
            current_hour, future_hour
        )

        # Trend-based change (decay over time)
        decay_factor = 0.75 ** hours_ahead  # 25% decay per hour (faster damping)
        trend_change = self.change_1h * hours_ahead * decay_factor

        # Combine effects
        predicted_temp = self.current + trend_change + diurnal_adjustment

        # Realistic limits: ±12°C change PER 24h (progressive for multi-day)
        # For predictions > 24h, allow cumulative change but limit daily rate
        max_change_per_day = 12.0
        days_ahead = hours_ahead / 24.0
        max_total_change = max_change_per_day * min(days_ahead, 3.0)  # Cap at 3 days

        if abs(predicted_temp - self.current) > max_total_change:
            if predicted_temp > self.current:
                predicted_temp = self.current + max_total_change
            else:
                predicted_temp = self.current - max_total_change

        result = round(predicted_temp, 1)

        _LOGGER.debug(
            f"TempModel: {hours_ahead}h → {result:.1f}°C "
            f"(current={self.current:.1f}, trend={trend_change:+.1f}, diurnal={diurnal_adjustment:+.1f})"
        )

        return result

    def _calculate_diurnal_effect(
        self,
        current_hour: int,
        future_hour: int
    ) -> float:
        """Calculate diurnal (daily) temperature cycle effect.

        Simple sinusoidal model:
        - Peak at 14:00 (2 PM)
        - Minimum at 04:00 (4 AM)
        - Amplitude: ~2.0°C (winter/autumn typical)

        Args:
            current_hour: Current hour (0-23)
            future_hour: Future hour (0-23)

        Returns:
            Temperature adjustment in °C
        """
        import math

        # Sinusoidal cycle: peak at 14:00, minimum at 04:00
        amplitude = 2.0  # °C (conservative for winter)
        peak_hour = 14.0

        # Current position in cycle
        current_phase = (current_hour - peak_hour) * math.pi / 12.0
        current_effect = amplitude * math.cos(current_phase)

        # Future position in cycle
        future_phase = (future_hour - peak_hour) * math.pi / 12.0
        future_effect = amplitude * math.cos(future_phase)

        # Net change
        return future_effect - current_effect


class HourlyForecastGenerator:
    """Generate hourly weather forecasts using advanced models."""

    def __init__(
        self,
        hass: HomeAssistant,
        pressure_model: PressureModel,
        temp_model: TemperatureModel,
        zambretti: "ZambrettiForecaster",
        wind_direction: int = 0,
        wind_speed: float = 0.0,
        latitude: float = 0.0
    ):
        """Initialize hourly forecast generator.

        Args:
            hass: Home Assistant instance
            pressure_model: Pressure forecasting model
            temp_model: Temperature forecasting model
            zambretti: Zambretti forecaster instance
            wind_direction: Wind direction in degrees (0-360)
            wind_speed: Wind speed in m/s
            latitude: Station latitude for season detection
        """
        self.hass = hass
        self.pressure = pressure_model
        self.temperature = temp_model
        self.zambretti = zambretti
        self.wind_dir = wind_direction
        self.wind_speed = wind_speed
        self.latitude = latitude

    def generate(
        self,
        hours_count: int = 24,
        interval_hours: int = 1
    ) -> list[dict]:
        """Generate hourly forecast points.

        Args:
            hours_count: Total hours to forecast (default: 24)
            interval_hours: Interval between points (default: 1 hour)

        Returns:
            List of forecast dictionaries with datetime, condition, temperature, etc.
        """
        _LOGGER.debug(
            f"Generating {hours_count}h forecast with {interval_hours}h intervals"
        )

        forecasts = []
        current_time = self.temperature.time

        for hour in range(0, hours_count + 1, interval_hours):
            forecast_time = current_time + timedelta(hours=hour)

            # Predict values
            predicted_pressure = self.pressure.predict(hour)
            predicted_temp = self.temperature.predict(hour)
            pressure_trend = self.pressure.get_trend(hour)

            # Run Zambretti for this hour
            zambretti_result = self.zambretti.forecast(
                p0=predicted_pressure,
                trend_text=pressure_trend,
                wind_direction=self.wind_dir,
                wind_speed_ms=self.wind_speed,
                latitude=self.latitude
            )

            # Extract forecast data
            forecast_text = zambretti_result[0] if zambretti_result else "Unknown"
            forecast_num = zambretti_result[1] if len(zambretti_result) > 1 else 0

            # For hour=0 (current time), use None to trigger sun entity check
            # For future hours, pass the forecast_time for astral calculation
            check_time = None if hour == 0 else forecast_time

            # Map to Home Assistant condition with night detection
            # IMPORTANT: Pass check_time (not forecast_time) to ensure hour=0 uses sun entity
            condition = self._map_to_condition(forecast_num, forecast_text, check_time)

            _LOGGER.debug(
                f"🎯 Hour {hour} ({forecast_time.strftime('%H:%M')}): "
                f"forecast_text='{forecast_text}', num={forecast_num}, "
                f"check_time={'None (current)' if check_time is None else check_time.strftime('%H:%M')}, "
                f"→ condition={condition}"
            )

            # Calculate rain probability
            rain_prob = self._calculate_rain_probability(
                forecast_num,
                predicted_pressure,
                pressure_trend
            )

            # Determine if this forecast time is daytime
            is_daytime = not self._is_night_time(check_time)

            forecast_point = {
                "datetime": forecast_time.isoformat(),
                "condition": condition,
                "temperature": predicted_temp,
                "native_temperature": predicted_temp,
                "pressure": predicted_pressure,
                "precipitation_probability": rain_prob,
                "is_daytime": is_daytime,
                "forecast_text": forecast_text,
            }

            forecasts.append(forecast_point)

            _LOGGER.debug(
                f"Hour {hour}: {forecast_time.strftime('%H:%M')} - "
                f"{condition}, {predicted_temp}°C, {predicted_pressure}hPa, "
                f"rain {rain_prob}%, {'day' if is_daytime else 'night'}"
            )

        return forecasts

    def _map_to_condition(self, forecast_num: int, forecast_text: str, forecast_time: datetime | None = None) -> str:
        """Map Zambretti forecast to Home Assistant weather condition.

        This is a Zambretti-specific wrapper around the universal map_forecast_to_condition().

        Args:
            forecast_num: Zambretti forecast number (0-25)
            forecast_text: Zambretti forecast text
            forecast_time: Time to check for night (defaults to now)

        Returns:
            HA condition: sunny, cloudy, rainy, etc.
        """
        # Use universal mapping function
        return map_forecast_to_condition(
            forecast_text=forecast_text,
            forecast_num=forecast_num,
            is_night_func=lambda: self._is_night_time(forecast_time),
            source="Zambretti"
        )

    def _is_night_time(self, check_time: datetime | None = None) -> bool:
        """Check if given time is during night (sun below horizon).

        Uses Home Assistant's sun entity for current time, and calculates
        sunrise/sunset for future times using latitude.

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if nighttime, False if daytime
        """
        try:
            import homeassistant.util.dt as dt_util
            from datetime import date

            # Get sun entity state
            sun_entity = self.hass.states.get("sun.sun")

            # Check if check_time is current time (within 30 minute tolerance)
            now = dt_util.now()
            is_current_time = False

            _LOGGER.debug(
                f"🌙 Night check START: check_time={check_time.strftime('%Y-%m-%d %H:%M:%S') if check_time else 'None'}, "
                f"now={now.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            if check_time is None:
                is_current_time = True
                _LOGGER.debug("🌙 Night check: check_time is None → treating as CURRENT time")
            elif check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=timezone.utc)
                time_diff = abs((check_time - now).total_seconds())
                is_current_time = time_diff < 1800  # Within 30 minutes = current time
                _LOGGER.debug(
                    f"🌙 Night check: check_time had no timezone, added UTC. "
                    f"Time diff={time_diff:.0f}s, is_current={is_current_time}"
                )
            else:
                time_diff = abs((check_time - now).total_seconds())
                is_current_time = time_diff < 1800  # Within 30 minutes = current time
                _LOGGER.debug(
                    f"🌙 Night check: check_time has timezone. "
                    f"Time diff={time_diff:.0f}s, is_current={is_current_time}"
                )

            if is_current_time:
                # Check current time using sun entity
                if sun_entity:
                    is_night = sun_entity.state == "below_horizon"
                    _LOGGER.debug(
                        f"🌙 Night check CURRENT time from sun.sun: {is_night} "
                        f"(state={sun_entity.state}, check_time={check_time.strftime('%H:%M') if check_time else 'now'})"
                    )
                    return is_night
                else:
                    # Fallback to simple time check
                    current_hour = now.hour
                    is_night = current_hour >= 19 or current_hour < 7
                    _LOGGER.debug(
                        f"🌙 Night check CURRENT time (no sun entity): hour={current_hour}, is_night={is_night}"
                    )
                    return is_night
            else:
                # For future times, calculate sunrise/sunset using astral
                _LOGGER.debug(f"🌙 Night check: Using ASTRAL for FUTURE time")
                try:
                    from astral import LocationInfo
                    from astral.sun import sun

                    # Create location with latitude (longitude not critical for sunrise/sunset)
                    location = LocationInfo(
                        name="Station",
                        region="",
                        timezone="UTC",
                        latitude=self.latitude,
                        longitude=0  # Approximate, not critical
                    )

                    # Get sunrise/sunset for the forecast day
                    forecast_date = check_time.date()
                    s = sun(location.observer, date=forecast_date)

                    sunrise = s["sunrise"]
                    sunset = s["sunset"]

                    _LOGGER.debug(
                        f"🌙 Night check FUTURE: date={forecast_date}, "
                        f"sunrise={sunrise.strftime('%H:%M')}, sunset={sunset.strftime('%H:%M')}"
                    )

                    # Make check_time timezone-aware if it isn't already
                    if check_time.tzinfo is None:
                        check_time = check_time.replace(tzinfo=timezone.utc)

                    # Check if time is before sunrise or after sunset
                    is_night = check_time < sunrise or check_time > sunset

                    _LOGGER.debug(
                        f"🌙 Night check FUTURE result: check_time={check_time.strftime('%H:%M')}, "
                        f"is_night={is_night} (sunrise={sunrise.strftime('%H:%M')}, sunset={sunset.strftime('%H:%M')})"
                    )

                    return is_night

                    _LOGGER.debug(
                        f"Night check for {check_time.strftime('%Y-%m-%d %H:%M')}: "
                        f"sunrise={sunrise.strftime('%H:%M')}, sunset={sunset.strftime('%H:%M')}, "
                        f"is_night={is_night}"
                    )

                    return is_night

                except ImportError:
                    # Fallback if astral not available
                    _LOGGER.debug("Astral not available, using simple hour check for future time")
                    hour = check_time.hour
                    return hour >= 19 or hour < 7
                except Exception as e:
                    _LOGGER.debug(f"Error calculating sunrise/sunset: {e}, falling back to hour check")
                    hour = check_time.hour
                    return hour >= 19 or hour < 7

        except Exception as e:
            _LOGGER.debug(f"Night check error: {e}")
            return False

    def _calculate_rain_probability(
        self,
        forecast_num: int,
        pressure: float,
        trend: str
    ) -> int:
        """Calculate rain probability percentage.

        Args:
            forecast_num: Zambretti forecast number (0-25)
            pressure: Predicted pressure (hPa)
            trend: Pressure trend ("rising", "falling", "steady")

        Returns:
            Rain probability 0-100%
        """
        # Base probability from Zambretti number
        # 0-5: Low (0-20%)
        # 6-14: Medium (20-60%)
        # 15-25: High (60-100%)

        if forecast_num <= 5:
            base_prob = forecast_num * 4  # 0-20%
        elif forecast_num <= 14:
            base_prob = 20 + (forecast_num - 5) * 4  # 20-56%
        else:
            base_prob = 56 + (forecast_num - 14) * 4  # 56-100%

        # Adjust for pressure
        if pressure < 1000:
            base_prob += 10  # Low pressure increases rain chance
        elif pressure > 1020:
            base_prob -= 10  # High pressure decreases rain chance

        # Adjust for trend
        if trend == "falling":
            base_prob += 5  # Falling pressure increases rain
        elif trend == "rising":
            base_prob -= 5  # Rising pressure decreases rain

        # Clamp to 0-100
        result = max(0, min(100, base_prob))

        _LOGGER.debug(
            f"RainProb: Z{forecast_num} @ {pressure:.1f}hPa ({trend}) → {result}% "
            f"(base={base_prob})"
        )

        return result


class DailyForecastGenerator:
    """Generate daily weather forecasts using advanced models."""

    def __init__(
        self,
        hourly_generator: HourlyForecastGenerator
    ):
        """Initialize daily forecast generator.

        Args:
            hourly_generator: Configured hourly forecast generator
        """
        self.hourly = hourly_generator

    def generate(self, days_count: int = 3) -> list[dict]:
        """Generate daily forecast for N days.

        Aggregates hourly forecasts into daily summaries.

        Args:
            days_count: Number of days to forecast (default: 3)

        Returns:
            List of daily forecast dictionaries
        """
        _LOGGER.debug(f"Generating {days_count}-day forecast")

        # Generate 24-hour forecasts for each day
        hourly_forecasts = self.hourly.generate(
            hours_count=days_count * 24,
            interval_hours=3  # Every 3 hours for efficiency
        )

        if not hourly_forecasts:
            _LOGGER.warning("No hourly forecasts generated")
            return []

        daily_forecasts = []
        current_time = self.hourly.temperature.time

        for day in range(days_count):
            day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            day_start += timedelta(days=day)
            forecast_time = day_start.replace(hour=14)  # 2 PM as representative

            # Get hourly points for this day
            day_hours = [
                h for h in hourly_forecasts
                if day_start <= datetime.fromisoformat(h["datetime"]) < day_start + timedelta(days=1)
            ]

            if not day_hours:
                continue

            # Aggregate: most common condition, temp range, avg rain prob
            condition = self._get_dominant_condition(day_hours)
            temp_high = max(h["temperature"] for h in day_hours)
            temp_low = min(h["temperature"] for h in day_hours)
            avg_rain_prob = sum(h["precipitation_probability"] for h in day_hours) / len(day_hours)

            daily_forecast = {
                "datetime": forecast_time.isoformat(),
                "condition": condition,
                "temperature": temp_high,  # High temp
                "native_temperature": temp_high,
                "templow": temp_low,
                "native_templow": temp_low,
                "precipitation_probability": round(avg_rain_prob),
                "is_daytime": True,  # Daily forecasts represent daytime
            }

            daily_forecasts.append(daily_forecast)

            _LOGGER.debug(
                f"Day {day}: {forecast_time.strftime('%Y-%m-%d')} - "
                f"{condition}, {temp_low}-{temp_high}°C, rain {round(avg_rain_prob)}%"
            )

        return daily_forecasts

    def _get_dominant_condition(self, hourly_points: list[dict]) -> str:
        """Get the most representative weather condition for a day.

        Args:
            hourly_points: List of hourly forecast dictionaries

        Returns:
            Dominant HA weather condition
        """
        if not hourly_points:
            return "partlycloudy"

        # Count occurrences
        conditions = [h["condition"] for h in hourly_points]
        condition_counts = {}
        for cond in conditions:
            condition_counts[cond] = condition_counts.get(cond, 0) + 1

        # Return most common
        dominant = max(condition_counts, key=condition_counts.get)

        _LOGGER.debug(
            f"DominantCondition: {dominant} (counts: {condition_counts})"
        )

        return dominant

