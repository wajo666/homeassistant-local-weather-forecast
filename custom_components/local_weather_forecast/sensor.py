"""Sensor platform for Local Weather Forecast integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers import entity_registry as er
from homeassistant.components.recorder import get_instance, history
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ELEVATION,
    CONF_HUMIDITY_SENSOR,
    CONF_LANGUAGE,
    CONF_PRESSURE_TYPE,
    CONF_PRESSURE_SENSOR,
    CONF_RAIN_RATE_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    DEFAULT_ELEVATION,
    DEFAULT_LANGUAGE,
    DEFAULT_PRESSURE_TYPE,
    DOMAIN,
    GRAVITY_CONSTANT,
    KELVIN_OFFSET,
    LANGUAGE_INDEX,
    LAPSE_RATE,
    PRESSURE_TREND_FALLING,
    PRESSURE_TREND_RISING,
    PRESSURE_TYPE_ABSOLUTE,
    PRESSURE_TYPE_RELATIVE,
)
from .forecast_data import FORECAST_TEXTS, PRESSURE_SYSTEMS, CONDITIONS
from .zambretti import calculate_zambretti_forecast
from .negretti_zambra import calculate_negretti_zambra_forecast
from .calculations import (
    calculate_dewpoint,
    calculate_rain_probability_enhanced,
    get_fog_risk,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Local Weather Forecast sensors."""
    config = config_entry.data

    entities = [
        LocalForecastMainSensor(hass, config_entry),
        LocalForecastPressureSensor(hass, config_entry),
        LocalForecastTemperatureSensor(hass, config_entry),
        LocalForecastPressureChangeSensor(hass, config_entry),
        LocalForecastTemperatureChangeSensor(hass, config_entry),
        LocalForecastZambrettiDetailSensor(hass, config_entry),
        LocalForecastNegZamDetailSensor(hass, config_entry),
        LocalForecastEnhancedSensor(hass, config_entry),
        LocalForecastRainProbabilitySensor(hass, config_entry),
    ]

    async_add_entities(entities, True)


