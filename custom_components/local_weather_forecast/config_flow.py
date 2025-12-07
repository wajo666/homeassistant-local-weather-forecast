"""Config flow for Local Weather Forecast integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector

from .const import (
    CONF_CLOUD_COVERAGE_SENSOR,
    CONF_DEWPOINT_SENSOR,
    CONF_ELEVATION,
    CONF_ENABLE_WEATHER_ENTITY,
    CONF_HUMIDITY_SENSOR,
    CONF_LANGUAGE,
    CONF_PRESSURE_SENSOR,
    CONF_PRESSURE_TYPE,
    CONF_RAIN_RATE_SENSOR,
    CONF_SOLAR_RADIATION_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_UV_INDEX_SENSOR,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    DEFAULT_ELEVATION,
    DEFAULT_ENABLE_WEATHER_ENTITY,
    DEFAULT_LANGUAGE,
    DEFAULT_PRESSURE_TYPE,
    DOMAIN,
    LANGUAGES,
    PRESSURE_TYPE_ABSOLUTE,
    PRESSURE_TYPE_RELATIVE,
)

_LOGGER = logging.getLogger(__name__)


class LocalWeatherForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Local Weather Forecast."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("Config flow user input: %s", user_input)

            # Validate required sensors exist
            pressure_sensor = user_input[CONF_PRESSURE_SENSOR]
            _LOGGER.debug("Validating required pressure sensor: %s", pressure_sensor)

            pressure_state = self.hass.states.get(pressure_sensor)
            if not pressure_state:
                _LOGGER.error("Pressure sensor not found: %s", pressure_sensor)
                errors[CONF_PRESSURE_SENSOR] = "sensor_not_found"
            else:
                _LOGGER.debug("Pressure sensor found: %s (state=%s, unit=%s)",
                            pressure_sensor,
                            pressure_state.state,
                            pressure_state.attributes.get("unit_of_measurement"))

            # Validate optional sensors if provided (with safe access)
            if temp_sensor := user_input.get(CONF_TEMPERATURE_SENSOR):
                try:
                    _LOGGER.debug("Validating optional temperature sensor: %s", temp_sensor)
                    temp_state = self.hass.states.get(temp_sensor)
                    if temp_sensor and not temp_state:
                        _LOGGER.error("Temperature sensor not found: %s", temp_sensor)
                        errors[CONF_TEMPERATURE_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Temperature sensor found: %s (state=%s, unit=%s)",
                                    temp_sensor,
                                    temp_state.state if temp_state else None,
                                    temp_state.attributes.get("unit_of_measurement") if temp_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating temperature sensor %s: %s", temp_sensor, e)
                    errors[CONF_TEMPERATURE_SENSOR] = "sensor_validation_error"

            if wind_dir_sensor := user_input.get(CONF_WIND_DIRECTION_SENSOR):
                try:
                    _LOGGER.debug("Validating optional wind direction sensor: %s", wind_dir_sensor)
                    wind_dir_state = self.hass.states.get(wind_dir_sensor)
                    if wind_dir_sensor and not wind_dir_state:
                        _LOGGER.error("Wind direction sensor not found: %s", wind_dir_sensor)
                        errors[CONF_WIND_DIRECTION_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Wind direction sensor found: %s (state=%s, unit=%s)",
                                    wind_dir_sensor,
                                    wind_dir_state.state if wind_dir_state else None,
                                    wind_dir_state.attributes.get("unit_of_measurement") if wind_dir_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating wind direction sensor %s: %s", wind_dir_sensor, e)
                    errors[CONF_WIND_DIRECTION_SENSOR] = "sensor_validation_error"

            if wind_speed_sensor := user_input.get(CONF_WIND_SPEED_SENSOR):
                try:
                    _LOGGER.debug("Validating optional wind speed sensor: %s", wind_speed_sensor)
                    wind_speed_state = self.hass.states.get(wind_speed_sensor)
                    if wind_speed_sensor and not wind_speed_state:
                        _LOGGER.error("Wind speed sensor not found: %s", wind_speed_sensor)
                        errors[CONF_WIND_SPEED_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Wind speed sensor found: %s (state=%s, unit=%s)",
                                    wind_speed_sensor,
                                    wind_speed_state.state if wind_speed_state else None,
                                    wind_speed_state.attributes.get("unit_of_measurement") if wind_speed_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating wind speed sensor %s: %s", wind_speed_sensor, e)
                    errors[CONF_WIND_SPEED_SENSOR] = "sensor_validation_error"

            # Validate elevation
            elevation = user_input.get(CONF_ELEVATION, DEFAULT_ELEVATION)
            _LOGGER.debug("Validating elevation: %s", elevation)
            if elevation < 0 or elevation > 9000:
                _LOGGER.error("Invalid elevation: %s (must be 0-9000m)", elevation)
                errors[CONF_ELEVATION] = "invalid_elevation"

            if not errors:
                # Create unique ID based on pressure sensor
                await self.async_set_unique_id(pressure_sensor)
                self._abort_if_unique_id_configured()

                # Clean up empty strings - convert to None for optional fields
                cleaned_input = user_input.copy()
                for key in [CONF_TEMPERATURE_SENSOR, CONF_WIND_DIRECTION_SENSOR, CONF_WIND_SPEED_SENSOR]:
                    # Convert empty strings to None, ensure key exists even if not provided
                    if key not in cleaned_input or not cleaned_input[key]:
                        old_value = cleaned_input.get(key)
                        cleaned_input[key] = None
                        if old_value:
                            _LOGGER.debug("Cleaned sensor config: %s: %s -> None", key, old_value)

                _LOGGER.info("Creating config entry with data: %s", cleaned_input)
                return self.async_create_entry(
                    title=f"Local Weather Forecast",
                    data=cleaned_input,
                )

        # Build schema with entity selectors
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_PRESSURE_SENSOR,
                    default=user_input.get(CONF_PRESSURE_SENSOR, "")
                    if user_input
                    else "",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=SENSOR_DOMAIN,
                        device_class=["atmospheric_pressure", "pressure"],
                    )
                ),
                vol.Optional(
                    CONF_TEMPERATURE_SENSOR,
                    description={"suggested_value": user_input.get(CONF_TEMPERATURE_SENSOR)}
                    if user_input and user_input.get(CONF_TEMPERATURE_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=SENSOR_DOMAIN,
                        device_class="temperature",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_WIND_DIRECTION_SENSOR,
                    description={"suggested_value": user_input.get(CONF_WIND_DIRECTION_SENSOR)}
                    if user_input and user_input.get(CONF_WIND_DIRECTION_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=SENSOR_DOMAIN,
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_WIND_SPEED_SENSOR,
                    description={"suggested_value": user_input.get(CONF_WIND_SPEED_SENSOR)}
                    if user_input and user_input.get(CONF_WIND_SPEED_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=SENSOR_DOMAIN,
                        device_class="wind_speed",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_ELEVATION,
                    default=user_input.get(CONF_ELEVATION, DEFAULT_ELEVATION)
                    if user_input
                    else DEFAULT_ELEVATION,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=9000,
                        step=1,
                        unit_of_measurement="m",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PRESSURE_TYPE,
                    default=user_input.get(CONF_PRESSURE_TYPE, DEFAULT_PRESSURE_TYPE)
                    if user_input
                    else DEFAULT_PRESSURE_TYPE,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=PRESSURE_TYPE_ABSOLUTE,
                                label="Absolute (QFE - Station Pressure)"
                            ),
                            selector.SelectOptionDict(
                                value=PRESSURE_TYPE_RELATIVE,
                                label="Relative (QNH - Sea Level Pressure)"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_LANGUAGE,
                    default=user_input.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
                    if user_input
                    else DEFAULT_LANGUAGE,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=k, label=v)
                            for k, v in LANGUAGES.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LocalWeatherForecastOptionsFlow:
        """Get the options flow for this handler."""
        return LocalWeatherForecastOptionsFlow()


class LocalWeatherForecastOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Local Weather Forecast."""


    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _LOGGER.debug("Options flow user input: %s", user_input)

            # Validate sensors if changed (with safe access to prevent HA crashes)
            if temp_sensor := user_input.get(CONF_TEMPERATURE_SENSOR):
                try:
                    _LOGGER.debug("Validating optional temperature sensor: %s", temp_sensor)
                    temp_state = self.hass.states.get(temp_sensor)
                    if temp_sensor and not temp_state:
                        _LOGGER.error("Temperature sensor not found: %s", temp_sensor)
                        errors[CONF_TEMPERATURE_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Temperature sensor found: %s (state=%s, unit=%s)",
                                    temp_sensor,
                                    temp_state.state if temp_state else None,
                                    temp_state.attributes.get("unit_of_measurement") if temp_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating temperature sensor %s: %s", temp_sensor, e)
                    errors[CONF_TEMPERATURE_SENSOR] = "sensor_validation_error"

            if wind_dir_sensor := user_input.get(CONF_WIND_DIRECTION_SENSOR):
                try:
                    _LOGGER.debug("Validating optional wind direction sensor: %s", wind_dir_sensor)
                    wind_dir_state = self.hass.states.get(wind_dir_sensor)
                    if wind_dir_sensor and not wind_dir_state:
                        _LOGGER.error("Wind direction sensor not found: %s", wind_dir_sensor)
                        errors[CONF_WIND_DIRECTION_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Wind direction sensor found: %s (state=%s, unit=%s)",
                                    wind_dir_sensor,
                                    wind_dir_state.state if wind_dir_state else None,
                                    wind_dir_state.attributes.get("unit_of_measurement") if wind_dir_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating wind direction sensor %s: %s", wind_dir_sensor, e)
                    errors[CONF_WIND_DIRECTION_SENSOR] = "sensor_validation_error"

            if wind_speed_sensor := user_input.get(CONF_WIND_SPEED_SENSOR):
                try:
                    _LOGGER.debug("Validating optional wind speed sensor: %s", wind_speed_sensor)
                    wind_speed_state = self.hass.states.get(wind_speed_sensor)
                    if wind_speed_sensor and not wind_speed_state:
                        _LOGGER.error("Wind speed sensor not found: %s", wind_speed_sensor)
                        errors[CONF_WIND_SPEED_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Wind speed sensor found: %s (state=%s, unit=%s)",
                                    wind_speed_sensor,
                                    wind_speed_state.state if wind_speed_state else None,
                                    wind_speed_state.attributes.get("unit_of_measurement") if wind_speed_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating wind speed sensor %s: %s", wind_speed_sensor, e)
                    errors[CONF_WIND_SPEED_SENSOR] = "sensor_validation_error"

            # Validate new optional sensors (with safe access)
            if humidity_sensor := user_input.get(CONF_HUMIDITY_SENSOR):
                try:
                    _LOGGER.debug("Validating optional humidity sensor: %s", humidity_sensor)
                    humidity_state = self.hass.states.get(humidity_sensor)
                    if humidity_sensor and not humidity_state:
                        _LOGGER.error("Humidity sensor not found: %s", humidity_sensor)
                        errors[CONF_HUMIDITY_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Humidity sensor found: %s (state=%s, unit=%s)",
                                    humidity_sensor,
                                    humidity_state.state if humidity_state else None,
                                    humidity_state.attributes.get("unit_of_measurement") if humidity_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating humidity sensor %s: %s", humidity_sensor, e)
                    errors[CONF_HUMIDITY_SENSOR] = "sensor_validation_error"

            if wind_gust_sensor := user_input.get(CONF_WIND_GUST_SENSOR):
                try:
                    _LOGGER.debug("Validating optional wind gust sensor: %s", wind_gust_sensor)
                    wind_gust_state = self.hass.states.get(wind_gust_sensor)
                    if wind_gust_sensor and not wind_gust_state:
                        _LOGGER.error("Wind gust sensor not found: %s", wind_gust_sensor)
                        errors[CONF_WIND_GUST_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Wind gust sensor found: %s (state=%s, unit=%s)",
                                    wind_gust_sensor,
                                    wind_gust_state.state if wind_gust_state else None,
                                    wind_gust_state.attributes.get("unit_of_measurement") if wind_gust_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating wind gust sensor %s: %s", wind_gust_sensor, e)
                    errors[CONF_WIND_GUST_SENSOR] = "sensor_validation_error"

            if rain_rate_sensor := user_input.get(CONF_RAIN_RATE_SENSOR):
                try:
                    _LOGGER.debug("Validating optional rain rate sensor: %s", rain_rate_sensor)
                    rain_rate_state = self.hass.states.get(rain_rate_sensor)
                    if rain_rate_sensor and not rain_rate_state:
                        _LOGGER.error("Rain rate sensor not found: %s", rain_rate_sensor)
                        errors[CONF_RAIN_RATE_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Rain rate sensor found: %s (state=%s, unit=%s)",
                                    rain_rate_sensor,
                                    rain_rate_state.state if rain_rate_state else None,
                                    rain_rate_state.attributes.get("unit_of_measurement") if rain_rate_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating rain rate sensor %s: %s", rain_rate_sensor, e)
                    errors[CONF_RAIN_RATE_SENSOR] = "sensor_validation_error"

            # Validate future sensors (prepared for v3.2.0+) with safe access
            if dewpoint_sensor := user_input.get(CONF_DEWPOINT_SENSOR):
                try:
                    _LOGGER.debug("Validating optional dewpoint sensor: %s", dewpoint_sensor)
                    dewpoint_state = self.hass.states.get(dewpoint_sensor)
                    if dewpoint_sensor and not dewpoint_state:
                        _LOGGER.error("Dewpoint sensor not found: %s", dewpoint_sensor)
                        errors[CONF_DEWPOINT_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Dewpoint sensor found: %s (state=%s, unit=%s)",
                                    dewpoint_sensor,
                                    dewpoint_state.state if dewpoint_state else None,
                                    dewpoint_state.attributes.get("unit_of_measurement") if dewpoint_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating dewpoint sensor %s: %s", dewpoint_sensor, e)
                    errors[CONF_DEWPOINT_SENSOR] = "sensor_validation_error"


            if solar_radiation_sensor := user_input.get(CONF_SOLAR_RADIATION_SENSOR):
                try:
                    _LOGGER.debug("Validating optional solar radiation sensor: %s", solar_radiation_sensor)
                    solar_radiation_state = self.hass.states.get(solar_radiation_sensor)
                    if solar_radiation_sensor and not solar_radiation_state:
                        _LOGGER.error("Solar radiation sensor not found: %s", solar_radiation_sensor)
                        errors[CONF_SOLAR_RADIATION_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Solar radiation sensor found: %s (state=%s, unit=%s)",
                                    solar_radiation_sensor,
                                    solar_radiation_state.state if solar_radiation_state else None,
                                    solar_radiation_state.attributes.get("unit_of_measurement") if solar_radiation_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating solar radiation sensor %s: %s", solar_radiation_sensor, e)
                    errors[CONF_SOLAR_RADIATION_SENSOR] = "sensor_validation_error"

            if uv_index_sensor := user_input.get(CONF_UV_INDEX_SENSOR):
                try:
                    _LOGGER.debug("Validating optional UV index sensor: %s", uv_index_sensor)
                    uv_index_state = self.hass.states.get(uv_index_sensor)
                    if uv_index_sensor and not uv_index_state:
                        _LOGGER.error("UV index sensor not found: %s", uv_index_sensor)
                        errors[CONF_UV_INDEX_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("UV index sensor found: %s (state=%s, unit=%s)",
                                    uv_index_sensor,
                                    uv_index_state.state if uv_index_state else None,
                                    uv_index_state.attributes.get("unit_of_measurement") if uv_index_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating UV index sensor %s: %s", uv_index_sensor, e)
                    errors[CONF_UV_INDEX_SENSOR] = "sensor_validation_error"

            if cloud_coverage_sensor := user_input.get(CONF_CLOUD_COVERAGE_SENSOR):
                try:
                    _LOGGER.debug("Validating optional cloud coverage sensor: %s", cloud_coverage_sensor)
                    cloud_coverage_state = self.hass.states.get(cloud_coverage_sensor)
                    if cloud_coverage_sensor and not cloud_coverage_state:
                        _LOGGER.error("Cloud coverage sensor not found: %s", cloud_coverage_sensor)
                        errors[CONF_CLOUD_COVERAGE_SENSOR] = "sensor_not_found"
                    else:
                        _LOGGER.debug("Cloud coverage sensor found: %s (state=%s, unit=%s)",
                                    cloud_coverage_sensor,
                                    cloud_coverage_state.state if cloud_coverage_state else None,
                                    cloud_coverage_state.attributes.get("unit_of_measurement") if cloud_coverage_state else None)
                except Exception as e:
                    _LOGGER.error("Error validating cloud coverage sensor %s: %s", cloud_coverage_sensor, e)
                    errors[CONF_CLOUD_COVERAGE_SENSOR] = "sensor_validation_error"

            elevation = user_input.get(CONF_ELEVATION, DEFAULT_ELEVATION)
            _LOGGER.debug("Validating elevation: %s", elevation)
            if elevation < 0 or elevation > 9000:
                _LOGGER.error("Invalid elevation: %s (must be 0-9000m)", elevation)
                errors[CONF_ELEVATION] = "invalid_elevation"

            if not errors:
                # Clean up empty strings - convert to None for optional fields
                cleaned_input = user_input.copy()
                optional_sensors = [
                    CONF_TEMPERATURE_SENSOR,
                    CONF_WIND_DIRECTION_SENSOR,
                    CONF_WIND_SPEED_SENSOR,
                    CONF_HUMIDITY_SENSOR,
                    CONF_WIND_GUST_SENSOR,
                    CONF_RAIN_RATE_SENSOR,
                    CONF_DEWPOINT_SENSOR,
                    CONF_SOLAR_RADIATION_SENSOR,
                    CONF_UV_INDEX_SENSOR,
                    CONF_CLOUD_COVERAGE_SENSOR,
                ]
                for key in optional_sensors:
                    # Convert empty strings to None, ensure key exists even if not provided
                    if key not in cleaned_input or not cleaned_input[key]:
                        old_value = cleaned_input.get(key)
                        cleaned_input[key] = None
                        if old_value:
                            _LOGGER.debug("Cleaned sensor config: %s: %s -> None", key, old_value)

                try:
                    _LOGGER.info("Updating config entry with data: %s", cleaned_input)
                    # Update config entry with new data
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={**self.config_entry.data, **cleaned_input},
                    )
                    return self.async_create_entry(title="", data={})
                except Exception as e:
                    _LOGGER.error("Failed to update config entry: %s", e)
                    errors["base"] = "update_failed"
                    # Don't return here, let the form be shown again with error

        current_config = self.config_entry.data

        options_schema = vol.Schema(
            {
                # Core sensors
                vol.Optional(
                    CONF_TEMPERATURE_SENSOR,
                    description={"suggested_value": current_config.get(CONF_TEMPERATURE_SENSOR)}
                    if current_config.get(CONF_TEMPERATURE_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="temperature",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_WIND_DIRECTION_SENSOR,
                    description={"suggested_value": current_config.get(CONF_WIND_DIRECTION_SENSOR)}
                    if current_config.get(CONF_WIND_DIRECTION_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_WIND_SPEED_SENSOR,
                    description={"suggested_value": current_config.get(CONF_WIND_SPEED_SENSOR)}
                    if current_config.get(CONF_WIND_SPEED_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="wind_speed",
                        multiple=False,
                    )
                ),
                # Enhanced sensors for better forecast accuracy
                vol.Optional(
                    CONF_HUMIDITY_SENSOR,
                    description={"suggested_value": current_config.get(CONF_HUMIDITY_SENSOR)}
                    if current_config.get(CONF_HUMIDITY_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="humidity",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_WIND_GUST_SENSOR,
                    description={"suggested_value": current_config.get(CONF_WIND_GUST_SENSOR)}
                    if current_config.get(CONF_WIND_GUST_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="wind_speed",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_RAIN_RATE_SENSOR,
                    description={"suggested_value": current_config.get(CONF_RAIN_RATE_SENSOR)}
                    if current_config.get(CONF_RAIN_RATE_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class=["precipitation_intensity", "precipitation"],
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_DEWPOINT_SENSOR,
                    description={"suggested_value": current_config.get(CONF_DEWPOINT_SENSOR)}
                    if current_config.get(CONF_DEWPOINT_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="temperature",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_SOLAR_RADIATION_SENSOR,
                    description={"suggested_value": current_config.get(CONF_SOLAR_RADIATION_SENSOR)}
                    if current_config.get(CONF_SOLAR_RADIATION_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="irradiance",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_UV_INDEX_SENSOR,
                    description={"suggested_value": current_config.get(CONF_UV_INDEX_SENSOR)}
                    if current_config.get(CONF_UV_INDEX_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        multiple=False,
                    )
                ),
                vol.Optional(
                    CONF_CLOUD_COVERAGE_SENSOR,
                    description={"suggested_value": current_config.get(CONF_CLOUD_COVERAGE_SENSOR)}
                    if current_config.get(CONF_CLOUD_COVERAGE_SENSOR)
                    else None,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        multiple=False,
                    )
                ),
                # Configuration options
                vol.Optional(
                    CONF_ELEVATION,
                    default=current_config.get(CONF_ELEVATION, DEFAULT_ELEVATION),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=9000,
                        step=1,
                        unit_of_measurement="m",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PRESSURE_TYPE,
                    default=current_config.get(CONF_PRESSURE_TYPE, DEFAULT_PRESSURE_TYPE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=PRESSURE_TYPE_ABSOLUTE,
                                label="Absolute (QFE - Station Pressure)"
                            ),
                            selector.SelectOptionDict(
                                value=PRESSURE_TYPE_RELATIVE,
                                label="Relative (QNH - Sea Level Pressure)"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_LANGUAGE,
                    default=current_config.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=k, label=v)
                            for k, v in LANGUAGES.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                # Feature toggles
                vol.Optional(
                    CONF_ENABLE_WEATHER_ENTITY,
                    default=current_config.get(CONF_ENABLE_WEATHER_ENTITY, DEFAULT_ENABLE_WEATHER_ENTITY),
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )

