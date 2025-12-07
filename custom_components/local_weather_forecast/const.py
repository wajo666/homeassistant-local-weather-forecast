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
CONF_SOLAR_RADIATION_SENSOR: Final = "solar_radiation_sensor"
CONF_UV_INDEX_SENSOR: Final = "uv_index_sensor"
CONF_VISIBILITY_SENSOR: Final = "visibility_sensor"
CONF_WIND_GUST_SENSOR: Final = "wind_gust_sensor"
CONF_RAIN_RATE_SENSOR: Final = "rain_rate_sensor"
# Note: CONF_PRECIPITATION_SENSOR removed - use CONF_RAIN_RATE_SENSOR instead (supports both mm/h and mm accumulation)
CONF_LATITUDE: Final = "latitude"

# Configuration keys - Feature flags
CONF_ENABLE_WEATHER_ENTITY: Final = "enable_weather_entity"
CONF_ENABLE_EXTENDED_SENSORS: Final = "enable_extended_sensors"
CONF_FORECAST_INTERVAL: Final = "forecast_interval"

# Pressure types
PRESSURE_TYPE_ABSOLUTE: Final = "absolute"  # QFE - Station pressure
PRESSURE_TYPE_RELATIVE: Final = "relative"  # QNH - Sea level pressure

# Defaults
DEFAULT_ELEVATION: Final = 0
DEFAULT_LATITUDE: Final = 50.0  # Europe middle latitude
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
    "A": "sunny",             # Settled fine (code 0) - stable, clear skies
    "B": "partlycloudy",      # Fine weather (code 1) - mostly clear with some clouds
    "C": "partlycloudy",      # Becoming fine (code 2) - improving conditions
    "D": "partlycloudy",      # Fine, becoming less settled (code 3)
    "E": "partlycloudy",      # Fine, possible showers (code 4)
    "F": "cloudy",            # Fairly fine, improving (code 5)
    "G": "cloudy",            # Fairly fine, possible showers early (code 6)
    "H": "rainy",             # Fairly fine, showery later (code 7)
    "I": "rainy",             # Showery early, improving (code 8)
    "J": "rainy",             # Changeable, mending (code 9)
    "K": "rainy",             # Fairly fine, showers likely (code 10)
    "L": "rainy",             # Rather unsettled clearing later (code 11)
    "M": "rainy",             # Unsettled, probably improving (code 12)
    "N": "rainy",             # Showery, bright intervals (code 13)
    "O": "rainy",             # Showery, becoming more unsettled (code 14)
    "P": "pouring",           # Changeable, some rain (code 15)
    "Q": "pouring",           # Unsettled, short fine intervals (code 16)
    "R": "pouring",           # Unsettled, rain later (code 17)
    "S": "pouring",           # Unsettled, some rain (code 18)
    "T": "pouring",           # Mostly very unsettled (code 19)
    "U": "pouring",           # Occasional rain, worsening (code 20)
    "V": "pouring",           # Rain at times, very unsettled (code 21)
    "W": "pouring",           # Rain at frequent intervals (code 22)
    "X": "pouring",           # Very unsettled, rain (code 23)
    "Y": "pouring",           # Stormy, may improve (code 24)
    "Z": "lightning-rainy",   # Stormy, much rain (code 25)
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

