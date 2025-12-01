"""Constants for the Local Weather Forecast integration."""
from typing import Final

DOMAIN: Final = "local_weather_forecast"

# Configuration keys - Required sensors
CONF_PRESSURE_SENSOR: Final = "pressure_sensor"
CONF_TEMPERATURE_SENSOR: Final = "temperature_sensor"
CONF_WIND_DIRECTION_SENSOR: Final = "wind_direction_sensor"
CONF_WIND_SPEED_SENSOR: Final = "wind_speed_sensor"
CONF_ELEVATION: Final = "elevation"
CONF_LANGUAGE: Final = "language"
CONF_PRESSURE_TYPE: Final = "pressure_type"

# Configuration keys - Optional extended sensors (v3.1.0+)
CONF_HUMIDITY_SENSOR: Final = "humidity_sensor"
CONF_DEWPOINT_SENSOR: Final = "dewpoint_sensor"
CONF_CLOUD_COVERAGE_SENSOR: Final = "cloud_coverage_sensor"
CONF_UV_INDEX_SENSOR: Final = "uv_index_sensor"
CONF_VISIBILITY_SENSOR: Final = "visibility_sensor"
CONF_WIND_GUST_SENSOR: Final = "wind_gust_sensor"
CONF_RAIN_RATE_SENSOR: Final = "rain_rate_sensor"
CONF_PRECIPITATION_SENSOR: Final = "precipitation_sensor"

# Configuration keys - Feature flags
CONF_ENABLE_WEATHER_ENTITY: Final = "enable_weather_entity"
CONF_ENABLE_EXTENDED_SENSORS: Final = "enable_extended_sensors"
CONF_FORECAST_INTERVAL: Final = "forecast_interval"

# Pressure types
PRESSURE_TYPE_ABSOLUTE: Final = "absolute"  # QFE - Station pressure
PRESSURE_TYPE_RELATIVE: Final = "relative"  # QNH - Sea level pressure

# Defaults
DEFAULT_ELEVATION: Final = 0
DEFAULT_LANGUAGE: Final = "en"
DEFAULT_PRESSURE_TYPE: Final = PRESSURE_TYPE_ABSOLUTE
DEFAULT_ENABLE_WEATHER_ENTITY: Final = False
DEFAULT_ENABLE_EXTENDED_SENSORS: Final = False
DEFAULT_FORECAST_INTERVAL: Final = 3  # hours

# Languages (available in UI configuration)
LANGUAGES: Final = {
    "de": "Deutsch (German)",
    "en": "English",
    "gr": "Ελληνικά (Greek)",
    "it": "Italiano (Italian)",
    "sk": "Slovenčina (Slovak)",
}

# Language index mapping to forecast_data.py arrays
# forecast_data.py format: [German, English, Greek, Italian, Slovak]
LANGUAGE_INDEX: Final = {
    "de": 0,  # German
    "en": 1,  # English
    "gr": 2,  # Greek
    "it": 3,  # Italian
    "sk": 4,  # Slovak
}

# Sensor update intervals
PRESSURE_CHANGE_MINUTES: Final = 180
PRESSURE_SAMPLING_SIZE: Final = 1890
TEMPERATURE_CHANGE_MINUTES: Final = 60
TEMPERATURE_SAMPLING_SIZE: Final = 140

# Pressure thresholds
PRESSURE_TREND_RISING: Final = 1.6
PRESSURE_TREND_FALLING: Final = -1.6

# Barometric constants
LAPSE_RATE: Final = 0.0065  # K/m
GRAVITY_CONSTANT: Final = 5.257
KELVIN_OFFSET: Final = 273.15

# Weather conditions mapping (Zambretti -> Home Assistant standard conditions)
# https://developers.home-assistant.io/docs/core/entity/weather/#recommended-values-for-state-and-condition
ZAMBRETTI_TO_CONDITION: Final = {
    # Zambretti codes A-Z mapped to HA weather conditions
    # clear-night, cloudy, exceptional, fog, hail, lightning, lightning-rainy,
    # partlycloudy, pouring, rainy, snowy, snowy-rainy, sunny, windy
    "A": "pouring",           # Settled fine -> pouring (code 1-2)
    "B": "sunny",             # Fine weather -> sunny (code 3-4)
    "C": "partlycloudy",      # Becoming fine -> partly cloudy (code 5-6)
    "D": "partlycloudy",      # Fine, becoming less settled
    "E": "partlycloudy",      # Fine, possible showers
    "F": "cloudy",            # Fairly fine, improving
    "G": "cloudy",            # Fairly fine, possible showers early
    "H": "rainy",             # Fairly fine, showery later
    "I": "rainy",             # Showery early, improving
    "J": "rainy",             # Changeable, mending
    "K": "rainy",             # Fairly fine, showers likely
    "L": "rainy",             # Rather unsettled clearing later
    "M": "rainy",             # Unsettled, probably improving
    "N": "rainy",             # Showery, bright intervals
    "O": "rainy",             # Showery, becoming more unsettled
    "P": "pouring",           # Changeable, some rain
    "Q": "pouring",           # Unsettled, short fine intervals
    "R": "pouring",           # Unsettled, rain later
    "S": "pouring",           # Unsettled, some rain
    "T": "pouring",           # Mostly very unsettled
    "U": "pouring",           # Occasional rain, worsening
    "V": "pouring",           # Rain at times, very unsettled
    "W": "pouring",           # Rain at frequent intervals
    "X": "pouring",           # Very unsettled, rain
    "Y": "pouring",           # Stormy, may improve
    "Z": "lightning-rainy",   # Stormy, much rain
}

# Forecast intervals (hours)
FORECAST_INTERVALS: Final = [1, 3, 6, 12, 24]

# Comfort levels
COMFORT_VERY_COLD: Final = "very_cold"
COMFORT_COLD: Final = "cold"
COMFORT_COOL: Final = "cool"
COMFORT_COMFORTABLE: Final = "comfortable"
COMFORT_WARM: Final = "warm"
COMFORT_HOT: Final = "hot"
COMFORT_VERY_HOT: Final = "very_hot"

# Fog risk levels
FOG_RISK_NONE: Final = "none"
FOG_RISK_LOW: Final = "low"
FOG_RISK_MEDIUM: Final = "medium"
FOG_RISK_HIGH: Final = "high"

# Trend states
TREND_IMPROVING: Final = "improving"
TREND_DETERIORATING: Final = "deteriorating"
TREND_STABLE: Final = "stable"
TREND_RISING: Final = "rising"
TREND_FALLING: Final = "falling"
TREND_STEADY: Final = "steady"

# Confidence levels
CONFIDENCE_LOW: Final = "low"
CONFIDENCE_MEDIUM: Final = "medium"
CONFIDENCE_HIGH: Final = "high"

