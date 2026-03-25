"""Tests for QFE-based pressure trend fix.

Verifies that PressureChangeSensor tracks the source QFE sensor (not QNH)
when pressure_type == ABSOLUTE, eliminating the temperature-dependent
barometric conversion artifact that causes false pressure trends at high elevations.
"""
import math
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

from custom_components.local_weather_forecast.sensor import (
    LocalForecastPressureChangeSensor,
    PRESSURE_MIN_RECORDS,
)
from custom_components.local_weather_forecast.const import (
    PRESSURE_QC_MIN,
    PRESSURE_QC_MAX,
    PRESSURE_SPIKE_LIMIT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    hass.async_create_task = Mock(side_effect=lambda coro: None)
    return hass


def _make_config_entry(pressure_type="absolute", pressure_sensor="sensor.test_pressure"):
    """Build a mock config entry with the given pressure settings."""
    entry = Mock()
    entry.data = {
        "pressure_sensor": pressure_sensor,
        "temperature_sensor": "sensor.test_temperature",
        "pressure_type": pressure_type,
        "elevation": 314.0,
    }
    entry.options = {}
    entry.entry_id = "test_entry_id"
    return entry


def _make_event(pressure_value, unit="hPa"):
    """Build a mock state_changed event."""
    new_state = Mock()
    new_state.state = str(pressure_value)
    new_state.attributes = {"unit_of_measurement": unit}
    event = Mock()
    event.data = {"new_state": new_state}
    return event


# ===========================================================================
# TestQFETrendFix — source sensor selection & unit conversion
# ===========================================================================

class TestQFETrendFix:
    """Verify correct source sensor tracking and unit conversion."""

    def test_tracks_source_sensor_when_absolute(self, mock_hass):
        """ABSOLUTE mode → track the user's source QFE sensor."""
        entry = _make_config_entry(pressure_type="absolute", pressure_sensor="sensor.netatmo_pressure")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)

        assert sensor._use_qfe is True
        assert sensor._source_sensor_id == "sensor.netatmo_pressure"

    def test_tracks_internal_sensor_when_relative(self, mock_hass):
        """RELATIVE mode → track internal QNH sensor (no conversion artifact)."""
        entry = _make_config_entry(pressure_type="relative")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)

        assert sensor._use_qfe is False
        assert sensor._source_sensor_id == "sensor.local_forecast_pressure"

    def test_tracks_source_sensor_default_type(self, mock_hass):
        """Missing pressure_type → default (ABSOLUTE) → track source sensor."""
        entry = Mock()
        entry.data = {
            "pressure_sensor": "sensor.test_pressure",
            "temperature_sensor": "sensor.test_temperature",
            "elevation": 314.0,
        }
        entry.options = {}
        entry.entry_id = "test_entry_id"
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)

        assert sensor._use_qfe is True
        assert sensor._source_sensor_id == "sensor.test_pressure"

    def test_qfe_handles_unit_conversion_inhg(self, mock_hass):
        """Source sensor in inHg → converted to hPa before storage."""
        entry = _make_config_entry(pressure_type="absolute")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        # 29.92 inHg ≈ 1013.25 hPa
        event = _make_event(29.92, unit="inHg")
        sensor._handle_pressure_update(event)

        assert len(sensor._history) == 1
        stored_pressure = sensor._history[0][1]
        assert abs(stored_pressure - 1013.25) < 0.5, \
            f"Expected ~1013.25 hPa, got {stored_pressure}"

    def test_qfe_handles_unit_conversion_kpa(self, mock_hass):
        """Source sensor in kPa → converted to hPa before storage."""
        entry = _make_config_entry(pressure_type="absolute")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        # 89.7 kPa = 897.0 hPa (typical QFE at ~1200m)
        event = _make_event(89.7, unit="kPa")
        sensor._handle_pressure_update(event)

        assert len(sensor._history) == 1
        stored_pressure = sensor._history[0][1]
        assert abs(stored_pressure - 897.0) < 0.5, \
            f"Expected ~897.0 hPa, got {stored_pressure}"

    def test_qfe_no_conversion_when_hpa(self, mock_hass):
        """Source sensor already in hPa → stored as-is."""
        entry = _make_config_entry(pressure_type="absolute")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        event = _make_event(897.5, unit="hPa")
        sensor._handle_pressure_update(event)

        assert len(sensor._history) == 1
        assert sensor._history[0][1] == 897.5

    def test_relative_mode_no_conversion(self, mock_hass):
        """RELATIVE mode → no unit conversion attempted (internal sensor always hPa)."""
        entry = _make_config_entry(pressure_type="relative")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        # Internal sensor always reports hPa — no attributes needed
        event = _make_event(1013.25, unit="hPa")
        sensor._handle_pressure_update(event)

        assert len(sensor._history) == 1
        assert sensor._history[0][1] == 1013.25


