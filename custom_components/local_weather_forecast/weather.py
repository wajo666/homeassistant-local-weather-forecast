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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .calculations import (
    calculate_apparent_temperature,
    calculate_dewpoint,
    get_comfort_level,
    get_fog_risk,
)
from .const import (
    CONF_ENABLE_WEATHER_ENTITY,
    CONF_HUMIDITY_SENSOR,
    CONF_PRESSURE_SENSOR,
    CONF_RAIN_RATE_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    DEFAULT_ENABLE_WEATHER_ENTITY,
    DOMAIN,
    ZAMBRETTI_TO_CONDITION,
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
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

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
            "sw_version": "3.0.3",
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

    def _is_night(self) -> bool:
        """Check if it's currently night time."""
        # Simple check: between 19:00 and 07:00
        current_hour = datetime.now().hour
        return current_hour >= 19 or current_hour < 7

    @property
    def forecast(self) -> list[Forecast] | None:
        """Return the forecast array."""
        # Get forecast from main sensor attributes
        main_sensor = self.hass.states.get("sensor.local_forecast")
        if not main_sensor or main_sensor.state in ("unknown", "unavailable"):
            return None

        attrs = main_sensor.attributes

        # Create a simple 1-day forecast based on Zambretti
        forecast_short = attrs.get("forecast_short_term", ["Unknown", 0])
        zambretti = attrs.get("forecast_zambretti", ["Unknown", 0, "A"])

        if len(zambretti) >= 3:
            letter_code = zambretti[2]
            condition = ZAMBRETTI_TO_CONDITION.get(letter_code, ATTR_CONDITION_PARTLYCLOUDY)
        else:
            condition = ATTR_CONDITION_PARTLYCLOUDY

        # Get temperature forecast
        temp_short_sensor = self.hass.states.get("sensor.local_forecast_temperature_short")
        temp_forecast = None
        if temp_short_sensor and temp_short_sensor.state not in ("unknown", "unavailable"):
            try:
                temp_forecast = float(temp_short_sensor.state)
            except (ValueError, TypeError):
                pass

        forecast_data: list[Forecast] = [
            {
                "datetime": datetime.now().replace(hour=12, minute=0, second=0, microsecond=0).isoformat(),
                "condition": condition,
                "temperature": temp_forecast,
                "native_temperature": temp_forecast,
                "templow": None,
                "native_templow": None,
                "precipitation": None,
                "native_precipitation": None,
            }
        ]

        return forecast_data

    @property
    def attribution(self) -> str:
        """Return the attribution."""
        return "Local Weather Forecast based on Zambretti and Negretti-Zambra algorithms"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        main_sensor = self.hass.states.get("sensor.local_forecast")
        if not main_sensor or main_sensor.state in ("unknown", "unavailable"):
            return {}

        attrs = main_sensor.attributes

        # Calculate additional comfort/risk indicators
        extra_attrs = {
            "forecast_short_term": attrs.get("forecast_short_term", ["Unknown", 0]),
            "forecast_zambretti": attrs.get("forecast_zambretti", ["Unknown", 0, "A"]),
            "forecast_negretti_zambra": attrs.get("forecast_neg_zam", ["Unknown", 0, "A"]),
            "pressure_trend": attrs.get("forecast_pressure_trend", ["Steady", 0]),
            "zambretti_number": attrs.get("zambretti_number"),
            "neg_zam_number": attrs.get("neg_zam_number"),
        }

        # Add comfort level based on feels like temperature
        feels_like = self.native_apparent_temperature
        if feels_like is not None:
            extra_attrs["comfort_level"] = get_comfort_level(feels_like)
            extra_attrs["feels_like"] = feels_like

        # Add fog risk based on dew point
        temp = self.native_temperature
        dewpoint = self.native_dew_point
        if temp is not None and dewpoint is not None:
            extra_attrs["dew_point"] = dewpoint
            extra_attrs["fog_risk"] = get_fog_risk(temp, dewpoint)
            extra_attrs["dewpoint_spread"] = round(temp - dewpoint, 1)

        return extra_attrs

