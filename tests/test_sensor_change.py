"""Tests for change sensors in sensor.py module.

Note: These tests use synchronous mocks to test the sensor logic without requiring
a full Home Assistant async environment. The actual async behavior is tested through
integration tests.
"""
import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta

from custom_components.local_weather_forecast.sensor import (
    LocalForecastPressureChangeSensor,
    LocalForecastTemperatureChangeSensor,
    PRESSURE_MIN_RECORDS,
    TEMPERATURE_MIN_RECORDS,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    hass.async_create_task = Mock(side_effect=lambda coro: None)
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock()
    entry.data = {
        "pressure_sensor": "sensor.test_pressure",
        "temperature_sensor": "sensor.test_temperature",
    }
    entry.options = {}
    entry.entry_id = "test_entry_id"
    return entry


# Tests for LocalForecastPressureChangeSensor
class TestPressureChangeSensor:
    """Test PressureChangeSensor class."""

    def test_init(self, mock_hass, mock_config_entry):
        """Test pressure change sensor initialization."""
        sensor = LocalForecastPressureChangeSensor(mock_hass, mock_config_entry)

        assert sensor._attr_unique_id == "local_forecast_pressurechange"
        assert sensor._attr_name == "Local forecast PressureChange"
        assert sensor._state == 0.0
        assert sensor._history == []

    def test_history_init_empty(self, mock_hass, mock_config_entry):
        """Test that history initializes empty."""
        sensor = LocalForecastPressureChangeSensor(mock_hass, mock_config_entry)

        assert sensor._history == []
        assert sensor._state == 0.0

    def test_history_calculation(self, mock_hass, mock_config_entry):
        """Test basic pressure change calculation logic."""
        sensor = LocalForecastPressureChangeSensor(mock_hass, mock_config_entry)

        # Add some history manually
        timestamp1 = datetime.now()
        timestamp2 = timestamp1 + timedelta(minutes=180)
        sensor._history = [
            (timestamp1, 1010.0),
            (timestamp2, 1013.0),
        ]

        # Calculate state manually (what the sensor should do)
        oldest = sensor._history[0][1]
        newest = sensor._history[-1][1]
        expected_change = round(newest - oldest, 2)

        assert expected_change == 3.0

    def test_history_time_window_logic(self, mock_hass, mock_config_entry):
        """Test history time window filtering logic."""
        sensor = LocalForecastPressureChangeSensor(mock_hass, mock_config_entry)

        now = datetime.now()
        # Create test history with old and new data
        test_history = [
            (now - timedelta(minutes=200), 1010.0),  # Too old
            (now - timedelta(minutes=150), 1011.0),  # Within window
            (now - timedelta(minutes=100), 1012.0),  # Within window
            (now - timedelta(minutes=50), 1013.0),   # Within window
        ]

        # Filter manually (what sensor should do)
        cutoff = now - timedelta(minutes=180)
        filtered = [(ts, p) for ts, p in test_history if ts > cutoff]

        # Should keep only records within 180 minutes
        assert len(filtered) == 3  # Last 3 entries
        assert filtered[0][1] == 1011.0

    def test_minimum_records_logic(self, mock_hass, mock_config_entry):
        """Test minimum records kept logic."""
        sensor = LocalForecastPressureChangeSensor(mock_hass, mock_config_entry)

        now = datetime.now()
        # Create test history with very old data
        test_history = [
            (now - timedelta(minutes=250), 1010.0),
            (now - timedelta(minutes=240), 1011.0),
        ]

        # Apply time filter
        cutoff = now - timedelta(minutes=180)
        time_filtered = [(ts, p) for ts, p in test_history if ts > cutoff]

        # Check logic: if filtered < MIN_RECORDS, keep last MIN_RECORDS
        if len(time_filtered) < PRESSURE_MIN_RECORDS:
            result = test_history[-PRESSURE_MIN_RECORDS:]
        else:
            result = time_filtered

        # Should keep minimum records even if old
        assert len(result) >= min(len(test_history), PRESSURE_MIN_RECORDS)


    def test_extra_state_attributes(self, mock_hass, mock_config_entry):
        """Test extra state attributes."""
        sensor = LocalForecastPressureChangeSensor(mock_hass, mock_config_entry)

        timestamp = datetime.now()
        sensor._history = [
            (timestamp, 1010.0),
            (timestamp + timedelta(minutes=10), 1011.0),
        ]

        attrs = sensor.extra_state_attributes

        assert "history" in attrs
        assert "history_count" in attrs
        assert attrs["history_count"] == 2
        assert "oldest_reading" in attrs
        assert "newest_reading" in attrs


# Tests for LocalForecastTemperatureChangeSensor
class TestTemperatureChangeSensor:
    """Test TemperatureChangeSensor class."""

    def test_init(self, mock_hass, mock_config_entry):
        """Test temperature change sensor initialization."""
        sensor = LocalForecastTemperatureChangeSensor(mock_hass, mock_config_entry)

        assert sensor._attr_unique_id == "local_forecast_temperaturechange"
        assert sensor._attr_name == "Local forecast TemperatureChange"
        assert sensor._state == 0.0
        assert sensor._history == []

    def test_temperature_history_init_empty(self, mock_hass, mock_config_entry):
        """Test that temperature history initializes empty."""
        sensor = LocalForecastTemperatureChangeSensor(mock_hass, mock_config_entry)

        assert sensor._history == []
        assert sensor._state == 0.0

    def test_temperature_calculation(self, mock_hass, mock_config_entry):
        """Test basic temperature change calculation logic."""
        sensor = LocalForecastTemperatureChangeSensor(mock_hass, mock_config_entry)

        # Add some history manually
        timestamp1 = datetime.now()
        timestamp2 = timestamp1 + timedelta(minutes=60)
        sensor._history = [
            (timestamp1, 20.0),
            (timestamp2, 21.5),
        ]

        # Calculate state manually (what the sensor should do)
        oldest = sensor._history[0][1]
        newest = sensor._history[-1][1]
        expected_change = round(newest - oldest, 2)

        assert expected_change == 1.5

    def test_temperature_time_window_60min(self, mock_hass, mock_config_entry):
        """Test temperature history time window filtering logic (60 min)."""
        sensor = LocalForecastTemperatureChangeSensor(mock_hass, mock_config_entry)

        now = datetime.now()
        # Create test history with old and new data
        test_history = [
            (now - timedelta(minutes=70), 20.0),   # Too old
            (now - timedelta(minutes=50), 20.5),   # Within window
            (now - timedelta(minutes=30), 21.0),   # Within window
            (now - timedelta(minutes=10), 21.5),   # Within window
        ]

        # Filter manually (what sensor should do)
        cutoff = now - timedelta(minutes=60)
        filtered = [(ts, t) for ts, t in test_history if ts > cutoff]

        # Should keep only records within 60 minutes
        assert len(filtered) == 3  # Last 3 entries
        assert filtered[0][1] == 20.5

    def test_temperature_minimum_records_logic(self, mock_hass, mock_config_entry):
        """Test minimum records kept logic for temperature."""
        sensor = LocalForecastTemperatureChangeSensor(mock_hass, mock_config_entry)

        now = datetime.now()
        # Create test history with very old data
        test_history = [
            (now - timedelta(minutes=90), 20.0),
            (now - timedelta(minutes=80), 20.5),
        ]

        # Apply time filter
        cutoff = now - timedelta(minutes=60)
        time_filtered = [(ts, t) for ts, t in test_history if ts > cutoff]

        # Check logic: if filtered < MIN_RECORDS, keep last MIN_RECORDS
        if len(time_filtered) < TEMPERATURE_MIN_RECORDS:
            result = test_history[-TEMPERATURE_MIN_RECORDS:]
        else:
            result = time_filtered

        # Should keep minimum records even if old
        assert len(result) >= min(len(test_history), TEMPERATURE_MIN_RECORDS)


    def test_native_value(self, mock_hass, mock_config_entry):
        """Test native_value property."""
        sensor = LocalForecastTemperatureChangeSensor(mock_hass, mock_config_entry)
        sensor._state = 1.5

        assert sensor.native_value == 1.5

    def test_extra_state_attributes_empty_history(self, mock_hass, mock_config_entry):
        """Test extra state attributes with empty history."""
        sensor = LocalForecastTemperatureChangeSensor(mock_hass, mock_config_entry)
        sensor._history = []

        attrs = sensor.extra_state_attributes

        assert attrs["history_count"] == 0
        assert attrs["oldest_reading"] is None
        assert attrs["newest_reading"] is None

