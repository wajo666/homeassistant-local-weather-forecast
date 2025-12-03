"""
Advanced forecast models for Local Weather Forecast integration.

Provides scientific weather forecasting models based on pressure trends,
temperature cycles, and barometric algorithms.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from .zambretti import ZambrettiForecaster

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


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
        predicted_change = max(-20, min(20, predicted_change))

        predicted_pressure = self.current + predicted_change

        # Absolute limits: 950-1050 hPa (Zambretti range)
        return max(950, min(1050, predicted_pressure))

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
            return "rising"
        elif change < -1.0:
            return "falling"
        else:
            return "steady"


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
        # Peak at 14:00 (~+3°C), minimum at 04:00 (~-2°C)
        diurnal_adjustment = self._calculate_diurnal_effect(
            current_hour, future_hour
        )

        # Trend-based change (decay over time)
        decay_factor = 0.9 ** hours_ahead  # 10% decay per hour
        trend_change = self.change_1h * hours_ahead * decay_factor

        # Combine effects
        predicted_temp = self.current + trend_change + diurnal_adjustment

        # Realistic limits: ±15°C change in 24h
        max_change = 15.0
        if abs(predicted_temp - self.current) > max_change:
            if predicted_temp > self.current:
                predicted_temp = self.current + max_change
            else:
                predicted_temp = self.current - max_change

        return round(predicted_temp, 1)

    def _calculate_diurnal_effect(
        self,
        current_hour: int,
        future_hour: int
    ) -> float:
        """Calculate diurnal (daily) temperature cycle effect.

        Simple sinusoidal model:
        - Peak at 14:00 (2 PM)
        - Minimum at 04:00 (4 AM)
        - Amplitude: ~2.5°C

        Args:
            current_hour: Current hour (0-23)
            future_hour: Future hour (0-23)

        Returns:
            Temperature adjustment in °C
        """
        import math

        # Sinusoidal cycle: peak at 14:00, minimum at 04:00
        amplitude = 2.5  # °C
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
        zambretti: ZambrettiForecaster,
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

            # Map to Home Assistant condition
            condition = self._map_to_condition(forecast_num, forecast_text)

            # Calculate rain probability
            rain_prob = self._calculate_rain_probability(
                forecast_num,
                predicted_pressure,
                pressure_trend
            )

            forecast_point = {
                "datetime": forecast_time.isoformat(),
                "condition": condition,
                "temperature": predicted_temp,
                "native_temperature": predicted_temp,
                "pressure": predicted_pressure,
                "precipitation_probability": rain_prob,
                "forecast_text": forecast_text,
            }

            forecasts.append(forecast_point)

            _LOGGER.debug(
                f"Hour {hour}: {forecast_time.strftime('%H:%M')} - "
                f"{condition}, {predicted_temp}°C, {predicted_pressure}hPa, "
                f"rain {rain_prob}%"
            )

        return forecasts

    def _map_to_condition(self, forecast_num: int, forecast_text: str) -> str:
        """Map Zambretti forecast to Home Assistant weather condition.

        Args:
            forecast_num: Zambretti forecast number (0-25)
            forecast_text: Zambretti forecast text

        Returns:
            HA condition: sunny, cloudy, rainy, etc.
        """
        # Zambretti mapping to HA conditions
        # Based on forecast number and keywords in text

        text_lower = forecast_text.lower()

        # Strong weather
        if any(word in text_lower for word in ["storm", "thunder", "gale"]):
            return "lightning-rainy"

        # Rain
        if forecast_num >= 20 or any(word in text_lower for word in ["rain", "shower", "wet"]):
            if "heavy" in text_lower:
                return "pouring"
            return "rainy"

        # Poor weather
        if forecast_num >= 15 or any(word in text_lower for word in ["unsettled", "changeable"]):
            return "partlycloudy"

        # Fair weather
        if forecast_num <= 5 or any(word in text_lower for word in ["fine", "fair", "settled"]):
            return "sunny"

        # Default: partly cloudy
        return "partlycloudy"

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
        return max(0, min(100, base_prob))


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
        return max(condition_counts, key=condition_counts.get)

