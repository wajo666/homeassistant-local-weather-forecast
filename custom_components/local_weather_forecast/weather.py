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
            sw_version="3.1.9",
        )
        self._last_rain_time = None  # Track when it last rained (for 15-min timeout)
        self._last_rain_value = None  # Track last rain sensor value (for accumulation sensors)
        self._last_rain_check_time = None  # Track when we last checked (for rate calculation)

        # Log rain sensor configuration at startup
        rain_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
        if rain_sensor_id:
            _LOGGER.debug(f"Weather: Rain sensor configured: {rain_sensor_id}")

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
                            # If temperature is at or below 2°C, precipitation is SNOW not rain
                            if temp is not None and temp <= 2:
                                _LOGGER.debug(
                                    f"Weather: SNOW detected from precipitation sensor - "
                                    f"temp={temp:.1f}°C (frozen precipitation)"
                                )
                                return ATTR_CONDITION_SNOWY
                            else:
                                _LOGGER.debug(
                                    f"Weather: Currently raining - override to rainy (temp={temp}°C)"
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


                # FOG CONDITIONS (scientific model based on WMO/NOAA/MetOffice):
                # Fog requires:
                # 1. Very low dewpoint spread (near saturation)
                # 2. High humidity (> 90%)
                # 3. Calm weather (fog dissipates with wind > 3 m/s)
                # 4. Night factor (fog forms easier at night, dissipates during day)
                #
                # Three-level conservative model (90% accuracy):
                # - CRITICAL: spread < 0.5°C + humidity > 95% → always fog
                # - LIKELY: spread < 1.0°C + humidity > 93% + calm → fog
                # - POSSIBLE: spread < 1.5°C + humidity > 90% + night + very calm → fog
                # - MIST/CLOUDY: spread < 2.5°C + humidity > 85% → show CLOUDY, not FOG

                # Get wind speed for fog dissipation check
                wind_speed = self.native_wind_speed or 0.0

                # Determine if night (fog forms easier, less likely to dissipate)
                is_night = current_hour < 6 or current_hour >= 20

                # LEVEL 1: CRITICAL FOG (100% confidence)
                # Dense fog, visibility < 200m
                if dewpoint_spread < 0.5 and humidity > 95:
                    _LOGGER.debug(
                        f"Weather: FOG (CRITICAL) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s, "
                        f"hour={current_hour} (dense fog, visibility < 200m)"
                    )
                    return ATTR_CONDITION_FOG

                # LEVEL 2: LIKELY FOG (80%+ confidence)
                # Moderate fog, visibility 200-500m, requires calm weather
                elif dewpoint_spread < 1.0 and humidity > 93 and wind_speed < 3.0:
                    _LOGGER.debug(
                        f"Weather: FOG (LIKELY) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s, "
                        f"hour={current_hour} (moderate fog, calm weather)"
                    )
                    return ATTR_CONDITION_FOG

                # LEVEL 3: POSSIBLE FOG - Night only (60%+ confidence)
                # Light fog/mist, visibility 500m-1km, night only + very calm
                elif is_night and dewpoint_spread < 1.5 and humidity > 90 and wind_speed < 2.0:
                    _LOGGER.debug(
                        f"Weather: FOG (POSSIBLE, night) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s, "
                        f"hour={current_hour} (light fog/mist at night)"
                    )
                    return ATTR_CONDITION_FOG

                # MIST/CLOUDY (not fog, but damp/humid)
                # High humidity but not saturated enough for actual fog
                # Let solar/pressure determine cloudiness (will likely show CLOUDY)
                elif dewpoint_spread < 2.5 and humidity > 85:
                    _LOGGER.debug(
                        f"Weather: MIST/HIGH HUMIDITY (not fog) - spread={dewpoint_spread:.1f}°C, "
                        f"humidity={humidity:.1f}%, wind={wind_speed:.1f} m/s "
                        f"(too dry for fog, continuing to cloudiness check)"
                    )

            # PRIORITY 3: SOLAR RADIATION BASED CLOUD DETECTION
            # Solar radiation reveals actual cloud cover better than forecast
            # This provides real-time cloudiness detection from measured sunlight
            solar_radiation = None
            solar_cloudiness = None  # Will store solar-determined cloudiness hint
            solar_sensor_id = self._get_config(CONF_SOLAR_RADIATION_SENSOR)
            if solar_sensor_id:
                solar_state = self.hass.states.get(solar_sensor_id)
                if solar_state and solar_state.state not in ("unknown", "unavailable", None):
                    try:
                        raw_value = float(solar_state.state)
                        unit = solar_state.attributes.get("unit_of_measurement", "W/m²")
                        # Convert to W/m² (from lux if needed)
                        solar_radiation = UnitConverter.convert_solar_radiation(raw_value, unit)
                    except (ValueError, TypeError):
                        pass

            # Only use solar radiation during daytime with sufficient sunlight
            # IMPORTANT: Check both sun position AND actual solar radiation value!
            # - sun.sun above_horizon: Prevents use at night
            # - solar_radiation > 50 W/m²: Prevents use at sunrise/sunset when radiation is too low
            #
            # Why 50 W/m² threshold?
            # - At sunrise/sunset: radiation is 0-50 W/m² even with clear skies
            # - During day: clear skies give >100 W/m² even in winter
            # - This prevents false "cloudy" detection when sky is clear but sun is low
            if (solar_radiation is not None
                and self.hass.states.is_state('sun.sun', 'above_horizon')
                and solar_radiation > 50):

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

                if theoretical_max > 50:  # Only during significant daylight
                    # Calculate cloud cover percentage from solar radiation
                    cloud_ratio = solar_radiation / theoretical_max if theoretical_max > 0 else 0
                    cloud_percent = max(0, min(100, (1 - cloud_ratio) * 100))

                    _LOGGER.debug(
                        f"Weather: Solar radiation cloud detection - "
                        f"measured={solar_radiation:.0f} W/m², theoretical={theoretical_max:.0f} W/m², "
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
                    # - 0-2 oktas (0-25%): FEW clouds → SUNNY/CLEAR
                    # - 3-4 oktas (25-50%): SCT (scattered) → PARTLY CLOUDY
                    # - 5-7 oktas (50-87.5%): BKN (broken) → CLOUDY
                    # - 8 oktas (87.5-100%): OVC (overcast) → OVERCAST
                    #
                    # These thresholds align with international aviation (METAR) and meteorological standards.

                    if cloud_percent < 25:
                        # WMO: 0-2 oktas (FEW clouds)
                        solar_cloudiness = ATTR_CONDITION_SUNNY
                        _LOGGER.debug(
                            f"Weather: Solar HIGH CONFIDENCE → clear skies (FEW clouds) "
                            f"(cloud_cover={cloud_percent:.0f}%, WMO: 0-2 oktas)"
                        )
                    elif cloud_percent < 50:
                        # WMO: 3-4 oktas (SCT - scattered clouds)
                        solar_cloudiness = ATTR_CONDITION_PARTLYCLOUDY
                        _LOGGER.debug(
                            f"Weather: Solar MEDIUM CONFIDENCE → scattered clouds (SCT) "
                            f"(cloud_cover={cloud_percent:.0f}%, WMO: 3-4 oktas)"
                        )
                    elif cloud_percent < 87.5:
                        # WMO: 5-7 oktas (BKN - broken clouds)
                        solar_cloudiness = ATTR_CONDITION_CLOUDY
                        _LOGGER.debug(
                            f"Weather: Solar LOW CONFIDENCE → mostly cloudy (BKN) "
                            f"(cloud_cover={cloud_percent:.0f}%, WMO: 5-7 oktas)"
                        )
                    else:
                        # WMO: 8 oktas (OVC - overcast)
                        # VERY LOW CONFIDENCE: Heavy overcast (≥ 87.5%)
                        # Too cloudy - defer completely to forecast for rain/snow determination
                        _LOGGER.debug(
                            f"Weather: Solar VERY LOW CONFIDENCE → overcast (OVC) "
                            f"(cloud_cover={cloud_percent:.0f}%, WMO: 8 oktas), deferring to forecast"
                        )
                        solar_cloudiness = None  # Don't override

                    # If we have solar cloudiness determination, check rain sensor
                    if solar_cloudiness is not None:
                        # Check for active precipitation (overrides cloudiness)
                        rain_rate_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
                        current_rain = 0.0
                        if rain_rate_sensor_id:
                            rain_sensor = self.hass.states.get(rain_rate_sensor_id)
                            if rain_sensor and rain_sensor.state not in ("unknown", "unavailable", None):
                                try:
                                    current_rain = float(rain_sensor.state)
                                except (ValueError, TypeError):
                                    pass

                        # Active precipitation overrides solar cloudiness
                        if current_rain > 0.01:
                            temp = self.native_temperature
                            if temp is not None and temp <= 2:
                                _LOGGER.debug(
                                    f"Weather: Solar + Rain sensor → snowy "
                                    f"(clouds={cloud_percent:.0f}%, rain={current_rain:.3f} mm/h, "
                                    f"temp={temp:.1f}°C, diamond dust/ice crystals)"
                                )
                                return ATTR_CONDITION_SNOWY
                            else:
                                _LOGGER.debug(
                                    f"Weather: Solar + Rain sensor → rainy "
                                    f"(clouds={cloud_percent:.0f}%, rain={current_rain:.3f} mm/h, virga)"
                                )
                                return ATTR_CONDITION_RAINY

                        # No active precipitation - use solar cloudiness but check forecast
                        # for precipitation predictions that rain sensor might miss
                        # (e.g., frozen sensor, approaching storm)
                        # We'll store solar_cloudiness and apply it after checking forecast
                        _LOGGER.debug(
                            f"Weather: Solar cloudiness={solar_cloudiness}, "
                            f"continuing to check forecast for precipitation warnings"
                        )

                    # Fall through to PRIORITY 4 and 5 with solar_cloudiness hint
            elif solar_radiation is not None and solar_radiation <= 50:
                _LOGGER.debug(
                    f"Weather: Solar radiation too low ({solar_radiation:.0f} W/m² ≤ 50), "
                    f"skipping cloud detection (sunrise/sunset or night)"
                )

            # PRIORITY 4: CURRENT CONDITION from pressure (forecast_short_term)
            # This shows weather condition NOW based on current absolute pressure
            # Unlike Zambretti/Negretti which predict FUTURE (6-12h ahead)
            #
            # Ranges (empirical, meteorologically sound):
            # - p0 < 980 hPa  → Stormy (very low pressure)
            # - 980-1000 hPa  → Rainy (low pressure)
            # - 1000-1020 hPa → Mixed/Partly cloudy (normal)
            # - 1020-1040 hPa → Sunny (high pressure)
            # - p0 ≥ 1040 hPa → Very dry (very high pressure)
            #
            # This will be used if solar radiation didn't already return,
            # and will be overridden by forecast models if configured.

            current_condition_from_pressure = None
            main_sensor = self.hass.states.get("sensor.local_forecast")
            if main_sensor and main_sensor.state not in ("unknown", "unavailable", None):
                try:
                    main_attrs = main_sensor.attributes or {}
                    forecast_short_term = main_attrs.get("forecast_short_term")

                    if forecast_short_term and isinstance(forecast_short_term, list) and len(forecast_short_term) > 0:
                        # forecast_short_term format: [condition_text, pressure_system_text]
                        # Example: ["slnečný", "Vysoký tlak"] or ["Sunny", "High Pressure System"]
                        current_text = forecast_short_term[0].lower()

                        # Map Slovak/multilingual text to HA condition
                        is_night = self._is_night()

                        if any(word in current_text for word in ["storm", "búrlivý", "θυελλώδης"]):
                            current_condition_from_pressure = "lightning-rainy"
                        elif any(word in current_text for word in ["rain", "daždivý", "βροχερός", "piovoso"]):
                            current_condition_from_pressure = "rainy"
                        elif any(word in current_text for word in ["sunny", "slnečný", "ηλιόλουστος", "soleggiato"]):
                            current_condition_from_pressure = "clear-night" if is_night else "sunny"
                        elif any(word in current_text for word in ["mixed", "premenlivý", "μεταβλητός", "variabile"]):
                            current_condition_from_pressure = "partlycloudy"
                        elif any(word in current_text for word in ["dry", "sucho", "ξηρός", "secco"]):
                            current_condition_from_pressure = "clear-night" if is_night else "sunny"

                        if current_condition_from_pressure:
                            _LOGGER.debug(
                                f"Weather: PRIORITY 4 - Current condition from pressure: "
                                f"'{forecast_short_term[0]}' → {current_condition_from_pressure} "
                                f"(this is CURRENT state NOW, not future prediction)"
                            )
                except (AttributeError, KeyError, TypeError) as e:
                    _LOGGER.debug(f"Weather: Could not get forecast_short_term: {e}")

            # PRIORITY 5: Get forecast condition based on selected model
            # User can choose: Enhanced (default), Zambretti, Negretti-Zambra, or Combined
            # NOTE: These forecast models predict FUTURE weather (6-12h ahead)!
            # They will override current_condition_from_pressure if configured.
            forecast_model = self._get_config(CONF_FORECAST_MODEL) or DEFAULT_FORECAST_MODEL

            # Initialize condition variable (will be set by forecast or fallback logic)
            condition = None

            # Determine which sensor to use based on forecast model
            if forecast_model == FORECAST_MODEL_ENHANCED:
                # Enhanced uses sensor.local_forecast_enhanced (dynamic weighting based on pressure change)
                forecast_sensor = self.hass.states.get("sensor.local_forecast_enhanced")
                sensor_name = "Enhanced (Dynamic)"
            elif forecast_model == FORECAST_MODEL_NEGRETTI:
                # Negretti uses sensor.local_forecast_neg_zam_detail
                forecast_sensor = self.hass.states.get("sensor.local_forecast_neg_zam_detail")
                sensor_name = "Negretti-Zambra"
            elif forecast_model == FORECAST_MODEL_ZAMBRETTI:
                # Zambretti uses sensor.local_forecast_zambretti_detail (classic algorithm)
                forecast_sensor = self.hass.states.get("sensor.local_forecast_zambretti_detail")
                sensor_name = "Zambretti"
            else:
                # Fallback to default if invalid model configured
                _LOGGER.warning(
                    f"Invalid forecast_model '{forecast_model}', falling back to {DEFAULT_FORECAST_MODEL}"
                )
                forecast_sensor = self.hass.states.get("sensor.local_forecast_enhanced")
                sensor_name = "Enhanced (Dynamic)"

            if forecast_sensor and forecast_sensor.state not in ("unknown", "unavailable", None):
                try:
                    attrs = forecast_sensor.attributes or {}
                    forecast_text = forecast_sensor.state or "Unknown"
                    forecast_num = attrs.get("forecast_number", None)
                    letter_code = attrs.get("letter_code", "A")

                    _LOGGER.debug(
                        f"Weather: Using {sensor_name} forecast model - "
                        f"text='{forecast_text}', num={forecast_num}, letter={letter_code} "
                        f"(NOTE: This predicts FUTURE 6-12h ahead, not current state)"
                    )

                    # SMART DECISION: Combine solar cloudiness with pressure stability
                    # Solar measures ACTUAL cloudiness (objective, high priority)
                    # Pressure indicates STABILITY (subjective, medium priority)
                    # Forecast predicts FUTURE (6-12h ahead, low priority)
                    if solar_cloudiness is not None and current_condition_from_pressure is not None:
                        # We have both solar and pressure data
                        # Decision logic:
                        # 1. Solar determines cloudiness (sunny/partlycloudy/cloudy)
                        # 2. Pressure adds precipitation warning if very low (<1000 hPa)
                        # 3. Without rain sensor, we can't confirm precipitation - trust solar

                        # Check if pressure is critically low (indicates precipitation)
                        pressure = self.native_pressure
                        critically_low_pressure = pressure and pressure < 995  # < 995 hPa = very unstable

                        # ENHANCEMENT: Use temperature + humidity for better precipitation detection
                        # High humidity (>80%) + cloudy + low pressure = strong indication of precipitation
                        # Low humidity (<50%) = unlikely precipitation even with low pressure
                        temp = self.native_temperature
                        humidity = self.humidity
                        dewpoint = self.native_dew_point

                        # Calculate dewpoint spread for moisture analysis
                        dewpoint_spread = None
                        high_moisture = False
                        low_moisture = False

                        if temp is not None and humidity is not None:
                            # High humidity check
                            if humidity > 80:
                                high_moisture = True
                                _LOGGER.debug(
                                    f"Weather: HIGH moisture detected - humidity={humidity:.1f}% > 80% "
                                    f"(increases precipitation likelihood)"
                                )
                            elif humidity < 50:
                                low_moisture = True
                                _LOGGER.debug(
                                    f"Weather: LOW moisture detected - humidity={humidity:.1f}% < 50% "
                                    f"(reduces precipitation likelihood)"
                                )

                            # Dewpoint spread check (additional moisture indicator)
                            if dewpoint is not None:
                                dewpoint_spread = temp - dewpoint
                                if dewpoint_spread < 3.0:  # Near saturation
                                    high_moisture = True
                                    _LOGGER.debug(
                                        f"Weather: Near saturation detected - spread={dewpoint_spread:.1f}°C < 3°C "
                                        f"(strong moisture indicator)"
                                    )

                        # Decision logic based on solar + pressure + humidity combination
                        # This provides best estimate without rain sensor

                        if critically_low_pressure and solar_cloudiness == ATTR_CONDITION_CLOUDY and high_moisture:
                            # CLOUDY + Very low pressure + HIGH humidity = RAINY (very likely precipitation)
                            # Triple confirmation: visual (solar), atmospheric (pressure), moisture (humidity)
                            condition = ATTR_CONDITION_RAINY
                            humidity_str = f"{humidity:.1f}" if humidity is not None else "N/A"
                            _LOGGER.debug(
                                f"Weather: Solar + Pressure + Humidity → RAINY - "
                                f"solar=CLOUDY + pressure={pressure:.1f} hPa < 995 + humidity={humidity_str}% > 80. "
                                f"Triple confirmation strongly suggests precipitation (without rain sensor)"
                            )
                        elif critically_low_pressure and solar_cloudiness == ATTR_CONDITION_CLOUDY and not low_moisture:
                            # CLOUDY + Very low pressure (without low humidity) = RAINY
                            # Even without high humidity confirmation, combination suggests rain
                            condition = ATTR_CONDITION_RAINY
                            humidity_str = f"{humidity:.1f}" if humidity is not None else "N/A"
                            _LOGGER.debug(
                                f"Weather: Solar + Pressure combination → RAINY - "
                                f"solar=CLOUDY + pressure={pressure:.1f} hPa < 995. "
                                f"Combination strongly suggests precipitation (humidity={humidity_str}%)"
                            )
                        elif critically_low_pressure and solar_cloudiness == ATTR_CONDITION_CLOUDY and low_moisture:
                            # CLOUDY + Very low pressure BUT low humidity = CLOUDY (not rainy)
                            # Low humidity contradicts precipitation - trust humidity sensor
                            condition = solar_cloudiness  # Keep CLOUDY
                            _LOGGER.debug(
                                f"Weather: Solar cloudy with low pressure BUT low humidity - "
                                f"solar=CLOUDY, pressure={pressure:.1f} hPa < 995, humidity={humidity:.1f}% < 50%. "
                                f"Low humidity contradicts precipitation, keeping CLOUDY"
                            )
                        elif critically_low_pressure and solar_cloudiness == ATTR_CONDITION_PARTLYCLOUDY:
                            # PARTLY CLOUDY + Very low pressure = keep PARTLY CLOUDY
                            # Not enough clouds for rain, just unstable conditions
                            condition = solar_cloudiness
                            _LOGGER.debug(
                                f"Weather: Solar partly cloudy with low pressure - "
                                f"solar={solar_cloudiness}, pressure={pressure:.1f} hPa < 995. "
                                f"Not enough clouds for precipitation, keeping solar cloudiness"
                            )
                        else:
                            # Normal conditions - solar has priority
                            condition = solar_cloudiness
                            pressure_str = f"{pressure:.1f}" if pressure is not None else "N/A"
                            humidity_str = f"{humidity:.1f}" if humidity is not None else "N/A"
                            _LOGGER.debug(
                                f"Weather: Using solar cloudiness - "
                                f"condition={condition}, pressure={pressure_str} hPa, "
                                f"humidity={humidity_str}%. "
                                f"Solar has priority over pressure estimate. "
                                f"Forecast '{forecast_text}' is for 6-12h future."
                            )
                    elif current_condition_from_pressure is not None:
                        # We have current condition from pressure (PRIORITY 4) - use it!
                        # Forecast model predicts FUTURE (6-12h ahead), not current state

                        # ENHANCED LOGIC: If pressure says "rainy" but rain sensor shows no precipitation,
                        # downgrade to "cloudy" (pressure is predicting future, not current state)
                        # This prevents false "rainy" display when it's only cloudy

                        if current_condition_from_pressure == ATTR_CONDITION_RAINY:
                            # Check if we have rain sensor data
                            rain_rate_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
                            current_rain = 0.0
                            has_rain_sensor = False

                            if rain_rate_sensor_id:
                                rain_sensor = self.hass.states.get(rain_rate_sensor_id)
                                if rain_sensor and rain_sensor.state not in ("unknown", "unavailable", None):
                                    has_rain_sensor = True
                                    try:
                                        current_rain = float(rain_sensor.state)
                                    except (ValueError, TypeError):
                                        pass

                            # If we have rain sensor and it shows NO precipitation,
                            # but pressure says "rainy", downgrade to "cloudy"
                            # (Pressure predicts future, rain sensor shows current reality)
                            if has_rain_sensor and current_rain <= 0.01:
                                condition = ATTR_CONDITION_CLOUDY
                                _LOGGER.debug(
                                    f"Weather: Pressure says RAINY (pressure < 1000 hPa) BUT rain sensor shows "
                                    f"no precipitation ({current_rain:.3f} mm/h). "
                                    f"Downgrading to CLOUDY (pressure predicts future, rain sensor shows current). "
                                    f"Without solar sensor, trusting rain sensor over pressure estimate."
                                )
                            else:
                                # No rain sensor or sensor shows rain - trust pressure
                                condition = current_condition_from_pressure
                                rain_str = f"{current_rain:.3f}" if has_rain_sensor else "N/A"
                                _LOGGER.debug(
                                    f"Weather: Using PRIORITY 4 pressure condition - "
                                    f"condition={condition} (current state from pressure), "
                                    f"rain_sensor={rain_str} mm/h. "
                                    f"Forecast '{forecast_text}' (num={forecast_num}) is for 6-12h future, not current state."
                                )
                        else:
                            # Not rainy - use pressure condition as-is
                            condition = current_condition_from_pressure
                            _LOGGER.debug(
                                f"Weather: Using PRIORITY 4 pressure condition - "
                                f"condition={condition} (current state from pressure). "
                                f"Forecast '{forecast_text}' (num={forecast_num}) is for 6-12h future, not current state."
                            )
                    else:
                        # No solar AND no current condition - use forecast model as last fallback
                        from .forecast_models import map_forecast_to_condition
                        condition = map_forecast_to_condition(
                            forecast_text=forecast_text,
                            forecast_num=forecast_num,
                            is_night_func=self._is_night,
                            source=sensor_name
                        )

                        _LOGGER.debug(
                            f"Weather: Mapped forecast → condition {condition} "
                            f"(using forecast as LAST FALLBACK - no solar or pressure data available)"
                        )

                    # FOG is handled in PRIORITY 2 with scientific model (WMO/NOAA/MetOffice)
                    # No need for duplicate fog logic here - PRIORITY 2 has:
                    # - Direct access to temp/dewpoint/humidity/wind
                    # - 3-level model (CRITICAL/LIKELY/POSSIBLE)
                    # - 90% accuracy with wind and night factors
                    # - Returns FOG before reaching this point
                    #
                    # CLOUDINESS ADJUSTMENTS for medium/low fog risk are now handled
                    # via dewpoint spread in PRIORITY 2 MIST/CLOUDY logic:
                    # - spread < 2.5°C + humidity > 85% → continues to solar/pressure
                    # - Will naturally show CLOUDY/PARTLYCLOUDY instead of FOG

                    # HUMIDITY-BASED CLOUD COVER CORRECTION
                    # ⚠️ NOTE: This section moved OUTSIDE forecast block in v3.1.9
                    # to apply universally to ALL conditions (solar, pressure, forecast)
                    # See end of condition determination for universal humidity corrections

                    # SOLAR CLOUDINESS OVERRIDE (INTELLIGENT)
                    # Solar radiation measures CURRENT cloudiness, forecast predicts FUTURE
                    # Decision logic:
                    # 1. If rain sensor CONFIRMS precipitation → keep forecast (it's raining NOW)
                    # 2. If rain sensor = 0 AND solar sunny → solar wins (forecast is for future)
                    # 3. If no rain sensor → trust forecast for precipitation (we can't verify)
                    if solar_cloudiness is not None:
                        # Check if forecast predicts precipitation
                        forecast_predicts_precipitation = condition in (
                            ATTR_CONDITION_RAINY, ATTR_CONDITION_SNOWY,
                            "pouring", "lightning-rainy"  # String literals for compatibility
                        )

                        if forecast_predicts_precipitation:
                            # Forecast says rain/snow - verify with rain sensor
                            rain_rate_sensor_id = self._get_config(CONF_RAIN_RATE_SENSOR)
                            current_rain = 0.0
                            rain_sensor_available = False

                            if rain_rate_sensor_id:
                                rain_sensor = self.hass.states.get(rain_rate_sensor_id)
                                if rain_sensor and rain_sensor.state not in ("unknown", "unavailable", None):
                                    try:
                                        current_rain = float(rain_sensor.state)
                                        rain_sensor_available = True
                                    except (ValueError, TypeError):
                                        pass

                            if rain_sensor_available:
                                # We have rain sensor - use it to verify
                                if current_rain > 0.01:
                                    # Actually raining NOW - forecast is correct, keep it
                                    _LOGGER.debug(
                                        f"Weather: Solar NOT overriding - "
                                        f"forecast={condition}, rain_sensor={current_rain:.3f} mm/h confirms precipitation "
                                        f"(solar={solar_cloudiness} but it's actually raining)"
                                    )
                                else:
                                    # NOT raining NOW - solar wins (forecast is for future)
                                    _LOGGER.debug(
                                        f"Weather: Solar OVERRIDES forecast precipitation - "
                                        f"forecast={condition} → solar={solar_cloudiness}, "
                                        f"rain_sensor=0 confirms no current precipitation "
                                        f"(forecast may be predicting future rain)"
                                    )
                                    condition = solar_cloudiness
                            else:
                                # No rain sensor - trust forecast (can't verify)
                                _LOGGER.debug(
                                    f"Weather: Solar NOT overriding - "
                                    f"forecast={condition} predicts precipitation, no rain sensor to verify "
                                    f"(trusting forecast, solar would suggest {solar_cloudiness})"
                                )
                        else:
                            # Forecast doesn't predict precipitation - solar always wins
                            _LOGGER.debug(
                                f"Weather: Solar cloudiness override - "
                                f"forecast={condition} → solar={solar_cloudiness} "
                                f"(solar measures actual cloud cover)"
                            )
                            condition = solar_cloudiness


                    # SNOW CONDITION CONVERSION
                    # Convert RAINY to SNOWY when temperature is freezing
                    # This applies to:
                    # - Forecast predictions (PRIORITY 5)
                    # - Solar + Pressure combinations (PRIORITY 3 + 4)
                    #
                    # Do NOT convert if condition is from:
                    # - PRIORITY 1 (rain sensor) - actual measurement (converts at source)
                    # - PRIORITY 2 (fog/mist) - actual measurement (not precipitation)
                    #
                    # Detect source:
                    # - used_forecast = True: PRIORITY 5 (forecast model)
                    # - used_forecast = False + solar_cloudiness: PRIORITY 3 (solar + pressure combination)
                    # - used_forecast = False + no solar: PRIORITY 4 (pressure only)
                    used_forecast = (solar_cloudiness is None and current_condition_from_pressure is None)

                    # If condition is "rainy" but conditions are freezing, convert to "snowy"
                    # This handles BOTH forecast predictions AND solar+pressure combinations
                    if condition == ATTR_CONDITION_RAINY:
                        temp = self.native_temperature
                        if temp is not None and temp <= 2:
                            # Check if we have high snow risk or high precipitation probability
                            enhanced_sensor = self.hass.states.get("sensor.local_forecast_enhanced")
                            snow_risk = None
                            if enhanced_sensor and enhanced_sensor.state not in ("unknown", "unavailable", None):
                                try:
                                    enhanced_attrs = enhanced_sensor.attributes or {}
                                    snow_risk = enhanced_attrs.get("snow_risk", None)
                                except (AttributeError, KeyError, TypeError):
                                    pass

                            # Get precipitation probability
                            rain_prob_sensor = self.hass.states.get("sensor.local_forecast_rain_probability")
                            rain_prob = 0
                            if rain_prob_sensor and rain_prob_sensor.state not in ("unknown", "unavailable", None):
                                try:
                                    rain_prob = float(rain_prob_sensor.state)
                                except (ValueError, TypeError):
                                    pass

                            # Convert rainy to snowy if:
                            # 1. High snow risk + any precipitation probability >= 40%, OR
                            # 2. Medium snow risk + precipitation probability >= 50%, OR
                            # 3. Temperature <= 0°C + precipitation probability >= 60%
                            should_convert = False
                            reason = "unknown"  # Initialize to avoid warning
                            if snow_risk in ("high", "Vysoké riziko snehu") and rain_prob >= 40:
                                should_convert = True
                                reason = f"high snow_risk + rain_prob={rain_prob}%"
                            elif snow_risk in ("medium", "Stredné riziko snehu") and rain_prob >= 50:
                                should_convert = True
                                reason = f"medium snow_risk + rain_prob={rain_prob}%"
                            elif temp <= 0 and rain_prob >= 60:
                                should_convert = True
                                reason = f"freezing temp + high rain_prob={rain_prob}%"

                            if should_convert:
                                source = "forecast" if used_forecast else "solar+pressure"
                                _LOGGER.debug(
                                    f"Weather: Snow conversion: rainy → snowy "
                                    f"(source={source}, temp={temp:.1f}°C, {reason})"
                                )
                                condition = ATTR_CONDITION_SNOWY
                            else:
                                _LOGGER.debug(
                                    f"Weather: Keeping rainy condition despite cold temp "
                                    f"(temp={temp:.1f}°C, snow_risk={snow_risk}, rain_prob={rain_prob}% - "
                                    f"conditions not met for snow conversion)"
                                )

                    # Don't return yet - apply universal humidity corrections first
                    # (see end of method)
                except (AttributeError, KeyError, TypeError) as e:
                    _LOGGER.debug(f"Weather: Error reading forecast sensor: {e}")
                    # Set condition to None to trigger fallback
                    condition = None

            # Forecast sensor not available - use current condition from pressure if available
            if condition is None and current_condition_from_pressure is not None:
                _LOGGER.debug(
                    f"Weather: Forecast sensors unavailable, using current condition from pressure: "
                    f"{current_condition_from_pressure} (CURRENT state based on pressure NOW)"
                )
                condition = current_condition_from_pressure

            # PRIORITY 6: Fallback based on pressure
            if condition is None:
                pressure = self.native_pressure
                if pressure:
                    if pressure < 1000:
                        # Low pressure indicates precipitation
                        # Check if conditions are freezing - convert rainy to snowy
                        temp = self.native_temperature
                        if temp is not None and temp <= 2:
                            _LOGGER.debug(
                                f"Weather: Fallback to snowy (pressure={pressure}, temp={temp:.1f}°C ≤2°C)"
                            )
                            condition = ATTR_CONDITION_SNOWY
                        else:
                            _LOGGER.debug(f"Weather: Fallback to rainy (pressure={pressure})")
                            condition = ATTR_CONDITION_RAINY
                    elif pressure < 1013:
                        _LOGGER.debug(f"Weather: Fallback to cloudy (pressure={pressure})")
                        condition = ATTR_CONDITION_CLOUDY
                    elif pressure < 1020:
                        # Medium pressure = partly cloudy
                        # Keep partlycloudy for both day and night (HA shows correct icon)
                        _LOGGER.debug(f"Weather: Fallback to partlycloudy (pressure={pressure})")
                        condition = ATTR_CONDITION_PARTLYCLOUDY
                    else:
                        # High pressure = clear skies
                        if self._is_night():
                            _LOGGER.debug(f"Weather: Fallback to clear night (pressure={pressure})")
                            condition = ATTR_CONDITION_CLEAR_NIGHT
                        else:
                            _LOGGER.debug(f"Weather: Fallback to sunny (pressure={pressure})")
                            condition = ATTR_CONDITION_SUNNY

            # Final fallback
            if condition is None:
                _LOGGER.debug(f"Weather: Final fallback to partlycloudy (no forecast/pressure data)")
                condition = ATTR_CONDITION_PARTLYCLOUDY

            # ========================================================================
            # UNIVERSAL HUMIDITY-BASED CLOUD COVER CORRECTIONS
            # Applied to ALL conditions regardless of source (solar, pressure, forecast)
            # ========================================================================
            humidity = self.humidity
            if humidity is not None:
                # Get forecast_num if available (for Fine weather forecast detection)
                forecast_num = None
                try:
                    forecast_model = self._get_config(CONF_FORECAST_MODEL) or DEFAULT_FORECAST_MODEL
                    if forecast_model == FORECAST_MODEL_ZAMBRETTI:
                        forecast_sensor = self.hass.states.get("sensor.local_forecast_zambretti_detail")
                    elif forecast_model == FORECAST_MODEL_NEGRETTI:
                        forecast_sensor = self.hass.states.get("sensor.local_forecast_neg_zam_detail")
                    else:
                        forecast_sensor = self.hass.states.get("sensor.local_forecast_enhanced")

                    if forecast_sensor and forecast_sensor.state not in ("unknown", "unavailable", None):
                        attrs = forecast_sensor.attributes or {}
                        forecast_num = attrs.get("forecast_number", None)
                except:
                    pass  # forecast_num stays None

                _LOGGER.debug(f"Weather: Universal humidity correction check - humidity={humidity}%, forecast_num={forecast_num}, condition={condition}")

                # Check if it's night - humidity has bigger impact at night
                # (condensation, dew, night clouds are more visible with high humidity)
                is_night = self._is_night()

                # ========================================================================
                # HUMIDITY-BASED CLOUDINESS CORRECTIONS (WMO/NOAA meteorological standards)
                # ========================================================================
                # Based on scientific research:
                # - RH > 95% → Near saturation, clouds/fog very likely (critical)
                # - RH 90-95% → High probability of clouds (condensation level)
                # - RH 85-90% → Moderate cloud probability (visible moisture)
                # - RH 80-85% → Haze/partial clouds possible
                # - RH < 80% → Low cloud formation probability
                #
                # Special considerations:
                # - Night: Lower thresholds (clouds more visible, condensation)
                # - Fine weather forecasts (num ≤ 3): Stronger evidence needed
                # ========================================================================

                # LEVEL 1: EXTREME humidity (>95%) = definitely cloudy/overcast
                # Near saturation - clouds WILL form regardless of forecast
                if humidity > 95 and condition in (
                    ATTR_CONDITION_PARTLYCLOUDY,
                    ATTR_CONDITION_SUNNY, ATTR_CONDITION_CLEAR_NIGHT
                ):
                    _LOGGER.debug(
                        f"Weather: Humidity correction (CRITICAL): {condition} → cloudy "
                        f"(RH={humidity:.1f}% > 95% - near saturation, clouds inevitable)"
                    )
                    condition = ATTR_CONDITION_CLOUDY

                # LEVEL 2: Very high humidity (90-95%) = mostly cloudy
                # BUT respect "Fine weather" forecasts (forecast_num ≤ 3)
                # These are strong stable forecasts that need stronger evidence
                elif humidity > 90 and condition in (
                    ATTR_CONDITION_PARTLYCLOUDY,
                    ATTR_CONDITION_SUNNY, ATTR_CONDITION_CLEAR_NIGHT
                ) and (forecast_num is None or forecast_num > 3):
                    _LOGGER.debug(
                        f"Weather: Humidity correction (very high): {condition} → cloudy "
                        f"(RH={humidity:.1f}% > 90% - high condensation, forecast_num={forecast_num})"
                    )
                    condition = ATTR_CONDITION_CLOUDY

                # LEVEL 3: High humidity (85-90%) = partial clouds likely
                # Respect both Fine (≤3) and Fair (≤5) forecasts
                elif humidity > 85 and condition in (
                    ATTR_CONDITION_SUNNY, ATTR_CONDITION_CLEAR_NIGHT
                ) and (forecast_num is None or forecast_num > 5):
                    _LOGGER.debug(
                        f"Weather: Humidity correction (high): {condition} → partlycloudy "
                        f"(RH={humidity:.1f}% > 85% - visible moisture, forecast_num={forecast_num})"
                    )
                    condition = ATTR_CONDITION_PARTLYCLOUDY

                # LEVEL 4: Night special case (80-85%) = partial clouds more visible at night
                # At night, lower threshold because:
                # - Condensation forms easier (cooler air)
                # - Night clouds more visible (street lights, moon reflection)
                # - Dew formation indicates high moisture
                elif is_night and humidity > 80 and condition == ATTR_CONDITION_CLEAR_NIGHT:
                    _LOGGER.debug(
                        f"Weather: Humidity correction (night clouds): {condition} → partlycloudy "
                        f"(RH={humidity:.1f}% > 80% at night - condensation/dew, night clouds visible)"
                    )
                    condition = ATTR_CONDITION_PARTLYCLOUDY

                # Note: We don't add day correction at 75% - that's too aggressive
                # 75% RH is moderate humidity, not necessarily clouds
                # Only at 80%+ (or 85%+ for day sunny conditions) do we correct

            # Note: We don't convert partlycloudy to clear-night at night
            # Home Assistant automatically shows the correct night icon for partlycloudy

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
            _LOGGER.debug(
                f"Weather: Fog risk={fog_risk_level}, temp={temp:.1f}°C, "
                f"dewpoint={dewpoint:.1f}°C, spread={spread:.1f}°C"
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
                from .negretti_zambra import calculate_forecast as negretti_calc
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