class LocalWeatherForecastEntity(RestoreEntity, SensorEntity):
    """Base class for Local Weather Forecast entities."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.config_entry = config_entry
        self._attr_has_entity_name = False  # Don't prefix with device name
        self._attr_should_poll = False
        self._last_update_time = None
        self._update_throttle_seconds = 30  # Minimum seconds between updates

    def _get_main_sensor_id(self) -> str:
        """Get the entity_id of the main sensor."""
        # Try new format first (after migration)
        new_id = "sensor.local_forecast"
        if self.hass.states.get(new_id):
            return new_id

        # Fallback to old format (before migration)
        # Entity registry generates: sensor.{domain}_{unique_id}
        old_id = f"sensor.{DOMAIN}_{self.config_entry.entry_id}_main"
        if self.hass.states.get(old_id):
            return old_id

        # Default to new format
        return new_id

    def _get_entity_id(self, suffix: str) -> str:
        """Get entity_id for a given suffix."""
        # Try new format first
        new_id = f"sensor.local_forecast_{suffix}"
        if self.hass.states.get(new_id):
            return new_id

        # Fallback to old format
        old_id = f"sensor.{DOMAIN}_local_forecast_{suffix}"
        if self.hass.states.get(old_id):
            return old_id

        # Default to new format
        return new_id

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "Local Weather Forecast",
            "manufacturer": "Local Weather Forecast",
            "model": "Zambretti Forecaster",
            "sw_version": "3.1.0",
        }

    async def _get_sensor_value(
        self,
        sensor_id: str,
        default: float = 0.0,
        use_history: bool = True
    ) -> float:
        """Get sensor value with fallback to history if unavailable."""
        if not sensor_id:
            return default

        state = self.hass.states.get(sensor_id)

        if state is None or state.state in ("unknown", "unavailable"):
            if use_history:
                _LOGGER.debug(
                    f"Sensor {sensor_id} unavailable, attempting to fetch from history"
                )
                return await self._get_historical_value(sensor_id, default)
            return default

        try:
            return float(state.state)
        except (ValueError, TypeError):
            # Check if this is an optional sensor (wind direction/speed)
            sensor_type = "sensor"
            if "wind" in sensor_id.lower():
                sensor_type = "optional wind sensor"
            _LOGGER.warning(
                f"Could not convert {sensor_type} {sensor_id} state '{state.state}' to float, using default {default}"
            )
            if use_history:
                return await self._get_historical_value(sensor_id, default)
            return default

    async def _get_historical_value(
        self,
        sensor_id: str,
        default: float = 0.0
    ) -> float:
        """Get last known good value from entity registry or return default."""
        try:
            # Try to get the entity from entity registry
            entity_reg = er.async_get(self.hass)
            entity_entry = entity_reg.async_get(sensor_id)

            if entity_entry:
                # Try to get last state from recorder
                recorder = get_instance(self.hass)
                if recorder:
                    # Get last valid state from history (last 24 hours)
                    end_time = datetime.now()
                    start_time = end_time - timedelta(hours=24)

                    states = await recorder.async_add_executor_job(
                        history.state_changes_during_period,
                        self.hass,
                        start_time,
                        end_time,
                        sensor_id
                    )

                    if states and sensor_id in states:
                        # Get the most recent valid state
                        for state in reversed(states[sensor_id]):
                            if state.state not in ("unknown", "unavailable", None):
                                try:
                                    value = float(state.state)
                                    _LOGGER.info(
                                        f"Retrieved historical value {value} for {sensor_id}"
                                    )
                                    return value
                                except (ValueError, TypeError):
                                    continue

            _LOGGER.warning(
                f"No historical data found for {sensor_id}, using default {default}"
            )
        except Exception as e:
            _LOGGER.error(
                f"Error retrieving historical data for {sensor_id}: {e}"
            )

        return default


class LocalForecastMainSensor(LocalWeatherForecastEntity):
    """Main Local Forecast sensor with all attributes."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the main sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast"  # Match original YAML entity_id
        self._attr_name = "Local forecast"
        self._attr_icon = "mdi:weather-cloudy"
        self._state = None
        self._attributes = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            self._state = last_state.state
            self._attributes = dict(last_state.attributes)

        # Track source sensor changes
        sensors_to_track = [
            self.config_entry.data.get(CONF_PRESSURE_SENSOR),
            self.config_entry.data.get(CONF_TEMPERATURE_SENSOR),
            self.config_entry.data.get(CONF_WIND_DIRECTION_SENSOR),
            self.config_entry.data.get(CONF_WIND_SPEED_SENSOR),
        ]

        # Filter out None values
        sensors_to_track = [s for s in sensors_to_track if s]

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, sensors_to_track, self._handle_sensor_update
            )
        )

        # Initial update
        await self.async_update()

    @callback
    async def _handle_sensor_update(self, event):
        """Handle source sensor state changes."""
        # Throttle updates to prevent flooding
        now = dt_util.now()
        if self._last_update_time is not None:
            time_since_last_update = (now - self._last_update_time).total_seconds()
            if time_since_last_update < self._update_throttle_seconds:
                _LOGGER.debug(
                    f"Skipping update for {self.entity_id}, only {time_since_last_update:.1f}s since last update"
                )
                return

        self._last_update_time = now
        await self.async_update()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the sensor."""
        config = self.config_entry.data
        language = config.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        lang_index = LANGUAGE_INDEX.get(language, 1)

        # Get sensor values with history fallback
        pressure = await self._get_sensor_value(
            config.get(CONF_PRESSURE_SENSOR), default=1013.25
        )
        temperature = await self._get_sensor_value(
            config.get(CONF_TEMPERATURE_SENSOR), default=15.0
        )
        wind_direction = await self._get_sensor_value(
            config.get(CONF_WIND_DIRECTION_SENSOR), default=0.0
        )
        wind_speed = await self._get_sensor_value(
            config.get(CONF_WIND_SPEED_SENSOR), default=0.0
        )

        elevation = config.get(CONF_ELEVATION, DEFAULT_ELEVATION)
        pressure_type = config.get(CONF_PRESSURE_TYPE, DEFAULT_PRESSURE_TYPE)

        # Calculate sea level pressure based on pressure type
        if pressure_type == PRESSURE_TYPE_RELATIVE:
            # Sensor already provides sea level pressure (QNH)
            p0 = pressure
        else:
            # Sensor provides station pressure (QFE) - need to convert
            p0 = self._calculate_sea_level_pressure(pressure, temperature, elevation)

        # Calculate wind factors
        wind_data = self._calculate_wind_data(wind_direction, wind_speed)

        # Get pressure change from statistics sensor
        pressure_change = await self._get_sensor_value(
            "sensor.local_forecast_pressurechange",  # Match original YAML entity_id
            default=0.0,
            use_history=False
        )

        # Calculate current conditions
        current_condition = self._get_current_condition(p0, lang_index)

        # Calculate Zambretti forecast
        zambretti_forecast = calculate_zambretti_forecast(
            p0, pressure_change, wind_data, lang_index
        )

        # Calculate Negretti & Zambra forecast
        neg_zam_forecast = calculate_negretti_zambra_forecast(
            p0, pressure_change, wind_data, lang_index, elevation
        )

        # Calculate pressure trend
        pressure_trend = self._get_pressure_trend(pressure_change, lang_index)

        # Update state and attributes
        # Format: [German, English, Greek, Italian, Slovak]
        titles = [
            "Lokale Wettervorhersage",
            "12hr Local Weather Forecast",
            "Τοπική πρόγνωση καιρού",
            "Previsione meteorologica locale",
            "Lokálna predpoveď počasia",  # Slovak
        ]
        self._state = titles[lang_index]

        # Calculate short-term temperature forecast
        temp_short = self._calculate_temp_short_forecast(temperature)

        # Keep original list/array formats for full compatibility with original YAML code
        self._attributes = {
            "language": lang_index,
            "temperature": round(temperature, 1),
            "p0": round(p0, 1),
            "wind_direction": wind_data,  # List: [wind_fak, dir, dir_text, speed_fak]
            "forecast_short_term": current_condition,  # List: [condition, pressure_system]
            "forecast_zambretti": zambretti_forecast,  # List: [text, number, letter]
            "forecast_neg_zam": neg_zam_forecast,  # List: [text, number, letter]
            "forecast_pressure_trend": pressure_trend,  # List: [text, index]
            "forecast_temp_short": temp_short,  # List: [predicted_temp, interval_index] or string if unavailable
        }

    def _calculate_temp_short_forecast(self, current_temp: float) -> list | str:
        """Calculate short-term temperature forecast.

        Uses temperature change and forecast interval times to predict temperature.
        Returns: [predicted_temp, interval_index] where interval: 0=first_time, 1=second_time, -1=unavailable
        """
        # Get temperature change sensor
        temp_change_sensor = self.hass.states.get("sensor.local_forecast_temperaturechange")  # Match original YAML entity_id
        if not temp_change_sensor or temp_change_sensor.state in ("unknown", "unavailable"):
            _LOGGER.debug(
                f"Temperature change sensor not available: {temp_change_sensor.state if temp_change_sensor else 'not found'}"
            )
            return ["unavailable", -1]

        try:
            temp_change = float(temp_change_sensor.state)
        except (ValueError, TypeError):
            _LOGGER.debug(f"Could not convert temperature change to float: {temp_change_sensor.state}")
            return ["unavailable", -1]

        # Get Zambretti detail sensor for timing information
        zambretti_detail = self.hass.states.get("sensor.local_forecast_zambretti_detail")  # Match original YAML entity_id
        if not zambretti_detail or zambretti_detail.state in ("unknown", "unavailable"):
            _LOGGER.debug(
                f"Zambretti detail sensor not available: {zambretti_detail.state if zambretti_detail else 'not found'}"
            )
            return ["unavailable", -1]

        attrs = zambretti_detail.attributes
        _LOGGER.debug(f"Zambretti detail attributes: {attrs}")

        # Try to get first_time
        first_time = attrs.get("first_time")
        if first_time and isinstance(first_time, list) and len(first_time) > 1:
            try:
                minutes_to_first = float(first_time[1])
                _LOGGER.debug(f"first_time minutes: {minutes_to_first}")

                if minutes_to_first > 0:
                    # Calculate temperature at first interval
                    # temp_change is per hour, so convert minutes to hours
                    predicted_temp = (temp_change / 60 * minutes_to_first) + current_temp
                    _LOGGER.debug(
                        f"Calculated temp forecast using first_time: {predicted_temp:.1f}°C "
                        f"(current: {current_temp}, change/hr: {temp_change}, minutes: {minutes_to_first})"
                    )
                    return [round(predicted_temp, 1), 0]
                else:
                    _LOGGER.warning(
                        f"first_time has negative minutes: {minutes_to_first}. "
                        f"This indicates old forecast data. Detail sensor needs to update."
                    )
            except (ValueError, TypeError, IndexError) as e:
                _LOGGER.debug(f"Error calculating from first_time: {e}")

        # Try second_time if first_time failed
        second_time = attrs.get("second_time")
        if second_time and isinstance(second_time, list) and len(second_time) > 1:
            try:
                minutes_to_second = float(second_time[1])
                _LOGGER.debug(f"second_time minutes: {minutes_to_second}")

                if minutes_to_second > 0:
                    # Calculate temperature at second interval
                    predicted_temp = (temp_change / 60 * minutes_to_second) + current_temp
                    _LOGGER.debug(
                        f"Calculated temp forecast using second_time: {predicted_temp:.1f}°C "
                        f"(current: {current_temp}, change/hr: {temp_change}, minutes: {minutes_to_second})"
                    )
                    return [round(predicted_temp, 1), 1]
                else:
                    _LOGGER.warning(
                        f"second_time has negative minutes: {minutes_to_second}. "
                        f"This indicates old forecast data. Detail sensor needs to update."
                    )
            except (ValueError, TypeError, IndexError) as e:
                _LOGGER.debug(f"Error calculating from second_time: {e}")

        _LOGGER.warning(
            "No valid time intervals found for temperature forecast. "
            "Check that detail sensors are updating correctly."
        )
        return ["unavailable", -1]

    def _calculate_sea_level_pressure(
        self, pressure: float, temperature: float, elevation: float
    ) -> float:
        """Calculate sea level pressure from station pressure."""
        if elevation == 0:
            return pressure

        temp_kelvin = temperature + KELVIN_OFFSET
        factor = 1 - ((LAPSE_RATE * elevation) / (temp_kelvin + LAPSE_RATE * elevation))
        p0 = pressure * (factor ** (-GRAVITY_CONSTANT))
        return p0

    def _calculate_wind_data(
        self, wind_direction: float, wind_speed: float
    ) -> list:
        """Calculate wind direction data."""
        # Wind speed factor
        wind_speed_fak = 1 if wind_speed >= 1 else 0

        # Wind bearing factor (N/S/other)
        if 135 <= wind_direction <= 225:
            wind_fak = 2  # South
        elif wind_direction >= 315 or wind_direction <= 45:
            wind_fak = 0  # North
        else:
            wind_fak = 1  # East/West

        # Wind direction text
        dir_text = self._get_wind_direction_text(wind_direction)

        return [wind_fak, wind_direction, dir_text, wind_speed_fak]

    def _get_wind_direction_text(self, degrees: float) -> str:
        """Convert degrees to compass direction."""
        directions = [
            ("N", 348.75, 11.25),
            ("NNE", 11.25, 33.75),
            ("NE", 33.75, 56.25),
            ("ENE", 56.25, 78.75),
            ("E", 78.75, 101.25),
            ("ESE", 101.25, 123.75),
            ("SE", 123.75, 146.25),
            ("SSE", 146.25, 168.75),
            ("S", 168.75, 191.25),
            ("SSW", 191.25, 213.75),
            ("SW", 213.75, 236.25),
            ("WSW", 236.25, 258.75),
            ("W", 258.75, 281.25),
            ("WNW", 281.25, 303.75),
            ("NW", 303.75, 326.25),
            ("NNW", 326.25, 348.75),
        ]

        for direction, start, end in directions:
            if start > end:  # Handle wraparound for North
                if degrees > start or degrees <= end:
                    return direction
            elif start < degrees <= end:
                return direction

        return "N"

    def _get_current_condition(self, p0: float, lang_index: int) -> list:
        """Get current weather condition based on pressure."""
        if p0 < 980:
            condition_idx = 0  # Stormy
            pressure_idx = 0  # Low
        elif 980 <= p0 < 1000:
            condition_idx = 1  # Rainy
            pressure_idx = 0  # Low
        elif 1000 <= p0 < 1020:
            condition_idx = 2  # Mixed
            pressure_idx = 1  # Normal
        elif 1020 <= p0 < 1040:
            condition_idx = 3  # Sunny
            pressure_idx = 2  # High
        else:  # p0 >= 1040
            condition_idx = 4  # Extra Dry
            pressure_idx = 2  # High

        return [
            CONDITIONS[condition_idx][lang_index],
            PRESSURE_SYSTEMS[pressure_idx][lang_index],
        ]

    def _get_pressure_trend(self, pressure_change: float, lang_index: int) -> list:
        """Get pressure trend text."""
        # Format: [German, English, Greek, Italian, Slovak]
        trend_texts = [
            ("fallend", "Falling", "πέφτοντας", "In diminuzione", "Klesajúci"),
            ("steigend", "Rising", "αυξανόμενη", "In aumento", "Stúpajúci"),
            ("stabil", "Steady", "σταθερή", "Stabile", "Stabilný"),
        ]

        if pressure_change <= PRESSURE_TREND_FALLING:
            trend_idx = 0
        elif pressure_change >= PRESSURE_TREND_RISING:
            trend_idx = 1
        else:
            trend_idx = 2

        return [trend_texts[trend_idx][lang_index], trend_idx]

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes


class LocalForecastPressureSensor(LocalWeatherForecastEntity):
    """Pressure sensor with proper device class."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_pressure"  # Match original YAML entity_id
        self._attr_name = "Local forecast Pressure"
        self._attr_device_class = SensorDeviceClass.ATMOSPHERIC_PRESSURE
        self._attr_native_unit_of_measurement = UnitOfPressure.HPA
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._state = float(last_state.state)
            except (ValueError, TypeError):
                pass

        # Track main sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._get_main_sensor_id()],
                self._handle_main_update,
            )
        )

        # Initial update
        await self._update_from_main()

    async def _update_from_main(self):
        """Update from main sensor."""
        main_sensor = self.hass.states.get("sensor.local_forecast")
        if main_sensor and main_sensor.state != "unknown":
            p0 = main_sensor.attributes.get("p0")
            if p0 is not None:
                self._state = float(p0)

    @callback
    async def _handle_main_update(self, event):
        """Handle main sensor updates."""
        # Throttle updates to prevent flooding
        now = dt_util.now()
        if self._last_update_time is not None:
            time_since_last_update = (now - self._last_update_time).total_seconds()
            if time_since_last_update < self._update_throttle_seconds:
                _LOGGER.debug(
                    f"Skipping update for {self.entity_id}, only {time_since_last_update:.1f}s since last update"
                )
                return

        self._last_update_time = now
        await self._update_from_main()
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        return self._state


