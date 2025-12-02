"""Weather entity for Local Weather Forecast integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .calculations import (
    calculate_apparent_temperature,
    calculate_dewpoint,
    get_comfort_level,
    get_fog_risk,
)
from .const import (
    CONF_CLOUD_COVERAGE_SENSOR,
    CONF_DEWPOINT_SENSOR,
    CONF_ENABLE_WEATHER_ENTITY,
    CONF_HUMIDITY_SENSOR,
    CONF_LATITUDE,
    CONF_PRESSURE_SENSOR,
    CONF_SOLAR_RADIATION_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    DEFAULT_ENABLE_WEATHER_ENTITY,
    DEFAULT_LATITUDE,
    DOMAIN,
    ZAMBRETTI_TO_CONDITION,
)
from .forecast_calculator import (
    DailyForecastGenerator,
    HourlyForecastGenerator,
    PressureModel,
    TemperatureModel,
    ZambrettiForecaster,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Local Weather Forecast weather entity."""
    # Check if weather entity is enabled in options (or data for backwards compatibility)
    enabled = entry.options.get(
        CONF_ENABLE_WEATHER_ENTITY,
        entry.data.get(CONF_ENABLE_WEATHER_ENTITY, DEFAULT_ENABLE_WEATHER_ENTITY)
    )

    if not enabled:
        _LOGGER.debug("Weather entity is disabled in configuration")
        return

    _LOGGER.debug("Setting up Local Weather Forecast weather entity")

    async_add_entities([LocalWeatherForecastWeather(entry)], True)


class LocalWeatherForecastWeather(WeatherEntity):
    """Representation of Local Weather Forecast weather entity."""

    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the weather entity."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_weather"
        self._attr_name = "Weather"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Local Weather Forecast",
            "manufacturer": "Local Weather Forecast",
            "model": "Zambretti/Negretti-Zambra",
            "sw_version": "3.1.0",
        }

    def _get_config(self, key: str) -> Any:
        """Get configuration value from options or data."""
        return self._entry.options.get(key, self._entry.data.get(key))

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        temp_sensor = self._get_config(CONF_TEMPERATURE_SENSOR)
        if temp_sensor:
            state = self.hass.states.get(temp_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure."""
        pressure_sensor = self._get_config(CONF_PRESSURE_SENSOR)
        if pressure_sensor:
            state = self.hass.states.get(pressure_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def humidity(self) -> float | None:
        """Return the humidity."""
        humidity_sensor = self._get_config(CONF_HUMIDITY_SENSOR)
        if humidity_sensor:
            state = self.hass.states.get(humidity_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        wind_speed_sensor = self._get_config(CONF_WIND_SPEED_SENSOR)
        if wind_speed_sensor:
            state = self.hass.states.get(wind_speed_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def wind_bearing(self) -> float | str | None:
        """Return the wind bearing."""
        wind_direction_sensor = self._get_config(CONF_WIND_DIRECTION_SENSOR)
        if wind_direction_sensor:
            state = self.hass.states.get(wind_direction_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def native_wind_gust_speed(self) -> float | None:
        """Return the wind gust speed."""
        wind_gust_sensor = self._get_config(CONF_WIND_GUST_SENSOR)
        if wind_gust_sensor:
            state = self.hass.states.get(wind_gust_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def native_dew_point(self) -> float | None:
        """Return the dew point temperature."""
        # Check if user provided a dewpoint sensor
        dewpoint_sensor = self._get_config(CONF_DEWPOINT_SENSOR)
        if dewpoint_sensor:
            state = self.hass.states.get(dewpoint_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass

        # Calculate from temperature and humidity if available
        temp = self.native_temperature
        humidity = self.humidity
        if temp is not None and humidity is not None:
            return calculate_dewpoint(temp, humidity)

        return None

    @property
    def native_apparent_temperature(self) -> float | None:
        """Return the apparent temperature (feels like).

        Uses all available sensors dynamically:
        - Temperature (required)
        - Humidity (optional)
        - Wind speed (optional)
        - Solar radiation (optional)
        - Cloud cover (optional)
        """
        temp = self.native_temperature
        if temp is None:
            return None

        # Get humidity (optional)
        humidity = self.humidity

        # Get wind speed (optional, convert m/s to km/h)
        wind_speed = self.native_wind_speed
        wind_speed_kmh = (wind_speed * 3.6) if wind_speed else None

        # Get solar radiation (optional)
        solar_radiation = None
        solar_sensor_id = self._get_config(CONF_SOLAR_RADIATION_SENSOR)
        if solar_sensor_id:
            solar_state = self.hass.states.get(solar_sensor_id)
            if solar_state and solar_state.state not in ("unknown", "unavailable"):
                try:
                    solar_radiation = float(solar_state.state)
                except (ValueError, TypeError):
                    pass

        # Get cloud coverage (optional)
        cloud_cover = None
        cloud_sensor_id = self._get_config(CONF_CLOUD_COVERAGE_SENSOR)
        if cloud_sensor_id:
            cloud_state = self.hass.states.get(cloud_sensor_id)
            if cloud_state and cloud_state.state not in ("unknown", "unavailable"):
                try:
                    cloud_cover = float(cloud_state.state)
                except (ValueError, TypeError):
                    pass

        # Calculate with all available sensors
        return calculate_apparent_temperature(
            temp,
            humidity,
            wind_speed_kmh,
            solar_radiation,
            cloud_cover
        )

    @property
    def condition(self) -> str | None:
        """Return the current condition based on Zambretti forecast."""
        # Get Zambretti detail sensor
        zambretti_sensor = self.hass.states.get("sensor.local_forecast_zambretti_detail")
        if zambretti_sensor and zambretti_sensor.state not in ("unknown", "unavailable"):
            attrs = zambretti_sensor.attributes
            letter_code = attrs.get("letter_code", "A")

            # Map Zambretti letter to HA condition
            condition = ZAMBRETTI_TO_CONDITION.get(letter_code, ATTR_CONDITION_PARTLYCLOUDY)

            # Check if it's night time (between sunset and sunrise)
            if condition == ATTR_CONDITION_SUNNY and self._is_night():
                return ATTR_CONDITION_CLEAR_NIGHT

            return condition

        # Fallback based on pressure
        pressure = self.native_pressure
        if pressure:
            if pressure < 1000:
                return ATTR_CONDITION_RAINY
            elif pressure < 1013:
                return ATTR_CONDITION_CLOUDY
            elif pressure < 1020:
                return ATTR_CONDITION_PARTLYCLOUDY
            else:
                if self._is_night():
                    return ATTR_CONDITION_CLEAR_NIGHT
                return ATTR_CONDITION_SUNNY

        return ATTR_CONDITION_PARTLYCLOUDY

    def _is_night(self, check_time: datetime | None = None) -> bool:
        """Check if it's night time based on sun position.

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if sun is below horizon (night time)
        """
        # Get sun entity state
        sun_entity = self.hass.states.get("sun.sun")

        if check_time is None:
            # Check current time
            if sun_entity:
                # sun.sun state is "above_horizon" or "below_horizon"
                return sun_entity.state == "below_horizon"
            else:
                # Fallback to simple time check if sun entity not available
                current_hour = datetime.now().hour
                return current_hour >= 19 or current_hour < 7
        else:
            # For future times, compare with sunrise/sunset
            if sun_entity:
                next_sunrise = sun_entity.attributes.get("next_rising")
                next_sunset = sun_entity.attributes.get("next_setting")

                if next_sunrise and next_sunset:
                    from datetime import timezone

                    try:
                        # Parse ISO format datetime strings
                        sunrise_dt = datetime.fromisoformat(next_sunrise.replace('Z', '+00:00'))
                        sunset_dt = datetime.fromisoformat(next_sunset.replace('Z', '+00:00'))

                        # Make check_time timezone aware if needed
                        if check_time.tzinfo is None:
                            check_time = check_time.replace(tzinfo=timezone.utc)

                        # If check time is before next sunrise, it's night
                        # If check time is after next sunset, it's night
                        # Otherwise it's day
                        if sunrise_dt < sunset_dt:
                            # Normal day: night is before sunrise or after sunset
                            return check_time < sunrise_dt or check_time > sunset_dt
                        else:
                            # Crossing midnight
                            return sunset_dt < check_time < sunrise_dt
                    except (ValueError, AttributeError):
                        pass

            # Fallback to simple time check
            return check_time.hour >= 19 or check_time.hour < 7

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}

        # Add forecast short term from main sensor
        main_sensor = self.hass.states.get("sensor.local_forecast")
        if main_sensor and main_sensor.state not in ("unknown", "unavailable"):
            main_attrs = main_sensor.attributes
            attrs["forecast_short_term"] = main_attrs.get("forecast_short_term", "Unknown")

            # Add Zambretti and Negretti-Zambra forecasts
            zambretti = main_attrs.get("forecast_zambretti", ["Unknown", 0, "A"])
            attrs["forecast_zambretti"] = f"{zambretti[0]}, {zambretti[1]}, {zambretti[2]}"

            negretti = main_attrs.get("forecast_neg_zam", ["Unknown", 0, "A"])
            attrs["forecast_negretti_zambra"] = f"{negretti[0]}, {negretti[1]}, {negretti[2]}"

            # Add pressure trend
            pressure_trend = main_attrs.get("forecast_pressure_trend", ["Steady", 2])
            attrs["pressure_trend"] = f"{pressure_trend[0]}, {pressure_trend[1]}"

            # Add Zambretti numbers for reference
            attrs["zambretti_number"] = zambretti[1] if len(zambretti) > 1 else None
            attrs["neg_zam_number"] = negretti[1] if len(negretti) > 1 else None

        # Add comfort level based on apparent temperature
        apparent_temp = self.native_apparent_temperature
        if apparent_temp is not None:
            attrs["comfort_level"] = get_comfort_level(apparent_temp)
            attrs["feels_like"] = round(apparent_temp, 1)

        # Add fog risk if we have dewpoint
        temp = self.native_temperature
        dewpoint = self.native_dew_point
        if temp is not None and dewpoint is not None:
            spread = temp - dewpoint
            attrs["fog_risk"] = get_fog_risk(spread, dewpoint)
            attrs["dewpoint_spread"] = round(spread, 1)

        attrs["attribution"] = "Local Weather Forecast based on Zambretti and Negretti-Zambra algorithms"

        return attrs

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast using advanced models."""
        _LOGGER.debug("async_forecast_daily called - generating with advanced models")

        def generate_forecast():
            return self._generate_advanced_daily_forecast(3)

        result = await self.hass.async_add_executor_job(generate_forecast)
        _LOGGER.debug(f"async_forecast_daily returning {len(result) if result else 0} days")
        return result

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast using advanced models."""
        _LOGGER.debug("async_forecast_hourly called - generating with advanced models")

        def generate_forecast():
            return self._generate_advanced_hourly_forecast(24)

        result = await self.hass.async_add_executor_job(generate_forecast)
        _LOGGER.debug(f"async_forecast_hourly returning {len(result) if result else 0} hours")
        return result

    def _generate_advanced_daily_forecast(self, days: int = 3) -> list[Forecast] | None:
        """Generate daily forecast using advanced models.

        Args:
            days: Number of days to forecast

        Returns:
            List of daily Forecast objects
        """
        try:
            # Get current sensor data
            pressure = self.native_pressure
            temperature = self.native_temperature
            wind_dir = self.wind_bearing or 0
            wind_speed = self.native_wind_speed or 0.0

            if pressure is None or temperature is None:
                _LOGGER.warning("Missing pressure or temperature for advanced forecast")
                return None

            # Get pressure and temperature changes
            pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
            temp_change_sensor = self.hass.states.get("sensor.local_forecast_temperaturechange")

            pressure_change_3h = 0.0
            if pressure_change_sensor and pressure_change_sensor.state not in ("unknown", "unavailable"):
                try:
                    pressure_change_3h = float(pressure_change_sensor.state)
                except (ValueError, TypeError):
                    pass

            temp_change_1h = 0.0
            if temp_change_sensor and temp_change_sensor.state not in ("unknown", "unavailable"):
                try:
                    temp_change_1h = float(temp_change_sensor.state)
                except (ValueError, TypeError):
                    pass

            # Create models
            pressure_model = PressureModel(pressure, pressure_change_3h)
            temp_model = TemperatureModel(temperature, temp_change_1h)

            # Create Zambretti forecaster with hass for sun entity access
            latitude = self._get_config(CONF_LATITUDE) or DEFAULT_LATITUDE
            zambretti = ZambrettiForecaster(hass=self.hass, latitude=latitude)

            # Create generators
            hourly_gen = HourlyForecastGenerator(
                self.hass,
                pressure_model,
                temp_model,
                zambretti,
                wind_direction=int(wind_dir),
                wind_speed=float(wind_speed),
                latitude=latitude
            )

            daily_gen = DailyForecastGenerator(hourly_gen)

            # Generate forecast
            forecasts = daily_gen.generate(days)

            _LOGGER.debug(
                f"Generated {len(forecasts)} daily forecasts: "
                f"P={pressure}hPa, T={temperature}°C, ΔP={pressure_change_3h}hPa"
            )

            return forecasts

        except Exception as e:
            _LOGGER.error(f"Error generating advanced daily forecast: {e}", exc_info=True)
            return None

    def _generate_advanced_hourly_forecast(self, hours: int = 24) -> list[Forecast] | None:
        """Generate hourly forecast using advanced models.

        Args:
            hours: Number of hours to forecast

        Returns:
            List of hourly Forecast objects
        """
        try:
            # Get current sensor data
            pressure = self.native_pressure
            temperature = self.native_temperature
            wind_dir = self.wind_bearing or 0
            wind_speed = self.native_wind_speed or 0.0

            if pressure is None or temperature is None:
                _LOGGER.warning("Missing pressure or temperature for advanced forecast")
                return None

            # Get pressure and temperature changes
            pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
            temp_change_sensor = self.hass.states.get("sensor.local_forecast_temperaturechange")

            pressure_change_3h = 0.0
            if pressure_change_sensor and pressure_change_sensor.state not in ("unknown", "unavailable"):
                try:
                    pressure_change_3h = float(pressure_change_sensor.state)
                except (ValueError, TypeError):
                    pass

            temp_change_1h = 0.0
            if temp_change_sensor and temp_change_sensor.state not in ("unknown", "unavailable"):
                try:
                    temp_change_1h = float(temp_change_sensor.state)
                except (ValueError, TypeError):
                    pass

            # Create models
            pressure_model = PressureModel(pressure, pressure_change_3h)
            temp_model = TemperatureModel(temperature, temp_change_1h)

            # Create Zambretti forecaster with hass for sun entity access
            latitude = self._get_config(CONF_LATITUDE) or DEFAULT_LATITUDE
            zambretti = ZambrettiForecaster(hass=self.hass, latitude=latitude)

            # Create generator
            hourly_gen = HourlyForecastGenerator(
                self.hass,
                pressure_model,
                temp_model,
                zambretti,
                wind_direction=int(wind_dir),
                wind_speed=float(wind_speed),
                latitude=latitude
            )

            # Generate forecast (1-hour intervals)
            forecasts = hourly_gen.generate(
                hours_count=hours,
                interval_hours=1
            )

            _LOGGER.debug(
                f"Generated {len(forecasts)} hourly forecasts: "
                f"P={pressure}hPa, T={temperature}°C, ΔP={pressure_change_3h}hPa"
            )

            return forecasts

        except Exception as e:
            _LOGGER.error(f"Error generating advanced hourly forecast: {e}", exc_info=True)
            return None

