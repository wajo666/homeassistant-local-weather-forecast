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

from .const import ZAMBRETTI_TO_CONDITION
from .zambretti import calculate_zambretti_forecast


class Forecast(TypedDict, total=False):
    """Typed dictionary for forecast data."""
    datetime: str
    condition: str
    temperature: float
    native_temperature: float
    precipitation: float | None
    native_precipitation: float | None
    precipitation_probability: int | None

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
        change_rate_3h: float,
        smoothing_factor: float = 0.3,
        damping_factor: float = 0.95
    ):
        """Initialize pressure model.

        Args:
            current_pressure: Current pressure in hPa
            change_rate_3h: Pressure change over last 3 hours in hPa
            smoothing_factor: Exponential smoothing (0-1, higher = more responsive)
            damping_factor: Rate decay factor (0-1, closer to 1 = slower decay)
        """
        self.current_pressure = current_pressure
        self.change_rate_3h = change_rate_3h
        self.change_rate_1h = change_rate_3h / 3.0  # Convert to hourly rate
        self.smoothing_factor = smoothing_factor
        self.damping_factor = damping_factor

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

        predicted = self.current_pressure + total_change

        # Clamp to realistic atmospheric pressure range (950-1050 hPa)
        return max(950.0, min(1050.0, predicted))

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
    """Model temperature with diurnal (daily) cycle.

    Combines:
    - Current temperature
    - Temperature trend (hourly change rate)
    - Diurnal cycle (based on solar position)
    - Seasonal baseline adjustment
    """

    def __init__(
        self,
        current_temp: float,
        change_rate_1h: float,
        diurnal_amplitude: float = 5.0
    ):
        """Initialize temperature model.

        Args:
            current_temp: Current temperature in °C
            change_rate_1h: Temperature change rate per hour
            diurnal_amplitude: Daily temperature swing amplitude (default ±5°C)
        """
        self.current_temp = current_temp
        self.change_rate_1h = change_rate_1h
        self.diurnal_amplitude = diurnal_amplitude
        self.current_hour = datetime.now(timezone.utc).hour

    def predict(self, hours_ahead: int) -> float:
        """Predict temperature N hours ahead.

        Combines linear trend with sinusoidal diurnal cycle.
        Peak at 14:00, minimum at 04:00.

        Args:
            hours_ahead: Hours into the future

        Returns:
            Predicted temperature in °C
        """
        if hours_ahead == 0:
            return self.current_temp

        # Linear trend component
        trend_change = self.change_rate_1h * hours_ahead

        # Diurnal cycle component
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

        # Combine trend and diurnal cycle
        predicted = self.current_temp + trend_change + diurnal_change

        # Realistic temperature limits (-40 to +50°C)
        return max(-40.0, min(50.0, predicted))

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

    def __init__(self, hass: HomeAssistant | None = None, latitude: float = 50.0):
        """Initialize Zambretti forecaster.

        Args:
            hass: Home Assistant instance for sun entity access
            latitude: Location latitude for seasonal adjustment
        """
        self.hass = hass
        self.latitude = latitude

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

        Args:
            letter_code: Zambretti letter (A-Z)
            forecast_time: Datetime to check for day/night

        Returns:
            HA weather condition string
        """
        condition = ZAMBRETTI_TO_CONDITION.get(letter_code, "partlycloudy")

        # Convert sunny to clear-night during night hours
        if condition == "sunny" and self._is_night(forecast_time):
            return "clear-night"

        return condition

    def _is_night(self, check_time: datetime) -> bool:
        """Check if it's night time based on sun position.

        Args:
            check_time: Time to check

        Returns:
            True if sun is below horizon
        """
        # Make check_time timezone aware first if needed
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=timezone.utc)

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

        time_diff = abs((check_time - now).total_seconds())

        if time_diff < 60:
            return sun_entity.state == "below_horizon"

        # For future times, use sunrise/sunset times from sun entity
        try:
            # Ensure check_time is timezone-aware
            if check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=timezone.utc)

            # Get next sunrise and sunset
            next_rising_str = sun_entity.attributes.get("next_rising")
            next_setting_str = sun_entity.attributes.get("next_setting")

            if next_rising_str and next_setting_str:
                from homeassistant.util import dt as dt_util
                next_rising = dt_util.parse_datetime(next_rising_str)
                next_setting = dt_util.parse_datetime(next_setting_str)

                if next_rising and next_setting:
                    # If check time is between sunset and next sunrise, it's night
                    if next_setting < next_rising:
                        # Currently day - night is after next_setting
                        return check_time >= next_setting
                    else:
                        # Currently night - day is after next_rising
                        return check_time < next_rising
        except (ValueError, AttributeError) as err:
            _LOGGER.debug(f"Could not parse sun times, using fallback: {err}")

        # Fallback: Night is between 19:00 and 07:00
        hour = check_time.hour
        return hour >= 19 or hour < 7



class RainProbabilityCalculator:
    """Calculate rain probability based on pressure evolution and weather conditions."""

    # Zambretti letter code to base rain probability mapping
    # Based on forecast conditions: A-E (fine) = low, F-O (mixed) = medium, P-Z (poor) = high
    LETTER_RAIN_PROB = {
        'A': 5, 'B': 10, 'C': 15, 'D': 20, 'E': 25,  # Settled fine to fine
        'F': 30, 'G': 35, 'H': 40, 'I': 45, 'J': 50,  # Fine becoming less settled
        'K': 50, 'L': 55, 'M': 55, 'N': 60, 'O': 60,  # Showery, becoming unsettled
        'P': 65, 'Q': 70, 'R': 75, 'S': 80, 'T': 85,  # Rain at times
        'U': 85, 'V': 90, 'W': 90, 'X': 95, 'Y': 95, 'Z': 95  # Very wet, stormy
    }

    @staticmethod
    def calculate(
        current_pressure: float,
        future_pressure: float,
        pressure_trend: str,
        zambretti_code: int,
        zambretti_letter: str = 'A'
    ) -> int:
        """Calculate rain probability percentage.

        Based on:
        - Zambretti letter code (weather condition)
        - Pressure level and change
        - Pressure trend direction

        Args:
            current_pressure: Current pressure in hPa
            future_pressure: Forecasted pressure in hPa
            pressure_trend: Trend string
            zambretti_code: Zambretti forecast number (0-25)
            zambretti_letter: Zambretti letter code (A-Z)

        Returns:
            Rain probability 0-100%
        """
        # Base probability from Zambretti letter code
        base_prob = RainProbabilityCalculator.LETTER_RAIN_PROB.get(
            zambretti_letter,
            50  # Default middle value if letter unknown
        )

        # Adjust for absolute pressure level
        # Very low pressure = unstable, high rain likelihood
        if future_pressure < 990:
            base_prob = min(100, base_prob + 25)
        elif future_pressure < 1000:
            base_prob = min(100, base_prob + 15)
        elif future_pressure < 1010:
            base_prob = min(100, base_prob + 5)
        elif future_pressure > 1030:
            base_prob = max(0, base_prob - 15)  # Very high pressure = stable, dry
        elif future_pressure > 1025:
            base_prob = max(0, base_prob - 10)

        # Adjust for pressure change (trend)
        pressure_change = future_pressure - current_pressure

        # Rapidly falling pressure = incoming bad weather
        if pressure_change < -5:
            base_prob = min(100, base_prob + 20)
        elif pressure_change < -3:
            base_prob = min(100, base_prob + 15)
        elif pressure_change < -1:
            base_prob = min(100, base_prob + 5)
        # Rapidly rising pressure = improving weather
        elif pressure_change > 5:
            base_prob = max(0, base_prob - 20)
        elif pressure_change > 3:
            base_prob = max(0, base_prob - 15)
        elif pressure_change > 1:
            base_prob = max(0, base_prob - 5)

        # Clamp to 0-100
        return max(0, min(100, base_prob))


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
        latitude: float = 50.0
    ):
        """Initialize hourly forecast generator.

        Args:
            hass: Home Assistant instance
            pressure_model: Pressure forecasting model
            temperature_model: Temperature forecasting model
            zambretti: Zambretti forecaster
            wind_direction: Current wind direction in degrees
            wind_speed: Current wind speed in m/s
            latitude: Location latitude
        """
        self.hass = hass
        self.pressure_model = pressure_model
        self.temperature_model = temperature_model
        self.zambretti = zambretti
        self.wind_direction = wind_direction
        self.wind_speed = wind_speed
        self.latitude = latitude

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
        forecasts = []
        now = datetime.now(timezone.utc)
        rain_calc = RainProbabilityCalculator()

        for hour_offset in range(0, hours_count + 1, interval_hours):
            future_time = now + timedelta(hours=hour_offset)

            # Predict atmospheric conditions
            future_pressure = self.pressure_model.predict(hour_offset)
            future_temp = self.temperature_model.predict(hour_offset)
            pressure_trend = self.pressure_model.get_trend(hour_offset)

            # Calculate pressure change for Zambretti
            pressure_change = future_pressure - self.pressure_model.current_pressure

            # Get Zambretti forecast for this hour
            zambretti_result = self.zambretti.forecast_hour(
                pressure=future_pressure,
                wind_direction=self.wind_direction,
                pressure_change=pressure_change,
                wind_speed=self.wind_speed
            )

            forecast_text, forecast_num, letter_code = zambretti_result

            # Determine weather condition
            condition = self.zambretti.get_condition(
                letter_code,
                future_time
            )

            # Calculate rain probability
            rain_prob = rain_calc.calculate(
                current_pressure=self.pressure_model.current_pressure,
                future_pressure=future_pressure,
                pressure_trend=pressure_trend,
                zambretti_code=forecast_num,
                zambretti_letter=letter_code
            )

            # Create forecast entry
            forecast: Forecast = {
                "datetime": future_time.isoformat(),
                "condition": condition,
                "temperature": round(future_temp, 1),
                "precipitation_probability": rain_prob,
            }

            forecasts.append(forecast)

        _LOGGER.debug(
            f"Generated {len(forecasts)} hourly forecasts "
            f"(interval: {interval_hours}h)"
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
        total_hours = days * 24
        hourly_forecasts = self.hourly_generator.generate(
            hours_count=total_hours,
            interval_hours=3  # 3-hour intervals for efficiency
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
                if datetime.fromisoformat(f["datetime"]).date() == day_start.date()
            ]

            if not day_hours:
                continue

            # Aggregate temperature (use noon or average)
            temps = [f["temperature"] for f in day_hours]
            daily_temp = round(sum(temps) / len(temps), 1)

            # Find most common condition (daytime hours only)
            daytime_hours = [
                f for f in day_hours
                if 7 <= datetime.fromisoformat(f["datetime"]).hour <= 19
            ]
            if daytime_hours:
                conditions = [f["condition"] for f in daytime_hours]
                # Get most frequent condition
                daily_condition = max(set(conditions), key=conditions.count)
            else:
                daily_condition = day_hours[len(day_hours) // 2]["condition"]

            # Average rain probability
            rain_probs = [
                f.get("precipitation_probability", 0)
                for f in day_hours
            ]
            daily_rain_prob = round(sum(rain_probs) / len(rain_probs))

            # Create daily forecast
            forecast: Forecast = {
                "datetime": day_time.isoformat(),
                "condition": daily_condition,
                "temperature": daily_temp,
                "precipitation_probability": daily_rain_prob,
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
        days: int = 3
    ) -> list[Forecast]:
        """Generate daily forecast.

        Args:
            hass: Home Assistant instance
            current_pressure: Current pressure in hPa
            current_temp: Current temperature in °C
            pressure_change_3h: 3-hour pressure change
            temp_change_1h: 1-hour temperature change
            wind_direction: Wind direction in degrees
            wind_speed: Wind speed in m/s
            latitude: Location latitude
            days: Number of days to forecast

        Returns:
            List of daily Forecast objects
        """
        # Create models
        pressure_model = PressureModel(current_pressure, pressure_change_3h)
        temp_model = TemperatureModel(current_temp, temp_change_1h)
        zambretti = ZambrettiForecaster(hass=hass, latitude=latitude)

        # Create generators
        hourly_gen = HourlyForecastGenerator(
            hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction,
            wind_speed,
            latitude
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
        hours: int = 24
    ) -> list[Forecast]:
        """Generate hourly forecast.

        Args:
            hass: Home Assistant instance
            current_pressure: Current pressure in hPa
            current_temp: Current temperature in °C
            pressure_change_3h: 3-hour pressure change
            temp_change_1h: 1-hour temperature change
            wind_direction: Wind direction in degrees
            wind_speed: Wind speed in m/s
            latitude: Location latitude
            hours: Number of hours to forecast

        Returns:
            List of hourly Forecast objects
        """
        # Create models
        pressure_model = PressureModel(current_pressure, pressure_change_3h)
        temp_model = TemperatureModel(current_temp, temp_change_1h)
        zambretti = ZambrettiForecaster(hass=hass, latitude=latitude)

        # Create generator
        hourly_gen = HourlyForecastGenerator(
            hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction,
            wind_speed,
            latitude
        )

        return hourly_gen.generate(hours_count=hours, interval_hours=1)

