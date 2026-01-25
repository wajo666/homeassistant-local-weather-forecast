"""Weather entity for Local Weather Forecast integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
    ATTR_FORECAST_CLOUD_COVERAGE,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_IS_DAYTIME,
    ATTR_FORECAST_NATIVE_APPARENT_TEMP,
    ATTR_FORECAST_NATIVE_DEW_POINT,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_PRESSURE,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_GUST_SPEED,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_WIND_BEARING,
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
from homeassistant.helpers.entity import DeviceInfo

from .calculations import (
    calculate_apparent_temperature,
    calculate_dewpoint,
    get_comfort_level,
    get_fog_risk,
)
from .const import (
    CONF_ELEVATION,
    CONF_ENABLE_WEATHER_ENTITY,
    CONF_FORECAST_MODEL,
    CONF_HEMISPHERE,
    CONF_HUMIDITY_SENSOR,
    CONF_LATITUDE,
    CONF_PRESSURE_SENSOR,
    CONF_RAIN_RATE_SENSOR,
    CONF_SOLAR_RADIATION_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_VISIBILITY_SENSOR,
    CONF_WIND_DIRECTION_SENSOR,
    CONF_WIND_GUST_SENSOR,
    CONF_WIND_SPEED_SENSOR,
    DEFAULT_ENABLE_WEATHER_ENTITY,
    DEFAULT_ELEVATION,
    DEFAULT_FORECAST_MODEL,
    DEFAULT_LATITUDE,
    DOMAIN,
    FORECAST_MODEL_ENHANCED,
    FORECAST_MODEL_NEGRETTI,
    FORECAST_MODEL_ZAMBRETTI,
)
from .forecast_calculator import (
    DailyForecastGenerator,
    HourlyForecastGenerator,
    PressureModel,
    TemperatureModel,
    ZambrettiForecaster,
)
from .language import get_wind_type, get_visibility_estimate
from .unit_conversion import UnitConverter

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
    _attr_native_visibility_unit = "km"  # HA auto-converts km ↔ mi based on user settings
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the weather entity."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_weather"
        self._attr_name = "Weather"
        self._attr_device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Local Weather Forecast",
            manufacturer="Local Weather Forecast",
            model="Zambretti/Negretti-Zambra",
            sw_version="3.1.10",
        )
        self._last_rain_time = None  # Track when it last rained (for 15-min timeout)
        self._last_rain_value = None  # Track last rain sensor value (for accumulation sensors)
        self._last_rain_check_time = None  # Track when we last checked (for rate calculation)
        self._hail_conditions_present = False  # Track if atmospheric conditions favor hail (v3.1.10)

        # Log rain sensor configuration at startup
        rain_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
        if rain_sensor_id:
            _LOGGER.debug(f"Weather: Rain sensor configured: {rain_sensor_id}")

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass - wait for ALL configured sensors to be ready."""
        await super().async_added_to_hass()

        import asyncio
        from datetime import datetime
        from homeassistant.helpers.event import async_track_state_change_event

        # Collect ALL configured sensors from config_flow
        all_sensor_keys = [
            CONF_PRESSURE_SENSOR,       # Required
            CONF_TEMPERATURE_SENSOR,    # Optional (uses defaults)
            CONF_HUMIDITY_SENSOR,       # Optional (enhanced features)
            CONF_WIND_SPEED_SENSOR,     # Optional (wind analysis)
            CONF_WIND_DIRECTION_SENSOR, # Optional (wind direction)
            CONF_WIND_GUST_SENSOR,      # Optional (atmosphere stability)
            CONF_RAIN_RATE_SENSOR,      # Optional (precipitation detection)
            CONF_SOLAR_RADIATION_SENSOR,# Optional (cloudiness detection)
            CONF_VISIBILITY_SENSOR,     # Optional (visibility)
        ]

        configured_sensors = {}
        for sensor_key in all_sensor_keys:
            sensor_id = self._get_config(sensor_key)
            if sensor_id:
                configured_sensors[sensor_key] = sensor_id

        if not configured_sensors:
            _LOGGER.warning(
                "Weather: No sensors configured! Weather entity will use defaults. "
                "If you add sensors later through config, they will be used automatically."
            )
            # Don't return - continue to set up basic entity
            # This allows manual state writes and future sensor additions

        # Log all configured sensors
        if configured_sensors:
            _LOGGER.info(f"Weather: Found {len(configured_sensors)} configured sensors:")
            for key, sensor_id in configured_sensors.items():
                is_required = "(REQUIRED)" if key == CONF_PRESSURE_SENSOR else "(optional)"
                _LOGGER.info(f"  - {key}: {sensor_id} {is_required}")

            # Wait for sensors with timeout
            start_time = datetime.now()
            max_wait = 30  # Maximum 30 seconds wait
            check_interval = 0.5  # Check every 500ms

            _LOGGER.info(f"Weather: Waiting up to {max_wait}s for sensors to become ready...")

            sensors_ready = {}
            elapsed = 0

            while elapsed < max_wait:
                # Check each configured sensor
                all_ready = True
                for key, sensor_id in configured_sensors.items():
                    if key not in sensors_ready:  # Not yet ready
                        state = self.hass.states.get(sensor_id)
                        if state and state.state not in ("unknown", "unavailable"):
                            sensors_ready[key] = sensor_id
                            elapsed_time = (datetime.now() - start_time).total_seconds()
                            _LOGGER.info(
                                f"Weather: ✅ {key} ready after {elapsed_time:.1f}s "
                                f"({len(sensors_ready)}/{len(configured_sensors)})"
                            )
                        else:
                            all_ready = False

                # If all sensors ready, break early
                if all_ready:
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    _LOGGER.info(
                        f"Weather: 🎉 All {len(configured_sensors)} sensors ready after {elapsed_time:.1f}s! "
                        f"Weather entity is fully operational."
                    )
                    break

                await asyncio.sleep(check_interval)
                elapsed += check_interval

            # Report timeout for sensors that didn't load
            if elapsed >= max_wait:
                missing_sensors = []
                for key, sensor_id in configured_sensors.items():
                    if key not in sensors_ready:
                        missing_sensors.append(f"{key} ({sensor_id})")

                if missing_sensors:
                    _LOGGER.warning(
                        f"Weather: ⏱️ Timeout after {max_wait}s. "
                        f"{len(sensors_ready)}/{len(configured_sensors)} sensors ready. "
                        f"Missing: {', '.join(missing_sensors)}"
                    )

                    # Check if pressure sensor (REQUIRED) is missing
                    if CONF_PRESSURE_SENSOR not in sensors_ready:
                        _LOGGER.error(
                            f"Weather: ❌ CRITICAL: Pressure sensor not ready! "
                            f"Weather entity will show 'partlycloudy' until pressure sensor initializes."
                        )
                    else:
                        _LOGGER.info(
                            f"Weather: ✅ Pressure sensor ready. Weather entity will work with available sensors. "
                            f"Missing sensors will be used when they become available."
                        )

        # Set up state change listeners for auto-refresh when sensors update
        # This handles both:
        # 1. Sensors that didn't load during startup (will auto-refresh when they appear)
        # 2. Normal sensor updates during operation
        sensors_to_track = list(configured_sensors.values())

        if sensors_to_track:
            _LOGGER.info(
                f"Weather: 📡 Tracking {len(sensors_to_track)} sensors for auto-refresh "
                f"(includes sensors not yet available)"
            )

            async def sensor_state_changed(event):
                """Handle sensor state changes - trigger weather entity update."""
                entity_id = event.data.get("entity_id")
                old_state = event.data.get("old_state")
                new_state = event.data.get("new_state")

                # Only update if state actually changed (not just attributes)
                if old_state and new_state and old_state.state != new_state.state:
                    # Check if transitioning from unavailable/unknown to valid
                    if old_state.state in ("unknown", "unavailable") and new_state.state not in ("unknown", "unavailable"):
                        _LOGGER.info(
                            f"Weather: 🔄 Sensor {entity_id} became available "
                            f"({old_state.state} → {new_state.state}), triggering refresh"
                        )

                    # Trigger weather entity state update
                    self.async_write_ha_state()

            self.async_on_remove(
                async_track_state_change_event(self.hass, sensors_to_track, sensor_state_changed)
            )


    def _get_config(self, key: str) -> Any:
        """Get configuration value from options or data."""
        return self._entry.options.get(key, self._entry.data.get(key))

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        if not self.hass:
            return None
        temp_sensor = self._get_config(CONF_TEMPERATURE_SENSOR)
        if temp_sensor:
            state = self.hass.states.get(temp_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    value = float(state.state)
                    # Apply unit conversion
                    unit = state.attributes.get("unit_of_measurement")
                    if unit:
                        return UnitConverter.convert_sensor_value(value, "temperature", unit)
                    return value
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure."""
        if not self.hass:
            return None
        pressure_sensor = self._get_config(CONF_PRESSURE_SENSOR)
        if pressure_sensor:
            state = self.hass.states.get(pressure_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    value = float(state.state)
                    # Apply unit conversion
                    unit = state.attributes.get("unit_of_measurement")
                    if unit:
                        return UnitConverter.convert_sensor_value(value, "pressure", unit)
                    return value
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def humidity(self) -> float | None:
        """Return the humidity."""
        if not self.hass:
            return None
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
        if not self.hass:
            return None
        wind_speed_sensor = self._get_config(CONF_WIND_SPEED_SENSOR)
        if wind_speed_sensor:
            state = self.hass.states.get(wind_speed_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    value = float(state.state)
                    # Apply unit conversion
                    unit = state.attributes.get("unit_of_measurement")
                    if unit:
                        return UnitConverter.convert_sensor_value(value, "wind_speed", unit)
                    return value
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def wind_bearing(self) -> float | str | None:
        """Return the wind bearing."""
        if not self.hass:
            return None
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
        if not self.hass:
            return None
        wind_gust_sensor = self._get_config(CONF_WIND_GUST_SENSOR)
        if wind_gust_sensor:
            state = self.hass.states.get(wind_gust_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    value = float(state.state)
                    # Apply unit conversion
                    unit = state.attributes.get("unit_of_measurement")
                    if unit:
                        converted = UnitConverter.convert_sensor_value(value, "wind_speed", unit)
                        _LOGGER.debug(
                            f"Weather: Wind gust converted: {value} {unit} → {converted:.2f} m/s"
                        )
                        return converted
                    return value
                except (ValueError, TypeError):
                    pass
        return None

    @property
    def native_dew_point(self) -> float | None:
        """Return the dew point temperature."""
        if not self.hass:
            return None

        # Calculate from temperature and humidity if available
        temp = self.native_temperature
        humidity = self.humidity
        if temp is not None and humidity is not None:
            return calculate_dewpoint(temp, humidity)

        return None

    @property
    def feels_like(self) -> float | None:
        """Return the feels like temperature (alias for native_apparent_temperature).

        This is an alias to ensure compatibility with templates that use
        state_attr("weather.entity", "feels_like").

        Returns:
            Apparent temperature, or actual temperature as fallback.
            Never returns None to prevent template errors.
        """
        apparent = self.native_apparent_temperature
        if apparent is not None:
            return apparent

        # Fallback to actual temperature if apparent temperature unavailable
        temp = self.native_temperature
        if temp is not None:
            return temp

        # Last resort - return 0 to prevent None errors in templates
        return 0.0


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
        if not self.hass:
            return None
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
                    raw_value = float(solar_state.state)
                    unit = solar_state.attributes.get("unit_of_measurement", "W/m²")
                    # Convert to W/m² (from lux if needed)
                    solar_radiation = UnitConverter.convert_solar_radiation(raw_value, unit)
                except (ValueError, TypeError):
                    pass

        # Calculate with all available sensors
        return calculate_apparent_temperature(
            temp,
            humidity,
            wind_speed_kmh,
            solar_radiation
        )

    @property
    def cloud_coverage(self) -> int | None:
        """Return the cloud coverage in %.

        Reuses existing solar radiation calculation from condition() method.
        Returns percentage (0-100) where 0 = clear sky, 100 = overcast.

        This uses the same WMO-standard calculation as weather condition determination,
        ensuring consistency between condition and cloud_coverage values.
        """
        if not self.hass:
            return None

        solar_sensor_id = self._get_config(CONF_SOLAR_RADIATION_SENSOR)
        if not solar_sensor_id:
            return None

        solar_state = self.hass.states.get(solar_sensor_id)
        if not solar_state or solar_state.state in ("unknown", "unavailable"):
            return None

        try:
            # Get solar radiation value with unit conversion
            raw_value = float(solar_state.state)
            unit = solar_state.attributes.get("unit_of_measurement", "W/m²")
            solar_radiation = UnitConverter.convert_solar_radiation(raw_value, unit)

            # Get sun elevation for theoretical maximum calculation
            from datetime import datetime
            from math import sin, radians

            sun_state = self.hass.states.get("sun.sun")
            solar_elevation_deg = 0
            if sun_state:
                solar_elevation_deg = sun_state.attributes.get("elevation", 0)

            # Only calculate during daytime (sun above horizon)
            if solar_elevation_deg <= 0:
                return None

            # Calculate theoretical maximum using same formula as condition()
            # This ensures consistency between cloud_coverage and condition
            solar_constant = 1361  # W/m² at top of atmosphere
            solar_elevation_rad = radians(solar_elevation_deg)
            sin_elev = sin(solar_elevation_rad)

            # Calculate air mass
            if solar_elevation_deg < 5:
                air_mass = 10.0
            else:
                air_mass = 1.0 / sin_elev

            # Atmospheric transmission with Linke turbidity
            from math import exp
            linke_turbidity = 3.0  # Standard value for urban areas
            transmission = exp(-0.09 * air_mass * linke_turbidity)

            # Calculate theoretical maximum
            theoretical_max = solar_constant * transmission * sin_elev

            # Apply elevation correction
            elevation = self.hass.config.elevation or 0
            if elevation > 0:
                elevation_factor = 1 + (elevation / 1000) * 0.12
                theoretical_max *= elevation_factor

            # WMO: Use any positive solar radiation value (not just >50 W/m²)
            # This allows accurate cloudiness detection even in low-light conditions
            if theoretical_max > 0:  # Avoid division by zero
                # Calculate sky transparency (same as in condition())
                sky_transparency = solar_radiation / theoretical_max if theoretical_max > 0 else 0
                # Cloud coverage = 100% - transparency%
                cloud_percent = int(max(0, min(100, (1 - sky_transparency) * 100)))
                return cloud_percent

        except (ValueError, TypeError, ZeroDivisionError):
            pass

        return None

    @property
    def native_visibility(self) -> float | None:
        """Return the visibility in km (native unit).

        Home Assistant will automatically convert to miles if user has imperial system.

        WMO-compliant visibility estimation:
        1. Base calculation from humidity (8 WMO categories)
        2. Further reduced if fog conditions detected (dewpoint spread)

        Visibility categories (WMO-No. 8):
        - Excellent: > 40 km (RH < 50%)
        - Very good: 20-40 km (RH 50-60%)
        - Good: 10-20 km (RH 60-70%)
        - Moderate: 4-10 km (RH 70-80%)
        - Poor: 2-4 km (RH 80-85%)
        - Very poor: 1-2 km (RH 85-90%)
        - Mist: 1-5 km (RH 90-95%)
        - Fog: < 1 km (RH > 95%)
        """
        if not self.hass:
            return None

        # Get humidity and temperature for visibility estimation
        humidity = self.humidity
        temp = self.native_temperature

        if humidity is None or temp is None:
            return None

        # Calculate visibility from humidity and temperature (returns km)
        from .calculations import calculate_visibility_from_humidity

        visibility_km = calculate_visibility_from_humidity(humidity, temp)

        # Further reduce visibility if fog conditions detected
        dewpoint = self.native_dew_point

        if dewpoint is not None:
            spread = temp - dewpoint

            # Critical fog (spread < 0.5°C) = very low visibility
            if spread < 0.5:
                visibility_km = min(visibility_km, 0.2)  # < 200m
            # High fog risk (spread < 1.0°C) = low visibility
            elif spread < 1.0:
                visibility_km = min(visibility_km, 0.5)  # < 500m
            # Medium fog risk (spread < 1.5°C) = moderate visibility
            elif spread < 1.5:
                visibility_km = min(visibility_km, 1.0)  # < 1km

        # Return km (Home Assistant auto-converts to miles for imperial users)
        return round(visibility_km, 1)

    @property
    def uv_index(self) -> float | None:
        """Return the UV index.

        Calculated from solar radiation if available.
        Scale: 0-15+ (0-2 low, 3-5 moderate, 6-7 high, 8-10 very high, 11+ extreme)
        """
        if not self.hass:
            return None

        solar_sensor_id = self._get_config(CONF_SOLAR_RADIATION_SENSOR)
        if not solar_sensor_id:
            return None

        solar_state = self.hass.states.get(solar_sensor_id)
        if not solar_state or solar_state.state in ("unknown", "unavailable"):
            return None

        try:
            raw_value = float(solar_state.state)
            unit = solar_state.attributes.get("unit_of_measurement", "W/m²")
            solar_radiation = UnitConverter.convert_solar_radiation(raw_value, unit)

            # Calculate UV index from solar radiation
            from .calculations import calculate_uv_index_from_solar_radiation
            uv = calculate_uv_index_from_solar_radiation(solar_radiation)

            return round(uv, 1)

        except (ValueError, TypeError):
            pass

        return None

    @property
    def condition(self) -> str | None:
        """Return the current condition based on Zambretti forecast and current weather."""
        try:
            # Safety check - if hass is not available yet, return default
            if not self.hass:
                return ATTR_CONDITION_PARTLYCLOUDY

            # ========================================================================
            # SECTION 1: HARD OVERRIDES (return immediately if condition met)
            # These conditions are DEFINITIVE - if detected, they end evaluation
            # ========================================================================

            # PRIORITY 0: EXCEPTIONAL & HAIL - Extreme weather conditions (highest priority!)
            # These override ALL other conditions for safety warnings
            pressure = self.native_pressure
            if pressure is not None:
                # Get pressure change for bomb cyclone detection
                pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
                pressure_change = 0.0
                if pressure_change_sensor and pressure_change_sensor.state not in ("unknown", "unavailable", None):
                    try:
                        pressure_change = float(pressure_change_sensor.state)
                    except (ValueError, TypeError):
                        pass

                # EXCEPTIONAL: Extreme pressure (hurricane, bomb cyclone, extreme anticyclone)
                # ✅ Using independent 'if' checks - each condition is evaluated separately
                # This ensures we catch all exceptional scenarios and log all reasons
                if pressure < 920:
                    # Hurricane-force low pressure
                    _LOGGER.debug(
                        f"⚠️ EXCEPTIONAL WEATHER: Hurricane-force low pressure detected! "
                        f"Pressure={pressure:.1f} hPa < 920 hPa"
                    )
                    return "exceptional"

                if pressure > 1070:
                    # Extreme high pressure (Siberian anticyclone)
                    _LOGGER.debug(
                        f"⚠️ EXCEPTIONAL WEATHER: Extreme high pressure detected! "
                        f"Pressure={pressure:.1f} hPa > 1070 hPa"
                    )
                    return "exceptional"

                if abs(pressure_change) > 10:
                    # Bomb cyclogenesis (rapid pressure change)
                    # Can occur at ANY pressure - independent of absolute pressure value
                    _LOGGER.debug(
                        f"⚠️ EXCEPTIONAL WEATHER: Bomb cyclone detected! "
                        f"Rapid pressure change: {pressure_change:+.1f} hPa/3h"
                    )
                    return "exceptional"

                # HAIL: Severe thunderstorm conditions
                # ✅ NEW v3.1.10: Check actual current conditions, not forecast!
                # Hail requires:
                # 1. Active precipitation (will be checked in PRIORITY 1)
                # 2. Convective temperature (15-30°C)
                # 3. High humidity (>80%)
                # 4. Very unstable atmosphere (gust_ratio >2.5)

                # We check these conditions here; if precipitation is detected in PRIORITY 1,
                # and these conditions are met, PRIORITY 1 will return "hail" instead of rain.
                # For now, we just store hail_risk_present flag for later use.

                temp = self.native_temperature
                humidity = self.humidity

                # Get gust ratio from enhanced sensor
                enhanced_sensor = self.hass.states.get("sensor.local_forecast_enhanced")
                gust_ratio = None
                if enhanced_sensor and enhanced_sensor.state not in ("unknown", "unavailable"):
                    gust_ratio = enhanced_sensor.attributes.get("gust_ratio")

                # Set internal flag if atmospheric conditions favor hail
                # (actual hail detection happens in PRIORITY 1 when precipitation is confirmed)
                if temp is not None and humidity is not None and gust_ratio is not None:
                    self._hail_conditions_present = (
                        15 <= temp <= 30 and
                        humidity > 80 and
                        gust_ratio > 2.5
                    )

                    if self._hail_conditions_present:
                        _LOGGER.debug(
                            f"Weather: ⚠️ HAIL-FAVORABLE conditions detected! "
                            f"Temp={temp:.1f}°C (convective zone), Humidity={humidity:.0f}% (high), "
                            f"Gust ratio={gust_ratio:.2f} (very unstable). "
                            f"Will return HAIL if active precipitation is detected."
                        )
                else:
                    self._hail_conditions_present = False

            # PRIORITY 1: Check if currently raining (Netatmo INCREMENT sensor detection)
            rain_rate_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
            if rain_rate_sensor_id:
                rain_sensor = self.hass.states.get(rain_rate_sensor_id)
                if rain_sensor and rain_sensor.state not in ("unknown", "unavailable", None):
                    try:
                        from datetime import datetime
                        current_rain = float(rain_sensor.state)
                        now = datetime.now()

                        # Detect sensor type by device_class and unit_of_measurement
                        attrs = rain_sensor.attributes or {}
                        device_class = attrs.get("device_class", "")
                        unit = attrs.get("unit_of_measurement", "")

                        # Log sensor detection on first run
                        if self._last_rain_value is None and self._last_rain_time is None:
                            _LOGGER.debug(
                                f"Weather: Rain sensor detected as ACCUMULATION sensor (mm): "
                                f"entity={rain_rate_sensor_id}, "
                                f"device_class={device_class}, "
                                f"unit={unit}, "
                                f"current_value={current_rain}"
                            )

                        is_raining_now = False

                        # For Netatmo ACCUMULATION sensors (device_class=precipitation, unit=mm):
                        # - Value > 0 means it rained recently (last 5 minutes)
                        # - Value resets to 0 when no rain detected for ~5 minutes
                        if device_class == "precipitation" and unit == "mm":
                            if current_rain > 0:
                                # Netatmo shows last increment (0.101, 0.202, etc.)
                                is_raining_now = True
                                _LOGGER.debug(
                                    f"Weather: Netatmo rain detected: {current_rain} mm → RAINING"
                                )
                            else:
                                # No rain detected (sensor = 0)
                                _LOGGER.debug(f"Weather: No rain detected (sensor = {current_rain} mm)")
                        else:
                            # For other rain sensors (mm/h rate sensors)
                            if current_rain > 0.1:
                                is_raining_now = True
                                _LOGGER.debug(f"Weather: Rain rate sensor: {current_rain} mm/h → RAINING")

                        # Update last value and time for next check
                        self._last_rain_value = current_rain
                        self._last_rain_check_time = now

                        # If precipitation is detected, check temperature to determine if it's rain or snow
                        if is_raining_now:
                            temp = self.native_temperature

                            # Check if fog is also present (secondary condition)
                            # Fog info will be added to attributes even though precipitation has priority
                            fog_also_present = False
                            dewpoint = self.native_dew_point
                            humidity = self.humidity
                            dewpoint_spread = 0.0  # Initialize for logging
                            wind_speed = 0.0  # Initialize for logging

                            if temp is not None and dewpoint is not None and humidity is not None:
                                dewpoint_spread = temp - dewpoint
                                wind_speed = self.native_wind_speed or 0.0

                                # Check fog conditions (same logic as PRIORITY 2)
                                if (dewpoint_spread < 0.5 and humidity > 95) or \
                                   (dewpoint_spread < 1.0 and humidity > 93 and wind_speed < 3.0) or \
                                   (1.5 <= dewpoint_spread < 2.5 and humidity > 85 and wind_speed < 2.0):
                                    fog_also_present = True

                            # Determine precipitation type based on temperature and humidity
                            # Scientific meteorological standards (WMO, NOAA):
                            #
                            # Mixed precipitation occurs when air temperature is near freezing
                            # but conditions allow both snow and rain to coexist.
                            #
                            # Key factors:
                            # 1. Temperature (air temperature)
                            # 2. Humidity (affects wet bulb temperature)
                            # 3. Atmospheric conditions
                            #
                            # Boundaries (simplified without wet bulb sensor):
                            # - Pure snow: temp < -1°C (always frozen)
                            # - Mixed zone: -1°C ≤ temp ≤ 4°C (depends on humidity)
                            #   * High humidity (>85%): snow melts partially → mixed
                            #   * Low humidity (<85%): depends on temp
                            # - Pure rain: temp > 4°C (always liquid)

                            if temp is not None:
                                # Get humidity for wet bulb approximation
                                current_humidity = humidity if humidity is not None else 70.0

                                if temp < -1:
                                    # SNOW - Cold enough that all precipitation is frozen
                                    # Below -1°C, humidity doesn't matter - too cold for melting
                                    if fog_also_present and dewpoint is not None and humidity is not None:
                                        _LOGGER.info(
                                            f"Weather: ⚠️ SNOWY + FOG detected simultaneously! "
                                            f"temp={temp:.1f}°C (frozen precipitation), "
                                            f"dewpoint_spread={dewpoint_spread:.1f}°C, humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s. "
                                            f"Showing SNOWY (precipitation priority), fog_detected=True in attributes."
                                        )
                                    else:
                                        _LOGGER.debug(
                                            f"Weather: SNOW detected - "
                                            f"temp={temp:.1f}°C < -1°C (pure frozen precipitation)"
                                        )
                                    return ATTR_CONDITION_SNOWY

                                elif -1 <= temp <= 4:
                                    # TRANSITION ZONE - Mixed precipitation possible
                                    # Depends on humidity (wet bulb approximation)

                                    # Scientific criteria for mixed precipitation:
                                    # 1. Temperature in transition zone (-1°C to +4°C)
                                    # 2. High humidity (>85%) increases melting → mixed
                                    # 3. Low temperature + low humidity → still snow
                                    # 4. High temperature + any humidity → starting to be rain

                                    if temp <= 1 and current_humidity < 85:
                                        # Cold + dry → SNOW
                                        # Snowflakes don't melt in dry air even near 0°C
                                        _LOGGER.debug(
                                            f"Weather: SNOW detected - "
                                            f"temp={temp:.1f}°C, humidity={current_humidity:.0f}% "
                                            f"(cold + dry = frozen precipitation)"
                                        )
                                        return ATTR_CONDITION_SNOWY

                                    elif temp >= 3 and current_humidity > 85:
                                        # Warm + humid → RAIN
                                        # Snow melts completely in humid warm air
                                        _LOGGER.debug(
                                            f"Weather: RAIN detected - "
                                            f"temp={temp:.1f}°C, humidity={current_humidity:.0f}% "
                                            f"(warm + humid = liquid precipitation)"
                                        )
                                        # Continue to rain logic below
                                        pass  # Will be handled by rain logic

                                    else:
                                        # MIXED (SNOWY-RAINY) - Transition conditions
                                        # Temperature and humidity in range where both can occur
                                        if fog_also_present and dewpoint is not None and humidity is not None:
                                            _LOGGER.info(
                                                f"Weather: ⚠️ MIXED PRECIPITATION + FOG detected simultaneously! "
                                                f"temp={temp:.1f}°C, humidity={current_humidity:.0f}% (transition zone), "
                                                f"dewpoint_spread={dewpoint_spread:.1f}°C, wind={wind_speed:.1f} m/s. "
                                                f"Showing SNOWY-RAINY (mixed precipitation), fog_detected=True in attributes."
                                            )
                                        else:
                                            _LOGGER.debug(
                                                f"Weather: MIXED precipitation (snow + rain) detected - "
                                                f"temp={temp:.1f}°C, humidity={current_humidity:.0f}% "
                                                f"(transition zone - both snow and rain possible)"
                                            )
                                        return ATTR_CONDITION_SNOWY_RAINY

                                # If we reach here, precipitation is liquid (RAIN or POURING):
                                # - temp > 4°C (outside transition zone), OR
                                # - temp 3-4°C + humidity > 85% (warm + humid in transition zone)
                                # Note: Other transition zone cases already returned SNOW (temp ≤1°C, dry)
                                #       or MIXED (temp 1-3°C or temp 3-4°C with humidity ≤85%)

                                # ✅ NEW v3.1.10: Check for HAIL before returning rain/pouring
                                # Hail occurs during severe thunderstorms with:
                                # - Active precipitation (already confirmed above)
                                # - Convective temperature (15-30°C)
                                # - High humidity (>80%)
                                # - Very unstable atmosphere (gust_ratio >2.5)
                                if hasattr(self, '_hail_conditions_present') and self._hail_conditions_present:
                                    _LOGGER.info(
                                        f"🧊 HAIL DETECTED! Active precipitation + hail-favorable atmospheric conditions. "
                                        f"Temp={temp:.1f}°C (convective), Humidity={current_humidity:.0f}% (high), "
                                        f"Gust ratio >2.5 (very unstable). Returning HAIL condition."
                                    )
                                    return ATTR_CONDITION_HAIL

                                # RAIN or POURING - Liquid precipitation
                                # For rate sensors (mm/h), we can detect intensity
                                # For accumulation sensors (mm), we cannot reliably detect intensity

                                # Check if this is a rate sensor with high intensity
                                is_pouring = False
                                if unit == "mm/h" and current_rain > 10:
                                    # Rate sensor + high rate + warm temp → POURING
                                    # WMO: > 10 mm/h = heavy rain (pouring)
                                    # Warm temperature (> 10°C) increases likelihood of convective rain
                                    if temp > 10:
                                        is_pouring = True

                                if is_pouring:
                                    # POURING - Heavy convective rain
                                    if fog_also_present and dewpoint is not None and humidity is not None:
                                        _LOGGER.info(
                                            f"Weather: ⚠️ POURING + FOG detected simultaneously! "
                                            f"rate={current_rain:.1f} mm/h (heavy rain), temp={temp:.1f}°C, "
                                            f"dewpoint_spread={dewpoint_spread:.1f}°C, humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s. "
                                            f"Showing POURING (precipitation priority), fog_detected=True in attributes."
                                        )
                                    else:
                                        _LOGGER.debug(
                                            f"Weather: Heavy rain (POURING) detected - "
                                            f"rate={current_rain:.1f} mm/h, temp={temp:.1f}°C"
                                        )
                                    return ATTR_CONDITION_POURING
                                else:
                                    # RAINY - Light to moderate rain
                                    if fog_also_present and dewpoint is not None and humidity is not None:
                                        _LOGGER.info(
                                            f"Weather: ⚠️ RAINY + FOG detected simultaneously! "
                                            f"temp={temp:.1f}°C, "
                                            f"dewpoint_spread={dewpoint_spread:.1f}°C, humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s. "
                                            f"Showing RAINY (precipitation priority), fog_detected=True in attributes."
                                        )
                                    else:
                                        _LOGGER.debug(
                                            f"Weather: Rain detected - temp={temp:.1f}°C"
                                        )
                                    return ATTR_CONDITION_RAINY

                            else:
                                # Temperature is None - cannot determine type, default to RAINY
                                _LOGGER.debug(
                                    f"Weather: Precipitation detected but temperature unknown - defaulting to RAINY"
                                )
                                return ATTR_CONDITION_RAINY

                    except (ValueError, TypeError) as e:
                        _LOGGER.debug(f"Weather: Error processing rain sensor: {e}")
                        pass

            # PRIORITY 2: Check for snow/ice/fog conditions (current observable weather)
            # These are visible weather phenomena and should override forecast
            from datetime import datetime as dt
            temp = self.native_temperature
            humidity = self.humidity
            dewpoint = self.native_dew_point

            if temp is not None and dewpoint is not None and humidity is not None:
                dewpoint_spread = temp - dewpoint
                current_hour = dt.now().hour

                # Get rain/snow probability sensor value (used for multiple checks)
                rain_prob_sensor = self.hass.states.get("sensor.local_forecast_rain_probability")
                rain_prob = 0
                if rain_prob_sensor and rain_prob_sensor.state not in ("unknown", "unavailable", None):
                    try:
                        rain_prob = float(rain_prob_sensor.state)
                    except (ValueError, TypeError):
                        pass

                # Get snow risk sensor if available (v3.1.3+)
                snow_risk = None
                snow_risk_sensor = self.hass.states.get("sensor.local_forecast_enhanced")
                if snow_risk_sensor and snow_risk_sensor.state not in ("unknown", "unavailable", None):
                    try:
                        snow_risk_attrs = snow_risk_sensor.attributes or {}
                        snow_risk = snow_risk_attrs.get("snow_risk", None)
                    except (AttributeError, KeyError, TypeError):
                        pass

                # SNOW CONDITIONS - REMOVED FROM PRIORITY 2
                # Snow risk is a PREDICTION, not current observation!
                # PRIORITY 2 is for observable weather (fog, active precipitation from sensor)
                # Snow risk will be handled in PRIORITY 3 (forecast conversion)
                #
                # This prevents showing "snowy" when it's actually sunny with just high snow RISK
                # Example: -11.8°C, sunny, 81% humidity, snow_risk=medium, rain_prob=63%
                #          → Should show SUNNY, not SNOWY (no active precipitation!)

                # Log snow risk for debugging, but don't return SNOWY here
                if snow_risk in ("high", "medium", "Vysoké riziko snehu", "Stredné riziko snehu"):
                    _LOGGER.debug(
                        f"Weather: Snow risk detected ({snow_risk}) with rain_prob={rain_prob}% - "
                        f"temp={temp:.1f}°C, humidity={humidity:.1f}%, spread={dewpoint_spread:.1f}°C. "
                        f"Not showing snowy in PRIORITY 2 (no active precipitation). "
                        f"Will use forecast model to determine condition."
                    )


                # FOG CONDITIONS (WMO/NOAA/MetOffice compliant model):
                #
                # WMO DEFINITION (WMO-No. 8, Manual of Codes):
                # FOG: Visibility < 1000m, RH > 90%, dewpoint spread < 1.5°C
                # MIST: Visibility 1-5km, RH 85-95%, dewpoint spread 1.5-4°C
                #
                # Fog requires:
                # 1. Very low dewpoint spread (< 1.5°C per WMO)
                # 2. High humidity (> 90% per WMO)
                # 3. Calm weather (fog dissipates with wind > 3 m/s)
                # 4. Night factor (fog forms easier at night, dissipates during day)
                #
                # Three-level WMO-compliant model (100% WMO compliance):
                # - CRITICAL: spread < 0.5°C + RH > 95% → dense fog (vis < 400m, WMO code 12)
                # - LIKELY: spread < 1.0°C + RH > 90% + calm → fog (vis 400-1000m, WMO code 11)
                # - POSSIBLE (night): spread 1.0-1.5°C + RH > 90% + night + calm → light fog (WMO code 10)
                # - MIST: spread 1.5-4°C + RH > 85% → show CLOUDY, not FOG (WMO code 30)

                # Get wind speed for fog dissipation check
                wind_speed = self.native_wind_speed or 0.0

                # Determine if night (fog forms easier, less likely to dissipate)
                is_night = current_hour < 6 or current_hour >= 20

                # LEVEL 1: CRITICAL FOG (WMO Code 12 - Dense fog)
                # Dense fog, visibility < 400m
                if dewpoint_spread < 0.5 and humidity > 95:
                    _LOGGER.debug(
                        f"Weather: FOG (CRITICAL) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s, "
                        f"hour={current_hour} (dense fog, visibility < 400m, WMO code 12)"
                    )
                    return ATTR_CONDITION_FOG

                # LEVEL 2: LIKELY FOG (WMO Code 11 - Fog)
                # Moderate fog, visibility 400-1000m, requires calm weather
                # WMO compliant: spread < 1.0°C + RH > 90%
                elif dewpoint_spread < 1.0 and humidity > 90 and wind_speed < 3.0:
                    _LOGGER.debug(
                        f"Weather: FOG (LIKELY) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s, "
                        f"hour={current_hour} (fog, calm weather, WMO code 11)"
                    )
                    return ATTR_CONDITION_FOG

                # LEVEL 3: POSSIBLE FOG (WMO Code 10 - Light fog, night only)
                # Light fog, visibility 500-1000m, night only + very calm
                # WMO compliant: spread 1.0-1.5°C + RH > 90%
                elif is_night and 1.0 <= dewpoint_spread < 1.5 and humidity > 90 and wind_speed < 2.0:
                    _LOGGER.debug(
                        f"Weather: FOG (POSSIBLE, night) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s, "
                        f"hour={current_hour} (light fog at night, WMO code 10)"
                    )
                    return ATTR_CONDITION_FOG

                # MIST (WMO Code 30 - not fog)
                # High humidity but spread too large for fog (1.5-4°C per WMO)
                # Show as CLOUDY, not FOG (HA has no dedicated MIST condition)
                elif 1.5 <= dewpoint_spread < 4.0 and humidity > 85:
                    _LOGGER.debug(
                        f"Weather: MIST detected (not fog) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s "
                        f"(WMO code 30: mist, visibility 1-5km, show as CLOUDY)"
                    )

            # PRIORITY 3: SOLAR RADIATION BASED CLOUD DETECTION
            # Solar radiation reveals actual cloud cover - determines cloudiness ONLY
            # Does NOT check precipitation (rain is handled by PRIORITY 1)
            # Provides real-time cloudiness hint for SECTION 2 (forecast determination)
            solar_radiation = None
            solar_cloudiness = None  # Will store solar-determined cloudiness hint
            solar_sensor_id = self._get_config(CONF_SOLAR_RADIATION_SENSOR)
            if solar_sensor_id:
                solar_state = self.hass.states.get(solar_sensor_id)
                if solar_state and solar_state.state not in ("unknown", "unavailable", None):
                    try:
                        from .unit_conversion import UnitConverter
                        raw_value = float(solar_state.state)
                        unit = solar_state.attributes.get("unit_of_measurement", "W/m²")
                        # Convert to W/m² (from lux if needed)
                        solar_radiation = UnitConverter.convert_solar_radiation(raw_value, unit)
                    except (ValueError, TypeError):
                        pass

            # Only use solar radiation during daytime with sufficient sunlight
            # IMPORTANT: Check both sun position AND actual solar radiation value!
            # - sun.sun above_horizon: Prevents use at night
            # - solar_radiation > 0 W/m²: Any positive value is valid (prevents division by zero)
            #
            # Why 0 W/m² threshold (changed from 10 W/m²)?
            # WMO UNIVERSAL APPROACH: Use transparency ratio (actual/theoretical) instead of absolute threshold
            # - Works for ANY sensor (weak or strong)
            # - Works in ANY conditions (twilight, winter, overcast)
            # - Accurate even at low light: 5 W/m² actual vs 20 W/m² theoretical = 25% transparency → cloudy ✓
            # - Old 10 W/m² threshold skipped valid measurements during:
            #   * Civil twilight: 5-20 W/m² (sun 0-6° below horizon)
            #   * Winter afternoon: 15-50 W/m²
            #   * Overcast morning: 20-100 W/m²
            # - Night (0 W/m²): Correctly skipped by sun.sun check + theoretical_max > 0 check
            if (solar_radiation is not None
                and self.hass.states.is_state('sun.sun', 'above_horizon')
                and solar_radiation > 0):

                # Calculate theoretical maximum solar radiation for current location and time
                # UNIVERSAL: Works for any latitude, elevation, season, and time of day
                from homeassistant.util import dt as dt_util
                import math

                now = dt_util.now()
                month = now.month
                hour = now.hour + (now.minute / 60.0)

                # Get location parameters with smart fallback priority:
                # 1st: Home Assistant global config (most accurate, set by user in HA)
                # 2nd: Integration config entry (for custom override)
                # 3rd: Default values (fallback if nothing configured)

                # Latitude from HA config or fallback
                latitude = None
                if self.hass.config.latitude is not None:
                    latitude = self.hass.config.latitude
                    _LOGGER.debug(f"Solar: Using HA global latitude: {latitude:.4f}°")
                else:
                    latitude = self._get_config(CONF_LATITUDE) or DEFAULT_LATITUDE
                    _LOGGER.debug(f"Solar: Using config/default latitude: {latitude:.4f}°")

                # Elevation from HA config or fallback
                elevation = None
                if self.hass.config.elevation is not None:
                    elevation = self.hass.config.elevation
                    _LOGGER.debug(f"Solar: Using HA global elevation: {elevation:.0f}m")
                else:
                    elevation = self._get_config(CONF_ELEVATION) or DEFAULT_ELEVATION
                    _LOGGER.debug(f"Solar: Using config/default elevation: {elevation:.0f}m")

                # 1. Calculate solar declination (angle of sun relative to equator)
                # Varies from -23.45° (Dec 21) to +23.45° (Jun 21)
                day_of_year = now.timetuple().tm_yday
                solar_declination = 23.45 * math.sin(math.radians((360/365) * (day_of_year - 81)))

                # 2. Calculate hour angle (sun's position in sky relative to solar noon)
                # 0° at noon, ±15° per hour
                hour_angle_deg = (hour - 12) * 15

                # 3. Calculate solar elevation angle (altitude above horizon)
                # Uses spherical trigonometry to find sun's position
                lat_rad = math.radians(latitude)
                dec_rad = math.radians(solar_declination)
                hour_rad = math.radians(hour_angle_deg)

                sin_elevation = (
                    math.sin(lat_rad) * math.sin(dec_rad) +
                    math.cos(lat_rad) * math.cos(dec_rad) * math.cos(hour_rad)
                )
                # Clamp to valid range [-1, 1] for asin
                sin_elevation = max(-1.0, min(1.0, sin_elevation))
                solar_elevation_deg = math.degrees(math.asin(sin_elevation))

                # 4. Calculate air mass (amount of atmosphere sunlight passes through)
                # Air mass = 1 at zenith (sun directly overhead)
                # Air mass ≈ 38 at horizon (sun at 90° angle)
                if solar_elevation_deg > 0:
                    # Kasten-Young formula (accurate for elevation > 0°)
                    air_mass = 1 / (math.sin(math.radians(solar_elevation_deg)) +
                                   0.50572 * (solar_elevation_deg + 6.07995) ** -1.6364)
                else:
                    air_mass = 38  # Sun below horizon

                # 5. Calculate clear-sky solar radiation at sea level
                # Solar constant (1361 W/m²) × atmospheric transmission
                solar_constant = 1361  # W/m² at top of atmosphere

                # Atmospheric transmission coefficient (0.7-0.8 for clear sky)
                # Varies with air mass: more atmosphere = more absorption
                transmission = 0.7 ** (air_mass ** 0.678)

                # Maximum solar radiation at sea level for current sun position
                max_solar_sea_level = solar_constant * transmission * max(0.0, sin_elevation)

                # 6. Adjust for elevation (thinner atmosphere at higher altitude)
                # For every 1000m elevation: ~10% more solar radiation
                # Formula: radiation increases by ~7-12% per 1000m (we use 10%)
                elevation_factor = 1 + (elevation / 1000) * 0.10

                # Final theoretical maximum for clear sky at this location and time
                theoretical_max = max_solar_sea_level * elevation_factor

                _LOGGER.debug(
                    f"Weather: Solar calculation - lat={latitude:.1f}°, elev={elevation}m, "
                    f"month={month}, hour={hour:.1f}, sun_elevation={solar_elevation_deg:.1f}°, "
                    f"air_mass={air_mass:.2f}, theoretical_max={theoretical_max:.0f} W/m²"
                )

                # WMO: Use any positive solar radiation value (not just >50 W/m²)
                # This allows accurate cloudiness detection even in low-light conditions
                if theoretical_max > 0:  # Avoid division by zero
                    # Calculate sky transparency ratio (how much sunlight reaches ground)
                    # This ratio is independent of time/position - compares actual vs expected
                    sky_transparency = solar_radiation / theoretical_max if theoretical_max > 0 else 0
                    cloud_percent = max(0, min(100, (1 - sky_transparency) * 100))

                    _LOGGER.debug(
                        f"Weather: Solar radiation analysis - "
                        f"measured={solar_radiation:.0f} W/m², theoretical_max={theoretical_max:.0f} W/m², "
                        f"sky_transparency={sky_transparency:.2f} ({sky_transparency*100:.0f}% of expected), "
                        f"cloud_cover={cloud_percent:.0f}%"
                    )

                    # HYBRID LOGIC: Solar radiation measures CLOUDINESS, forecast predicts PRECIPITATION
                    # Strategy:
                    # 1. Solar determines cloud cover (sunny/partlycloudy/cloudy)
                    # 2. Forecast checked for precipitation warnings
                    # 3. Rain sensor has final say if actively precipitating
                    #
                    # Night behavior: Solar radiation = 0 W/m² → skips to forecast (correct)

                    # Store solar-determined cloudiness for later use
                    solar_cloudiness = None

                    # WMO (World Meteorological Organization) Cloud Coverage Standards:
                    # Based on oktas (eighths of sky covered):
                    # - 0-2 oktas (0-25% clouds): FEW clouds → SUNNY/CLEAR (>75% transparency)
                    # - 3-4 oktas (25-50% clouds): SCT (scattered) → PARTLY CLOUDY (50-75% transparency)
                    # - 5-7 oktas (50-87.5% clouds): BKN (broken) → CLOUDY (12.5-50% transparency)
                    # - 8 oktas (87.5-100% clouds): OVC (overcast) → OVERCAST (<12.5% transparency)
                    #
                    # IMPORTANT: Thresholds based on sky_transparency (how much light reaches ground)
                    # NOT on absolute W/m² values which vary with sun position!
                    #
                    # These thresholds align with international aviation (METAR) and meteorological standards.
                    #
                    # REFERENCES:
                    # - WMO-No. 8, Vol I, Part A: "Guide to Instruments and Methods of Observation"
                    # - METAR/TAF standards: FEW (0-2 oktas), SCT (3-4), BKN (5-7), OVC (8)
                    # - Noia et al. (2015): "Cloud cover influence on solar radiation"
                    # - Long & Ackerman (2000): "Identification of clear skies" → 75-80% threshold

                    # WMO standard thresholds (universal, independent of sun position)
                    if sky_transparency >= 0.75:
                        # WMO: 0-2 oktas (FEW clouds) - sky allows >75% of expected sunlight
                        solar_cloudiness = ATTR_CONDITION_SUNNY
                        _LOGGER.debug(
                            f"Weather: Solar HIGH CONFIDENCE → clear skies (FEW clouds) "
                            f"(transparency={sky_transparency*100:.0f}%, cloud_cover={cloud_percent:.0f}%, WMO: 0-2 oktas)"
                        )
                    elif sky_transparency >= 0.50:
                        # WMO: 3-4 oktas (SCT - scattered clouds) - sky allows 50-75% of expected sunlight
                        solar_cloudiness = ATTR_CONDITION_PARTLYCLOUDY
                        _LOGGER.debug(
                            f"Weather: Solar MEDIUM CONFIDENCE → scattered clouds (SCT) "
                            f"(transparency={sky_transparency*100:.0f}%, cloud_cover={cloud_percent:.0f}%, WMO: 3-4 oktas)"
                        )
                    elif sky_transparency >= 0.125:
                        # WMO: 5-7 oktas (BKN - broken clouds) - sky allows 12.5-50% of expected sunlight
                        solar_cloudiness = ATTR_CONDITION_CLOUDY
                        _LOGGER.debug(
                            f"Weather: Solar LOW CONFIDENCE → mostly cloudy (BKN) "
                            f"(transparency={sky_transparency*100:.0f}%, cloud_cover={cloud_percent:.0f}%, WMO: 5-7 oktas)"
                        )
                    else:
                        # WMO: 8 oktas (OVC - overcast) - sky allows <12.5% of expected sunlight
                        # Overcast = still CLOUDY (87.5-100% cloud cover)
                        # Solar still shows cloudiness accurately - trust it!
                        # Rain sensor or pressure will determine if it's rainy/snowy
                        solar_cloudiness = ATTR_CONDITION_CLOUDY
                        _LOGGER.debug(
                            f"Weather: Solar OVERCAST (OVC) → cloudy "
                            f"(transparency={sky_transparency*100:.0f}%, cloud_cover={cloud_percent:.0f}%, WMO: 8 oktas). "
                            f"Solar accurately shows cloudiness - will check rain sensor/pressure for precipitation."
                        )

                    # Solar cloudiness determined - store hint for SECTION 2
                    # NOTE: Rain sensor is handled in PRIORITY 1 (already checked above)
                    # Solar ONLY determines cloudiness, NOT precipitation
                    if solar_cloudiness is not None:
                        _LOGGER.debug(
                            f"Weather: Solar cloudiness={solar_cloudiness}, "
                            f"continuing to SECTION 2 (forecast determination). "
                            f"Rain is handled by PRIORITY 1, solar only shows clouds."
                        )

                    # Fall through to SECTION 2 with solar_cloudiness hint
            elif solar_radiation is not None and solar_radiation <= 10:
                _LOGGER.debug(
                    f"Weather: Solar radiation too low ({solar_radiation:.0f} W/m² ≤ 10), "
                    f"skipping cloud detection (twilight or night)"
                )

            # ========================================================================
            # PHASE 2: PRESSURE-BASED CURRENT STATE (For NOW - 0h)
            # Use DIRECT pressure mapping for current conditions
            #
            # ⚠️ WHY NOT FORECAST ALGORITHMS (Zambretti/Negretti)?
            # - Zambretti (1915) designed for 6-12h PREDICTION, not current state
            # - Uses pressure TREND to predict FUTURE weather
            # - Example: Falling pressure → predicts "rain later" (but NOW may be clear!)
            # - Result: Often shows "cloudy" when actually sunny
            #
            # ✅ DIRECT PRESSURE MAPPING:
            # - Based on WMO/NOAA meteorological thresholds
            # - Reflects CURRENT atmospheric cloudiness
            # - More accurate for immediate state (0h)
            # - Simpler and more reliable than trend-based prediction
            #
            # ⚠️ CRITICAL: Maps to CLOUDINESS ONLY, never precipitation!
            # - Rain sensor (PRIORITY 1) determines if it's raining
            # - This mapping shows cloud conditions based on pressure
            # - Low pressure = cloudy (rain LIKELY), not "rainy" (rain NOW)
            #
            # Scientific basis:
            # - < 980 hPa: Deep cyclone → CLOUDY (storm clouds)
            # - 980-1008 hPa: Low pressure → CLOUDY (rain likely)
            # - 1008-1015 hPa: Slightly low → CLOUDY
            # - 1015-1023 hPa: Normal → PARTLY CLOUDY
            # - > 1023 hPa: High pressure → CLEAR/SUNNY
            # ========================================================================

            current_condition_from_pressure = None

            pressure = self.native_pressure
            if pressure is not None:
                # Get pressure change for trend analysis (optional enhancement)
                pressure_change_sensor = self.hass.states.get("sensor.local_forecast_pressurechange")
                pressure_change = 0.0
                if pressure_change_sensor and pressure_change_sensor.state not in ("unknown", "unavailable", None):
                    try:
                        pressure_change = float(pressure_change_sensor.state)
                    except (ValueError, TypeError):
                        pass

                # Get temperature for rain/snow determination
                temperature = self.native_temperature

                # ========================================================================
                # PRESSURE → WEATHER MAPPING (WMO Guide No. 8, 2018)
                # ========================================================================
                # 100% WMO COMPLIANT PRESSURE THRESHOLDS:
                #
                # Based on: WMO Guide No. 8 (2018), WMO-No. 100 (Manual on Codes)
                #
                # Pressure ranges (WMO official classification):
                # - < 970 hPa: INTENSE LOW (severe storms, hurricane-force)
                # - 970-990 hPa: DEEP LOW (strong cyclone, heavy precipitation)
                # - 990-1010 hPa: LOW (cyclonic activity, unsettled)
                # - 1010-1020 hPa: NORMAL (variable conditions)
                # - 1020-1030 hPa: HIGH (anticyclonic, fair weather)
                # - > 1030 hPa: VERY HIGH (strong anticyclone, settled)
                #
                # Pressure change (WMO Code for pressure tendency):
                # - ≤ -3.5 hPa/3h: Rapid fall (WMO Code 0-3)
                # - ≥ +3.5 hPa/3h: Rapid rise (WMO Code 5-8)
                # ========================================================================

                if pressure < 970:
                    # WMO: INTENSE LOW (< 970 hPa)
                    # Severe storms, hurricane-force winds
                    # Precipitation probability: 90-100%
                    current_condition_from_pressure = ATTR_CONDITION_LIGHTNING_RAINY
                    _LOGGER.debug(
                        f"Weather: PRESSURE → lightning-rainy "
                        f"(pressure={pressure:.1f} hPa < 970, WMO: Intense Low → severe storms)"
                    )

                elif pressure < 990:  # ✅ WMO STANDARD: Deep Low (970-990 hPa)
                    # WMO: DEEP LOW (970-990 hPa)
                    # Strong cyclone, heavy precipitation
                    # Precipitation probability: 70-95%
                    if pressure_change <= -3.5:  # WMO Code 0-3: Rapid fall
                        # Rapidly intensifying → severe storms
                        current_condition_from_pressure = ATTR_CONDITION_LIGHTNING_RAINY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → lightning-rainy "
                            f"(pressure={pressure:.1f} hPa < 990, WMO rapid fall {pressure_change:.1f} → intensifying storm)"
                        )
                    elif pressure_change <= -1.5:
                        # Falling → heavy rain
                        current_condition_from_pressure = ATTR_CONDITION_POURING
                        _LOGGER.debug(
                            f"Weather: PRESSURE → pouring "
                            f"(pressure={pressure:.1f} hPa < 990, WMO falling {pressure_change:.1f} → heavy rain)"
                        )
                    elif pressure_change >= 3.5:  # WMO Code 5-8: Rapid rise
                        # Rapidly improving → moderate rain
                        current_condition_from_pressure = ATTR_CONDITION_RAINY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → rainy "
                            f"(pressure={pressure:.1f} hPa < 990, WMO rapid rise {pressure_change:+.1f} → improving)"
                        )
                    else:
                        # Stable/moderate → rain
                        current_condition_from_pressure = ATTR_CONDITION_RAINY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → rainy "
                            f"(pressure={pressure:.1f} hPa < 990, WMO: Deep Low → rain)"
                        )

                elif pressure < 1010:  # ✅ WMO STANDARD: Low (990-1010 hPa)
                    # WMO: LOW (990-1010 hPa)
                    # Cyclonic activity, unsettled
                    # Precipitation probability: 30-70%
                    if pressure_change <= -3.0:
                        # Rapid fall → rain developing
                        current_condition_from_pressure = ATTR_CONDITION_RAINY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → rainy "
                            f"(pressure={pressure:.1f} hPa < 1010, WMO rapid fall {pressure_change:.1f} → rain developing)"
                        )
                    elif pressure_change <= -1.5:
                        # Moderate fall → cloudy (rain threat)
                        current_condition_from_pressure = ATTR_CONDITION_CLOUDY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → cloudy "
                            f"(pressure={pressure:.1f} hPa < 1010, WMO falling {pressure_change:.1f} → deteriorating)"
                        )
                    elif pressure_change >= 3.5:  # WMO Code 5-8: Rapid rise
                        # Rapid rise → improving
                        current_condition_from_pressure = ATTR_CONDITION_PARTLYCLOUDY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → partlycloudy "
                            f"(pressure={pressure:.1f} hPa < 1010, WMO rapid rise {pressure_change:+.1f} → improving)"
                        )
                    else:
                        # Stable → cloudy/unsettled
                        current_condition_from_pressure = ATTR_CONDITION_CLOUDY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → cloudy "
                            f"(pressure={pressure:.1f} hPa < 1010, WMO: Low → unsettled)"
                        )

                elif pressure < 1020:
                    # WMO: NORMAL (1010-1020 hPa)
                    # Variable conditions
                    # Cloudiness: 10-50%
                    if pressure_change <= -2.0:
                        # Falling → cloudy
                        current_condition_from_pressure = ATTR_CONDITION_CLOUDY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → cloudy "
                            f"(pressure={pressure:.1f} hPa < 1020, WMO falling {pressure_change:.1f} → deteriorating)"
                        )
                    else:
                        # Stable/rising → partly cloudy
                        current_condition_from_pressure = ATTR_CONDITION_PARTLYCLOUDY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → partlycloudy "
                            f"(pressure={pressure:.1f} hPa < 1020, WMO: Normal → variable)"
                        )

                elif pressure < 1030:  # ✅ NEW WMO BOUNDARY: High (1020-1030 hPa)
                    # WMO: HIGH (1020-1030 hPa)
                    # Anticyclonic, fair weather
                    # Cloudiness: 0-20%
                    if self._is_night():
                        current_condition_from_pressure = ATTR_CONDITION_CLEAR_NIGHT
                        _LOGGER.debug(
                            f"Weather: PRESSURE → clear-night "
                            f"(pressure={pressure:.1f} hPa < 1030, WMO: High, anticyclone, nighttime)"
                        )
                    else:
                        current_condition_from_pressure = ATTR_CONDITION_SUNNY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → sunny "
                            f"(pressure={pressure:.1f} hPa < 1030, WMO: High, anticyclone, daytime)"
                        )

                else:  # >= 1030 hPa
                    # WMO: VERY HIGH (> 1030 hPa)
                    # Strong anticyclone, settled fine weather
                    # Cloudiness: 0-10%
                    if self._is_night():
                        current_condition_from_pressure = ATTR_CONDITION_CLEAR_NIGHT
                        _LOGGER.debug(
                            f"Weather: PRESSURE → clear-night "
                            f"(pressure={pressure:.1f} hPa ≥ 1030, WMO: Very High, strong anticyclone, nighttime)"
                        )
                    else:
                        current_condition_from_pressure = ATTR_CONDITION_SUNNY
                        _LOGGER.debug(
                            f"Weather: PRESSURE → sunny "
                            f"(pressure={pressure:.1f} hPa ≥ 1030, WMO: Very High, strong anticyclone, daytime)"
                        )





            # ========================================================================
            # PHASE 3: HUMIDITY FINE-TUNING (After Pressure Mapping)
            # ========================================================================
            # Humidity refines/adjusts the pressure-based prediction:
            # - Can IMPROVE conditions (e.g., rainy → cloudy if RH low)
            # - Can WORSEN conditions (e.g., cloudy → rainy if RH very high)
            #
            # ⚠️ IMPORTANT: Skip humidity if solar radiation is available!
            # Solar (85% accuracy) is MORE ACCURATE than humidity (70% accuracy)
            # Humidity fine-tuning is ONLY for nighttime or when solar is not available
            # ========================================================================
            condition = None

            if current_condition_from_pressure is not None:
                # We have pressure-based prediction → use it as baseline
                condition = current_condition_from_pressure
                _LOGGER.debug(
                    f"Weather: PHASE 2 result - Pressure-based current state: {condition}"
                )

                # PHASE 3: Humidity fine-tuning (ONLY if solar NOT available!)
                # SKIP ENTIRELY if solar radiation is active (more accurate!)
                if solar_cloudiness is not None:
                    # Solar radiation available → skip humidity completely
                    _LOGGER.debug(
                        f"Weather: PHASE 3 - SKIPPING humidity fine-tuning "
                        f"(solar active: {solar_cloudiness}, 85% accuracy > 70% humidity). "
                        f"Solar will validate/override pressure in PHASE 4."
                    )
                    # Jump to PHASE 4 (solar validation)
                    pass
                else:
                    # No solar → use humidity fine-tuning
                    humidity = self.humidity

                    if humidity is not None:
                        # VALIDATION: Check if humidity sensor is valid
                        humidity_is_valid = True

                        # Check 1: Humidity should be 0-100%
                        if humidity < 0 or humidity > 100:
                            humidity_is_valid = False
                            _LOGGER.warning(
                                f"Weather: PHASE 3 - Humidity sensor INVALID: {humidity:.1f}% (out of range). "
                                f"Skipping humidity fine-tuning."
                            )

                        # Check 2: Don't override HARD OVERRIDES (fog, windy)
                        # But DO refine precipitation (rainy/pouring can be adjusted!)
                        if condition in (
                            ATTR_CONDITION_FOG,
                            "windy",
                            "windy-variant",
                        ):
                            _LOGGER.debug(
                                f"Weather: PHASE 3 - Skipping humidity for hard override: {condition}"
                            )
                            humidity_is_valid = False

                        if humidity_is_valid:
                            _LOGGER.debug(
                                f"Weather: PHASE 3 - Humidity fine-tuning - "
                                f"humidity={humidity:.1f}%, condition={condition}"
                            )

                            # ================================================================
                            # HUMIDITY-BASED WEATHER REFINEMENT
                            # Can IMPROVE (dry air → less severe) or WORSEN (wet air → more severe)
                            # ================================================================

                            original_condition = condition

                            # ----------------------------------------------------------------
                            # SCENARIO 1: IMPROVE conditions (low humidity = drier = better)
                            # ----------------------------------------------------------------

                            if humidity < 50:
                                # Very low humidity → significantly improve conditions
                                if condition == ATTR_CONDITION_RAINY:
                                    condition = ATTR_CONDITION_CLOUDY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - IMPROVED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% < 50%, too dry for sustained rain)"
                                    )
                                elif condition == ATTR_CONDITION_POURING:
                                    condition = ATTR_CONDITION_RAINY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - IMPROVED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% < 50%, too dry for heavy rain)"
                                    )
                                elif condition == ATTR_CONDITION_CLOUDY:
                                    condition = ATTR_CONDITION_PARTLYCLOUDY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - IMPROVED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% < 50%, dry air)"
                                    )

                            elif humidity < 65:
                                # Low-moderate humidity → moderately improve
                                if condition == ATTR_CONDITION_POURING:
                                    condition = ATTR_CONDITION_RAINY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - IMPROVED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% < 65%, not enough moisture for heavy rain)"
                                    )

                            # ----------------------------------------------------------------
                            # SCENARIO 2: WORSEN conditions (high humidity = wetter = worse)
                            # ----------------------------------------------------------------

                            elif humidity > 90:
                                # Very high humidity → significantly worsen conditions
                                if condition == ATTR_CONDITION_CLOUDY:
                                    condition = ATTR_CONDITION_RAINY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - WORSENED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% > 90%, very wet → rain likely)"
                                    )
                                elif condition == ATTR_CONDITION_PARTLYCLOUDY:
                                    condition = ATTR_CONDITION_CLOUDY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - WORSENED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% > 90%, very wet)"
                                    )
                                elif condition in (ATTR_CONDITION_SUNNY, ATTR_CONDITION_CLEAR_NIGHT):
                                    condition = ATTR_CONDITION_PARTLYCLOUDY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - WORSENED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% > 90%, moisture present)"
                                    )
                                elif condition == ATTR_CONDITION_RAINY:
                                    condition = ATTR_CONDITION_POURING
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - WORSENED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% > 90%, saturated → heavy rain)"
                                    )

                            elif humidity > 80:
                                # High humidity → moderately worsen
                                if condition == ATTR_CONDITION_PARTLYCLOUDY:
                                    condition = ATTR_CONDITION_CLOUDY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - WORSENED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% > 80%, high moisture)"
                                    )
                                elif condition in (ATTR_CONDITION_SUNNY, ATTR_CONDITION_CLEAR_NIGHT):
                                    condition = ATTR_CONDITION_PARTLYCLOUDY
                                    _LOGGER.debug(
                                        f"Weather: PHASE 3 - WORSENED: {original_condition} → {condition} "
                                        f"(RH={humidity:.1f}% > 80%, moisture present)"
                                    )

                            else:
                                # Normal humidity (65-80%) → no significant change
                                _LOGGER.debug(
                                    f"Weather: PHASE 3 - No significant humidity adjustment "
                                    f"(RH={humidity:.1f}%, normal range 65-80%)"
                                )

                        # After humidity fine-tuning, we have: condition with humidity adjustments
                        _LOGGER.debug(
                            f"Weather: PHASE 3 result - After humidity fine-tuning: {condition}"
                        )


            # ========================================================================
            # PHASE 4: SOLAR FINAL OVERRIDE (Real Data Wins!)
            # Solar radiation is REAL OBSERVATION → has PRIORITY over pressure-based estimates
            # MUST BE LAST because it's the most accurate (85% vs 60-70% pressure)
            #
            # CRITICAL LOGIC (v3.1.10):
            # ⚠️ "condition" here = PRESSURE + HUMIDITY result (NOT Zambretti/Negretti forecast!)
            # ✅ Solar shows ACTUAL cloudiness NOW (real measurement)
            # ✅ Pressure shows ESTIMATED cloudiness (statistical correlation)
            # ✅ Rain sensor shows ACTUAL precipitation NOW (handled in PRIORITY 1)
            #
            # CORRECT BEHAVIOR:
            # - If pressure suggests "cloudy" but solar shows "sunny" → use SOLAR
            # - If rain sensor > 0 → PRIORITY 1 already returned (we never reach here)
            # - Solar ALWAYS overrides pressure+humidity for CLOUDINESS determination
            # ========================================================================

            if condition is not None and solar_cloudiness is not None:
                # We have both PRESSURE+HUMIDITY result AND solar → validate
                # Map conditions to cloudiness level for comparison
                cloudiness_map = {
                    ATTR_CONDITION_SUNNY: 0,
                    ATTR_CONDITION_CLEAR_NIGHT: 0,
                    ATTR_CONDITION_PARTLYCLOUDY: 1,
                    ATTR_CONDITION_CLOUDY: 2,
                    ATTR_CONDITION_RAINY: 3,
                    ATTR_CONDITION_POURING: 3,
                    ATTR_CONDITION_SNOWY: 3,
                    ATTR_CONDITION_SNOWY_RAINY: 3,
                    ATTR_CONDITION_LIGHTNING_RAINY: 3,
                }

                solar_level = cloudiness_map.get(solar_cloudiness, 1)
                pressure_level = cloudiness_map.get(condition, 1)

                # CRITICAL: If pressure suggests precipitation (level 3) BUT rain sensor = 0
                # This can't happen anymore since PRIORITY 5 only returns cloudiness!
                # But keep this check for safety in case pressure mapping has bugs
                if pressure_level >= 3:
                    # Pressure erroneously suggests precipitation, but rain sensor = 0
                    # This should NOT happen (PRIORITY 5 bug if it does!)
                    # Solar shows actual cloudiness → OVERRIDE with solar!
                    _LOGGER.warning(
                        f"Weather: PHASE 4 - ⚠️ PRESSURE BUG DETECTED! "
                        f"Pressure suggests precipitation ({condition}), but rain sensor = 0. "
                        f"Using SOLAR cloudiness ({solar_cloudiness}) for CURRENT state. "
                        f"(This indicates PRIORITY 5 returned precipitation instead of cloudiness!)"
                    )
                    condition = solar_cloudiness
                elif abs(solar_level - pressure_level) >= 1:
                    # Solar and pressure disagree on cloudiness → use solar (real data wins!)
                    _LOGGER.info(
                        f"Weather: PHASE 4 - ☀️ SOLAR OVERRIDE! "
                        f"Pressure={condition} (level={pressure_level}) vs "
                        f"Solar={solar_cloudiness} (level={solar_level}), "
                        f"difference={abs(solar_level - pressure_level)} ≥ 1. "
                        f"Using SOLAR (real measurement > pressure estimate)."
                    )
                    condition = solar_cloudiness
                else:
                    # Solar and pressure perfectly agree (difference=0) → keep pressure
                    _LOGGER.debug(
                        f"Weather: PHASE 4 - Solar validation: pressure={condition} (level={pressure_level}), "
                        f"solar={solar_cloudiness} (level={solar_level}), "
                        f"difference=0. Perfect agreement!"
                    )
            elif condition is None and solar_cloudiness is not None:
                # No pressure result but have solar → use solar directly
                condition = solar_cloudiness
                _LOGGER.info(
                    f"Weather: No pressure-based condition available, using solar cloudiness directly: {condition}"
                )
            elif condition is not None:
                # Have pressure result but no solar → keep pressure
                _LOGGER.debug(
                    f"Weather: PHASE 4 - No solar radiation available, keeping pressure-based condition: {condition}"
                )

            # ========================================================================
            # PHASE 5: WIND CONDITIONS CHECK (After pressure+humidity+solar)
            # Check wind AFTER cloudiness determination for best accuracy
            # Uses result from pressure+humidity+solar (60-85% accuracy) instead of
            # simple pressure fallback (55% accuracy) - scientifically correct!
            #
            # IMPORTANT: Wind can ONLY override basic cloudiness conditions:
            # - sunny, clear-night, partlycloudy, cloudy
            # Wind CANNOT override precipitation/fog (they are more important):
            # - rainy, snowy, fog, pouring, lightning-rainy
            # ========================================================================
            wind_speed = self.native_wind_speed
            wind_gust = self.native_wind_gust_speed

            if (wind_speed is not None or wind_gust is not None) and condition is not None:
                # Determine effective wind speed (max of wind or gust)
                effective_wind = wind_speed if wind_speed is not None else 0.0
                if wind_gust is not None and wind_gust > effective_wind:
                    effective_wind = wind_gust

                if effective_wind >= 10.8:  # Force 6+ (Strong breeze or higher)
                    # Wind can ONLY override basic cloudiness conditions
                    # Check if current condition is basic cloudiness (not precipitation/fog)
                    basic_cloudiness_conditions = (
                        ATTR_CONDITION_SUNNY,
                        ATTR_CONDITION_CLEAR_NIGHT,
                        ATTR_CONDITION_PARTLYCLOUDY,
                        ATTR_CONDITION_CLOUDY
                    )

                    if condition in basic_cloudiness_conditions:
                        # Basic cloudiness - wind can override
                        if condition in (ATTR_CONDITION_SUNNY, ATTR_CONDITION_CLEAR_NIGHT, ATTR_CONDITION_PARTLYCLOUDY):
                            # Clear/partly cloudy → windy
                            _LOGGER.info(
                                f"Weather: PHASE 5 - Wind override → windy "
                                f"(wind={wind_speed:.1f if wind_speed else 0.0} m/s, "
                                f"gust={wind_gust:.1f if wind_gust else 0.0} m/s, "
                                f"effective={effective_wind:.1f} m/s ≥ 10.8 m/s, "
                                f"condition={condition} → clear/partly cloudy)"
                            )
                            condition = "windy"
                        else:  # cloudy
                            # Cloudy → windy-variant
                            _LOGGER.info(
                                f"Weather: PHASE 5 - Wind override → windy-variant "
                                f"(wind={wind_speed:.1f if wind_speed else 0.0} m/s, "
                                f"gust={wind_gust:.1f if wind_gust else 0.0} m/s, "
                                f"effective={effective_wind:.1f} m/s ≥ 10.8 m/s, "
                                f"condition={condition} → cloudy)"
                            )
                            condition = "windy-variant"
                    else:
                        # Precipitation/fog - wind CANNOT override!
                        # Rain, snow, fog are more important than wind
                        _LOGGER.debug(
                            f"Weather: PHASE 5 - Strong wind detected "
                            f"(wind={wind_speed:.1f if wind_speed else 0.0} m/s, "
                            f"gust={wind_gust:.1f if wind_gust else 0.0} m/s, "
                            f"effective={effective_wind:.1f} m/s ≥ 10.8 m/s) "
                            f"but condition={condition} (precipitation/fog) - NOT overriding. "
                            f"Precipitation/fog has priority over wind."
                        )

            # ========================================================================
            # PHASE 6: ABSOLUTE FINAL FALLBACK (Only if pressure sensor missing)
            # This should NEVER happen in normal operation (pressure is REQUIRED sensor!)
            # If we reach here during startup, sensors may not be ready yet
            # ========================================================================
            if condition is None:
                pressure = self.native_pressure
                if pressure is None:
                    # Likely startup - sensors not ready yet
                    _LOGGER.info(
                        f"Weather: PHASE 5 - Sensors not ready yet (startup). "
                        f"Pressure sensor not available. Using default condition (partlycloudy) "
                        f"until sensors initialize."
                    )
                    condition = ATTR_CONDITION_PARTLYCLOUDY  # ✅ Better default than exceptional
                else:
                    # Runtime failure - this should never happen!
                    _LOGGER.warning(
                        f"Weather: PHASE 5 - No condition could be determined! "
                        f"Pressure={pressure:.1f} hPa available, but no priority matched. "
                        f"This is unexpected - falling back to EXCEPTIONAL."
                    )
                    condition = ATTR_CONDITION_EXCEPTIONAL



            return condition
        except Exception as e:
            _LOGGER.error(f"Error determining weather condition: {e}", exc_info=True)
            # Partlycloudy is safe fallback for both day and night (HA shows correct icon)
            return ATTR_CONDITION_PARTLYCLOUDY

    def _is_night(self, check_time: datetime | None = None) -> bool:
        """Check if it's night time based on sun position.

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if sun is below horizon (night time)
        """
        import homeassistant.util.dt as dt_util

        # Get sun entity state
        sun_entity = self.hass.states.get("sun.sun")

        if check_time is None:
            # Check current time
            if sun_entity:
                # sun.sun state is "above_horizon" or "below_horizon"
                is_night = sun_entity.state == "below_horizon"
                _LOGGER.debug(f"Weather: Night check from sun.sun entity: {is_night} (state={sun_entity.state})")
                return is_night
            else:
                # Fallback to simple time check if sun entity not available
                current_hour = dt_util.now().hour
                is_night = current_hour >= 19 or current_hour < 7
                _LOGGER.debug(f"Weather: Night check from time: {is_night} (hour={current_hour})")
                return is_night
        else:
            # For future times, compare with sunrise/sunset
            if sun_entity:
                next_sunrise = sun_entity.attributes.get("next_rising")
                next_sunset = sun_entity.attributes.get("next_setting")

                if next_sunrise and next_sunset:
                    try:
                        # Parse ISO format datetime strings with proper timezone handling
                        sunrise_dt = dt_util.parse_datetime(next_sunrise)
                        sunset_dt = dt_util.parse_datetime(next_sunset)

                        if sunrise_dt is None or sunset_dt is None:
                            # Fallback parsing
                            sunrise_dt = datetime.fromisoformat(next_sunrise.replace('Z', '+00:00'))
                            sunset_dt = datetime.fromisoformat(next_sunset.replace('Z', '+00:00'))

                        # Make check_time timezone aware using HA's timezone
                        if check_time.tzinfo is None:
                            check_time = dt_util.as_local(check_time)

                        # Convert all to same timezone for comparison
                        sunrise_dt = dt_util.as_local(sunrise_dt)
                        sunset_dt = dt_util.as_local(sunset_dt)
                        check_time = dt_util.as_local(check_time)

                        # If check time is before next sunrise, it's night
                        # If check time is after next sunset, it's night
                        # Otherwise it's day
                        if sunrise_dt < sunset_dt:
                            # Normal day: night is before sunrise or after sunset
                            return check_time < sunrise_dt or check_time > sunset_dt
                        else:
                            # Crossing midnight
                            return sunset_dt < check_time < sunrise_dt
                    except (ValueError, AttributeError, TypeError) as e:
                        _LOGGER.debug(f"Error parsing sun times: {e}")
                        pass

            # Fallback to simple time check
            return check_time.hour >= 19 or check_time.hour < 7

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.hass:
            return {"attribution": "Local Weather Forecast based on Zambretti and Negretti-Zambra algorithms"}

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

        # Get temperature for comfort and fog calculations
        temp = self.native_temperature

        # Add comfort level and feels_like based on apparent temperature
        # Use feels_like property which has built-in fallback logic
        feels_like_temp = self.feels_like
        if feels_like_temp is not None:
            attrs["comfort_level"] = get_comfort_level(feels_like_temp)
            attrs["feels_like"] = round(feels_like_temp, 2)
            _LOGGER.debug(f"Weather: Comfort level={attrs['comfort_level']}, feels_like={attrs['feels_like']}°C")
        else:
            # Should never happen due to feels_like fallbacks, but keep as safety
            attrs["comfort_level"] = "unknown"
            attrs["feels_like"] = 0.0
            _LOGGER.debug("Weather: No feels_like temperature available")

        # Add fog risk if we have dewpoint
        dewpoint = self.native_dew_point
        if temp is not None and dewpoint is not None:
            spread = temp - dewpoint
            fog_risk_level = get_fog_risk(temp, dewpoint)
            attrs["fog_risk"] = fog_risk_level
            attrs["dewpoint_spread"] = round(spread, 2)
            attrs["dew_point"] = round(dewpoint, 2)

            # Check if fog is CURRENTLY present (not just risk)
            # This is useful when condition shows precipitation but fog is also present
            wind_speed = self.native_wind_speed or 0.0
            humidity = self.humidity or 0.0
            current_hour = datetime.now().hour
            is_night = current_hour < 6 or current_hour >= 20

            fog_detected = False
            if (spread < 0.5 and humidity > 95) or \
               (spread < 1.0 and humidity > 93 and wind_speed < 3.0) or \
               (1.5 <= spread < 2.5 and humidity > 85 and wind_speed < 2.0) or \
               (is_night and 1.0 <= spread < 1.5 and humidity > 90 and wind_speed < 2.0):
                fog_detected = True

            attrs["fog_detected"] = fog_detected

            _LOGGER.debug(
                f"Weather: Fog risk={fog_risk_level}, fog_detected={fog_detected}, "
                f"temp={temp:.1f}°C, dewpoint={dewpoint:.1f}°C, spread={spread:.1f}°C"
            )

        # Add snow risk and frost/ice risk
        humidity = self.humidity
        if temp is not None and humidity is not None and dewpoint is not None:
            # Calculate spread for use in logging
            spread = temp - dewpoint

            # Get rain probability for snow risk calculation
            rain_prob = 0
            rain_prob_sensor = self.hass.states.get("sensor.local_forecast_rain_probability")
            if rain_prob_sensor and rain_prob_sensor.state not in ("unknown", "unavailable", None):
                try:
                    rain_prob = float(rain_prob_sensor.state)
                except (ValueError, TypeError):
                    pass

            from .calculations import get_snow_risk, get_frost_risk

            # Calculate snow risk (pass dewpoint, not spread - function calculates spread internally)
            snow_risk = get_snow_risk(temp, humidity, dewpoint, rain_prob)
            attrs["snow_risk"] = snow_risk
            _LOGGER.debug(
                f"Weather: Snow risk={snow_risk}, temp={temp:.1f}°C, "
                f"humidity={humidity:.1f}%, rain_prob={rain_prob}%"
            )

            # Calculate frost/ice risk
            wind_speed = self.native_wind_speed or 0.0
            frost_risk = get_frost_risk(temp, dewpoint, wind_speed, humidity)
            attrs["frost_risk"] = frost_risk
            _LOGGER.debug(
                f"Weather: Frost risk={frost_risk}, temp={temp:.1f}°C, "
                f"dewpoint={dewpoint:.1f}°C, wind={wind_speed:.1f} m/s"
            )

            # Log CRITICAL warnings
            if frost_risk == "critical":
                _LOGGER.debug(
                    f"FrostRisk: CRITICAL BLACK ICE - Temperature={temp:.1f}°C, "
                    f"Humidity={humidity:.1f}%, Spread={spread:.1f}°C"
                )
            if snow_risk == "high":
                _LOGGER.debug(
                    f"❄️ High snow risk: Temperature={temp:.1f}°C, Humidity={humidity:.1f}%, "
                    f"Rain probability={rain_prob}%"
                )

        # Add wind classification (Beaufort Scale) and atmospheric stability
        wind_speed = self.native_wind_speed
        if wind_speed is not None:
            attrs["wind_beaufort_scale"] = self._get_beaufort_number(wind_speed)
            attrs["wind_type"] = self._get_beaufort_wind_type(wind_speed)

        # Add wind gust and gust ratio if available
        wind_gust_sensor_id = self._get_config(CONF_WIND_GUST_SENSOR)
        if wind_gust_sensor_id and wind_speed and wind_speed > 0.1:
            wind_gust_state = self.hass.states.get(wind_gust_sensor_id)
            if wind_gust_state and wind_gust_state.state not in ("unknown", "unavailable"):
                try:
                    value = float(wind_gust_state.state)
                    # Apply unit conversion
                    unit = wind_gust_state.attributes.get("unit_of_measurement")
                    wind_gust = UnitConverter.convert_sensor_value(value, "wind_speed", unit) if unit else value
                    attrs["wind_gust"] = round(wind_gust, 2)
                    gust_ratio = wind_gust / wind_speed
                    attrs["gust_ratio"] = round(gust_ratio, 2)
                    stability = self._get_atmosphere_stability(wind_speed, gust_ratio)
                    attrs["atmosphere_stability"] = stability
                    _LOGGER.debug(
                        f"Weather: Wind gust={wind_gust:.2f} m/s, ratio={gust_ratio:.2f}, "
                        f"stability={stability}"
                    )
                except (ValueError, TypeError) as e:
                    _LOGGER.debug(f"Weather: Error processing wind gust: {e}")
                    pass

        # Add enhanced forecast details from Enhanced sensor
        enhanced_sensor = self.hass.states.get("sensor.local_forecast_enhanced")
        if enhanced_sensor and enhanced_sensor.state not in ("unknown", "unavailable"):
            enhanced_attrs = enhanced_sensor.attributes or {}

            # Add confidence and adjustments
            if "confidence" in enhanced_attrs:
                attrs["forecast_confidence"] = enhanced_attrs["confidence"]
            if "adjustments" in enhanced_attrs:
                attrs["forecast_adjustments"] = enhanced_attrs["adjustments"]
            if "adjustment_details" in enhanced_attrs:
                attrs["forecast_adjustment_details"] = enhanced_attrs["adjustment_details"]

        # Add rain probability if available
        rain_prob_sensor = self.hass.states.get("sensor.local_forecast_rain_probability")
        if rain_prob_sensor and rain_prob_sensor.state not in ("unknown", "unavailable"):
            try:
                attrs["rain_probability"] = int(float(rain_prob_sensor.state))
                rain_attrs = rain_prob_sensor.attributes or {}
                if "confidence" in rain_attrs:
                    attrs["rain_confidence"] = rain_attrs["confidence"]
            except (ValueError, TypeError):
                pass

        # Add humidity if available
        humidity = self.humidity
        if humidity is not None:
            attrs["humidity"] = round(humidity, 2)

        # Add visibility estimate based on fog risk
        if "fog_risk" in attrs:
            fog_risk = attrs["fog_risk"]
            attrs["visibility_estimate"] = get_visibility_estimate(self.hass, fog_risk)

        attrs["attribution"] = "Local Weather Forecast based on Zambretti and Negretti-Zambra algorithms"

        return attrs

    def _get_beaufort_number(self, wind_speed: float) -> int:
        """Get Beaufort scale number from wind speed (m/s)."""
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
        """Get wind type description from Beaufort scale in current HA language.

        Args:
            wind_speed: Wind speed in m/s

        Returns:
            Wind type description in user's language
        """
        beaufort = self._get_beaufort_number(wind_speed)
        return get_wind_type(self.hass, beaufort)

    def _get_atmosphere_stability(self, wind_speed: float, gust_ratio: float | None) -> str:
        """Determine atmospheric stability based on wind speed and gust ratio."""
        if gust_ratio is None:
            return "unknown"

        # For low wind speeds (< 3 m/s), gust ratio is not reliable indicator
        if wind_speed < 3.0:
            if wind_speed < 1.0:
                return "stable"
            else:
                return "moderate"

        # For moderate to strong winds (≥ 3 m/s), use gust ratio
        if gust_ratio < 1.3:
            return "stable"
        elif gust_ratio < 1.6:
            return "moderate"
        elif gust_ratio < 2.0:
            return "unstable"
        else:
            return "very_unstable"

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast using advanced models."""
        _LOGGER.debug("async_forecast_daily called - generating with advanced models")

        result = await self.hass.async_add_executor_job(
            self._generate_advanced_daily_forecast, 3
        )
        _LOGGER.debug(f"async_forecast_daily returning {len(result) if result else 0} days")
        return result

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast using advanced models."""
        _LOGGER.debug("async_forecast_hourly called - generating with advanced models")

        result = await self.hass.async_add_executor_job(
            self._generate_advanced_hourly_forecast, 24
        )
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

            _LOGGER.debug(
                f"📊 Daily forecast sensors: "
                f"P={pressure}hPa, T={temperature}°C, "
                f"Wind={wind_speed}m/s @{wind_dir}°"
            )

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

            _LOGGER.debug(
                f"📈 Trends: ΔP={pressure_change_3h}hPa/3h, "
                f"ΔT={temp_change_1h}°C/h"
            )

            # Get current rain rate for real-time override
            current_rain_rate = 0.0
            rain_rate_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
            _LOGGER.debug(f"🌧️ Rain rate sensor config: {rain_rate_sensor_id}")
            if rain_rate_sensor_id:
                rain_sensor = self.hass.states.get(rain_rate_sensor_id)
                _LOGGER.debug(
                    f"🌧️ Rain rate sensor state: {rain_sensor.state if rain_sensor else 'NOT_FOUND'} "
                    f"(entity: {rain_rate_sensor_id})"
                )
                if rain_sensor and rain_sensor.state not in ("unknown", "unavailable"):
                    try:
                        current_rain_rate = float(rain_sensor.state)
                        _LOGGER.debug(f"🌧️ Current rain rate: {current_rain_rate} mm/h")
                    except (ValueError, TypeError) as err:
                        _LOGGER.warning(f"🌧️ Failed to parse rain rate: {err}")
            else:
                _LOGGER.debug("🌧️ No rain rate sensor configured")

            # Get solar radiation for temperature model (optional)
            solar_radiation = None
            solar_sensor_id = self._get_config(CONF_SOLAR_RADIATION_SENSOR)
            if solar_sensor_id:
                solar_state = self.hass.states.get(solar_sensor_id)
                if solar_state and solar_state.state not in ("unknown", "unavailable"):
                    try:
                        raw_value = float(solar_state.state)
                        unit = solar_state.attributes.get("unit_of_measurement", "W/m²")
                        # Convert to W/m² (from lux if needed)
                        solar_radiation = UnitConverter.convert_solar_radiation(raw_value, unit)
                        _LOGGER.debug(f"☀️ Solar radiation: {solar_radiation} W/m²")
                    except (ValueError, TypeError):
                        pass
            else:
                _LOGGER.debug("☀️ No solar radiation sensor configured")

            # Get cloud coverage for temperature model (optional)
            cloud_cover = None

            # Get humidity for cloud cover estimation (optional)
            humidity = self.humidity
            if humidity is not None:
                _LOGGER.debug(f"💧 Humidity: {humidity}%")
            else:
                _LOGGER.debug("💧 No humidity data available")


            # Get location and hemisphere for temperature model
            # Try to get latitude from config, fall back to Home Assistant's location
            latitude = self._get_config(CONF_LATITUDE)
            if latitude is None:
                latitude = self.hass.config.latitude if self.hass and self.hass.config.latitude else DEFAULT_LATITUDE

            # Get longitude (not in CONF currently, use HA config)
            longitude = self.hass.config.longitude if self.hass and self.hass.config.longitude else 21.25  # Default: Košice

            # Get hemisphere from config
            hemisphere = self._get_config(CONF_HEMISPHERE)
            if hemisphere is None:
                hemisphere = "north"  # Default

            # Create models
            pressure_model = PressureModel(pressure, pressure_change_3h)
            temp_model = TemperatureModel(
                temperature,
                temp_change_1h,
                solar_radiation=solar_radiation,
                cloud_cover=cloud_cover,
                humidity=humidity,
                hass=self.hass,
                latitude=latitude,
                longitude=longitude,
                hemisphere=hemisphere
            )

            # Get user's selected forecast model
            forecast_model = self._get_config(CONF_FORECAST_MODEL) or DEFAULT_FORECAST_MODEL
            _LOGGER.debug(f"📊 Using forecast model for daily forecast: {forecast_model}")


            # Get elevation from config, fall back to Home Assistant's elevation, then to default
            elevation = self._get_config(CONF_ELEVATION)
            if elevation is None:
                elevation = self.hass.config.elevation if self.hass and self.hass.config.elevation else DEFAULT_ELEVATION
                _LOGGER.debug(f"📍 Using elevation from Home Assistant: {elevation}m")
            else:
                _LOGGER.debug(f"📍 Using elevation from config: {elevation}m")

            # Determine which algorithm to use based on selected model
            if forecast_model == FORECAST_MODEL_ENHANCED:
                # Enhanced: Use weighted combination of both algorithms
                # Generate forecasts from both and combine them
                zambretti = ZambrettiForecaster(
                    hass=self.hass,
                    latitude=latitude,
                    solar_radiation=solar_radiation
                )
                _LOGGER.debug("📊 Enhanced mode: Using combined Zambretti + Negretti algorithms")
            elif forecast_model == FORECAST_MODEL_NEGRETTI:
                # Negretti-Zambra: Conservative slide-rule method
                # Note: We still use Zambretti class but with Negretti-optimized parameters
                from .negretti_zambra import calculate_negretti_zambra_forecast as negretti_calc
                zambretti = ZambrettiForecaster(
                    hass=self.hass,
                    latitude=latitude,
                    solar_radiation=solar_radiation
                )
                _LOGGER.debug("📊 Negretti-Zambra mode: Using conservative algorithm")
            else:  # FORECAST_MODEL_ZAMBRETTI
                # Classic Zambretti: Optimized for rising/falling pressure
                zambretti = ZambrettiForecaster(
                    hass=self.hass,
                    latitude=latitude,
                    solar_radiation=solar_radiation
                )
                _LOGGER.debug("📊 Zambretti mode: Using classic algorithm")

            # Create generators with rain rate and selected model
            hourly_gen = HourlyForecastGenerator(
                self.hass,
                pressure_model,
                temp_model,
                zambretti,
                wind_direction=int(wind_dir),
                wind_speed=float(wind_speed),
                latitude=latitude,
                elevation=elevation,
                current_rain_rate=current_rain_rate,
                forecast_model=forecast_model
            )

            daily_gen = DailyForecastGenerator(hourly_gen)

            # Generate forecast
            forecasts = daily_gen.generate(days)

            _LOGGER.debug(
                f"✅ Generated {len(forecasts)} daily forecasts "
                f"(P={pressure}hPa, T={temperature}°C)"
            )

            return forecasts  # type: ignore[return-value]

        except Exception as e:
            _LOGGER.error(f"❌ Error generating advanced daily forecast: {e}", exc_info=True)
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

            # Get current rain rate for real-time override
            current_rain_rate = 0.0
            rain_rate_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
            _LOGGER.debug(f"Current rain rate sensor config: {rain_rate_sensor_id}")
            if rain_rate_sensor_id:
                rain_sensor = self.hass.states.get(rain_rate_sensor_id)
                _LOGGER.debug(
                    f"Rain rate sensor state: {rain_sensor.state if rain_sensor else 'NOT_FOUND'} "
                    f"(entity: {rain_rate_sensor_id})"
                )
                if rain_sensor and rain_sensor.state not in ("unknown", "unavailable"):
                    try:
                        current_rain_rate = float(rain_sensor.state)
                        _LOGGER.debug(f"Current rain rate: {current_rain_rate} mm/h")
                    except (ValueError, TypeError) as err:
                        _LOGGER.warning(f"Failed to parse rain rate: {err}")
            else:
                _LOGGER.debug("No rain rate sensor configured")

            # Get solar radiation for temperature model (optional)
            solar_radiation = None
            solar_sensor_id = self._get_config(CONF_SOLAR_RADIATION_SENSOR)
            if solar_sensor_id:
                solar_state = self.hass.states.get(solar_sensor_id)
                if solar_state and solar_state.state not in ("unknown", "unavailable"):
                    try:
                        raw_value = float(solar_state.state)
                        unit = solar_state.attributes.get("unit_of_measurement", "W/m²")
                        # Convert to W/m² (from lux if needed)
                        solar_radiation = UnitConverter.convert_solar_radiation(raw_value, unit)
                        _LOGGER.debug(f"Solar radiation for daily forecast: {solar_radiation} W/m²")
                    except (ValueError, TypeError):
                        pass


            # Get cloud coverage for temperature model (optional)
            cloud_cover = None

            # Get humidity for cloud cover estimation (optional)
            humidity = self.humidity
            if humidity is not None:
                _LOGGER.debug(f"Humidity for hourly forecast: {humidity}%")


            # Get location and hemisphere for temperature model
            # Try to get latitude from config, fall back to Home Assistant's location
            latitude = self._get_config(CONF_LATITUDE)
            if latitude is None:
                latitude = self.hass.config.latitude if self.hass and self.hass.config.latitude else DEFAULT_LATITUDE

            # Get longitude (not in CONF currently, use HA config)
            longitude = self.hass.config.longitude if self.hass and self.hass.config.longitude else 21.25  # Default: Košice

            # Get hemisphere from config
            hemisphere = self._get_config(CONF_HEMISPHERE)
            if hemisphere is None:
                hemisphere = "north"  # Default

            # Create models
            pressure_model = PressureModel(pressure, pressure_change_3h)
            temp_model = TemperatureModel(
                temperature,
                temp_change_1h,
                solar_radiation=solar_radiation,
                cloud_cover=cloud_cover,
                humidity=humidity,
                hass=self.hass,
                latitude=latitude,
                longitude=longitude,
                hemisphere=hemisphere
            )

            # Get user's selected forecast model
            forecast_model = self._get_config(CONF_FORECAST_MODEL) or DEFAULT_FORECAST_MODEL
            _LOGGER.debug(f"📊 Using forecast model for hourly forecast: {forecast_model}")


            # Get elevation from config, fall back to Home Assistant's elevation, then to default
            elevation = self._get_config(CONF_ELEVATION)
            if elevation is None:
                elevation = self.hass.config.elevation if self.hass and self.hass.config.elevation else DEFAULT_ELEVATION
                _LOGGER.debug(f"📍 Using elevation from Home Assistant: {elevation}m")
            else:
                _LOGGER.debug(f"📍 Using elevation from config: {elevation}m")

            # Determine which algorithm to use based on selected model
            if forecast_model == FORECAST_MODEL_ENHANCED:
                # Enhanced: Use weighted combination of both algorithms
                zambretti = ZambrettiForecaster(
                    hass=self.hass,
                    latitude=latitude,
                    solar_radiation=solar_radiation
                )
                _LOGGER.debug("📊 Enhanced mode: Using combined Zambretti + Negretti algorithms")
            elif forecast_model == FORECAST_MODEL_NEGRETTI:
                # Negretti-Zambra: Conservative slide-rule method
                zambretti = ZambrettiForecaster(
                    hass=self.hass,
                    latitude=latitude,
                    solar_radiation=solar_radiation
                )
                _LOGGER.debug("📊 Negretti-Zambra mode: Using conservative algorithm")
            else:  # FORECAST_MODEL_ZAMBRETTI
                # Classic Zambretti: Optimized for rising/falling pressure
                zambretti = ZambrettiForecaster(
                    hass=self.hass,
                    latitude=latitude,
                    solar_radiation=solar_radiation
                )
                _LOGGER.debug("📊 Zambretti mode: Using classic algorithm")

            # Create generator with rain rate and selected model
            hourly_gen = HourlyForecastGenerator(
                self.hass,
                pressure_model,
                temp_model,
                zambretti,
                wind_direction=int(wind_dir),
                wind_speed=float(wind_speed),
                latitude=latitude,
                elevation=elevation,
                current_rain_rate=current_rain_rate,
                forecast_model=forecast_model
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

            return forecasts  # type: ignore[return-value]

        except Exception as e:
            _LOGGER.error(f"Error generating advanced hourly forecast: {e}", exc_info=True)
            return None