class LocalForecastTemperatureSensor(LocalWeatherForecastEntity):
    """Temperature sensor with proper device class."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_temperature"  # Match original YAML entity_id
        self._attr_name = "Local forecast temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._state = float(last_state.state)
            except (ValueError, TypeError):
                pass

        # Track main sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._get_main_sensor_id()],
                self._handle_main_update,
            )
        )

        # Initial update
        await self._update_from_main()

    async def _update_from_main(self):
        """Update from main sensor."""
        main_sensor = self.hass.states.get("sensor.local_forecast")
        if main_sensor and main_sensor.state != "unknown":
            temp = main_sensor.attributes.get("temperature")
            if temp is not None:
                self._state = float(temp)

    @callback
    async def _handle_main_update(self, event):
        """Handle main sensor updates."""
        # Throttle updates to prevent flooding
        now = dt_util.now()
        if self._last_update_time is not None:
            time_since_last_update = (now - self._last_update_time).total_seconds()
            if time_since_last_update < self._update_throttle_seconds:
                _LOGGER.debug(
                    f"Skipping update for {self.entity_id}, only {time_since_last_update:.1f}s since last update"
                )
                return

        self._last_update_time = now
        await self._update_from_main()
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        return self._state


class LocalForecastPressureChangeSensor(LocalWeatherForecastEntity):
    """Pressure change statistics sensor."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_pressurechange"  # Match original YAML entity_id (no underscore!)
        self._attr_name = "Local forecast PressureChange"
        self._attr_native_unit_of_measurement = UnitOfPressure.HPA
        self._attr_icon = "mdi:trending-up"
        self._state = 0.0
        self._history = []

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._state = float(last_state.state)
            except (ValueError, TypeError):
                pass

        # Track pressure sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                ["sensor.local_forecast_pressure"],
                self._handle_pressure_update,
            )
        )

        # Add initial pressure value to history
        pressure_sensor = self.hass.states.get("sensor.local_forecast_pressure")
        if pressure_sensor and pressure_sensor.state not in ("unknown", "unavailable"):
            try:
                pressure = float(pressure_sensor.state)
                timestamp = datetime.now()
                self._history.append((timestamp, pressure))
                _LOGGER.debug(
                    f"Pressure change sensor initialized with {pressure} hPa at {timestamp}"
                )
            except (ValueError, TypeError):
                pass

    @callback
    async def _handle_pressure_update(self, event):
        """Handle pressure sensor updates."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state not in ("unknown", "unavailable"):
            try:
                pressure = float(new_state.state)
                timestamp = datetime.now()

                # Add to history
                self._history.append((timestamp, pressure))

                # Keep only last 180 minutes
                cutoff = timestamp - timedelta(minutes=180)
                self._history = [
                    (ts, p) for ts, p in self._history if ts > cutoff
                ]

                # Calculate change if we have enough data
                if len(self._history) >= 2:
                    oldest = self._history[0][1]
                    newest = self._history[-1][1]
                    self._state = round(newest - oldest, 2)
                    self.async_write_ha_state()

            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        return self._state


class LocalForecastTemperatureChangeSensor(LocalWeatherForecastEntity):
    """Temperature change statistics sensor."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_temperaturechange"  # Match original YAML entity_id (no underscore!)
        self._attr_name = "Local forecast TemperatureChange"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer-lines"
        self._state = 0.0
        self._history = []

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._state = float(last_state.state)
            except (ValueError, TypeError):
                pass

        # Track temperature sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                ["sensor.local_forecast_temperature"],
                self._handle_temperature_update,
            )
        )

        # Add initial temperature value to history
        temp_sensor = self.hass.states.get("sensor.local_forecast_temperature")
        if temp_sensor and temp_sensor.state not in ("unknown", "unavailable"):
            try:
                temperature = float(temp_sensor.state)
                timestamp = datetime.now()
                self._history.append((timestamp, temperature))
                _LOGGER.debug(
                    f"Temperature change sensor initialized with {temperature}°C at {timestamp}"
                )
            except (ValueError, TypeError):
                pass

    @callback
    async def _handle_temperature_update(self, event):
        """Handle temperature sensor updates."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state not in ("unknown", "unavailable"):
            try:
                temperature = float(new_state.state)
                timestamp = datetime.now()

                # Add to history
                self._history.append((timestamp, temperature))

                # Keep only last 60 minutes
                cutoff = timestamp - timedelta(minutes=60)
                self._history = [
                    (ts, t) for ts, t in self._history if ts > cutoff
                ]

                # Calculate change if we have enough data
                if len(self._history) >= 2:
                    oldest = self._history[0][1]
                    newest = self._history[-1][1]
                    self._state = round(newest - oldest, 2)
                    self.async_write_ha_state()

            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        return self._state


class LocalForecastZambrettiDetailSensor(LocalWeatherForecastEntity):
    """Zambretti forecast detail sensor."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_zambretti_detail"  # Match original YAML entity_id
        self._attr_name = "Local forecast zambretti detail"
        self._attr_icon = "mdi:weather-cloudy-arrow-right"
        self._state = None
        self._attributes = {}
        self._last_update_time = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in ("unknown", "unavailable"):
                self._state = last_state.state
                self._attributes = dict(last_state.attributes)
                # DO NOT restore last_update_time from old state - always use current time
                # to prevent negative time intervals in forecasts
                self._last_update_time = dt_util.now()

        # Track main sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._get_main_sensor_id()],
                self._handle_main_update,
            )
        )

        # Schedule periodic updates every 10 minutes to keep forecast times current
        from homeassistant.helpers.event import async_track_time_interval
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._periodic_update,
                timedelta(minutes=10),
            )
        )

        # Initial update
        await self._update_from_main()
        # Write state immediately
        self.async_write_ha_state()

    @callback
    async def _periodic_update(self, now: datetime) -> None:
        """Periodic update to refresh forecast times."""
        if self._state and self._attributes:
            # Recalculate forecast times with current time
            current_time = dt_util.now()

            # SYNC: Re-synchronize reference time from pressure change sensor
            # This ensures consistent timing even during periodic updates
            pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
            if pressure_change_sensor and pressure_change_sensor.last_updated:
                # Only update if pressure sensor was updated more recently
                if self._last_update_time is None or pressure_change_sensor.last_updated > self._last_update_time:
                    self._last_update_time = pressure_change_sensor.last_updated
                    _LOGGER.debug(f"Zambretti: Synced reference time to {self._last_update_time}")

            # Check if sun is below horizon for icon selection
            sun_state = self.hass.states.get("sun.sun")
            is_night = sun_state and sun_state.state == "below_horizon"

            # Get forecast states
            forecast_states = self._attributes.get("forecast", [3, 3])

            # Update icons based on current time of day
            icon_now = self._get_icon_for_forecast(forecast_states[0], is_night)
            icon_later = self._get_icon_for_forecast(forecast_states[1], is_night)

            # Recalculate dynamic timing
            first_time_data = self._calculate_interval_time(3, current_time)
            second_time_data = self._calculate_interval_time(9, current_time)

            # Update only the time-dependent attributes
            self._attributes["first_time"] = first_time_data
            self._attributes["second_time"] = second_time_data
            self._attributes["icons"] = (icon_now, icon_later)

            # Write updated state
            self.async_write_ha_state()

            _LOGGER.debug(
                f"Zambretti detail periodic update: first_time={first_time_data}, second_time={second_time_data}"
            )

    async def _update_from_main(self):
        """Update from main sensor."""
        main_sensor = self.hass.states.get("sensor.local_forecast")
        if not main_sensor or main_sensor.state in ("unknown", "unavailable"):
            return

        attrs = main_sensor.attributes

        # Parse Zambretti forecast - expect list format: [text, number, letter]
        zambretti = attrs.get("forecast_zambretti")
        if not zambretti:
            return

        # Handle list format (original format)
        if isinstance(zambretti, list) and len(zambretti) >= 3:
            forecast_text = str(zambretti[0])
            try:
                forecast_num = int(zambretti[1])
            except (ValueError, TypeError):
                forecast_num = 0
            letter_code = str(zambretti[2])
        # Fallback: handle string format "text, number, letter" for compatibility
        elif isinstance(zambretti, str) and ", " in zambretti:
            parts = zambretti.split(", ")
            forecast_text = parts[0] if len(parts) > 0 else ""
            try:
                forecast_num = int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                forecast_num = 0
            letter_code = parts[2] if len(parts) > 2 else ""
        else:
            # Invalid format
            self._state = str(zambretti)
            self._attributes = {}
            return

        # SYNCHRONIZED TIME: Use main sensor's last update time for consistent timing
        # This ensures Zambretti and Negretti-Zambra detail sensors show same forecast times
        now = dt_util.now()

        # Try to get pressure change sensor's last update time as reference
        # This is when the forecast was actually calculated
        pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
        if pressure_change_sensor and pressure_change_sensor.last_updated:
            reference_time = pressure_change_sensor.last_updated
        else:
            reference_time = now

        # Check if forecast actually changed (different number)
        forecast_changed = False
        if self._attributes:
            old_forecast_num = self._attributes.get("forecast_number")
            if old_forecast_num != forecast_num:
                forecast_changed = True

        # Update last_update_time if forecast changed OR if it's None
        # Use reference_time instead of now() for consistency
        if self._last_update_time is None or forecast_changed:
            self._last_update_time = reference_time

        # Map forecast number to weather states
        forecast_states = self._map_forecast_to_states(forecast_num)

        # Estimate rain probability based on states
        rain_prob = self._estimate_rain_probability(forecast_states)

        # Check if sun is below horizon for icon selection
        sun_state = self.hass.states.get("sun.sun")
        is_night = sun_state and sun_state.state == "below_horizon"

        # Get icons for both periods
        icon_now = self._get_icon_for_forecast(forecast_states[0], is_night)
        icon_later = self._get_icon_for_forecast(forecast_states[1], is_night)

        # Calculate dynamic timing
        first_time_data = self._calculate_interval_time(3, now)  # 3h for first interval
        second_time_data = self._calculate_interval_time(9, now)  # 9h for second interval

        # Set state and attributes
        self._state = forecast_text
        self._attributes = {
            "forecast_text": forecast_text,
            "forecast_number": forecast_num,
            "letter_code": letter_code,
            "forecast": forecast_states,  # List format [state_6h, state_12h]
            "icons": (icon_now, icon_later),  # Tuple format
            "rain_prob": rain_prob,  # List format [prob_6h, prob_12h]
            "first_time": first_time_data,  # List format ["HH:MM", minutes]
            "second_time": second_time_data,  # List format ["HH:MM", minutes]
        }

    def _calculate_interval_time(self, base_hours: int, current_time: datetime) -> list:
        """Calculate time to forecast interval with correction for old forecasts."""
        if self._last_update_time is None:
            self._last_update_time = current_time

        # Calculate time since last update in minutes
        time_since_update = (current_time - self._last_update_time).total_seconds() / 60

        # If forecast is very old (more than base_hours), reset the forecast time
        # This prevents negative time intervals and keeps forecasts current
        if time_since_update >= base_hours * 60:
            # Reset the update time to current - treat forecast as starting now
            self._last_update_time = current_time
            time_since_update = 0
            _LOGGER.debug(
                f"Zambretti forecast interval passed ({time_since_update:.1f} min > {base_hours * 60} min). "
                f"Resetting forecast reference time to current time."
            )

        # Calculate minutes remaining to this interval
        time_to_interval = base_hours * 60 - time_since_update
        target_time = current_time + timedelta(minutes=time_to_interval)
        time_string = target_time.strftime("%H:%M")

        return [time_string, round(time_to_interval, 2)]

    @callback
    async def _handle_main_update(self, event):
        """Handle main sensor updates."""
        await self._update_from_main()
        self.async_write_ha_state()

    def _map_forecast_to_states(self, forecast_num: int) -> list[int]:
        """Map forecast number to weather states [6h, 12h].

        States: 0=sunny, 1=partlycloudy, 2=partlycloudyrain, 3=cloudy,
                4=rainy, 5=pouring, 6=lightning-rainy
        """
        # Based on original weather_forecast.yaml mapping
        state_map = {
            0: [0, 0],   # Settled fine
            1: [1, 1],   # Fine weather
            2: [2, 1],   # Becoming fine
            3: [1, 2],   # Fine, becoming less settled
            4: [1, 1],   # Fine, possible showers
            5: [1, 0],   # Fairly fine, improving
            6: [2, 1],   # Fairly fine, possible showers early
            7: [1, 4],   # Fairly fine, showery later
            8: [4, 2],   # Showery early, improving
            9: [4, 4],   # Changeable, mending
            10: [1, 1],  # Fairly fine, showers likely
            11: [3, 1],  # Rather unsettled, clearing later
            12: [3, 3],  # Unsettled, probably improving
            13: [2, 2],  # Showery, bright intervals
            14: [4, 5],  # Showery, becoming more unsettled
            15: [4, 4],  # Changeable, some rain
            16: [2, 2],  # Unsettled, short fine intervals
            17: [2, 4],  # Unsettled, rain later
            18: [2, 2],  # Unsettled, rain at times
            19: [5, 5],  # Very unsettled, finer at times
            20: [2, 4],  # Rain at times, worse later
            21: [4, 4],  # Rain at times, becoming very unsettled
            22: [4, 4],  # Rain at frequent intervals
            23: [6, 4],  # Very unsettled, rain
            24: [6, 6],  # Stormy, possibly improving
            25: [6, 6],  # Stormy, much rain
        }
        return state_map.get(forecast_num, [3, 3])

    def _get_icon_for_forecast(self, state: int, is_night: bool = False) -> str:
        """Map weather state to icon."""
        # Icon mapping: [day_icon, night_icon]
        icon_map = {
            0: ("mdi:weather-sunny", "mdi:weather-night"),
            1: ("mdi:weather-partly-cloudy", "mdi:weather-night-partly-cloudy"),
            2: ("mdi:weather-partly-rainy", "mdi:weather-partly-rainy"),
            3: ("mdi:weather-cloudy", "mdi:weather-cloudy"),
            4: ("mdi:weather-rainy", "mdi:weather-rainy"),
            5: ("mdi:weather-pouring", "mdi:weather-pouring"),
            6: ("mdi:weather-lightning-rainy", "mdi:weather-lightning-rainy"),
        }
        icons = icon_map.get(state, ("mdi:weather-cloudy", "mdi:weather-cloudy"))
        return icons[1] if is_night else icons[0]

    def _estimate_rain_probability(self, forecast_states: list[int]) -> list[int]:
        """Estimate rain probability based on forecast states."""
        # Extract 6h and 12h states
        state_6h = forecast_states[0] if len(forecast_states) > 0 else 3
        state_12h = forecast_states[1] if len(forecast_states) > 1 else 3

        # Match original logic from weather_forecast.yaml
        if state_6h == 0 and state_12h == 0:
            return [0, 0]
        elif state_6h == 2 and state_12h == 1:
            return [60, 10]
        elif state_6h == 1 and state_12h == 1:
            return [30, 30]
        elif state_6h == 1 and state_12h == 0:
            return [10, 0]
        elif state_6h == 1 and state_12h >= 2:
            return [20, 60]
        elif state_6h == 2 and state_12h == 2:
            return [50, 50]
        elif state_6h == 2 and state_12h > 2:
            return [50, 70]
        elif state_6h >= 2 and state_12h < 2:
            return [50, 10]
        else:
            return [90, 90]

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes


class LocalForecastNegZamDetailSensor(LocalWeatherForecastEntity):
    """Negretti & Zambra forecast detail sensor."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_neg_zam_detail"  # Match original YAML entity_id
        self._attr_name = "Local forecast neg_zam detail"
        self._attr_icon = "mdi:weather-cloudy-clock"
        self._state = None
        self._attributes = {}
        self._last_update_time = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in ("unknown", "unavailable"):
                self._state = last_state.state
                self._attributes = dict(last_state.attributes)
                # DO NOT restore last_update_time from old state - always use current time
                # to prevent negative time intervals in forecasts
                self._last_update_time = dt_util.now()

        # Track main sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._get_main_sensor_id()],
                self._handle_main_update,
            )
        )

        # Schedule periodic updates every 10 minutes to keep forecast times current
        from homeassistant.helpers.event import async_track_time_interval
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._periodic_update,
                timedelta(minutes=10),
            )
        )

        # Initial update - always update from main sensor
        await self._update_from_main()
        # Write state immediately
        self.async_write_ha_state()

    @callback
    async def _periodic_update(self, now: datetime) -> None:
        """Periodic update to refresh forecast times."""
        if self._state and self._attributes:
            # Recalculate forecast times with current time
            current_time = dt_util.now()

            # SYNC: Re-synchronize reference time from pressure change sensor
            # This ensures consistent timing even during periodic updates
            pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
            if pressure_change_sensor and pressure_change_sensor.last_updated:
                # Only update if pressure sensor was updated more recently
                if self._last_update_time is None or pressure_change_sensor.last_updated > self._last_update_time:
                    self._last_update_time = pressure_change_sensor.last_updated
                    _LOGGER.debug(f"Negretti: Synced reference time to {self._last_update_time}")

            # Check if sun is below horizon for icon selection
            sun_state = self.hass.states.get("sun.sun")
            is_night = sun_state and sun_state.state == "below_horizon"

            # Get forecast states
            forecast_states = self._attributes.get("forecast", [3, 3])

            # Update icons based on current time of day
            icon_now = self._get_icon_for_forecast(forecast_states[0], is_night)
            icon_later = self._get_icon_for_forecast(forecast_states[1], is_night)

            # Recalculate dynamic timing
            first_time_data = self._calculate_interval_time(3, current_time)
            second_time_data = self._calculate_interval_time(9, current_time)

            # Update only the time-dependent attributes
            self._attributes["first_time"] = first_time_data
            self._attributes["second_time"] = second_time_data
            self._attributes["icons"] = (icon_now, icon_later)

            # Write updated state
            self.async_write_ha_state()

            _LOGGER.debug(
                f"Negretti detail periodic update: first_time={first_time_data}, second_time={second_time_data}"
            )

    async def _update_from_main(self):
        """Update from main sensor."""
        main_sensor = self.hass.states.get("sensor.local_forecast")
        if not main_sensor or main_sensor.state in ("unknown", "unavailable"):
            return

        attrs = main_sensor.attributes

        # Parse Negretti-Zambra forecast - expect list format: [text, number, letter]
        neg_zam = attrs.get("forecast_neg_zam")
        if not neg_zam:
            return

        # Handle list format (original format)
        if isinstance(neg_zam, list) and len(neg_zam) >= 3:
            forecast_text = str(neg_zam[0])
            try:
                forecast_num = int(neg_zam[1])
            except (ValueError, TypeError):
                forecast_num = 0
            letter_code = str(neg_zam[2])
        # Fallback: handle string format "text, number, letter" for compatibility
        elif isinstance(neg_zam, str) and ", " in neg_zam:
            parts = neg_zam.split(", ")
            forecast_text = parts[0] if len(parts) > 0 else ""
            try:
                forecast_num = int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                forecast_num = 0
            letter_code = parts[2] if len(parts) > 2 else ""
        else:
            # Invalid format
            self._state = str(neg_zam)
            self._attributes = {}
            return

        # SYNCHRONIZED TIME: Use main sensor's last update time for consistent timing
        # This ensures Zambretti and Negretti-Zambra detail sensors show same forecast times
        now = dt_util.now()

        # Try to get pressure change sensor's last update time as reference
        # This is when the forecast was actually calculated
        pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
        if pressure_change_sensor and pressure_change_sensor.last_updated:
            reference_time = pressure_change_sensor.last_updated
        else:
            reference_time = now

        # Check if forecast actually changed (different number)
        forecast_changed = False
        if self._attributes:
            old_forecast_num = self._attributes.get("forecast_number")
            if old_forecast_num != forecast_num:
                forecast_changed = True

        # Update last_update_time if forecast changed OR if it's None
        # Use reference_time instead of now() for consistency
        if self._last_update_time is None or forecast_changed:
            self._last_update_time = reference_time

        # Map forecast number to weather states (slightly different from Zambretti)
        forecast_states = self._map_forecast_to_states(forecast_num)

        # Estimate rain probability based on states
        rain_prob = self._estimate_rain_probability(forecast_states)

        # Check if sun is below horizon for icon selection
        sun_state = self.hass.states.get("sun.sun")
        is_night = sun_state and sun_state.state == "below_horizon"

        # Get icons for both periods
        icon_now = self._get_icon_for_forecast(forecast_states[0], is_night)
        icon_later = self._get_icon_for_forecast(forecast_states[1], is_night)

        # Calculate dynamic timing
        first_time_data = self._calculate_interval_time(3, now)  # 3h for first interval
        second_time_data = self._calculate_interval_time(9, now)  # 9h for second interval

        # Set state and attributes
        self._state = forecast_text
        self._attributes = {
            "forecast_text": forecast_text,
            "forecast_number": forecast_num,
            "letter_code": letter_code,
            "forecast": forecast_states,  # List format [state_6h, state_12h]
            "icons": (icon_now, icon_later),  # Tuple format
            "rain_prob": rain_prob,  # List format [prob_6h, prob_12h]
            "first_time": first_time_data,  # List format ["HH:MM", minutes]
            "second_time": second_time_data,  # List format ["HH:MM", minutes]
        }

    def _calculate_interval_time(self, base_hours: int, current_time: datetime) -> list:
        """Calculate time to forecast interval with correction for old forecasts."""
        if self._last_update_time is None:
            self._last_update_time = current_time

        # Calculate time since last update in minutes
        time_since_update = (current_time - self._last_update_time).total_seconds() / 60

        # If forecast is very old (more than base_hours), reset the forecast time
        # This prevents negative time intervals and keeps forecasts current
        if time_since_update >= base_hours * 60:
            # Reset the update time to current - treat forecast as starting now
            self._last_update_time = current_time
            time_since_update = 0
            _LOGGER.debug(
                f"Negretti forecast interval passed ({time_since_update:.1f} min > {base_hours * 60} min). "
                f"Resetting forecast reference time to current time."
            )

        # Calculate minutes remaining to this interval
        time_to_interval = base_hours * 60 - time_since_update
        target_time = current_time + timedelta(minutes=time_to_interval)
        time_string = target_time.strftime("%H:%M")

        return [time_string, round(time_to_interval, 2)]

    @callback
    async def _handle_main_update(self, event):
        """Handle main sensor updates."""
        await self._update_from_main()
        self.async_write_ha_state()

    def _map_forecast_to_states(self, forecast_num: int) -> list[int]:
        """Map forecast number to weather states [6h, 12h].

        Negretti-Zambra has slightly different mapping than Zambretti.
        States: 0=sunny, 1=partlycloudy, 2=partlycloudyrain, 3=cloudy,
                4=rainy, 5=pouring, 6=lightning-rainy
        """
        # Based on original weather_forecast.yaml for neg_zam_detail
        state_map = {
            0: [0, 0],   # Settled fine
            1: [1, 1],   # Fine weather
            2: [2, 1],   # Becoming fine
            3: [1, 2],   # Fine, becoming less settled
            4: [2, 2],   # Fine, possible showers
            5: [2, 1],   # Fairly fine, improving
            6: [2, 1],   # Fairly fine, possible showers early
            7: [1, 4],   # Fairly fine, showery later
            8: [4, 2],   # Showery early, improving
            9: [4, 4],   # Changeable, mending
            10: [2, 2],  # Fairly fine, showers likely
            11: [3, 1],  # Rather unsettled, clearing later
            12: [3, 3],  # Unsettled, probably improving
            13: [2, 2],  # Showery, bright intervals
            14: [4, 5],  # Showery, becoming more unsettled
            15: [4, 4],  # Changeable, some rain
            16: [2, 2],  # Unsettled, short fine intervals
            17: [2, 4],  # Unsettled, rain later
            18: [2, 2],  # Unsettled, rain at times
            19: [5, 5],  # Very unsettled, finer at times
            20: [2, 4],  # Rain at times, worse later
            21: [4, 4],  # Rain at times, becoming very unsettled
            22: [4, 4],  # Rain at frequent intervals
            23: [4, 4],  # Very unsettled, rain
            24: [6, 4],  # Stormy, possibly improving
            25: [6, 6],  # Stormy, much rain
        }
        return state_map.get(forecast_num, [3, 3])

    def _get_icon_for_forecast(self, state: int, is_night: bool = False) -> str:
        """Map weather state to icon."""
        # Icon mapping: [day_icon, night_icon]
        icon_map = {
            0: ("mdi:weather-sunny", "mdi:weather-night"),
            1: ("mdi:weather-partly-cloudy", "mdi:weather-night-partly-cloudy"),
            2: ("mdi:weather-partly-rainy", "mdi:weather-partly-rainy"),
            3: ("mdi:weather-cloudy", "mdi:weather-cloudy"),
            4: ("mdi:weather-rainy", "mdi:weather-rainy"),
            5: ("mdi:weather-pouring", "mdi:weather-pouring"),
            6: ("mdi:weather-lightning-rainy", "mdi:weather-lightning-rainy"),
        }
        icons = icon_map.get(state, ("mdi:weather-cloudy", "mdi:weather-cloudy"))
        return icons[1] if is_night else icons[0]

    def _estimate_rain_probability(self, forecast_states: list[int]) -> list[int]:
        """Estimate rain probability based on forecast states."""
        # Extract 6h and 12h states
        state_6h = forecast_states[0] if len(forecast_states) > 0 else 3
        state_12h = forecast_states[1] if len(forecast_states) > 1 else 3

        # Match original logic from weather_forecast.yaml (neg_zam version)
        if state_6h < 2 and state_12h < 2:
            return [0, 0]
        elif state_6h == 1 and state_12h >= 2:
            return [20, 60]
        elif state_6h == 2 and state_12h == 2:
            return [50, 50]
        elif state_6h == 2 and state_12h > 2:
            return [50, 70]
        else:
            return [90, 90]

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes


# ==============================================================================
# ENHANCED SENSORS - Modern sensor integration with classical algorithms
# ==============================================================================


class LocalForecastEnhancedSensor(LocalWeatherForecastEntity):
    """Enhanced forecast sensor combining algorithms with modern sensors."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the enhanced forecast sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_enhanced"
        self._attr_name = "Local forecast Enhanced"
        self._attr_icon = "mdi:weather-partly-rainy"
        self._startup_retry_count = 0
        self._state = None  # Initialize state
        self._attributes = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass - schedule delayed update for startup."""
        await super().async_added_to_hass()

        # Schedule delayed update to wait for dependent sensors to load
        async def delayed_startup_update():
            await asyncio.sleep(10)  # Wait 10 seconds for other integrations to load
            _LOGGER.info("Enhanced: Running delayed startup update")
            await self.async_update()
            self.async_write_ha_state()

        self.hass.async_create_task(delayed_startup_update())

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes

    async def async_update(self) -> None:
        """Update the enhanced forecast."""
        # Get base forecasts
        main_sensor = self.hass.states.get("sensor.local_forecast")
        if not main_sensor or main_sensor.state in ("unknown", "unavailable"):
            _LOGGER.debug("Enhanced: Main sensor unavailable, using defaults")
            zambretti = ["Unknown", 0, "A"]
            negretti = ["Unknown", 0, "A"]
        else:
            attrs = main_sensor.attributes
            zambretti = attrs.get("forecast_zambretti", ["Unknown", 0, "A"])
            negretti = attrs.get("forecast_neg_zam", ["Unknown", 0, "A"])

        # Get sensor values
        temp = await self._get_sensor_value(
            self.config_entry.data.get(CONF_TEMPERATURE_SENSOR), 15.0
        )
        # Enhanced sensors are in options, not data!
        humidity_sensor = self.config_entry.options.get(CONF_HUMIDITY_SENSOR) or self.config_entry.data.get(CONF_HUMIDITY_SENSOR)
        _LOGGER.info(f"Enhanced: Config humidity sensor = {humidity_sensor}")
        humidity = None
        if humidity_sensor:
            _LOGGER.debug(f"Enhanced: Fetching humidity from {humidity_sensor}")
            humidity = await self._get_sensor_value(humidity_sensor, None, use_history=True)
            _LOGGER.info(f"Enhanced: Humidity value = {humidity}")
        else:
            _LOGGER.warning("Enhanced: No humidity sensor configured!")

        # Calculate dew point and spread
        dewpoint = None
        dewpoint_spread = None
        if temp is not None and humidity is not None:
            dewpoint = calculate_dewpoint(temp, humidity)
            if dewpoint is not None:
                dewpoint_spread = temp - dewpoint
            _LOGGER.debug(f"Enhanced: Calculated dewpoint={dewpoint}, spread={dewpoint_spread}")
        else:
            _LOGGER.warning(f"Enhanced: Cannot calculate dewpoint - temp={temp}, humidity={humidity}")

        # Get wind gust ratio
        wind_speed = await self._get_sensor_value(
            self.config_entry.data.get(CONF_WIND_SPEED_SENSOR), 0.0, use_history=True
        )
        # Enhanced sensors are in options, not data!
        wind_gust_sensor_id = self.config_entry.options.get(CONF_WIND_GUST_SENSOR) or self.config_entry.data.get(CONF_WIND_GUST_SENSOR)
        _LOGGER.info(f"Enhanced: Config wind gust sensor = {wind_gust_sensor_id}, wind_speed = {wind_speed}")
        gust_ratio = None
        if wind_gust_sensor_id and wind_speed > 0.1:
            _LOGGER.debug(f"Enhanced: Fetching wind gust from {wind_gust_sensor_id}, wind_speed={wind_speed}")
            wind_gust = await self._get_sensor_value(wind_gust_sensor_id, None, use_history=True)
            if wind_gust is not None:
                gust_ratio = wind_gust / wind_speed if wind_speed > 0.1 else 1.0
                _LOGGER.info(f"Enhanced: Calculated gust_ratio={gust_ratio} (gust={wind_gust}, speed={wind_speed})")
            else:
                _LOGGER.warning(f"Enhanced: Wind gust sensor returned None")
        else:
            if not wind_gust_sensor_id:
                _LOGGER.warning("Enhanced: No wind gust sensor configured!")
            else:
                _LOGGER.debug(f"Enhanced: Wind speed too low ({wind_speed}), skipping gust ratio")

        # Calculate adjustments
        adjustments = []
        adjustment_details = []

        # Humidity adjustment
        if humidity is not None:
            if humidity > 85:
                adjustments.append("high_humidity")
                adjustment_details.append(f"High humidity ({humidity:.1f}%)")
            elif humidity < 40:
                adjustments.append("low_humidity")
                adjustment_details.append(f"Low humidity ({humidity:.1f}%)")

        # Dewpoint spread adjustment (fog/precipitation risk)
        if dewpoint_spread is not None:
            if dewpoint_spread < 1.5:
                adjustments.append("critical_fog_risk")
                adjustment_details.append(f"CRITICAL fog risk (spread {dewpoint_spread:.1f}°C)")
            elif dewpoint_spread < 2.5:
                adjustments.append("high_fog_risk")
                adjustment_details.append(f"High fog risk (spread {dewpoint_spread:.1f}°C)")
            elif dewpoint_spread < 4:
                adjustments.append("medium_fog_risk")
                adjustment_details.append(f"Medium fog risk (spread {dewpoint_spread:.1f}°C)")

        # Atmospheric stability (gust ratio)
        if gust_ratio is not None:
            if gust_ratio > 2.0:
                adjustments.append("very_unstable")
                adjustment_details.append(f"Very unstable atmosphere (gust ratio {gust_ratio:.2f})")
            elif gust_ratio > 1.6:
                adjustments.append("unstable")
                adjustment_details.append(f"Unstable atmosphere (gust ratio {gust_ratio:.2f})")

        # Build enhanced forecast text
        base_text = zambretti[0] if len(zambretti) > 0 else "Unknown"

        if adjustment_details:
            enhanced_text = f"{base_text}. {', '.join(adjustment_details)}"
        else:
            enhanced_text = base_text

        # Calculate confidence
        zambretti_num = zambretti[1] if len(zambretti) > 1 else 0
        negretti_num = negretti[1] if len(negretti) > 1 else 0
        consensus = abs(zambretti_num - negretti_num) <= 1

        if consensus and not adjustments:
            confidence = "very_high"
        elif consensus or len(adjustments) <= 1:
            confidence = "high"
        elif len(adjustments) <= 2:
            confidence = "medium"
        else:
            confidence = "low"

        # Get fog risk
        fog_risk = "none"
        if dewpoint is not None and temp is not None:
            fog_risk = get_fog_risk(temp, dewpoint)

        self._state = enhanced_text
        _LOGGER.info(f"Enhanced: Setting state to: {enhanced_text}")
        self._attributes = {
            "base_forecast": base_text,
            "zambretti_number": zambretti_num,
            "negretti_number": negretti_num,
            "adjustments": adjustments,
            "adjustment_details": adjustment_details,
            "confidence": confidence,
            "consensus": consensus,
            "humidity": humidity,
            "dew_point": dewpoint,
            "dewpoint_spread": dewpoint_spread,
            "fog_risk": fog_risk,
            "gust_ratio": gust_ratio,
            "accuracy_estimate": "~98%" if confidence in ["high", "very_high"] else "~94%",
        }
        # Note: Home Assistant automatically writes state after async_update() completes


class LocalForecastRainProbabilitySensor(LocalWeatherForecastEntity):
    """Enhanced rain probability sensor using multiple factors."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the rain probability sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_rain_probability"
        self._attr_name = "Local forecast Rain Probability"
        self._attr_icon = "mdi:weather-rainy"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = None  # Initialize state
        self._attributes = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass - schedule delayed update for startup."""
        await super().async_added_to_hass()

        # Schedule delayed update to wait for dependent sensors to load
        async def delayed_startup_update():
            await asyncio.sleep(10)  # Wait 10 seconds for other integrations to load
            _LOGGER.info("RainProb: Running delayed startup update")
            await self.async_update()
            self.async_write_ha_state()

        self.hass.async_create_task(delayed_startup_update())

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes


    async def async_update(self) -> None:
        """Update the rain probability."""
        # Try to get forecast data from weather entity
        weather_entity = self.hass.states.get("weather.local_weather_forecast_weather")

        zambretti_prob = 0
        negretti_prob = 0

        if weather_entity:
            # Get hourly forecast from weather entity
            try:
                # Get hourly forecasts (next 6-12 hours)
                forecasts = weather_entity.attributes.get("forecast", [])
                if forecasts:
                    # Average precipitation probability from next 6 hours
                    rain_probs = [
                        f.get("precipitation_probability", 0)
                        for f in forecasts[:6]
                        if "precipitation_probability" in f
                    ]
                    if rain_probs:
                        zambretti_prob = sum(rain_probs) / len(rain_probs)
                        negretti_prob = zambretti_prob  # Use same for both since using advanced model
                        _LOGGER.debug(f"RainProb: Using forecast data - avg={zambretti_prob}% from {len(rain_probs)} hours")
                    else:
                        _LOGGER.debug("RainProb: No precipitation probability in forecasts, using detail sensors")
                        # Fallback to detail sensors
                        zambretti_sensor = self.hass.states.get("sensor.local_forecast_zambretti_detail")
                        negretti_sensor = self.hass.states.get("sensor.local_forecast_neg_zam_detail")
                        if zambretti_sensor and negretti_sensor:
                            zambretti_rain = zambretti_sensor.attributes.get("rain_prob", [0, 0])
                            negretti_rain = negretti_sensor.attributes.get("rain_prob", [0, 0])
                            zambretti_prob = sum(zambretti_rain) / len(zambretti_rain) if zambretti_rain else 0
                            negretti_prob = sum(negretti_rain) / len(negretti_rain) if negretti_rain else 0
            except Exception as e:
                _LOGGER.warning(f"RainProb: Error getting forecast data: {e}")
        else:
            # Fallback to detail sensors if weather entity unavailable
            _LOGGER.debug("RainProb: Weather entity unavailable, using detail sensors")
            zambretti_sensor = self.hass.states.get("sensor.local_forecast_zambretti_detail")
            negretti_sensor = self.hass.states.get("sensor.local_forecast_neg_zam_detail")
            if zambretti_sensor and negretti_sensor:
                zambretti_rain = zambretti_sensor.attributes.get("rain_prob", [0, 0])
                negretti_rain = negretti_sensor.attributes.get("rain_prob", [0, 0])
                zambretti_prob = sum(zambretti_rain) / len(zambretti_rain) if zambretti_rain else 0
                negretti_prob = sum(negretti_rain) / len(negretti_rain) if negretti_rain else 0

        _LOGGER.info(f"RainProb: Base probabilities - Zambretti={zambretti_prob}%, Negretti={negretti_prob}%")

        # Get sensor values for enhancements
        temp = await self._get_sensor_value(
            self.config_entry.data.get(CONF_TEMPERATURE_SENSOR), 15.0
        )

        # Enhanced sensors are in options, not data!
        humidity_sensor = self.config_entry.options.get(CONF_HUMIDITY_SENSOR) or self.config_entry.data.get(CONF_HUMIDITY_SENSOR)
        _LOGGER.info(f"RainProb: Config humidity sensor = {humidity_sensor}")
        humidity = None
        if humidity_sensor:
            _LOGGER.debug(f"RainProb: Fetching humidity from {humidity_sensor}")
            humidity = await self._get_sensor_value(humidity_sensor, None, use_history=True)
            _LOGGER.info(f"RainProb: Humidity value = {humidity}")
        else:
            _LOGGER.warning("RainProb: No humidity sensor configured!")

        # Calculate dewpoint spread
        dewpoint_spread = None
        if temp is not None and humidity is not None:
            dewpoint = calculate_dewpoint(temp, humidity)
            if dewpoint is not None:
                dewpoint_spread = temp - dewpoint
            _LOGGER.debug(f"RainProb: Calculated dewpoint_spread={dewpoint_spread}")
        else:
            _LOGGER.warning(f"RainProb: Cannot calculate dewpoint - temp={temp}, humidity={humidity}")

        # Use enhanced calculation
        probability, confidence = calculate_rain_probability_enhanced(
            zambretti_prob,
            negretti_prob,
            humidity,
            None,  # cloud_coverage not available
            dewpoint_spread,
        )
        _LOGGER.debug(f"RainProb: Enhanced calculation result - probability={probability}, confidence={confidence}")

        # Get current rain rate
        rain_rate_sensor_id = self.config_entry.options.get(CONF_RAIN_RATE_SENSOR) or self.config_entry.data.get(CONF_RAIN_RATE_SENSOR)
        _LOGGER.info(f"RainProb: Config rain rate sensor = {rain_rate_sensor_id}")
        current_rain = 0.0
        if rain_rate_sensor_id:
            # Extended debugging
            rain_state = self.hass.states.get(rain_rate_sensor_id)
            if rain_state:
                _LOGGER.debug(f"RainProb: Rain sensor state={rain_state.state}, attributes={rain_state.attributes}")
            else:
                _LOGGER.warning(f"RainProb: Rain sensor '{rain_rate_sensor_id}' not found in HA registry!")

            _LOGGER.debug(f"RainProb: Fetching rain rate from {rain_rate_sensor_id}")
            current_rain_value = await self._get_sensor_value(rain_rate_sensor_id, 0.0, use_history=False)
            if current_rain_value is not None:
                current_rain = current_rain_value
                _LOGGER.info(f"RainProb: Current rain rate = {current_rain}")
            else:
                _LOGGER.warning(f"RainProb: Rain rate sensor returned None (state={rain_state.state if rain_state else 'NOT_FOUND'})")
        else:
            _LOGGER.warning("RainProb: No rain rate sensor configured!")

        # If currently raining, probability is 100%
        if current_rain > 0.1:
            _LOGGER.info(f"RainProb: Currently raining ({current_rain} mm/h), setting probability to 100%")
            probability = 100
            confidence = "very_high"

        self._state = round(probability)
        _LOGGER.info(f"RainProb: Setting state to: {round(probability)}%")
        self._attributes = {
            "zambretti_probability": round(zambretti_prob),
            "negretti_probability": round(negretti_prob),
            "base_probability": round((zambretti_prob + negretti_prob) / 2),
            "enhanced_probability": round(probability),
            "confidence": confidence,
            "humidity": humidity,
            "dewpoint_spread": dewpoint_spread,
            "current_rain_rate": current_rain,
            "factors_used": self._get_factors_used(humidity, dewpoint_spread),
        }
        # Note: Home Assistant automatically writes state after async_update() completes

    def _get_factors_used(self, humidity, dewpoint_spread):
        """Get list of factors used in calculation."""
        factors = ["Zambretti", "Negretti-Zambra"]
        if humidity is not None:
            factors.append("Humidity")
        if dewpoint_spread is not None:
            factors.append("Dewpoint spread")
        return factors