# ===========================================================================
# TestQFETrendScenarios — meteorological scenarios
# ===========================================================================

class TestQFETrendScenarios:
    """Verify QFE-based trend eliminates temperature artifact."""

    def test_stable_qfe_rising_temp_trend_zero(self, mock_hass):
        """Core bug scenario: stable QFE + rising temperature → trend ≈ 0.

        At 1200m elevation, morning 8°C temperature rise would cause
        QNH to drop ~3.5 hPa/3h, but QFE stays flat. The trend from
        QFE should be approximately zero.
        """
        entry = _make_config_entry(pressure_type="absolute")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        # Simulate 3h of stable QFE at ~897 hPa (1200m elevation)
        # with tiny random noise ±0.05 hPa (sensor resolution)
        base_time = datetime(2025, 7, 15, 6, 0, 0)  # 6:00 AM
        stable_qfe = 897.0
        noise = [0.0, 0.02, -0.03, 0.05, -0.02, 0.01, -0.04, 0.03,
                 0.0, -0.01, 0.02, -0.03, 0.05, -0.02, 0.01, 0.0,
                 -0.03, 0.04]

        for i in range(18):  # 18 readings over 3h (every 10min)
            ts = base_time + timedelta(minutes=i * 10)
            qfe = stable_qfe + noise[i]
            sensor._history.append((ts, qfe))

        # Manually trigger regression calculation via _handle_pressure_update
        # by adding one more point
        event = _make_event(stable_qfe + 0.01, unit="hPa")
        sensor._handle_pressure_update(event)

        # Trend should be near zero (not -3.5 hPa/3h as with QNH)
        assert abs(sensor._state) < 0.5, \
            f"Stable QFE should give near-zero trend, got {sensor._state} hPa/3h"

    def test_falling_qfe_correct_negative_trend(self, mock_hass):
        """QFE drops 3 hPa over 3h → trend ≈ -3.0 hPa/3h."""
        entry = _make_config_entry(pressure_type="absolute")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        now = datetime.now()
        base_time = now - timedelta(minutes=180)
        for i in range(18):
            ts = base_time + timedelta(minutes=i * 10)
            # Linear drop: 900.0 → 897.0 over 180 minutes
            qfe = 900.0 - (3.0 * i / 18)
            sensor._history.append((ts, qfe))

        # The last point added via _handle_pressure_update
        event = _make_event(897.0, unit="hPa")
        sensor._handle_pressure_update(event)

        assert sensor._state < -2.5, \
            f"Expected trend ≈ -3.0, got {sensor._state}"
        assert sensor._state > -3.5, \
            f"Expected trend ≈ -3.0, got {sensor._state}"

    def test_rising_qfe_correct_positive_trend(self, mock_hass):
        """QFE rises 3 hPa over 3h → trend ≈ +3.0 hPa/3h."""
        entry = _make_config_entry(pressure_type="absolute")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        now = datetime.now()
        base_time = now - timedelta(minutes=180)
        for i in range(18):
            ts = base_time + timedelta(minutes=i * 10)
            # Linear rise: 897.0 → 900.0 over 180 minutes
            qfe = 897.0 + (3.0 * i / 18)
            sensor._history.append((ts, qfe))

        event = _make_event(900.0, unit="hPa")
        sensor._handle_pressure_update(event)

        assert sensor._state > 2.5, \
            f"Expected trend ≈ +3.0, got {sensor._state}"
        assert sensor._state < 3.5, \
            f"Expected trend ≈ +3.0, got {sensor._state}"

    def test_qfe_value_at_elevation_passes_qc(self, mock_hass):
        """QFE 897 hPa at 1200m elevation passes QC_MIN=870 check."""
        entry = _make_config_entry(pressure_type="absolute")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        event = _make_event(897.0, unit="hPa")
        sensor._handle_pressure_update(event)

        assert len(sensor._history) == 1, "897 hPa should pass QC"
        assert sensor._history[0][1] == 897.0

    def test_qfe_value_below_qc_min_rejected(self, mock_hass):
        """QFE 860 hPa is below QC_MIN=870 and must be rejected."""
        entry = _make_config_entry(pressure_type="absolute")
        sensor = LocalForecastPressureChangeSensor(mock_hass, entry)
        sensor.async_write_ha_state = Mock()

        event = _make_event(860.0, unit="hPa")
        sensor._handle_pressure_update(event)

        assert len(sensor._history) == 0, \
            f"860 hPa should be rejected by QC_MIN={PRESSURE_QC_MIN}"
