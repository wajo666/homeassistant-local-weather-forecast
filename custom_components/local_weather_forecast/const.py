"""Constants for the Local Weather Forecast integration."""
from typing import Final

DOMAIN: Final = "local_weather_forecast"

# Configuration keys
CONF_PRESSURE_SENSOR: Final = "pressure_sensor"
CONF_TEMPERATURE_SENSOR: Final = "temperature_sensor"
CONF_WIND_DIRECTION_SENSOR: Final = "wind_direction_sensor"
CONF_WIND_SPEED_SENSOR: Final = "wind_speed_sensor"
CONF_ELEVATION: Final = "elevation"
CONF_LANGUAGE: Final = "language"
CONF_PRESSURE_TYPE: Final = "pressure_type"

# Pressure types
PRESSURE_TYPE_ABSOLUTE: Final = "absolute"  # QFE - Station pressure
PRESSURE_TYPE_RELATIVE: Final = "relative"  # QNH - Sea level pressure

# Defaults
DEFAULT_ELEVATION: Final = 0
DEFAULT_LANGUAGE: Final = "en"
DEFAULT_PRESSURE_TYPE: Final = PRESSURE_TYPE_ABSOLUTE

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

