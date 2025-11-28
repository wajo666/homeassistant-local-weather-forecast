"""Sensor platform for Local Weather Forecast integration."""
from __future__ import annotations

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
    ]

    async_add_entities(entities, True)


class LocalWeatherForecastEntity(RestoreEntity, SensorEntity):
    """Base class for Local Weather Forecast entities."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.config_entry = config_entry
        self._attr_has_entity_name = True
        self._attr_should_poll = False

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "Local Weather Forecast",
            "manufacturer": "Local Weather Forecast",
            "model": "Zambretti Forecaster",
            "sw_version": "2.0.0",
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
            _LOGGER.warning(
                f"Could not convert {sensor_id} state '{state.state}' to float"
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
        self._attr_unique_id = f"{config_entry.entry_id}_main"
        self._attr_name = "Local Forecast"
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
            f"sensor.{self.config_entry.entry_id}_pressure_change",
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
        titles = [
            "Lokale Wettervorhersage",
            "12hr Local Weather Forecast",
            "Τοπική πρόγνωση καιρού",
            "Previsione meteorologica locale",
        ]
        self._state = titles[lang_index]

        # Convert forecast lists to strings for easier parsing by detail sensors
        zambretti_str = ", ".join(str(x) for x in zambretti_forecast) if isinstance(zambretti_forecast, list) else str(zambretti_forecast)
        neg_zam_str = ", ".join(str(x) for x in neg_zam_forecast) if isinstance(neg_zam_forecast, list) else str(neg_zam_forecast)
        current_condition_str = ", ".join(str(x) for x in current_condition) if isinstance(current_condition, list) else str(current_condition)
        pressure_trend_str = ", ".join(str(x) for x in pressure_trend) if isinstance(pressure_trend, list) else str(pressure_trend)

        self._attributes = {
            "language": lang_index,
            "temperature": round(temperature, 1),
            "p0": round(p0, 1),
            "wind_direction": wind_data,
            "forecast_short_term": current_condition_str,
            "forecast_zambretti": zambretti_str,
            "forecast_neg_zam": neg_zam_str,
            "forecast_pressure_trend": pressure_trend_str,
        }

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
        trend_texts = [
            ("fallend", "Falling", "πέφτοντας", "In diminuzione"),
            ("steigend", "Rising", "αυξανόμενη", "In aumento"),
            ("stabil", "Steady", "σταθερή", "Stabile"),
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
        self._attr_unique_id = f"{config_entry.entry_id}_pressure"
        self._attr_name = "Pressure"
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
                ["sensor.local_weather_forecast_local_forecast"],
                self._handle_main_update,
            )
        )

        # Initial update
        await self._update_from_main()

    async def _update_from_main(self):
        """Update from main sensor."""
        main_sensor = self.hass.states.get("sensor.local_weather_forecast_local_forecast")
        if main_sensor and main_sensor.state != "unknown":
            p0 = main_sensor.attributes.get("p0")
            if p0 is not None:
                self._state = float(p0)

    @callback
    async def _handle_main_update(self, event):
        """Handle main sensor updates."""
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
        self._attr_unique_id = f"{config_entry.entry_id}_temperature"
        self._attr_name = "Temperature"
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
                ["sensor.local_weather_forecast_local_forecast"],
                self._handle_main_update,
            )
        )

        # Initial update
        await self._update_from_main()

    async def _update_from_main(self):
        """Update from main sensor."""
        main_sensor = self.hass.states.get("sensor.local_weather_forecast_local_forecast")
        if main_sensor and main_sensor.state != "unknown":
            temp = main_sensor.attributes.get("temperature")
            if temp is not None:
                self._state = float(temp)

    @callback
    async def _handle_main_update(self, event):
        """Handle main sensor updates."""
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
        self._attr_unique_id = f"{config_entry.entry_id}_pressure_change"
        self._attr_name = "Pressure Change"
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
                ["sensor.local_weather_forecast_pressure"],
                self._handle_pressure_update,
            )
        )

        # Add initial pressure value to history
        pressure_sensor = self.hass.states.get("sensor.local_weather_forecast_pressure")
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
        self._attr_unique_id = f"{config_entry.entry_id}_temperature_change"
        self._attr_name = "Temperature Change"
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
                ["sensor.local_weather_forecast_temperature"],
                self._handle_temperature_update,
            )
        )

        # Add initial temperature value to history
        temp_sensor = self.hass.states.get("sensor.local_weather_forecast_temperature")
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
        self._attr_unique_id = f"{config_entry.entry_id}_zambretti_detail"
        self._attr_name = "Zambretti Detail"
        self._attr_icon = "mdi:weather-cloudy-arrow-right"
        self._state = None
        self._attributes = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Track main sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                ["sensor.local_weather_forecast_local_forecast"],
                self._handle_main_update,
            )
        )

        # Initial update
        await self._update_from_main()

    async def _update_from_main(self):
        """Update from main sensor."""
        main_sensor = self.hass.states.get("sensor.local_weather_forecast_local_forecast")
        if not main_sensor or main_sensor.state in ("unknown", "unavailable"):
            return

        attrs = main_sensor.attributes

        # Parse Zambretti forecast - can be list ['Fine', 1, 'B'] or string "Fine, 1, B"
        zambretti = attrs.get("forecast_zambretti")
        if not zambretti:
            return

        # Handle both list and string formats
        if isinstance(zambretti, list):
            forecast_text = str(zambretti[0]) if len(zambretti) > 0 else ""
            forecast_num = int(zambretti[1]) if len(zambretti) > 1 else 0
            letter_code = str(zambretti[2]) if len(zambretti) > 2 else ""
        elif isinstance(zambretti, str) and ", " in zambretti:
            parts = zambretti.split(", ")
            forecast_text = parts[0] if len(parts) > 0 else ""
            try:
                forecast_num = int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                forecast_num = 0
            letter_code = parts[2] if len(parts) > 2 else ""
        else:
            # Fallback
            self._state = str(zambretti)
            self._attributes = {}
            return

        # Map to icon
        icon_6h = self._get_icon_for_forecast(forecast_num)
        icon_12h = icon_6h

        # Estimate rain probability
        rain_6h, rain_12h = self._estimate_rain_probability(forecast_num)

        # Set state and attributes
        self._state = forecast_text
        self._attributes = {
            "forecast_text": forecast_text,
            "forecast_number": forecast_num,
            "letter_code": letter_code,
            "icons": f"{icon_6h}, {icon_12h}",
            "rain_prob": f"{rain_6h}, {rain_12h}",
            "first_time": "6",
            "second_time": "12",
        }

    @callback
    async def _handle_main_update(self, event):
        """Handle main sensor updates."""
        await self._update_from_main()
        self.async_write_ha_state()

    def _get_icon_for_forecast(self, forecast_num: int) -> str:
        """Map forecast number to icon."""
        # Based on forecast_data.py CONDITIONS mapping
        icon_map = {
            0: "mdi:weather-sunny",           # Settled fine
            1: "mdi:weather-sunny",           # Fine weather
            2: "mdi:weather-partly-cloudy",   # Becoming fine
            3: "mdi:weather-partly-cloudy",   # Fine, becoming less settled
            4: "mdi:weather-partly-cloudy",   # Fine, possible showers
            5: "mdi:weather-cloudy",          # Fairly fine, improving
            6: "mdi:weather-cloudy",          # Fairly fine, possible showers early
            7: "mdi:weather-partly-rainy",    # Fairly fine, showery later
            8: "mdi:weather-rainy",           # Showery early, improving
            9: "mdi:weather-rainy",           # Changeable, mending
            10: "mdi:weather-cloudy",         # Fairly fine, showers likely
            11: "mdi:weather-rainy",          # Rather unsettled, clearing later
            12: "mdi:weather-rainy",          # Unsettled, probably improving
            13: "mdi:weather-rainy",          # Showery, bright intervals
            14: "mdi:weather-rainy",          # Showery, becoming more unsettled
            15: "mdi:weather-pouring",        # Changeable, some rain
            16: "mdi:weather-pouring",        # Unsettled, short fine intervals
            17: "mdi:weather-pouring",        # Unsettled, rain later
            18: "mdi:weather-pouring",        # Unsettled, rain at times
            19: "mdi:weather-lightning-rainy",# Very unsettled, finer at times
            20: "mdi:weather-lightning-rainy",# Stormy, possibly improving
            21: "mdi:weather-lightning-rainy",# Stormy, much rain
        }
        return icon_map.get(forecast_num, "mdi:weather-cloudy")

    def _estimate_rain_probability(self, forecast_num: int) -> tuple[int, int]:
        """Estimate rain probability for 6h and 12h based on forecast number."""
        # Map forecast number to rain probability
        rain_map = {
            0: (5, 10),    # Settled fine
            1: (10, 15),   # Fine weather
            2: (15, 20),   # Becoming fine
            3: (20, 30),   # Fine, becoming less settled
            4: (30, 40),   # Fine, possible showers
            5: (25, 35),   # Fairly fine, improving
            6: (30, 40),   # Fairly fine, possible showers early
            7: (40, 50),   # Fairly fine, showery later
            8: (45, 35),   # Showery early, improving
            9: (40, 30),   # Changeable, mending
            10: (50, 60),  # Fairly fine, showers likely
            11: (55, 45),  # Rather unsettled, clearing later
            12: (50, 40),  # Unsettled, probably improving
            13: (60, 60),  # Showery, bright intervals
            14: (65, 70),  # Showery, becoming more unsettled
            15: (70, 75),  # Changeable, some rain
            16: (75, 70),  # Unsettled, short fine intervals
            17: (70, 80),  # Unsettled, rain later
            18: (80, 80),  # Unsettled, rain at times
            19: (85, 75),  # Very unsettled, finer at times
            20: (80, 70),  # Stormy, possibly improving
            21: (90, 95),  # Stormy, much rain
        }
        return rain_map.get(forecast_num, (50, 50))

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
        self._attr_unique_id = f"{config_entry.entry_id}_neg_zam_detail"
        self._attr_name = "Negretti Zambra Detail"
        self._attr_icon = "mdi:weather-cloudy-clock"
        self._state = None
        self._attributes = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in ("unknown", "unavailable"):
                self._state = last_state.state
                self._attributes = dict(last_state.attributes)

        # Track main sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                ["sensor.local_weather_forecast_local_forecast"],
                self._handle_main_update,
            )
        )

        # Initial update - always update from main sensor
        await self._update_from_main()
        # Write state immediately
        self.async_write_ha_state()

    async def _update_from_main(self):
        """Update from main sensor."""
        main_sensor = self.hass.states.get("sensor.local_weather_forecast_local_forecast")
        if not main_sensor or main_sensor.state in ("unknown", "unavailable"):
            return

        attrs = main_sensor.attributes

        # Parse Negretti-Zambra forecast - can be list or string
        neg_zam = attrs.get("forecast_neg_zam")
        if not neg_zam:
            return

        # Handle both list and string formats
        if isinstance(neg_zam, list):
            forecast_text = str(neg_zam[0]) if len(neg_zam) > 0 else ""
            forecast_num = int(neg_zam[1]) if len(neg_zam) > 1 else 0
            letter_code = str(neg_zam[2]) if len(neg_zam) > 2 else ""
        elif isinstance(neg_zam, str) and ", " in neg_zam:
            parts = neg_zam.split(", ")
            forecast_text = parts[0] if len(parts) > 0 else ""
            try:
                forecast_num = int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                forecast_num = 0
            letter_code = parts[2] if len(parts) > 2 else ""
        else:
            # Fallback
            self._state = str(neg_zam)
            self._attributes = {}
            return

        # Map to icon
        icon_6h = self._get_icon_for_forecast(forecast_num)
        icon_12h = icon_6h

        # Estimate rain probability
        rain_6h, rain_12h = self._estimate_rain_probability(forecast_num)

        # Set state and attributes
        self._state = forecast_text
        self._attributes = {
            "forecast_text": forecast_text,
            "forecast_number": forecast_num,
            "letter_code": letter_code,
            "icons": f"{icon_6h}, {icon_12h}",
            "rain_prob": f"{rain_6h}, {rain_12h}",
            "first_time": "6",
            "second_time": "12",
        }

    @callback
    async def _handle_main_update(self, event):
        """Handle main sensor updates."""
        await self._update_from_main()
        self.async_write_ha_state()

    def _get_icon_for_forecast(self, forecast_num: int) -> str:
        """Map forecast number to icon."""
        icon_map = {
            0: "mdi:weather-sunny",
            1: "mdi:weather-sunny",
            2: "mdi:weather-partly-cloudy",
            3: "mdi:weather-partly-cloudy",
            4: "mdi:weather-partly-cloudy",
            5: "mdi:weather-cloudy",
            6: "mdi:weather-cloudy",
            7: "mdi:weather-partly-rainy",
            8: "mdi:weather-rainy",
            9: "mdi:weather-rainy",
            10: "mdi:weather-cloudy",
            11: "mdi:weather-rainy",
            12: "mdi:weather-rainy",
            13: "mdi:weather-rainy",
            14: "mdi:weather-rainy",
            15: "mdi:weather-pouring",
            16: "mdi:weather-pouring",
            17: "mdi:weather-pouring",
            18: "mdi:weather-pouring",
            19: "mdi:weather-lightning-rainy",
            20: "mdi:weather-lightning-rainy",
            21: "mdi:weather-lightning-rainy",
        }
        return icon_map.get(forecast_num, "mdi:weather-cloudy")

    def _estimate_rain_probability(self, forecast_num: int) -> tuple[int, int]:
        """Estimate rain probability."""
        rain_map = {
            0: (5, 10), 1: (10, 15), 2: (15, 20), 3: (20, 30), 4: (30, 40),
            5: (25, 35), 6: (30, 40), 7: (40, 50), 8: (45, 35), 9: (40, 30),
            10: (50, 60), 11: (55, 45), 12: (50, 40), 13: (60, 60), 14: (65, 70),
            15: (70, 75), 16: (75, 70), 17: (70, 80), 18: (80, 80), 19: (85, 75),
            20: (80, 70), 21: (90, 95),
        }
        return rain_map.get(forecast_num, (50, 50))

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes

