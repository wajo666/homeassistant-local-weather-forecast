"""Weather entity for Local Weather Forecast integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SUNNY,
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
    CONF_CLOUD_COVERAGE_SENSOR,
    CONF_DEWPOINT_SENSOR,
    CONF_ENABLE_WEATHER_ENTITY,
    CONF_HUMIDITY_SENSOR,
    CONF_LATITUDE,
    CONF_PRESSURE_SENSOR,
    CONF_RAIN_RATE_SENSOR,
    CONF_SOLAR_RADIATION_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    CONF_UV_INDEX_SENSOR,
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
            sw_version="3.1.2",
        )
        self._last_rain_time = None  # Track when it last rained (for 15-min timeout)
        self._last_rain_value = None  # Track last rain sensor value (for accumulation sensors)
        self._last_rain_check_time = None  # Track when we last checked (for rate calculation)

        # Log rain sensor configuration at startup
        rain_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
        if rain_sensor_id:
            _LOGGER.info(f"Weather: Rain sensor configured: {rain_sensor_id}")

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
        # Check if user provided a dewpoint sensor
        dewpoint_sensor = self._get_config(CONF_DEWPOINT_SENSOR)
        if dewpoint_sensor:
            state = self.hass.states.get(dewpoint_sensor)
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
        """Return the current condition based on Zambretti forecast and current weather."""
        try:
            # Safety check - if hass is not available yet, return default
            if not self.hass:
                return ATTR_CONDITION_PARTLYCLOUDY

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
                            _LOGGER.info(
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
                                _LOGGER.info(
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

                        # If it's currently raining, return rainy condition
                        if is_raining_now:
                            _LOGGER.debug(f"Weather: Currently raining - override to rainy")
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

                # SNOW CONDITIONS (temperature ≤ 4°C + high humidity + precipitation likely):
                # Snow detected when temp is freezing + high moisture + near saturation
                if temp <= 0 and humidity > 80 and dewpoint_spread < 2.0:
                    # Get rain probability to check if precipitation is likely
                    rain_prob_sensor = self.hass.states.get("sensor.local_forecast_rain_probability")
                    rain_prob = 0
                    if rain_prob_sensor and rain_prob_sensor.state not in ("unknown", "unavailable", None):
                        try:
                            rain_prob = float(rain_prob_sensor.state)
                        except (ValueError, TypeError):
                            pass

                    if rain_prob > 60:  # High snow risk
                        _LOGGER.info(
                            f"Weather: SNOW detected - temp={temp:.1f}°C, humidity={humidity:.1f}%, "
                            f"dewpoint_spread={dewpoint_spread:.1f}°C, rain_prob={rain_prob}%"
                        )
                        return ATTR_CONDITION_SNOWY

                # Medium snow risk (0-2°C range)
                elif 0 < temp <= 2 and humidity > 70 and dewpoint_spread < 3.0:
                    rain_prob_sensor = self.hass.states.get("sensor.local_forecast_rain_probability")
                    rain_prob = 0
                    if rain_prob_sensor and rain_prob_sensor.state not in ("unknown", "unavailable", None):
                        try:
                            rain_prob = float(rain_prob_sensor.state)
                        except (ValueError, TypeError):
                            pass

                    if rain_prob > 40:  # Medium snow risk
                        _LOGGER.info(
                            f"Weather: SNOW likely - temp={temp:.1f}°C, humidity={humidity:.1f}%, "
                            f"dewpoint_spread={dewpoint_spread:.1f}°C, rain_prob={rain_prob}%"
                        )
                        return ATTR_CONDITION_SNOWY

                # FOG CONDITIONS (meteorologically justified):
                # Fog occurs when dewpoint spread is very low and humidity is high
                # This can happen anytime (day or night) when conditions are met
                # - Dewpoint spread < 1.5°C = CRITICAL fog risk
                # - Humidity > 85% = high moisture content
                # - Combined = actual fog likely present
                # NOTE: Check fog AFTER snow (snow takes priority if temp is freezing)
                if dewpoint_spread < 1.5 and humidity > 85:
                    _LOGGER.info(
                        f"Weather: FOG detected - dewpoint spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, hour={current_hour}"
                    )
                    return ATTR_CONDITION_FOG
                # Near-fog conditions (very low spread + high humidity)
                elif dewpoint_spread < 1.0 and humidity > 80:
                    _LOGGER.info(
                        f"Weather: FOG detected (near saturation) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, hour={current_hour}"
                    )
                    return ATTR_CONDITION_FOG

            # PRIORITY 3: Get Zambretti forecast condition
            zambretti_sensor = self.hass.states.get("sensor.local_forecast_zambretti_detail")
            if zambretti_sensor and zambretti_sensor.state not in ("unknown", "unavailable", None):
                try:
                    attrs = zambretti_sensor.attributes or {}
                    letter_code = attrs.get("letter_code", "A")

                    _LOGGER.debug(
                        f"Weather: Zambretti sensor state={zambretti_sensor.state}, "
                        f"letter_code={letter_code}"
                    )

                    # Map Zambretti letter to HA condition
                    condition = ZAMBRETTI_TO_CONDITION.get(letter_code, ATTR_CONDITION_PARTLYCLOUDY)

                    _LOGGER.debug(f"Weather: Mapped letter {letter_code} → condition {condition}")

                    # HUMIDITY-BASED CLOUD COVER CORRECTION
                    # If high humidity but Zambretti says partly cloudy, upgrade to cloudy
                    # This addresses the issue where high humidity (80%+) should mean more clouds
                    humidity = self.humidity
                    if humidity is not None:
                        _LOGGER.debug(f"Weather: Current humidity={humidity}%")

                        # Very high humidity (>85%) = overcast conditions
                        if humidity > 85 and condition in (ATTR_CONDITION_PARTLYCLOUDY, ATTR_CONDITION_SUNNY):
                            _LOGGER.info(
                                f"Weather: Humidity correction: {condition} → cloudy "
                                f"(RH={humidity:.1f}% > 85%)"
                            )
                            condition = ATTR_CONDITION_CLOUDY
                        # High humidity (70-85%) = mostly cloudy if Zambretti says sunny
                        elif humidity > 70 and condition == ATTR_CONDITION_SUNNY:
                            _LOGGER.info(
                                f"Weather: Humidity correction: sunny → partlycloudy "
                                f"(RH={humidity:.1f}% > 70%)"
                            )
                            condition = ATTR_CONDITION_PARTLYCLOUDY

                    # Check if it's night time (between sunset and sunrise)
                    if condition == ATTR_CONDITION_SUNNY and self._is_night():
                        _LOGGER.debug("Weather: Night time, converting sunny → clear-night")
                        return ATTR_CONDITION_CLEAR_NIGHT

                    return condition
                except (AttributeError, KeyError, TypeError) as e:
                    _LOGGER.debug(f"Weather: Error reading Zambretti sensor: {e}")

            # PRIORITY 4: Fallback based on pressure
            pressure = self.native_pressure
            if pressure:
                if pressure < 1000:
                    _LOGGER.debug(f"Weather: Fallback to rainy (pressure={pressure})")
                    return ATTR_CONDITION_RAINY
                elif pressure < 1013:
                    _LOGGER.debug(f"Weather: Fallback to cloudy (pressure={pressure})")
                    return ATTR_CONDITION_CLOUDY
                elif pressure < 1020:
                    _LOGGER.debug(f"Weather: Fallback to partly cloudy (pressure={pressure})")
                    return ATTR_CONDITION_PARTLYCLOUDY
                else:
                    if self._is_night():
                        _LOGGER.debug(f"Weather: Fallback to clear night (pressure={pressure})")
                        return ATTR_CONDITION_CLEAR_NIGHT
                    _LOGGER.debug(f"Weather: Fallback to sunny (pressure={pressure})")
                    return ATTR_CONDITION_SUNNY

            return ATTR_CONDITION_PARTLYCLOUDY
        except Exception as e:
            _LOGGER.error(f"Error determining weather condition: {e}", exc_info=True)
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
            _LOGGER.debug(
                f"Weather: Fog risk={fog_risk_level}, temp={temp:.1f}°C, "
                f"dewpoint={dewpoint:.1f}°C, spread={spread:.1f}°C"
            )

        # Add snow risk and frost/ice risk
        humidity = self.humidity
        if temp is not None and humidity is not None and dewpoint is not None:
            # Get rain probability for snow risk calculation
            rain_prob = 0
            rain_prob_sensor = self.hass.states.get("sensor.local_forecast_rain_probability")
            if rain_prob_sensor and rain_prob_sensor.state not in ("unknown", "unavailable", None):
                try:
                    rain_prob = float(rain_prob_sensor.state)
                except (ValueError, TypeError):
                    pass

            from .calculations import get_snow_risk, get_frost_risk

            # Calculate snow risk
            spread = temp - dewpoint
            snow_risk = get_snow_risk(temp, humidity, spread, rain_prob)
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
                _LOGGER.warning(
                    f"⚠️ CRITICAL: BLACK ICE WARNING! Temperature={temp:.1f}°C, "
                    f"Humidity={humidity:.1f}%, Spread={spread:.1f}°C"
                )
            if snow_risk == "high":
                _LOGGER.info(
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
                        solar_radiation = float(solar_state.state)
                        _LOGGER.debug(f"☀️ Solar radiation: {solar_radiation} W/m²")
                    except (ValueError, TypeError):
                        pass
            else:
                _LOGGER.debug("☀️ No solar radiation sensor configured")

            # Get cloud coverage for temperature model (optional)
            cloud_cover = None
            cloud_sensor_id = self._get_config(CONF_CLOUD_COVERAGE_SENSOR)
            if cloud_sensor_id:
                cloud_state = self.hass.states.get(cloud_sensor_id)
                if cloud_state and cloud_state.state not in ("unknown", "unavailable"):
                    try:
                        cloud_cover = float(cloud_state.state)
                        _LOGGER.debug(f"☁️ Cloud cover: {cloud_cover}%")
                    except (ValueError, TypeError):
                        pass
            else:
                _LOGGER.debug("☁️ No cloud coverage sensor configured")

            # Get humidity for cloud cover estimation (optional)
            humidity = self.humidity
            if humidity is not None:
                _LOGGER.debug(f"💧 Humidity: {humidity}%")
            else:
                _LOGGER.debug("💧 No humidity data available")

            # Get UV index for cloud cover correction (optional, Ecowitt WS90)
            uv_index = None
            uv_sensor_id = self._get_config(CONF_UV_INDEX_SENSOR)
            if uv_sensor_id:
                uv_state = self.hass.states.get(uv_sensor_id)
                if uv_state and uv_state.state not in ("unknown", "unavailable"):
                    try:
                        uv_index = float(uv_state.state)
                        _LOGGER.debug(f"☀️ UV index: {uv_index}")
                    except (ValueError, TypeError):
                        pass
            else:
                _LOGGER.debug("☀️ No UV index sensor configured")

            # Create models
            pressure_model = PressureModel(pressure, pressure_change_3h)
            temp_model = TemperatureModel(
                temperature,
                temp_change_1h,
                solar_radiation=solar_radiation,
                cloud_cover=cloud_cover,
                humidity=humidity,
                hass=self.hass
            )

            # Create Zambretti forecaster with hass for sun entity access
            # Try to get latitude from config, fall back to Home Assistant's location, then to default
            latitude = self._get_config(CONF_LATITUDE)
            if latitude is None:
                latitude = self.hass.config.latitude if self.hass and self.hass.config.latitude else DEFAULT_LATITUDE
                _LOGGER.debug(f"📍 Using latitude from Home Assistant: {latitude}°")
            else:
                _LOGGER.debug(f"📍 Using latitude from config: {latitude}°")

            zambretti = ZambrettiForecaster(
                hass=self.hass,
                latitude=latitude,
                uv_index=uv_index,
                solar_radiation=solar_radiation
            )

            # Create generators with rain rate
            hourly_gen = HourlyForecastGenerator(
                self.hass,
                pressure_model,
                temp_model,
                zambretti,
                wind_direction=int(wind_dir),
                wind_speed=float(wind_speed),
                latitude=latitude,
                current_rain_rate=current_rain_rate
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
                        solar_radiation = float(solar_state.state)
                        _LOGGER.debug(f"Solar radiation for hourly forecast: {solar_radiation} W/m²")
                    except (ValueError, TypeError):
                        pass

            # Get cloud coverage for temperature model (optional)
            cloud_cover = None
            cloud_sensor_id = self._get_config(CONF_CLOUD_COVERAGE_SENSOR)
            if cloud_sensor_id:
                cloud_state = self.hass.states.get(cloud_sensor_id)
                if cloud_state and cloud_state.state not in ("unknown", "unavailable"):
                    try:
                        cloud_cover = float(cloud_state.state)
                        _LOGGER.debug(f"Cloud cover for hourly forecast: {cloud_cover}%")
                    except (ValueError, TypeError):
                        pass

            # Get humidity for cloud cover estimation (optional)
            humidity = self.humidity
            if humidity is not None:
                _LOGGER.debug(f"Humidity for hourly forecast: {humidity}%")

            # Get UV index for cloud cover correction (optional, Ecowitt WS90)
            uv_index = None
            uv_sensor_id = self._get_config(CONF_UV_INDEX_SENSOR)
            if uv_sensor_id:
                uv_state = self.hass.states.get(uv_sensor_id)
                if uv_state and uv_state.state not in ("unknown", "unavailable"):
                    try:
                        uv_index = float(uv_state.state)
                        _LOGGER.debug(f"UV index for hourly forecast: {uv_index}")
                    except (ValueError, TypeError):
                        pass

            # Create models
            pressure_model = PressureModel(pressure, pressure_change_3h)
            temp_model = TemperatureModel(
                temperature,
                temp_change_1h,
                solar_radiation=solar_radiation,
                cloud_cover=cloud_cover,
                humidity=humidity,
                hass=self.hass
            )

            # Create Zambretti forecaster with hass for sun entity access
            # Try to get latitude from config, fall back to Home Assistant's location, then to default
            latitude = self._get_config(CONF_LATITUDE)
            if latitude is None:
                latitude = self.hass.config.latitude if self.hass and self.hass.config.latitude else DEFAULT_LATITUDE
                _LOGGER.debug(f"📍 Using latitude from Home Assistant: {latitude}°")
            else:
                _LOGGER.debug(f"📍 Using latitude from config: {latitude}°")

            zambretti = ZambrettiForecaster(
                hass=self.hass,
                latitude=latitude,
                uv_index=uv_index,
                solar_radiation=solar_radiation
            )

            # Create generator with rain rate
            hourly_gen = HourlyForecastGenerator(
                self.hass,
                pressure_model,
                temp_model,
                zambretti,
                wind_direction=int(wind_dir),
                wind_speed=float(wind_speed),
                latitude=latitude,
                current_rain_rate=current_rain_rate
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

