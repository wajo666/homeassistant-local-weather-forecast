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
    CONF_ELEVATION,
    CONF_LANGUAGE,
    CONF_PRESSURE_TYPE,
    CONF_PRESSURE_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    DEFAULT_ELEVATION,
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
            # Validate required sensors exist
            pressure_sensor = user_input[CONF_PRESSURE_SENSOR]

            if not self.hass.states.get(pressure_sensor):
                errors[CONF_PRESSURE_SENSOR] = "sensor_not_found"

            # Validate optional sensors if provided
            if temp_sensor := user_input.get(CONF_TEMPERATURE_SENSOR):
                if temp_sensor and not self.hass.states.get(temp_sensor):
                    errors[CONF_TEMPERATURE_SENSOR] = "sensor_not_found"

            if wind_dir_sensor := user_input.get(CONF_WIND_DIRECTION_SENSOR):
                if wind_dir_sensor and not self.hass.states.get(wind_dir_sensor):
                    errors[CONF_WIND_DIRECTION_SENSOR] = "sensor_not_found"

            if wind_speed_sensor := user_input.get(CONF_WIND_SPEED_SENSOR):
                if wind_speed_sensor and not self.hass.states.get(wind_speed_sensor):
                    errors[CONF_WIND_SPEED_SENSOR] = "sensor_not_found"

            # Validate elevation
            elevation = user_input.get(CONF_ELEVATION, DEFAULT_ELEVATION)
            if elevation < 0 or elevation > 9000:
                errors[CONF_ELEVATION] = "invalid_elevation"

            if not errors:
                # Create unique ID based on pressure sensor
                await self.async_set_unique_id(pressure_sensor)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Local Weather Forecast",
                    data=user_input,
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
                        device_class="atmospheric_pressure",
                    )
                ),
                vol.Optional(
                    CONF_TEMPERATURE_SENSOR,
                    default=user_input.get(CONF_TEMPERATURE_SENSOR, "")
                    if user_input
                    else "",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=SENSOR_DOMAIN,
                        device_class="temperature",
                    )
                ),
                vol.Optional(
                    CONF_WIND_DIRECTION_SENSOR,
                    default=user_input.get(CONF_WIND_DIRECTION_SENSOR, "")
                    if user_input
                    else "",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=SENSOR_DOMAIN)
                ),
                vol.Optional(
                    CONF_WIND_SPEED_SENSOR,
                    default=user_input.get(CONF_WIND_SPEED_SENSOR, "")
                    if user_input
                    else "",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=SENSOR_DOMAIN,
                        device_class="wind_speed",
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
        return LocalWeatherForecastOptionsFlow(config_entry)


class LocalWeatherForecastOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Local Weather Forecast."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate sensors if changed
            if temp_sensor := user_input.get(CONF_TEMPERATURE_SENSOR):
                if temp_sensor and not self.hass.states.get(temp_sensor):
                    errors[CONF_TEMPERATURE_SENSOR] = "sensor_not_found"

            if wind_dir_sensor := user_input.get(CONF_WIND_DIRECTION_SENSOR):
                if wind_dir_sensor and not self.hass.states.get(wind_dir_sensor):
                    errors[CONF_WIND_DIRECTION_SENSOR] = "sensor_not_found"

            if wind_speed_sensor := user_input.get(CONF_WIND_SPEED_SENSOR):
                if wind_speed_sensor and not self.hass.states.get(wind_speed_sensor):
                    errors[CONF_WIND_SPEED_SENSOR] = "sensor_not_found"

            elevation = user_input.get(CONF_ELEVATION, DEFAULT_ELEVATION)
            if elevation < 0 or elevation > 9000:
                errors[CONF_ELEVATION] = "invalid_elevation"

            if not errors:
                # Update config entry with new data
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **user_input},
                )
                return self.async_create_entry(title="", data={})

        current_config = self.config_entry.data

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_TEMPERATURE_SENSOR,
                    default=current_config.get(CONF_TEMPERATURE_SENSOR, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="temperature",
                    )
                ),
                vol.Optional(
                    CONF_WIND_DIRECTION_SENSOR,
                    default=current_config.get(CONF_WIND_DIRECTION_SENSOR, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_WIND_SPEED_SENSOR,
                    default=current_config.get(CONF_WIND_SPEED_SENSOR, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="wind_speed",
                    )
                ),
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
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )

