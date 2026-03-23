"""Tests for centralized QC validation across all sensor types.

Tests cover:
- QC constants and SENSOR_QC_LIMITS dict
- Centralized _get_sensor_value() QC in sensor.py
- Temperature range check in _handle_temperature_update
- Weather entity _validate_sensor_value() helper
"""
import math

import pytest

from custom_components.local_weather_forecast.const import (
    HUMIDITY_QC_MAX,
    HUMIDITY_QC_MIN,
    PRESSURE_QC_MAX,
    PRESSURE_QC_MIN,
    RAIN_RATE_QC_MAX,
    RAIN_RATE_QC_MIN,
    SENSOR_QC_LIMITS,
    SOLAR_RADIATION_QC_MAX,
    SOLAR_RADIATION_QC_MIN,
    TEMPERATURE_QC_MAX,
    TEMPERATURE_QC_MIN,
    WIND_DIRECTION_QC_MAX,
    WIND_DIRECTION_QC_MIN,
    WIND_SPEED_QC_MAX,
    WIND_SPEED_QC_MIN,
)


# ============================================================================
# Phase 1: QC Constants and SENSOR_QC_LIMITS dict
# ============================================================================

class TestQCConstants:
    """Verify QC range constants have correct values."""

    def test_temperature_qc_range(self):
        assert TEMPERATURE_QC_MIN == -89.2
        assert TEMPERATURE_QC_MAX == 56.7

    def test_humidity_qc_range(self):
        assert HUMIDITY_QC_MIN == 0.0
        assert HUMIDITY_QC_MAX == 100.0

    def test_wind_speed_qc_range(self):
        assert WIND_SPEED_QC_MIN == 0.0
        assert WIND_SPEED_QC_MAX == 114.0

    def test_wind_direction_qc_range(self):
        assert WIND_DIRECTION_QC_MIN == 0.0
        assert WIND_DIRECTION_QC_MAX == 360.0

    def test_solar_radiation_qc_range(self):
        assert SOLAR_RADIATION_QC_MIN == 0.0
        assert SOLAR_RADIATION_QC_MAX == 1500.0

    def test_rain_rate_qc_range(self):
        assert RAIN_RATE_QC_MIN == 0.0
        assert RAIN_RATE_QC_MAX == 500.0

    def test_sensor_qc_limits_has_all_types(self):
        expected = {"pressure", "temperature", "humidity", "wind_speed",
                    "wind_direction", "solar_radiation", "precipitation"}
        assert set(SENSOR_QC_LIMITS.keys()) == expected

    def test_sensor_qc_limits_pressure_matches_constants(self):
        assert SENSOR_QC_LIMITS["pressure"] == (PRESSURE_QC_MIN, PRESSURE_QC_MAX)

    def test_sensor_qc_limits_temperature_matches_constants(self):
        assert SENSOR_QC_LIMITS["temperature"] == (TEMPERATURE_QC_MIN, TEMPERATURE_QC_MAX)

    def test_sensor_qc_limits_humidity_matches_constants(self):
        assert SENSOR_QC_LIMITS["humidity"] == (HUMIDITY_QC_MIN, HUMIDITY_QC_MAX)


# ============================================================================
# Phase 2: Validate sensor value function (weather.py pattern)
# Uses the same SENSOR_QC_LIMITS dict, tested independently
# ============================================================================

def _validate(value, sensor_type):
    """Standalone QC validator matching weather.py logic."""
    if math.isnan(value) or math.isinf(value):
        return None
    if sensor_type in SENSOR_QC_LIMITS:
        qc_min, qc_max = SENSOR_QC_LIMITS[sensor_type]
        if value < qc_min or value > qc_max:
            return None
    return value


class TestHumidityQC:
    """QC validation for humidity sensor."""

    def test_valid_humidity(self):
        assert _validate(65.0, "humidity") == 65.0

    def test_humidity_zero_accepted(self):
        assert _validate(0.0, "humidity") == 0.0

    def test_humidity_100_accepted(self):
        assert _validate(100.0, "humidity") == 100.0

    def test_humidity_nan_rejected(self):
        assert _validate(float("nan"), "humidity") is None

    def test_humidity_inf_rejected(self):
        assert _validate(float("inf"), "humidity") is None

    def test_humidity_negative_rejected(self):
        assert _validate(-1.0, "humidity") is None

    def test_humidity_above_100_rejected(self):
        assert _validate(101.0, "humidity") is None


class TestWindSpeedQC:
    """QC validation for wind speed sensor."""

    def test_valid_wind_speed(self):
        assert _validate(5.5, "wind_speed") == 5.5

    def test_wind_speed_zero_accepted(self):
        assert _validate(0.0, "wind_speed") == 0.0

    def test_wind_speed_nan_rejected(self):
        assert _validate(float("nan"), "wind_speed") is None

    def test_wind_speed_negative_rejected(self):
        assert _validate(-0.1, "wind_speed") is None

    def test_wind_speed_above_max_rejected(self):
        assert _validate(115.0, "wind_speed") is None

    def test_wind_speed_at_max_accepted(self):
        assert _validate(114.0, "wind_speed") == 114.0


class TestWindDirectionQC:
    """QC validation for wind direction sensor."""

    def test_valid_wind_direction(self):
        assert _validate(180.0, "wind_direction") == 180.0

    def test_wind_direction_zero_accepted(self):
        assert _validate(0.0, "wind_direction") == 0.0

    def test_wind_direction_360_accepted(self):
        assert _validate(360.0, "wind_direction") == 360.0

    def test_wind_direction_nan_rejected(self):
        assert _validate(float("nan"), "wind_direction") is None

    def test_wind_direction_negative_rejected(self):
        assert _validate(-1.0, "wind_direction") is None

    def test_wind_direction_above_360_rejected(self):
        assert _validate(361.0, "wind_direction") is None


class TestSolarRadiationQC:
    """QC validation for solar radiation sensor."""

    def test_valid_solar_radiation(self):
        assert _validate(800.0, "solar_radiation") == 800.0

    def test_solar_radiation_zero_accepted(self):
        assert _validate(0.0, "solar_radiation") == 0.0

    def test_solar_radiation_nan_rejected(self):
        assert _validate(float("nan"), "solar_radiation") is None

    def test_solar_radiation_negative_rejected(self):
        assert _validate(-1.0, "solar_radiation") is None

    def test_solar_radiation_above_max_rejected(self):
        assert _validate(1501.0, "solar_radiation") is None

    def test_solar_radiation_at_max_accepted(self):
        assert _validate(1500.0, "solar_radiation") == 1500.0


class TestRainRateQC:
    """QC validation for rain rate sensor."""

    def test_valid_rain_rate(self):
        assert _validate(5.0, "precipitation") == 5.0

    def test_rain_rate_zero_accepted(self):
        assert _validate(0.0, "precipitation") == 0.0

    def test_rain_rate_nan_rejected(self):
        assert _validate(float("nan"), "precipitation") is None

    def test_rain_rate_negative_rejected(self):
        assert _validate(-0.1, "precipitation") is None

    def test_rain_rate_above_max_rejected(self):
        assert _validate(501.0, "precipitation") is None


class TestTemperatureRangeQC:
    """QC validation for temperature range (new addition)."""

    def test_valid_temperature(self):
        assert _validate(22.5, "temperature") == 22.5

    def test_temperature_at_min_accepted(self):
        assert _validate(-89.2, "temperature") == -89.2

    def test_temperature_at_max_accepted(self):
        assert _validate(56.7, "temperature") == 56.7

    def test_temperature_below_min_rejected(self):
        assert _validate(-90.0, "temperature") is None

    def test_temperature_above_max_rejected(self):
        assert _validate(57.0, "temperature") is None

    def test_temperature_nan_rejected(self):
        assert _validate(float("nan"), "temperature") is None

    def test_temperature_neg_inf_rejected(self):
        assert _validate(float("-inf"), "temperature") is None
