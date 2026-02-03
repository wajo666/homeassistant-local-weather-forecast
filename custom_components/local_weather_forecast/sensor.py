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
    UnitOfPressure,
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
    CONF_HEMISPHERE,
    CONF_HUMIDITY_SENSOR,
    CONF_PRESSURE_TYPE,
    CONF_PRESSURE_SENSOR,
    CONF_RAIN_RATE_SENSOR,
    CONF_SOLAR_RADIATION_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    DEFAULT_ELEVATION,
    DEFAULT_HEMISPHERE,
    DEFAULT_PRESSURE_TYPE,
    DOMAIN,
    GRAVITY_CONSTANT,
    KELVIN_OFFSET,
    LAPSE_RATE,
    PRESSURE_TREND_FALLING,
    PRESSURE_TREND_RISING,
    PRESSURE_TYPE_RELATIVE,
    PRESSURE_MIN_RECORDS,
    TEMPERATURE_MIN_RECORDS,
)
from .forecast_data import PRESSURE_SYSTEMS, CONDITIONS
from .zambretti import calculate_zambretti_forecast
from .negretti_zambra import calculate_negretti_zambra_forecast
from .calculations import (
    calculate_dewpoint,
    calculate_rain_probability_enhanced,
    get_fog_risk,
    get_snow_risk,
    get_frost_risk,
)
from .language import (
    get_language_index,
    get_wind_type,
    get_adjustment_text,
    get_atmosphere_stability_text,
    get_fog_risk_text,
    get_snow_risk_text,
    get_frost_risk_text,
)
from .unit_conversion import UnitConverter

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
            "sw_version": "3.1.14",
        }

    async def _wait_for_entity(
        self,
        entity_id: str,
        timeout: int = 30,
        retry_interval: float = 1.0
    ) -> bool:
        """
        Wait for an entity to become available.

        Args:
            entity_id: Entity ID to wait for
            timeout: Maximum seconds to wait
            retry_interval: Seconds between checks

        Returns:
            True if entity became available, False if timeout
        """
        if not entity_id:
            return False

        elapsed = 0
        while elapsed < timeout:
            state = self.hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                _LOGGER.debug(f"Entity {entity_id} is now available (waited {elapsed}s)")
                return True

            await asyncio.sleep(retry_interval)
            elapsed += retry_interval

        _LOGGER.debug(f"Entity {entity_id} did not become available after {timeout}s")
        return False

    async def _get_sensor_value(
        self,
        sensor_id: str,
        default: float | None = 0.0,
        use_history: bool = True,
        sensor_type: str | None = None
    ) -> float | None:
        """Get sensor value with automatic unit conversion and fallback to history if unavailable.

        Args:
            sensor_id: Entity ID of the sensor
            default: Default value if sensor unavailable
            use_history: Whether to use historical data as fallback
            sensor_type: Type for unit conversion (pressure, temperature, wind_speed, humidity)

        Returns:
            Sensor value converted to required unit
        """
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
            value = float(state.state)

            # Apply unit conversion if sensor type specified
            if sensor_type:
                unit = state.attributes.get("unit_of_measurement")
                if unit:
                    converted_value = UnitConverter.convert_sensor_value(value, sensor_type, unit)
                    if converted_value != value:
                        _LOGGER.debug(
                            f"Converted {sensor_id}: {value} {unit} → {converted_value:.2f} "
                            f"{UnitConverter.REQUIRED_UNITS.get(sensor_type, '')}"
                        )
                    return converted_value

            return value

        except (ValueError, TypeError):
            # Check if this is an optional sensor (wind direction/speed)
            sensor_label = "sensor"
            if "wind" in sensor_id.lower():
                sensor_label = "optional wind sensor"
            _LOGGER.debug(
                f"Could not convert {sensor_label} {sensor_id} state '{state.state}' to float, using default {default}"
            )
            if use_history:
                return await self._get_historical_value(sensor_id, default)
            return default

    async def _get_historical_value(
        self,
        sensor_id: str,
        default: float | None = 0.0
    ) -> float | None:
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
                                    value = float(str(state.state))
                                    _LOGGER.debug(
                                        f"Retrieved historical value {value} for {sensor_id}"
                                    )
                                    return value
                                except (ValueError, TypeError):
                                    continue

            _LOGGER.debug(
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
        self.async_write_ha_state()

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

        # Get language index from centralized helper
        lang_index = get_language_index(self.hass)

        # Get sensor values with automatic unit conversion
        pressure = await self._get_sensor_value(
            config.get(CONF_PRESSURE_SENSOR) or "", default=1013.25, sensor_type="pressure"
        )
        temperature = await self._get_sensor_value(
            config.get(CONF_TEMPERATURE_SENSOR) or "", default=15.0, sensor_type="temperature"
        )
        wind_direction = await self._get_sensor_value(
            config.get(CONF_WIND_DIRECTION_SENSOR) or "", default=0.0
        )
        wind_speed = await self._get_sensor_value(
            config.get(CONF_WIND_SPEED_SENSOR) or "", default=0.0, sensor_type="wind_speed"
        )

        elevation = config.get(CONF_ELEVATION, DEFAULT_ELEVATION)
        pressure_type = config.get(CONF_PRESSURE_TYPE, DEFAULT_PRESSURE_TYPE)

        # Calculate sea level pressure based on pressure type
        if pressure_type == PRESSURE_TYPE_RELATIVE:
            # Sensor already provides sea level pressure (QNH)
            p0 = pressure
        else:
            # Sensor provides station pressure (QFE) - need to convert
            p0 = self._calculate_sea_level_pressure(pressure or 1013.25, temperature or 15.0, elevation)

        # Calculate wind factors
        wind_data = self._calculate_wind_data(wind_direction or 0.0, wind_speed or 0.0)

        # Get pressure change from statistics sensor
        pressure_change = await self._get_sensor_value(
            "sensor.local_forecast_pressurechange",  # Match original YAML entity_id
            default=0.0,
            use_history=False
        )

        # Calculate current conditions based on pressure
        # This is kept in sensor for reference/debugging, but NOT used in weather.py priority chain
        current_condition = self._get_current_condition(p0 or 1013.25, lang_index)

        # Calculate Zambretti forecast
        zambretti_forecast = calculate_zambretti_forecast(
            p0 or 1013.25, pressure_change or 0.0, wind_data, lang_index
        )

        # Calculate Negretti & Zambra forecast
        hemisphere = self.config_entry.data.get(CONF_HEMISPHERE, DEFAULT_HEMISPHERE)
        neg_zam_forecast = calculate_negretti_zambra_forecast(
            p0 or 1013.25, pressure_change or 0.0, wind_data, lang_index, elevation, hemisphere
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
        temp_short = await self._calculate_temp_short_forecast(temperature)

        # Keep original list/array formats for full compatibility with original YAML code
        self._attributes = {
            "language": lang_index,
            "temperature": round(temperature, 1) if temperature is not None else None,
            "p0": round(p0, 1) if p0 is not None else 1013.2,
            "wind_direction": wind_data,  # List: [wind_fak, dir, dir_text, speed_fak]
            "forecast_short_term": current_condition,  # List: [condition, pressure_system] - kept for reference, not used in weather.py
            "forecast_zambretti": zambretti_forecast,  # ✅ SIMPLIFIED: [text, code]
            "forecast_neg_zam": neg_zam_forecast,  # ✅ SIMPLIFIED: [text, code]
            "forecast_pressure_trend": pressure_trend,  # List: [text, index]
            "forecast_temp_short": temp_short,  # List: [predicted_temp, interval_index] or string if unavailable
        }

    async def _calculate_temp_short_forecast(self, current_temp: float) -> list | str:
        """Calculate short-term temperature forecast using advanced TemperatureModel.

        Combines:
        - Temperature trend (from sensor.local_forecast_temperaturechange)
        - Diurnal cycle (solar position based on sun.sun entity)
        - Solar radiation warming (if sensor configured)
        - Cloud cover reduction (if sensor configured or estimated from humidity)
        - Hemisphere and seasonal adjustments

        Returns: [predicted_temp, interval_index] where interval: 0=first_time, 1=second_time, -1=unavailable
        """
        # Get temperature change sensor
        temp_change_sensor = self.hass.states.get("sensor.local_forecast_temperaturechange")
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
        zambretti_detail = self.hass.states.get("sensor.local_forecast_zambretti_detail")
        if not zambretti_detail or zambretti_detail.state in ("unknown", "unavailable"):
            _LOGGER.debug(
                f"Zambretti detail sensor not available: {zambretti_detail.state if zambretti_detail else 'not found'}"
            )
            return ["unavailable", -1]

        attrs = zambretti_detail.attributes
        _LOGGER.debug(f"Zambretti detail attributes: {attrs}")

        # Get optional sensors for enhanced temperature modeling
        config = self.config_entry

        # Solar radiation (if configured)
        solar_radiation = None
        solar_sensor_id = config.options.get(CONF_SOLAR_RADIATION_SENSOR) or config.data.get(CONF_SOLAR_RADIATION_SENSOR)
        if solar_sensor_id:
            solar_radiation = await self._get_sensor_value(
                solar_sensor_id, None, use_history=False, sensor_type="solar_radiation"
            )

        # Humidity (for cloud cover estimation if no direct sensor)
        humidity = None
        humidity_sensor_id = config.options.get(CONF_HUMIDITY_SENSOR) or config.data.get(CONF_HUMIDITY_SENSOR)
        if humidity_sensor_id:
            humidity = await self._get_sensor_value(
                humidity_sensor_id, None, use_history=False, sensor_type="humidity"
            )

        # Wind speed (affects nighttime radiative cooling)
        wind_speed = None
        wind_sensor_id = config.options.get(CONF_WIND_SPEED_SENSOR) or config.data.get(CONF_WIND_SPEED_SENSOR)
        if wind_sensor_id:
            wind_speed = await self._get_sensor_value(
                wind_sensor_id, None, use_history=False, sensor_type="wind_speed"
            )

        # Get location and hemisphere
        elevation = config.data.get(CONF_ELEVATION, DEFAULT_ELEVATION)
        hemisphere = config.data.get(CONF_HEMISPHERE, DEFAULT_HEMISPHERE)
        latitude = self.hass.config.latitude
        longitude = self.hass.config.longitude

        # Import TemperatureModel
        from .forecast_calculator import TemperatureModel

        # Create temperature model with all available data
        temp_model = TemperatureModel(
            current_temp=current_temp,
            change_rate_1h=temp_change,
            solar_radiation=solar_radiation,
            humidity=humidity,
            wind_speed=wind_speed,
            hass=self.hass,
            latitude=latitude,
            longitude=longitude,
            hemisphere=hemisphere,
            elevation=elevation
        )

        # Try to get first_time
        first_time = attrs.get("first_time")
        if first_time and isinstance(first_time, list) and len(first_time) > 1:
            try:
                minutes_to_first = float(first_time[1])
                _LOGGER.debug(f"first_time minutes: {minutes_to_first}")

                if minutes_to_first > 0:
                    # Use advanced model to predict temperature
                    hours_to_first = minutes_to_first / 60.0
                    predicted_temp = temp_model.predict(int(round(hours_to_first)))
                    _LOGGER.debug(
                        f"Advanced temp forecast using first_time: {predicted_temp:.1f}°C "
                        f"(current: {current_temp:.1f}, hours: {hours_to_first:.1f}, "
                        f"solar: {solar_radiation if solar_radiation else 'N/A'} W/m², "
                        f"humidity: {humidity if humidity else 'N/A'}%)"
                    )
                    return [round(predicted_temp, 1), 0]
                else:
                    _LOGGER.debug(
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
                    # Use advanced model to predict temperature
                    hours_to_second = minutes_to_second / 60.0
                    predicted_temp = temp_model.predict(int(round(hours_to_second)))
                    _LOGGER.debug(
                        f"Advanced temp forecast using second_time: {predicted_temp:.1f}°C "
                        f"(current: {current_temp:.1f}, hours: {hours_to_second:.1f}, "
                        f"solar: {solar_radiation if solar_radiation else 'N/A'} W/m², "
                        f"humidity: {humidity if humidity else 'N/A'}%)"
                    )
                    return [round(predicted_temp, 1), 1]
                else:
                    _LOGGER.debug(
                        f"second_time has negative minutes: {minutes_to_second}. "
                        f"This indicates old forecast data. Detail sensor needs to update."
                    )
            except (ValueError, TypeError, IndexError) as e:
                _LOGGER.debug(f"Error calculating from second_time: {e}")

        _LOGGER.debug(
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
        """Get current weather condition based on pressure.

        Pressure ranges based on WMO meteorological standards:
        - < 980 hPa: Stormy (deep cyclone, storms)
        - 980-1008 hPa: Rainy (low pressure, precipitation likely)
        - 1008-1015 hPa: Cloudy (slightly reduced pressure, cloudy)
        - 1015-1023 hPa: Mixed/Partly cloudy (normal pressure, variable cloudiness)
        - ≥ 1023 hPa: Sunny (high/very high pressure, clear)

        Note: 1013.25 hPa = standard atmospheric pressure at sea level

        NOTE: This is kept in sensor.py for reference/debugging (forecast_short_term attribute).
        However, weather.py does NOT use it in priority chain - it uses forecast models instead.

        Condition indices:
        0 = Stormy, 1 = Rainy, 2 = Cloudy, 3 = Mixed, 4 = Sunny, 5 = Extra Dry
        """
        if p0 < 980:
            condition_idx = 0  # Stormy
            pressure_idx = 0  # Low
        elif 980 <= p0 < 1008:
            condition_idx = 1  # Rainy
            pressure_idx = 0  # Low
        elif 1008 <= p0 < 1015:
            condition_idx = 2  # Cloudy
            pressure_idx = 1  # Normal
        elif 1015 <= p0 < 1023:
            condition_idx = 3  # Mixed/Partly cloudy
            pressure_idx = 1  # Normal
        else:  # p0 >= 1023
            condition_idx = 4  # Sunny
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
        self._attr_device_class = SensorDeviceClass.ATMOSPHERIC_PRESSURE
        self._attr_native_unit_of_measurement = UnitOfPressure.HPA
        self._attr_state_class = SensorStateClass.MEASUREMENT  # Enable statistics recording
        self._attr_icon = "mdi:trending-up"
        self._state = 0.0
        self._history = []

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state AND history
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._state = float(last_state.state)

                # Restore history from attributes
                if last_state.attributes.get("history"):
                    restored_history = []
                    for entry in last_state.attributes["history"]:
                        try:
                            # entry format: [timestamp_iso, pressure_value]
                            timestamp = datetime.fromisoformat(entry[0])
                            pressure = float(entry[1])
                            restored_history.append((timestamp, pressure))
                        except (ValueError, TypeError, IndexError):
                            continue

                    if restored_history:
                        self._history = restored_history
                        _LOGGER.debug(
                            f"PressureChange: Restored {len(self._history)} historical values from previous session"
                        )
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

        # Add initial pressure value to history (only if history is empty)
        if not self._history:
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

                _LOGGER.debug(f"PressureChange: New pressure reading: {pressure} hPa at {timestamp}")

                # Add to history
                self._history.append((timestamp, pressure))

                # Keep records using BOTH time-based AND count-based limits:
                # 1. Keep all records within 180 minutes (time window)
                # 2. ALWAYS keep at least PRESSURE_MIN_RECORDS newest records (even if older)
                # This ensures we have enough data even if sensor updates irregularly
                cutoff = timestamp - timedelta(minutes=180)
                time_filtered = [
                    (ts, p) for ts, p in self._history if ts > cutoff
                ]

                # If we don't have enough records after time filtering, keep more
                if len(time_filtered) < PRESSURE_MIN_RECORDS:
                    # Keep the last PRESSURE_MIN_RECORDS records regardless of age
                    self._history = self._history[-PRESSURE_MIN_RECORDS:]
                    _LOGGER.debug(
                        f"PressureChange: Kept {len(self._history)} records (minimum required, "
                        f"time filter would leave only {len(time_filtered)})"
                    )
                else:
                    self._history = time_filtered
                    _LOGGER.debug(f"PressureChange: Kept {len(self._history)} records within 180-minute window")

                # Calculate change if we have enough data
                if len(self._history) >= 2:
                    oldest = self._history[0][1]
                    newest = self._history[-1][1]
                    self._state = round(newest - oldest, 2)
                    time_span = (self._history[-1][0] - self._history[0][0]).total_seconds() / 60
                    _LOGGER.debug(
                        f"PressureChange: Calculated change = {self._state} hPa "
                        f"over {time_span:.1f} minutes ({oldest} → {newest} hPa)"
                    )
                    self.async_write_ha_state()
                else:
                    _LOGGER.debug(f"PressureChange: Not enough data for calculation (have {len(self._history)} records)")

            except (ValueError, TypeError) as e:
                _LOGGER.debug(f"PressureChange: Error processing update: {e}")
                pass

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        # Save history in ISO format for persistence across restarts
        history_data = [
            [ts.isoformat(), pressure]
            for ts, pressure in self._history
        ]
        return {
            "history": history_data,
            "history_count": len(self._history),
            "oldest_reading": self._history[0][0].isoformat() if self._history else None,
            "newest_reading": self._history[-1][0].isoformat() if self._history else None,
        }


class LocalForecastTemperatureChangeSensor(LocalWeatherForecastEntity):
    """Temperature change statistics sensor."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_temperaturechange"  # Match original YAML entity_id (no underscore!)
        self._attr_name = "Local forecast TemperatureChange"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT  # Enable statistics recording
        self._attr_icon = "mdi:thermometer-lines"
        self._state = 0.0
        self._history = []

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state AND history
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._state = float(last_state.state)

                # Restore history from attributes
                if last_state.attributes.get("history"):
                    restored_history = []
                    for entry in last_state.attributes["history"]:
                        try:
                            # entry format: [timestamp_iso, temperature_value]
                            timestamp = datetime.fromisoformat(entry[0])
                            temperature = float(entry[1])
                            restored_history.append((timestamp, temperature))
                        except (ValueError, TypeError, IndexError):
                            continue

                    if restored_history:
                        self._history = restored_history
                        _LOGGER.debug(
                            f"TemperatureChange: Restored {len(self._history)} historical values from previous session"
                        )
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

        # Add initial temperature value to history (only if history is empty)
        if not self._history:
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

                _LOGGER.debug(f"TemperatureChange: New temperature reading: {temperature}°C at {timestamp}")

                # Add to history
                self._history.append((timestamp, temperature))

                # Keep records using BOTH time-based AND count-based limits:
                # 1. Keep all records within 60 minutes (time window)
                # 2. ALWAYS keep at least TEMPERATURE_MIN_RECORDS newest records (even if older)
                # This ensures we have enough data even if sensor updates irregularly
                cutoff = timestamp - timedelta(minutes=60)
                time_filtered = [
                    (ts, t) for ts, t in self._history if ts > cutoff
                ]

                # If we don't have enough records after time filtering, keep more
                if len(time_filtered) < TEMPERATURE_MIN_RECORDS:
                    # Keep the last TEMPERATURE_MIN_RECORDS records regardless of age
                    self._history = self._history[-TEMPERATURE_MIN_RECORDS:]
                    _LOGGER.debug(
                        f"TemperatureChange: Kept {len(self._history)} records (minimum required, "
                        f"time filter would leave only {len(time_filtered)})"
                    )
                else:
                    self._history = time_filtered
                    _LOGGER.debug(f"TemperatureChange: Kept {len(self._history)} records within 60-minute window")

                # Calculate change if we have enough data
                if len(self._history) >= 2:
                    oldest = self._history[0][1]
                    newest = self._history[-1][1]
                    self._state = round(newest - oldest, 2)
                    time_span = (self._history[-1][0] - self._history[0][0]).total_seconds() / 60
                    _LOGGER.debug(
                        f"TemperatureChange: Calculated change = {self._state}°C "
                        f"over {time_span:.1f} minutes ({oldest} → {newest}°C)"
                    )
                    self.async_write_ha_state()
                else:
                    _LOGGER.debug(f"TemperatureChange: Not enough data for calculation (have {len(self._history)} records)")

            except (ValueError, TypeError) as e:
                _LOGGER.debug(f"TemperatureChange: Error processing update: {e}")
                pass

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        # Save history in ISO format for persistence across restarts
        history_data = [
            [ts.isoformat(), temperature]
            for ts, temperature in self._history
        ]
        return {
            "history": history_data,
            "history_count": len(self._history),
            "oldest_reading": self._history[0][0].isoformat() if self._history else None,
            "newest_reading": self._history[-1][0].isoformat() if self._history else None,
        }


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
        """Estimate rain probability based on scientific meteorological standards.

        Based on WMO Technical Note No. 13 and NOAA forecasting guidelines.
        Uses state-based base probabilities with trend adjustments.

        States: 0=sunny, 1=partlycloudy, 2=partlycloudyrain, 3=cloudy,
                4=rainy, 5=pouring, 6=lightning-rainy
        """
        # Extract 6h and 12h states
        state_6h = forecast_states[0] if len(forecast_states) > 0 else 3
        state_12h = forecast_states[1] if len(forecast_states) > 1 else 3

        # Base probabilities by state (WMO/NOAA scientific values)
        # These represent measured probability of measurable precipitation (≥0.1mm)
        base_prob = {
            0: 2,    # sunny - anticyclonic, very low probability
            1: 15,   # partlycloudy - stable air mass, low probability
            2: 40,   # partly rainy - scattered showers possible
            3: 30,   # cloudy - overcast but no active precipitation
            4: 70,   # rainy - active precipitation expected
            5: 90,   # pouring - heavy rain, high certainty
            6: 95,   # lightning - thunderstorms, very high certainty
        }

        prob_6h = base_prob.get(state_6h, 30)
        prob_12h = base_prob.get(state_12h, 30)

        # Trend adjustment (meteorological principle: continuity and persistence)
        trend = state_12h - state_6h

        if trend < -1:  # Rapidly improving (e.g., storm clearing)
            prob_12h = max(5, prob_12h - 15)
        elif trend == -1:  # Improving (e.g., clearing skies)
            prob_12h = max(5, prob_12h - 10)
        elif trend == 0:  # Stable (persistence principle)
            pass  # No adjustment - current conditions persist
        elif trend == 1:  # Worsening (e.g., clouds thickening)
            prob_12h = min(95, prob_12h + 10)
        elif trend > 1:  # Rapidly worsening (e.g., approaching front)
            prob_12h = min(95, prob_12h + 20)

        # Clamp to valid percentage range
        prob_6h = max(0, min(100, prob_6h))
        prob_12h = max(0, min(100, prob_12h))

        return [prob_6h, prob_12h]

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
        """Estimate rain probability based on scientific meteorological standards.

        Based on WMO Technical Note No. 13 and NOAA forecasting guidelines.
        Uses state-based base probabilities with trend adjustments.

        Negretti-Zambra uses same scientific method as Zambretti for consistency.

        States: 0=sunny, 1=partlycloudy, 2=partlycloudyrain, 3=cloudy,
                4=rainy, 5=pouring, 6=lightning-rainy
        """
        # Extract 6h and 12h states
        state_6h = forecast_states[0] if len(forecast_states) > 0 else 3
        state_12h = forecast_states[1] if len(forecast_states) > 1 else 3

        # Base probabilities by state (WMO/NOAA scientific values)
        # These represent measured probability of measurable precipitation (≥0.1mm)
        base_prob = {
            0: 2,    # sunny - anticyclonic, very low probability
            1: 15,   # partlycloudy - stable air mass, low probability
            2: 40,   # partly rainy - scattered showers possible
            3: 30,   # cloudy - overcast but no active precipitation
            4: 70,   # rainy - active precipitation expected
            5: 90,   # pouring - heavy rain, high certainty
            6: 95,   # lightning - thunderstorms, very high certainty
        }

        prob_6h = base_prob.get(state_6h, 30)
        prob_12h = base_prob.get(state_12h, 30)

        # Trend adjustment (meteorological principle: continuity and persistence)
        trend = state_12h - state_6h

        if trend < -1:  # Rapidly improving (e.g., storm clearing)
            prob_12h = max(5, prob_12h - 15)
        elif trend == -1:  # Improving (e.g., clearing skies)
            prob_12h = max(5, prob_12h - 10)
        elif trend == 0:  # Stable (persistence principle)
            pass  # No adjustment - current conditions persist
        elif trend == 1:  # Worsening (e.g., clouds thickening)
            prob_12h = min(95, prob_12h + 10)
        elif trend > 1:  # Rapidly worsening (e.g., approaching front)
            prob_12h = min(95, prob_12h + 20)

        # Clamp to valid percentage range
        prob_6h = max(0, min(100, prob_6h))
        prob_12h = max(0, min(100, prob_12h))

        return [prob_6h, prob_12h]

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

        # Track weather entity and main sensor changes for automatic updates
        entities_to_track = [
            "weather.local_weather_forecast_weather",  # Weather entity
            "sensor.local_forecast",  # Main forecast sensor
        ]

        # Track ALL configured sensors for automatic updates
        # Only PRESSURE is truly required (in config.data)
        # All others are optional enhancements (in config.options)
        sensors_to_check = [
            (CONF_PRESSURE_SENSOR, True),       # Only required sensor (config.data)
            (CONF_TEMPERATURE_SENSOR, False),   # Optional - for sea level pressure conversion
            (CONF_HUMIDITY_SENSOR, False),      # Optional - for dew point, fog detection
            (CONF_WIND_SPEED_SENSOR, False),    # Optional - for wind factor, Beaufort scale
            (CONF_WIND_DIRECTION_SENSOR, False),# Optional - for wind factor adjustment
            (CONF_WIND_GUST_SENSOR, False),     # Optional - for atmosphere stability
            (CONF_RAIN_RATE_SENSOR, False),     # Optional - for rain probability enhancement
        ]

        for sensor_key, use_data in sensors_to_check:
            if use_data:
                sensor_id = self.config_entry.data.get(sensor_key)
            else:
                sensor_id = self.config_entry.options.get(sensor_key) or self.config_entry.data.get(sensor_key)

            if sensor_id:
                entities_to_track.append(sensor_id)
                _LOGGER.debug(f"Enhanced: Tracking sensor {sensor_key}: {sensor_id}")

        # Set up state change tracking
        _LOGGER.debug(f"Enhanced: Tracking {len(entities_to_track)} entities for automatic updates")
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, entities_to_track, self._handle_sensor_update
            )
        )

        # Schedule delayed update to wait for dependent sensors to load
        async def delayed_startup_update():
            await asyncio.sleep(10)  # Wait 10 seconds for other integrations to load
            _LOGGER.debug("Enhanced: Running delayed startup update")
            await self.async_update()
            self.async_write_ha_state()

        self.hass.async_create_task(delayed_startup_update())

    @callback
    async def _handle_sensor_update(self, event):
        """Handle source sensor state changes."""
        # Throttle updates to prevent flooding
        now = dt_util.now()
        if self._last_update_time is not None:
            time_since_last_update = (now - self._last_update_time).total_seconds()
            if time_since_last_update < self._update_throttle_seconds:
                _LOGGER.debug(
                    f"Enhanced: Skipping update, only {time_since_last_update:.1f}s since last update"
                )
                return

        self._last_update_time = now
        _LOGGER.debug(f"Enhanced: Sensor update triggered by {event.data.get('entity_id')}")
        await self.async_update()
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes

    def _get_beaufort_number(self, wind_speed: float) -> int:
        """Get Beaufort scale number from wind speed (m/s).

        Args:
            wind_speed: Wind speed in m/s

        Returns:
            Beaufort number (0-12)
        """
        if wind_speed < 0.5:
            return 0  # Calm
        elif wind_speed < 1.6:
            return 1  # Light air
        elif wind_speed < 3.4:
            return 2  # Light breeze
        elif wind_speed < 5.5:
            return 3  # Gentle breeze
        elif wind_speed < 8.0:
            return 4  # Moderate breeze
        elif wind_speed < 10.8:
            return 5  # Fresh breeze
        elif wind_speed < 13.9:
            return 6  # Strong breeze
        elif wind_speed < 17.2:
            return 7  # High wind
        elif wind_speed < 20.8:
            return 8  # Gale
        elif wind_speed < 24.5:
            return 9  # Strong gale
        elif wind_speed < 28.5:
            return 10  # Storm
        elif wind_speed < 32.7:
            return 11  # Violent storm
        else:
            return 12  # Hurricane

    def _get_beaufort_wind_type(self, wind_speed: float) -> str:
        """Get wind type description from Beaufort scale (multilingual).

        Args:
            wind_speed: Wind speed in m/s

        Returns:
            Wind type description based on Home Assistant UI language
        """
        beaufort = self._get_beaufort_number(wind_speed)
        return get_wind_type(self.hass, beaufort)


    def _get_atmosphere_stability(self, wind_speed: float, gust_ratio: float | None) -> str:
        """Determine atmospheric stability based on wind speed and gust ratio.

        Args:
            wind_speed: Wind speed in m/s
            gust_ratio: Ratio of gust speed to average wind speed

        Returns:
            Stability description (Slovak/English): "stable", "moderate", "unstable", "very_unstable"
        """
        if gust_ratio is None:
            return "unknown"

        # For low wind speeds (< 3 m/s), gust ratio is not reliable indicator
        if wind_speed < 3.0:
            # Use only wind speed for very light conditions
            if wind_speed < 1.0:
                return "stable"  # Calm = stable
            else:
                return "moderate"  # Light breeze = moderate

        # For moderate to strong winds (≥ 3 m/s), use gust ratio
        # Meteorologically justified thresholds:
        # - Ratio 1.0-1.3: Stable (smooth airflow)
        # - Ratio 1.3-1.6: Moderate (normal turbulence)
        # - Ratio 1.6-2.0: Unstable (significant turbulence)
        # - Ratio > 2.0: Very unstable (severe turbulence, convection, storms)

        if gust_ratio < 1.3:
            return "stable"
        elif gust_ratio < 1.6:
            return "moderate"
        elif gust_ratio < 2.0:
            return "unstable"
        else:
            return "very_unstable"

    async def async_update(self) -> None:
        """Update the enhanced forecast."""
        # Get forecast model from config (options first, then data fallback, then default)
        from .const import CONF_FORECAST_MODEL, FORECAST_MODEL_ENHANCED
        forecast_model = (
            self.config_entry.options.get(CONF_FORECAST_MODEL)
            or self.config_entry.data.get(CONF_FORECAST_MODEL)
            or FORECAST_MODEL_ENHANCED
        )
        _LOGGER.debug(f"Enhanced: Using forecast model: {forecast_model}")

        # Get base forecasts from detail sensors (they update independently)
        zambretti_sensor = self.hass.states.get("sensor.local_forecast_zambretti_detail")
        negretti_sensor = self.hass.states.get("sensor.local_forecast_neg_zam_detail")

        if zambretti_sensor and zambretti_sensor.state not in ("unknown", "unavailable"):
            # ✅ SIMPLIFIED: Format is now [text, code]
            zambretti = [
                zambretti_sensor.state,
                zambretti_sensor.attributes.get("forecast_number", 0)
            ]
            _LOGGER.debug(f"Enhanced: Zambretti from detail sensor - {zambretti[0]} (code={zambretti[1]})")
        else:
            _LOGGER.debug("Enhanced: Zambretti detail sensor unavailable, using defaults")
            zambretti = ["Unknown", 0]

        if negretti_sensor and negretti_sensor.state not in ("unknown", "unavailable"):
            # ✅ SIMPLIFIED: Format is now [text, code]
            negretti = [
                negretti_sensor.state,
                negretti_sensor.attributes.get("forecast_number", 0)
            ]
            _LOGGER.debug(f"Enhanced: Negretti from detail sensor - {negretti[0]} (code={negretti[1]})")
        else:
            _LOGGER.debug("Enhanced: Negretti detail sensor unavailable, using defaults")
            negretti = ["Unknown", 0]

        # Get sensor values from weather entity first for consistency
        # Weather entity handles dewpoint sensor priority: uses sensor if exists, else calculates
        temp = None
        dewpoint = None
        humidity = None

        weather_entity = self.hass.states.get("weather.local_weather_forecast_weather")
        if weather_entity and weather_entity.state not in ("unknown", "unavailable"):
            # Get temperature from weather entity
            temp_attr = weather_entity.attributes.get("temperature")
            if temp_attr is not None:
                try:
                    temp = float(temp_attr)
                    _LOGGER.debug(f"Enhanced: Using temperature from weather entity: {temp}°C")
                except (ValueError, TypeError):
                    pass

            # Get dewpoint from weather entity (already handles dewpoint sensor priority)
            dewpoint_attr = weather_entity.attributes.get("dew_point")
            if dewpoint_attr is not None:
                try:
                    dewpoint = float(dewpoint_attr)
                    _LOGGER.debug(f"Enhanced: Using dew_point from weather entity: {dewpoint}°C")
                except (ValueError, TypeError):
                    pass

            # Get humidity from weather entity
            humidity_attr = weather_entity.attributes.get("humidity")
            if humidity_attr is not None:
                try:
                    humidity = float(humidity_attr)
                    _LOGGER.debug(f"Enhanced: Using humidity from weather entity: {humidity}%")
                except (ValueError, TypeError):
                    pass

        # Fallback: use configured sensors if weather entity not available
        if temp is None:
            temp = await self._get_sensor_value(
                self.config_entry.data.get(CONF_TEMPERATURE_SENSOR) or "", 15.0, sensor_type="temperature"
            )
            _LOGGER.debug(f"Enhanced: Fallback - temperature from configured sensor: {temp}°C")

        if humidity is None:
            humidity_sensor = self.config_entry.options.get(CONF_HUMIDITY_SENSOR) or self.config_entry.data.get(CONF_HUMIDITY_SENSOR) or ""
            if humidity_sensor:
                _LOGGER.debug(f"Enhanced: Fallback - fetching humidity from {humidity_sensor}")
                humidity = await self._get_sensor_value(humidity_sensor, None, use_history=True, sensor_type="humidity")
                _LOGGER.debug(f"Enhanced: Fallback - humidity value = {humidity}")
            else:
                _LOGGER.debug("Enhanced: No humidity sensor configured!")

        # Calculate dewpoint if not available from weather entity
        if dewpoint is None and temp is not None and humidity is not None:
            # Type guard - ensure we have valid float values
            if isinstance(temp, (int, float)) and isinstance(humidity, (int, float)):
                dewpoint = calculate_dewpoint(temp, humidity)
                _LOGGER.debug(f"Enhanced: Fallback - calculated dewpoint: {dewpoint}°C")

        # Calculate spread
        dewpoint_spread = None
        if temp is not None and dewpoint is not None:
            dewpoint_spread = temp - dewpoint
            _LOGGER.debug(f"Enhanced: ✓ SPREAD: {temp}°C - {dewpoint}°C = {dewpoint_spread:.1f}°C")
        else:
            _LOGGER.debug(f"Enhanced: ✗ Cannot calculate spread - temp={temp}, dewpoint={dewpoint}, humidity={humidity}")

        # Get wind gust ratio
        wind_speed = await self._get_sensor_value(
            self.config_entry.data.get(CONF_WIND_SPEED_SENSOR) or "", 0.0, use_history=True, sensor_type="wind_speed"
        )
        # Enhanced sensors are in options, not data!
        wind_gust_sensor_id = self.config_entry.options.get(CONF_WIND_GUST_SENSOR) or self.config_entry.data.get(CONF_WIND_GUST_SENSOR) or ""
        _LOGGER.debug(f"Enhanced: Config wind gust sensor = {wind_gust_sensor_id}, wind_speed = {wind_speed} m/s")
        gust_ratio = None
        wind_gust = None
        if wind_gust_sensor_id and wind_speed and wind_speed > 0.1:
            _LOGGER.debug(f"Enhanced: Fetching wind gust from {wind_gust_sensor_id}, wind_speed={wind_speed} m/s")
            wind_gust = await self._get_sensor_value(wind_gust_sensor_id, None, use_history=True, sensor_type="wind_speed")
            if wind_gust is not None and isinstance(wind_gust, (int, float)) and wind_speed is not None and wind_speed > 0.1:
                gust_ratio = wind_gust / wind_speed
                _LOGGER.debug(f"Enhanced: Calculated gust_ratio={gust_ratio:.2f} (gust={wind_gust} m/s, speed={wind_speed} m/s)")
            else:
                _LOGGER.debug(f"Enhanced: Wind gust sensor returned None")
        else:
            if not wind_gust_sensor_id:
                _LOGGER.debug("Enhanced: No wind gust sensor configured!")
            else:
                _LOGGER.debug(f"Enhanced: Wind speed too low ({wind_speed} m/s), skipping gust ratio")

        # Determine wind type based on Beaufort scale
        wind_type = self._get_beaufort_wind_type(wind_speed or 0.0)
        wind_beaufort_number = self._get_beaufort_number(wind_speed or 0.0)

        # Determine atmospheric stability based on gust ratio and wind speed
        atmosphere_stability = self._get_atmosphere_stability(wind_speed or 0.0, gust_ratio)

        # Calculate adjustments
        adjustments = []
        adjustment_details = []

        # Humidity adjustment
        if humidity is not None:
            if humidity > 85:
                adjustments.append("high_humidity")
                adjustment_details.append(get_adjustment_text(self.hass, "high_humidity", f"{humidity:.1f}"))
            elif humidity < 40:
                adjustments.append("low_humidity")
                adjustment_details.append(get_adjustment_text(self.hass, "low_humidity", f"{humidity:.1f}"))

        # Dewpoint spread adjustment (fog/precipitation risk)
        # Use fog risk levels consistently with get_fog_risk() thresholds
        if dewpoint_spread is not None:
            if dewpoint_spread < 1.5:  # HIGH fog risk
                adjustments.append("high_fog_risk")
                adjustment_details.append(get_adjustment_text(self.hass, "high_fog_risk", f"{dewpoint_spread:.1f}"))
            elif 1.5 <= dewpoint_spread < 2.5:  # MEDIUM fog risk
                adjustments.append("medium_fog_risk")
                adjustment_details.append(get_adjustment_text(self.hass, "medium_fog_risk", f"{dewpoint_spread:.1f}"))
            elif 2.5 <= dewpoint_spread < 4:  # LOW fog risk
                adjustments.append("low_fog_risk")
                adjustment_details.append(get_adjustment_text(self.hass, "low_fog_risk", f"{dewpoint_spread:.1f}"))

        # Atmospheric stability (gust ratio)
        # Only evaluate for significant wind speeds (>3 m/s)
        # Low wind speeds naturally have higher gust ratios without indicating instability
        # Example: 0.8 m/s wind with 1.1 m/s gusts = ratio 1.375 = NORMAL, not unstable
        if gust_ratio is not None and wind_speed is not None and wind_speed > 3.0:
            if gust_ratio > 2.0:
                adjustments.append("very_unstable")
                adjustment_details.append(get_adjustment_text(self.hass, "very_unstable", f"{gust_ratio:.2f}"))
            elif gust_ratio > 1.6:
                adjustments.append("unstable")
                adjustment_details.append(get_adjustment_text(self.hass, "unstable", f"{gust_ratio:.2f}"))
        elif gust_ratio is not None and wind_speed <= 3.0:
            _LOGGER.debug(
                f"Enhanced: Skipping gust ratio check for low wind speed "
                f"(wind={wind_speed:.1f} m/s, gust_ratio={gust_ratio:.2f})"
            )

        # Build enhanced forecast text
        # Select base forecast based on model configuration
        from .const import FORECAST_MODEL_ZAMBRETTI, FORECAST_MODEL_NEGRETTI, FORECAST_MODEL_ENHANCED
        from .combined_model import (
            calculate_combined_forecast,
            get_combined_forecast_text
        )

        # Initialize weights for export
        zambretti_weight = 0.5
        negretti_weight = 0.5
        consensus = False

        if forecast_model == FORECAST_MODEL_ZAMBRETTI:
            # Use Zambretti exclusively
            base_text = zambretti[0] if len(zambretti) > 0 else "Unknown"
            export_forecast_num = zambretti[1] if len(zambretti) > 1 else 0
            zambretti_weight = 1.0
            negretti_weight = 0.0
            _LOGGER.debug(f"Enhanced: Using Zambretti exclusively: {base_text}")

        elif forecast_model == FORECAST_MODEL_NEGRETTI:
            # Use Negretti & Zambra exclusively
            base_text = negretti[0] if len(negretti) > 0 else "Unknown"
            export_forecast_num = negretti[1] if len(negretti) > 1 else 0
            zambretti_weight = 0.0
            negretti_weight = 1.0
            _LOGGER.debug(f"Enhanced: Using Negretti exclusively: {base_text}")

        else:
            # FORECAST_MODEL_ENHANCED - Use combined_model.py
            # Get current pressure for anticyclone detection
            current_pressure = 1013.25  # Default
            pressure_sensor = self.hass.states.get("sensor.local_forecast_pressure")
            if pressure_sensor and pressure_sensor.state not in ("unknown", "unavailable", None):
                try:
                    current_pressure = float(pressure_sensor.state)
                except (ValueError, TypeError):
                    pass

            # Get pressure change
            pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
            pressure_change = 0.0
            if pressure_change_sensor and pressure_change_sensor.state not in ("unknown", "unavailable", None):
                try:
                    pressure_change = float(pressure_change_sensor.state)
                except (ValueError, TypeError):
                    pass

            # ✅ USE COMBINED MODEL MODULE (✅ SIMPLIFIED - no letter!)
            (
                export_forecast_num,
                zambretti_weight,
                negretti_weight,
                consensus
            ) = calculate_combined_forecast(
                zambretti_result=zambretti,
                negretti_result=negretti,
                current_pressure=current_pressure,
                pressure_change=pressure_change,
                source="EnhancedSensor"
            )

            # Get forecast text from selected model
            base_text = get_combined_forecast_text(
                zambretti_result=zambretti,
                negretti_result=negretti,
                forecast_number=export_forecast_num,
                zambretti_weight=zambretti_weight,
                lang_index=get_language_index(self.hass)
            )

        # Add adjustments to forecast text
        if adjustment_details:
            enhanced_text = f"{base_text}. {', '.join(adjustment_details)}"
        else:
            enhanced_text = base_text

        # Calculate confidence
        zambretti_num = zambretti[1] if len(zambretti) > 1 else 0
        negretti_num = negretti[1] if len(negretti) > 1 else 0

        # Confidence depends on model selection
        if forecast_model == FORECAST_MODEL_ENHANCED:
            # Enhanced model - confidence based on consensus + adjustments
            if consensus and not adjustments:
                confidence = "very_high"
            elif consensus or len(adjustments) <= 1:
                confidence = "high"
            elif len(adjustments) <= 2:
                confidence = "medium"
            else:
                confidence = "low"
        else:
            # Single model (Zambretti or Negretti) - confidence based on adjustments only
            if not adjustments:
                confidence = "high"
            elif len(adjustments) <= 1:
                confidence = "high"
            elif len(adjustments) <= 2:
                confidence = "medium"
            else:
                confidence = "low"

        # Get fog risk
        fog_risk = "none"
        if dewpoint is not None and temp is not None:
            fog_risk = get_fog_risk(temp, dewpoint, humidity)

        # Get snow risk (only calculate if conditions are cold enough)
        snow_risk = "none"
        if temp is not None and temp <= 4 and dewpoint is not None and humidity is not None:
            # Get rain probability if available for better snow risk assessment
            rain_prob_sensor = self.hass.states.get("sensor.local_forecast_rain_probability")
            rain_prob = None
            if rain_prob_sensor and rain_prob_sensor.state not in ("unknown", "unavailable", None):
                try:
                    rain_prob = int(rain_prob_sensor.state.rstrip('%'))
                except (ValueError, AttributeError):
                    pass

            snow_risk = get_snow_risk(temp, humidity, dewpoint, rain_prob)
            _LOGGER.debug(
                f"Enhanced: Snow risk={snow_risk} (temp={temp:.1f}°C, humidity={humidity:.1f}%, "
                f"dewpoint={dewpoint:.1f}°C, rain_prob={rain_prob}%)"
            )

        # Get frost/ice risk (námraza)
        frost_risk = "none"
        if temp is not None and temp <= 4 and dewpoint is not None:
            frost_risk = get_frost_risk(temp, dewpoint, wind_speed, humidity)
            _LOGGER.debug(
                f"Enhanced: Frost risk={frost_risk} (temp={temp:.1f}°C, dewpoint={dewpoint:.1f}°C, "
                f"wind_speed={wind_speed:.1f} m/s)"
            )

        self._state = enhanced_text
        _LOGGER.debug(f"Enhanced: Setting state to: {enhanced_text}")

        # ✅ SIMPLIFIED: No more letter_code export - only forecast_number!
        # export_forecast_num is already set above based on model selection

        self._attributes = {
            "forecast_model": forecast_model,  # Show which model is being used
            "base_forecast": base_text,
            "forecast_number": export_forecast_num,  # For weather entity (CODE only!)
            "zambretti_number": zambretti_num,       # Keep originals for reference
            "negretti_number": negretti_num,         # Keep originals for reference
            "adjustments": adjustments,
            "adjustment_details": adjustment_details,
            "confidence": confidence,
            "consensus": consensus,
            "humidity": round(humidity, 2) if humidity is not None else None,
            "dew_point": round(dewpoint, 2) if dewpoint is not None else None,
            "dewpoint_spread": round(dewpoint_spread, 2) if dewpoint_spread is not None else None,
            # RAW values for automations (English keys)
            "fog_risk": fog_risk,  # "none", "low", "medium", "high", "critical"
            "snow_risk": snow_risk,  # "none", "low", "medium", "high"
            "frost_risk": frost_risk,  # "none", "low", "medium", "high", "critical"
            # Translated values for UI display
            "fog_risk_text": get_fog_risk_text(self.hass, fog_risk),
            "snow_risk_text": get_snow_risk_text(self.hass, snow_risk),
            "frost_risk_text": get_frost_risk_text(self.hass, frost_risk),
            "wind_speed": round(wind_speed, 2) if wind_speed is not None else None,
            "wind_gust": round(wind_gust, 2) if wind_gust is not None else None,
            "gust_ratio": round(gust_ratio, 2) if gust_ratio is not None else None,
            "wind_type": wind_type,
            "wind_beaufort_scale": wind_beaufort_number,
            "atmosphere_stability": get_atmosphere_stability_text(self.hass, atmosphere_stability),  # Translated
            "accuracy_estimate": "~98%" if confidence in ["high", "very_high"] else "~94%",
        }
        # Note: Home Assistant automatically writes state after async_update() completes


class LocalForecastRainProbabilitySensor(LocalWeatherForecastEntity):
    """Enhanced precipitation probability sensor using multiple factors.

    Displays rain or snow icon based on temperature and conditions.
    """

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the precipitation probability sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = "local_forecast_rain_probability"
        self._attr_name = "Local Forecast Precipitation Probability"
        # Icon will be dynamic based on temperature (snow vs rain)
        self._attr_icon = "mdi:weather-rainy"  # Default, updated in async_update
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = None  # Initialize state
        self._attributes = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass - schedule delayed update for startup."""
        await super().async_added_to_hass()

        # Track detail sensors for updates
        sensors_to_track = [
            "sensor.local_forecast_zambretti_detail",
            "sensor.local_forecast_neg_zam_detail",
        ]

        # Add optional sensors if configured
        humidity_sensor = self.config_entry.options.get(CONF_HUMIDITY_SENSOR) or self.config_entry.data.get(CONF_HUMIDITY_SENSOR)
        if humidity_sensor:
            sensors_to_track.append(humidity_sensor)

        temp_sensor = self.config_entry.options.get(CONF_TEMPERATURE_SENSOR) or self.config_entry.data.get(CONF_TEMPERATURE_SENSOR)
        if temp_sensor:
            sensors_to_track.append(temp_sensor)

        rain_sensor = self.config_entry.options.get(CONF_RAIN_RATE_SENSOR) or self.config_entry.data.get(CONF_RAIN_RATE_SENSOR)
        if rain_sensor:
            sensors_to_track.append(rain_sensor)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, sensors_to_track, self._handle_sensor_update
            )
        )

        # Schedule delayed update to wait for dependent sensors to load
        async def delayed_startup_update():
            await asyncio.sleep(10)  # Wait 10 seconds for other integrations to load
            _LOGGER.debug("RainProb: Running delayed startup update")
            await self.async_update()
            self.async_write_ha_state()

        self.hass.async_create_task(delayed_startup_update())

    @callback
    async def _handle_sensor_update(self, event):
        """Handle source sensor state changes."""
        # Throttle updates to prevent flooding
        now = dt_util.now()
        if self._last_update_time is not None:
            time_since_last_update = (now - self._last_update_time).total_seconds()
            if time_since_last_update < self._update_throttle_seconds:
                _LOGGER.debug(
                    f"RainProb: Skipping update, only {time_since_last_update:.1f}s since last update"
                )
                return

        self._last_update_time = now
        _LOGGER.debug("RainProb: Handling sensor update")
        await self.async_update()
        self.async_write_ha_state()

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self._attributes


    async def async_update(self) -> None:
        """Update the rain probability based on selected forecast model."""
        # ✅ FIXED v3.1.10: Respect forecast model selection from config_flow
        # Previously: Always averaged both Zambretti + Negretti (incorrect!)
        # Now: Use only the selected model's rain probability

        # Get forecast model from config (options first, then data fallback, then default)
        from .const import CONF_FORECAST_MODEL, FORECAST_MODEL_ENHANCED
        forecast_model = (
            self.config_entry.options.get(CONF_FORECAST_MODEL)
            or self.config_entry.data.get(CONF_FORECAST_MODEL)
            or FORECAST_MODEL_ENHANCED
        )
        _LOGGER.debug(f"RainProb: Using forecast model: {forecast_model}")

        # Get detail sensors
        zambretti_sensor = self.hass.states.get("sensor.local_forecast_zambretti_detail")
        negretti_sensor = self.hass.states.get("sensor.local_forecast_neg_zam_detail")

        # ✅ ALWAYS load BOTH probabilities (sensors run independently)
        # Only base_probability calculation respects model selection
        zambretti_prob = 0
        negretti_prob = 0

        # Load Zambretti probability (always)
        if zambretti_sensor and zambretti_sensor.state not in ("unknown", "unavailable"):
            zambretti_rain = zambretti_sensor.attributes.get("rain_prob", [0, 0])
            zambretti_prob = sum(zambretti_rain) / len(zambretti_rain) if zambretti_rain else 0
            _LOGGER.debug(f"RainProb: Zambretti rain_prob={zambretti_rain} → avg={zambretti_prob}%")
        else:
            _LOGGER.debug("RainProb: Zambretti detail sensor unavailable")

        # Load Negretti probability (always)
        if negretti_sensor and negretti_sensor.state not in ("unknown", "unavailable"):
            negretti_rain = negretti_sensor.attributes.get("rain_prob", [0, 0])
            negretti_prob = sum(negretti_rain) / len(negretti_rain) if negretti_rain else 0
            _LOGGER.debug(f"RainProb: Negretti rain_prob={negretti_rain} → avg={negretti_prob}%")
        else:
            _LOGGER.debug("RainProb: Negretti detail sensor unavailable")

        # Initialize weights (will be set based on model)
        zambretti_weight = 0.5
        negretti_weight = 0.5

        # Set weights based on selected model
        from .const import FORECAST_MODEL_ZAMBRETTI, FORECAST_MODEL_NEGRETTI, FORECAST_MODEL_ENHANCED

        if forecast_model == FORECAST_MODEL_ZAMBRETTI:
            # Use ONLY Zambretti for base_probability calculation
            zambretti_weight = 1.0
            negretti_weight = 0.0
            _LOGGER.debug(f"RainProb: [ZAMBRETTI MODEL] Using only Zambretti (weight=1.0)")

        elif forecast_model == FORECAST_MODEL_NEGRETTI:
            # Use ONLY Negretti for base_probability calculation
            zambretti_weight = 0.0
            negretti_weight = 1.0
            _LOGGER.debug(f"RainProb: [NEGRETTI MODEL] Using only Negretti (weight=1.0)")

        else:  # FORECAST_MODEL_ENHANCED (default)
            # Use BOTH models with dynamic weighting from combined_model
            # (probabilities already loaded above)
            _LOGGER.debug(f"RainProb: [ENHANCED] Using dynamic weighting")

            # ✅ Get dynamic weights from combined_model
            # Same logic as Enhanced sensor for consistency
            from .combined_model import calculate_combined_forecast

            # Get current pressure
            current_pressure = 1013.25  # Default
            pressure_sensor = self.hass.states.get("sensor.local_forecast_pressure")
            if pressure_sensor and pressure_sensor.state not in ("unknown", "unavailable", None):
                try:
                    current_pressure = float(pressure_sensor.state)
                except (ValueError, TypeError):
                    pass

            # Get pressure change
            pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
            pressure_change = 0.0
            if pressure_change_sensor and pressure_change_sensor.state not in ("unknown", "unavailable", None):
                try:
                    pressure_change = float(pressure_change_sensor.state)
                except (ValueError, TypeError):
                    pass

            # Get dynamic weights (we don't need forecast_num, just weights)
            zambretti_result = [zambretti_sensor.state if zambretti_sensor else "", 0, "A"]
            negretti_result = [negretti_sensor.state if negretti_sensor else "", 0, "A"]

            try:
                (
                    _,  # forecast_num (not needed)
                    zambretti_weight,
                    negretti_weight,
                    _   # consensus (not needed)
                ) = calculate_combined_forecast(
                    zambretti_result=zambretti_result,
                    negretti_result=negretti_result,
                    current_pressure=current_pressure,
                    pressure_change=pressure_change,
                    source="RainProbabilitySensor"
                )

                _LOGGER.debug(
                    f"RainProb: [ENHANCED] Dynamic weights - Zambretti={zambretti_weight:.2f}, "
                    f"Negretti={negretti_weight:.2f} (pressure_change={pressure_change:.2f} hPa)"
                )
            except Exception as e:
                # Fallback to balanced if combined_model fails
                _LOGGER.debug(f"RainProb: Failed to get dynamic weights, using balanced: {e}")
                zambretti_weight = 0.5
                negretti_weight = 0.5

        _LOGGER.debug(
            f"RainProb: Model={forecast_model}, "
            f"Zambretti={zambretti_prob}% (weight={zambretti_weight:.2f}), "
            f"Negretti={negretti_prob}% (weight={negretti_weight:.2f})"
        )

        # Get sensor values for enhancements
        temp = await self._get_sensor_value(
            self.config_entry.data.get(CONF_TEMPERATURE_SENSOR) or "", 15.0, sensor_type="temperature"
        )

        # Enhanced sensors are in options, not data!
        humidity_sensor = self.config_entry.options.get(CONF_HUMIDITY_SENSOR) or self.config_entry.data.get(CONF_HUMIDITY_SENSOR) or ""
        _LOGGER.debug(f"RainProb: Config humidity sensor = {humidity_sensor}")
        humidity = None
        if humidity_sensor:
            _LOGGER.debug(f"RainProb: Fetching humidity from {humidity_sensor}")
            humidity = await self._get_sensor_value(humidity_sensor, None, use_history=True, sensor_type="humidity")
            _LOGGER.debug(f"RainProb: Humidity value = {humidity}")
        else:
            _LOGGER.debug("RainProb: No humidity sensor configured!")

        # Calculate dewpoint spread
        dewpoint_spread = None
        if temp is not None and humidity is not None:
            # Type guard - ensure we have valid float values
            if isinstance(temp, (int, float)) and isinstance(humidity, (int, float)):
                dewpoint = calculate_dewpoint(temp, humidity)
                if dewpoint is not None:
                    dewpoint_spread = temp - dewpoint
                    _LOGGER.debug(f"RainProb: Calculated dewpoint_spread={dewpoint_spread}")
        else:
            _LOGGER.debug(f"RainProb: Cannot calculate dewpoint - temp={temp}, humidity={humidity}")

        # ✅ FIXED v3.1.13: Use rain_prob from sensors (not LETTER_RAIN_PROB) for consistency
        # All models should use the same rain probability source (rain_prob attribute)
        # which already includes pressure adjustments from RainProbabilityCalculator
        
        # Apply weights to the rain probabilities loaded earlier
        weighted_zambretti = zambretti_prob * zambretti_weight
        weighted_negretti = negretti_prob * negretti_weight
        
        _LOGGER.debug(
            f"RainProb: [{forecast_model}] Applying weights - "
            f"Z: {zambretti_prob}% × {zambretti_weight:.2f} = {weighted_zambretti:.1f}%, "
            f"N: {negretti_prob}% × {negretti_weight:.2f} = {weighted_negretti:.1f}%"
        )

        # Use enhanced calculation with WEIGHTED probabilities
        # This applies humidity and dewpoint enhancements on top of the weighted base
        probability, confidence = calculate_rain_probability_enhanced(
            int(weighted_zambretti),
            int(weighted_negretti),
            humidity,
            dewpoint_spread,
            temp,
        )
        _LOGGER.debug(
            f"RainProb: [{forecast_model}] Result - "
            f"base={weighted_zambretti + weighted_negretti:.0f}%, "
            f"final={probability}% (confidence={confidence})"
        )

        # Get current rain rate
        rain_rate_sensor_id = self.config_entry.options.get(CONF_RAIN_RATE_SENSOR) or self.config_entry.data.get(CONF_RAIN_RATE_SENSOR)
        _LOGGER.debug(f"RainProb: Config rain rate sensor = {rain_rate_sensor_id}")
        current_rain = 0.0
        if rain_rate_sensor_id:
            # Wait for entity to become available (useful during HA restart)
            rain_state = self.hass.states.get(rain_rate_sensor_id)
            if not rain_state or rain_state.state in ("unknown", "unavailable"):
                _LOGGER.debug(f"RainProb: Rain sensor '{rain_rate_sensor_id}' not yet available, waiting...")
                await self._wait_for_entity(rain_rate_sensor_id, timeout=15, retry_interval=0.5)

            # Extended debugging
            rain_state = self.hass.states.get(rain_rate_sensor_id)
            if rain_state:
                _LOGGER.debug(f"RainProb: Rain sensor state={rain_state.state}, attributes={rain_state.attributes}")
            else:
                _LOGGER.debug(f"RainProb: Rain sensor '{rain_rate_sensor_id}' not found in HA registry!")

            _LOGGER.debug(f"RainProb: Fetching rain rate from {rain_rate_sensor_id}")
            current_rain_value = await self._get_sensor_value(rain_rate_sensor_id, 0.0, use_history=False, sensor_type="precipitation")
            if current_rain_value is not None:
                current_rain = current_rain_value
                _LOGGER.debug(f"RainProb: Current rain rate = {current_rain} mm/h")
            else:
                _LOGGER.debug(f"RainProb: Rain rate sensor returned None (state={rain_state.state if rain_state else 'NOT_FOUND'})")
        else:
            _LOGGER.debug("RainProb: No rain rate sensor configured!")

        # If currently raining, override probability to HIGH
        if current_rain > 0.01:  # More than 0.01 mm/h = active precipitation (lowered from 0.1)
            _LOGGER.debug(
                f"RainProb: Active precipitation detected ({current_rain:.3f} mm/h), "
                f"overriding probability from {probability}% to 95%"
            )
            probability = 95
            confidence = "very_high"

        # Dynamic icon based on temperature and probability
        # Simple meteorological logic: if cold enough, precipitation will be snow
        temp_sensor_id = self.config_entry.options.get(CONF_TEMPERATURE_SENSOR) or self.config_entry.data.get(CONF_TEMPERATURE_SENSOR)
        temperature = None
        if temp_sensor_id:
            temp_state = self.hass.states.get(temp_sensor_id)
            if temp_state and temp_state.state not in ("unknown", "unavailable", None):
                try:
                    temperature = UnitConverter.convert_sensor_value(
                        float(temp_state.state),
                        "temperature",
                        temp_state.attributes.get("unit_of_measurement", "°C")
                    )
                except (ValueError, TypeError):
                    pass

        # Get snow risk from enhanced sensor for consistent snow detection
        snow_risk = None
        enhanced_sensor = self.hass.states.get("sensor.local_forecast_enhanced")
        if enhanced_sensor and enhanced_sensor.state not in ("unknown", "unavailable", None):
            try:
                enhanced_attrs = enhanced_sensor.attributes or {}
                snow_risk = enhanced_attrs.get("snow_risk", None)
            except (AttributeError, KeyError, TypeError):
                pass

        # Determine icon based on temperature and probability
        # This prevents showing snow icon when conditions are just "cold" but not "snowy"
        # Example: -5°C, 75% humidity, spread 3.8°C, snow_risk=low → RAIN icon (not snow)

        if temperature is not None and temperature <= 2.0:
            # Cold enough for snow - check snow risk
            if snow_risk in ("high", "Vysoké riziko snehu") and probability >= 40:
                # High snow risk + moderate probability → SNOW
                self._attr_icon = "mdi:weather-snowy"
                precipitation_type = "snow"
                _LOGGER.debug(
                    f"RainProb: Icon set to SNOW (high risk) - temp={temperature:.1f}°C, "
                    f"probability={probability}%, snow_risk={snow_risk}"
                )
            elif snow_risk in ("medium", "Stredné riziko snehu") and probability >= 50:
                # Medium snow risk + higher probability → SNOW
                self._attr_icon = "mdi:weather-snowy"
                precipitation_type = "snow"
                _LOGGER.debug(
                    f"RainProb: Icon set to SNOW (medium risk) - temp={temperature:.1f}°C, "
                    f"probability={probability}%, snow_risk={snow_risk}"
                )
            elif probability >= 60 and humidity is not None and humidity > 70:
                # Very high probability + cold + humid → likely SNOW even without high snow_risk
                self._attr_icon = "mdi:weather-snowy"
                precipitation_type = "snow"
                _LOGGER.debug(
                    f"RainProb: Icon set to SNOW (high prob + humid) - temp={temperature:.1f}°C, "
                    f"probability={probability}%, humidity={humidity}%"
                )
            else:
                # Cold but low snow risk or low probability → RAIN (frozen rain sensor scenario)
                self._attr_icon = "mdi:weather-rainy"
                precipitation_type = "rain"
                _LOGGER.debug(
                    f"RainProb: Icon set to RAIN (cold but low snow risk) - temp={temperature:.1f}°C, "
                    f"probability={probability}%, snow_risk={snow_risk}"
                )
        elif temperature is not None and 2.0 < temperature <= 4.0 and probability >= 50:
            # Marginal snow temperature + high probability → mixed precipitation
            self._attr_icon = "mdi:weather-snowy-rainy"
            precipitation_type = "mixed"
            _LOGGER.debug(
                f"RainProb: Icon set to MIXED (temp={temperature:.1f}°C, probability={probability}%)"
            )
        else:
            # Warm temperature or no temperature data → RAIN
            self._attr_icon = "mdi:weather-rainy"
            precipitation_type = "rain"
            _LOGGER.debug(
                f"RainProb: Icon set to RAIN (temp={temperature if temperature is not None else 'unknown'}°C, probability={probability}%)"
            )

        self._state = round(probability)
        _LOGGER.debug(f"RainProb: Setting state to: {round(probability)}%")

        # Calculate base probability based on selected model
        # ✅ FIXED v3.1.10: Respect model selection AND use dynamic weights
        if forecast_model == FORECAST_MODEL_ZAMBRETTI:
            base_prob = zambretti_prob  # Only Zambretti
        elif forecast_model == FORECAST_MODEL_NEGRETTI:
            base_prob = negretti_prob   # Only Negretti
        else:  # FORECAST_MODEL_ENHANCED
            # ✅ NEW v3.1.10: Use weighted average, not simple average!
            # Same logic as Enhanced sensor for consistency
            base_prob = (zambretti_prob * zambretti_weight) + (negretti_prob * negretti_weight)
            _LOGGER.debug(
                f"RainProb: Weighted base_prob = "
                f"({zambretti_prob}% × {zambretti_weight:.2f}) + "
                f"({negretti_prob}% × {negretti_weight:.2f}) = {base_prob:.1f}%"
            )

        self._attributes = {
            "forecast_model": forecast_model,  # Show which model is used
            "zambretti_probability": round(zambretti_prob),
            "negretti_probability": round(negretti_prob),
            "base_probability": round(base_prob),  # Now uses weighted average!
            "enhanced_probability": round(probability),
            "confidence": confidence,
            "humidity": humidity,
            "dewpoint_spread": dewpoint_spread,
            "current_rain_rate": current_rain,
            "temperature": temperature,
            "precipitation_type": precipitation_type,
            "factors_used": self._get_factors_used(forecast_model, humidity, dewpoint_spread),
            # ✅ NEW v3.1.10: Export weights for transparency
            "zambretti_weight": round(zambretti_weight, 2) if forecast_model == FORECAST_MODEL_ENHANCED else None,
            "negretti_weight": round(negretti_weight, 2) if forecast_model == FORECAST_MODEL_ENHANCED else None,
        }

    def _get_factors_used(self, forecast_model, humidity, dewpoint_spread):
        """Get list of factors used in calculation based on selected model."""
        # ✅ FIXED v3.1.10: Show only factors from selected model
        factors = []

        from .const import FORECAST_MODEL_ZAMBRETTI, FORECAST_MODEL_NEGRETTI

        if forecast_model == FORECAST_MODEL_ZAMBRETTI:
            factors.append("Zambretti")
        elif forecast_model == FORECAST_MODEL_NEGRETTI:
            factors.append("Negretti-Zambra")
        else:  # Enhanced
            factors.extend(["Zambretti", "Negretti-Zambra"])

        if humidity is not None:
            factors.append("Humidity")
        if dewpoint_spread is not None:
            factors.append("Dewpoint spread")
        return factors
