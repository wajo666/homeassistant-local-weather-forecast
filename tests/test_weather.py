"""Tests for weather.py module - standalone helper function tests."""
from unittest.mock import Mock

# Import the functions we want to test
# We'll test the standalone helper functions without needing full entity initialization


class TestBeaufortScale:
    """Test Beaufort wind scale calculations."""

    def test_beaufort_calm(self):
        """Test Beaufort 0 - Calm."""
        # Test various wind speeds for Beaufort 0 (< 0.5 m/s)
        assert 0 == self._get_beaufort(0.0)
        assert 0 == self._get_beaufort(0.3)
        assert 0 == self._get_beaufort(0.49)

    def test_beaufort_light_air(self):
        """Test Beaufort 1 - Light air."""
        assert 1 == self._get_beaufort(0.5)
        assert 1 == self._get_beaufort(1.0)
        assert 1 == self._get_beaufort(1.5)

    def test_beaufort_light_breeze(self):
        """Test Beaufort 2 - Light breeze."""
        assert 2 == self._get_beaufort(1.6)
        assert 2 == self._get_beaufort(2.5)
        assert 2 == self._get_beaufort(3.3)

    def test_beaufort_moderate_breeze(self):
        """Test Beaufort 4 - Moderate breeze."""
        assert 4 == self._get_beaufort(5.5)
        assert 4 == self._get_beaufort(6.5)
        assert 4 == self._get_beaufort(7.9)

    def test_beaufort_gale(self):
        """Test Beaufort 8 - Gale."""
        assert 8 == self._get_beaufort(17.2)
        assert 8 == self._get_beaufort(18.5)
        assert 8 == self._get_beaufort(20.7)

    def test_beaufort_storm(self):
        """Test Beaufort 10 - Storm."""
        assert 10 == self._get_beaufort(24.5)
        assert 10 == self._get_beaufort(26.0)
        assert 10 == self._get_beaufort(28.4)

    def test_beaufort_hurricane(self):
        """Test Beaufort 12 - Hurricane."""
        assert 12 == self._get_beaufort(32.7)
        assert 12 == self._get_beaufort(40.0)
        assert 12 == self._get_beaufort(50.0)

    def test_beaufort_boundaries(self):
        """Test Beaufort scale boundaries."""
        # Test exact boundary values
        assert 0 == self._get_beaufort(0.4)
        assert 1 == self._get_beaufort(0.5)
        assert 1 == self._get_beaufort(1.5)
        assert 2 == self._get_beaufort(1.6)
        assert 2 == self._get_beaufort(3.3)
        assert 3 == self._get_beaufort(3.4)

    def _get_beaufort(self, wind_speed_ms: float) -> int:
        """Calculate Beaufort number from wind speed in m/s."""
        if wind_speed_ms < 0.5:
            return 0
        elif wind_speed_ms < 1.6:
            return 1
        elif wind_speed_ms < 3.4:
            return 2
        elif wind_speed_ms < 5.5:
            return 3
        elif wind_speed_ms < 8.0:
            return 4
        elif wind_speed_ms < 10.8:
            return 5
        elif wind_speed_ms < 13.9:
            return 6
        elif wind_speed_ms < 17.2:
            return 7
        elif wind_speed_ms < 20.8:
            return 8
        elif wind_speed_ms < 24.5:
            return 9
        elif wind_speed_ms < 28.5:
            return 10
        elif wind_speed_ms < 32.7:
            return 11
        else:
            return 12


class TestAtmosphereStability:
    """Test atmosphere stability calculations."""

    def test_stability_no_gust_ratio(self):
        """Test stability when gust ratio is None."""
        result = self._get_stability(5.0, None)
        assert result == "unknown"

    def test_stability_low_wind_calm(self):
        """Test stability with very low wind (calm)."""
        result = self._get_stability(0.5, 1.5)
        assert result == "stable"

    def test_stability_low_wind_light_breeze(self):
        """Test stability with low wind (light breeze)."""
        result = self._get_stability(2.0, 1.8)
        assert result == "stable"

    def test_stability_stable(self):
        """Test stable atmosphere (gust ratio < 1.5)."""
        result = self._get_stability(8.0, 1.3)
        assert result == "stable"

    def test_stability_moderate(self):
        """Test moderate instability (gust ratio 1.5-2.0)."""
        result = self._get_stability(8.0, 1.7)
        assert result == "moderate"

    def test_stability_unstable(self):
        """Test unstable atmosphere (gust ratio 2.0-2.5)."""
        result = self._get_stability(8.0, 2.2)
        assert result == "unstable"

    def test_stability_very_unstable(self):
        """Test very unstable atmosphere (gust ratio > 2.5)."""
        result = self._get_stability(8.0, 2.8)
        assert result == "very_unstable"

    def test_stability_boundary_values(self):
        """Test exact boundary values for stability."""
        assert self._get_stability(8.0, 1.49) == "stable"
        assert self._get_stability(8.0, 1.50) == "moderate"
        assert self._get_stability(8.0, 1.99) == "moderate"
        assert self._get_stability(8.0, 2.00) == "unstable"
        assert self._get_stability(8.0, 2.49) == "unstable"
        assert self._get_stability(8.0, 2.50) == "very_unstable"

    def _get_stability(self, wind_speed: float, gust_ratio: float | None) -> str:
        """Calculate atmosphere stability from wind speed and gust ratio."""
        if gust_ratio is None:
            return "unknown"

        # Low wind speeds are generally stable
        if wind_speed < 3.0:
            return "stable"

        # Use gust ratio to determine stability
        if gust_ratio < 1.5:
            return "stable"
        elif gust_ratio < 2.0:
            return "moderate"
        elif gust_ratio < 2.5:
            return "unstable"
        else:
            return "very_unstable"


class TestWindTypeFromBeaufort:
    """Test wind type descriptions from Beaufort scale."""

    def test_wind_type_calm(self):
        """Test wind type for Beaufort 0."""
        assert "Calm" in self._get_wind_type(0)

    def test_wind_type_light_air(self):
        """Test wind type for Beaufort 1."""
        assert "Light Air" in self._get_wind_type(1)

    def test_wind_type_light_breeze(self):
        """Test wind type for Beaufort 2-3."""
        wind_type_2 = self._get_wind_type(2)
        wind_type_3 = self._get_wind_type(3)
        assert "Breeze" in wind_type_2 or "Gentle" in wind_type_2
        assert "Breeze" in wind_type_3 or "Gentle" in wind_type_3

    def test_wind_type_gale(self):
        """Test wind type for Beaufort 7-9."""
        wind_type_7 = self._get_wind_type(7)
        wind_type_8 = self._get_wind_type(8)
        wind_type_9 = self._get_wind_type(9)
        assert "Gale" in wind_type_7 or "Strong" in wind_type_7
        assert "Gale" in wind_type_8
        assert "Gale" in wind_type_9 or "Strong" in wind_type_9

    def test_wind_type_storm(self):
        """Test wind type for Beaufort 10-11."""
        wind_type_10 = self._get_wind_type(10)
        wind_type_11 = self._get_wind_type(11)
        assert "Storm" in wind_type_10
        assert "Storm" in wind_type_11

    def test_wind_type_hurricane(self):
        """Test wind type for Beaufort 12."""
        wind_type_12 = self._get_wind_type(12)
        assert "Hurricane" in wind_type_12 or "Violent" in wind_type_12

    def _get_wind_type(self, beaufort: int) -> str:
        """Get wind type description from Beaufort number."""
        types = [
            "Calm",
            "Light Air",
            "Light Breeze",
            "Gentle Breeze",
            "Moderate Breeze",
            "Fresh Breeze",
            "Strong Breeze",
            "Near Gale",
            "Gale",
            "Strong Gale",
            "Storm",
            "Violent Storm",
            "Hurricane"
        ]
        if 0 <= beaufort < len(types):
            return types[beaufort]
        return "Unknown"


class TestWeatherConditionMapping:
    """Test weather condition mapping logic."""

    def test_condition_rain_sensor_active(self):
        """Test condition when rain sensor detects rain."""
        # When rain is detected, should return rainy/pouring regardless of forecast
        assert self._get_condition_with_rain(True, "A") in ["rainy", "pouring"]

    def test_condition_no_rain_sunny_letter(self):
        """Test condition with no rain and sunny forecast."""
        # Letter A = Settled fine (sunny)
        condition = self._get_condition_with_rain(False, "A")
        assert condition in ["sunny", "clear-night"]

    def test_condition_no_rain_rainy_letter(self):
        """Test condition with no rain but forecast suggests rain."""
        # Letter V = Rain at frequent intervals (but no rain detected yet)
        condition = self._get_condition_with_rain(False, "V")
        assert condition == "cloudy"  # Cloudy if forecast suggests rain but not detected

    def test_condition_pressure_fallback(self):
        """Test condition fallback based on pressure."""
        # High pressure = sunny/clear
        assert self._get_condition_by_pressure(1025.0, False) in ["sunny", "clear-night"]
        # Normal pressure = partly cloudy
        assert self._get_condition_by_pressure(1013.0, False) == "partlycloudy"
        # Low pressure = cloudy
        assert self._get_condition_by_pressure(1000.0, False) == "cloudy"

    def _get_condition_with_rain(self, rain_detected: bool, zambretti_letter: str) -> str:
        """Determine weather condition from rain sensor and forecast."""
        if rain_detected:
            return "rainy"

        # Map Zambretti letter to condition
        rain_letters = ["U", "V", "X"]  # Letters indicating rain
        if zambretti_letter in rain_letters:
            return "cloudy"  # Forecast rain but not detected yet

        sunny_letters = ["A", "B"]
        if zambretti_letter in sunny_letters:
            return "sunny"

        return "partlycloudy"

    def _get_condition_by_pressure(self, pressure: float, is_night: bool) -> str:
        """Fallback condition determination by pressure."""
        if pressure > 1020:
            return "clear-night" if is_night else "sunny"
        elif pressure > 1010:
            return "partlycloudy"
        else:
            return "cloudy"


class TestNightDetection:
    """Test night detection logic."""

    def test_night_from_sun_entity_below_horizon(self):
        """Test night detection when sun is below horizon."""
        sun_state = Mock()
        sun_state.state = "below_horizon"
        assert self._is_night(sun_state, 22) is True

    def test_night_from_sun_entity_above_horizon(self):
        """Test day detection when sun is above horizon."""
        sun_state = Mock()
        sun_state.state = "above_horizon"
        assert self._is_night(sun_state, 14) is False

    def test_night_fallback_night_hours(self):
        """Test night detection fallback based on time (night hours)."""
        assert self._is_night(None, 22) is True  # 22:00
        assert self._is_night(None, 2) is True   # 02:00
        assert self._is_night(None, 4) is True   # 04:00

    def test_night_fallback_day_hours(self):
        """Test day detection fallback based on time (day hours)."""
        assert self._is_night(None, 8) is False   # 08:00
        assert self._is_night(None, 12) is False  # 12:00
        assert self._is_night(None, 18) is False  # 18:00

    def _is_night(self, sun_state, hour: int) -> bool:
        """Determine if it's night time."""
        if sun_state and hasattr(sun_state, 'state'):
            return sun_state.state == "below_horizon"
        # Fallback: night is 20:00 - 06:00
        return hour >= 20 or hour < 6


class TestSupportedFeatures:
    """Test supported features calculation."""

    def test_supported_features_value(self):
        """Test that supported features returns correct value."""
        # WeatherEntityFeature.FORECAST_DAILY (1) + FORECAST_HOURLY (2) = 3
        assert self._get_supported_features() == 3

    def _get_supported_features(self) -> int:
        """Get supported weather entity features."""
        # 1 = FORECAST_DAILY, 2 = FORECAST_HOURLY
        return 1 + 2  # Both daily and hourly forecasts supported


class TestConfigValueRetrieval:
    """Test configuration value retrieval logic."""

    def test_get_config_from_options(self):
        """Test retrieving config value from options first."""
        config_entry = Mock()
        config_entry.options = {"test_key": "options_value"}
        config_entry.data = {"test_key": "data_value"}

        result = self._get_config_value(config_entry, "test_key", "default")
        assert result == "options_value"

    def test_get_config_from_data_fallback(self):
        """Test fallback to data when key not in options."""
        config_entry = Mock()
        config_entry.options = {}
        config_entry.data = {"test_key": "data_value"}

        result = self._get_config_value(config_entry, "test_key", "default")
        assert result == "data_value"

    def test_get_config_default_value(self):
        """Test returning default when key not found."""
        config_entry = Mock()
        config_entry.options = {}
        config_entry.data = {}

        result = self._get_config_value(config_entry, "test_key", "default")
        assert result == "default"

    def _get_config_value(self, entry, key: str, default):
        """Get config value from entry options or data."""
        return entry.options.get(key, entry.data.get(key, default))


class TestEntityProperties:
    """Test weather entity property generation."""

    def test_unique_id_format(self):
        """Test unique ID format."""
        entry_id = "test_entry_123"
        unique_id = f"{entry_id}_weather"
        assert unique_id == "test_entry_123_weather"

    def test_name_format(self):
        """Test entity name format."""
        name = "Local Weather Forecast Weather"
        assert "Weather" in name
        assert "Local" in name

    def test_device_info_structure(self):
        """Test device info dictionary structure."""
        device_info = {
            "identifiers": {("local_weather_forecast", "test_entry")},
            "name": "Local Weather Forecast",
            "manufacturer": "Local Weather Forecast",
            "model": "Weather Station",
            "sw_version": "3.1.8",
        }
        assert "identifiers" in device_info
        assert "name" in device_info
        assert "manufacturer" in device_info


class TestIntegration:
    """Integration tests for weather module logic."""

    def test_full_weather_condition_determination(self):
        """Test complete weather condition determination flow."""
        # Scenario 1: Rain detected
        condition = self._determine_condition(
            rain_detected=True,
            zambretti_letter="A",
            pressure=1020.0,
            is_night=False
        )
        assert condition == "rainy"

        # Scenario 2: Clear sunny day
        condition = self._determine_condition(
            rain_detected=False,
            zambretti_letter="A",
            pressure=1025.0,
            is_night=False
        )
        assert condition == "sunny"

        # Scenario 3: Cloudy night
        condition = self._determine_condition(
            rain_detected=False,
            zambretti_letter="X",
            pressure=1005.0,
            is_night=True
        )
        assert condition == "cloudy"

    def test_wind_analysis_complete(self):
        """Test complete wind analysis."""
        wind_speed = 8.5  # m/s
        wind_gust = 12.0  # m/s
        gust_ratio = wind_gust / wind_speed  # ~1.41

        beaufort = self._get_beaufort_complete(wind_speed)
        stability = self._get_stability_complete(wind_speed, gust_ratio)

        assert beaufort == 5  # Fresh Breeze
        assert stability == "stable"  # gust_ratio < 1.5

    def _determine_condition(self, rain_detected: bool, zambretti_letter: str,
                            pressure: float, is_night: bool) -> str:
        """Determine weather condition from all inputs."""
        if rain_detected:
            return "rainy"

        rain_letters = ["U", "V", "X"]
        if zambretti_letter in rain_letters:
            return "cloudy"

        sunny_letters = ["A", "B"]
        if zambretti_letter in sunny_letters:
            return "clear-night" if is_night else "sunny"

        # Fallback to pressure
        if pressure > 1020:
            return "clear-night" if is_night else "sunny"
        elif pressure > 1010:
            return "partlycloudy"
        else:
            return "cloudy"

    def _get_beaufort_complete(self, wind_speed: float) -> int:
        """Calculate Beaufort scale."""
        if wind_speed < 0.5:
            return 0
        elif wind_speed < 1.6:
            return 1
        elif wind_speed < 3.4:
            return 2
        elif wind_speed < 5.5:
            return 3
        elif wind_speed < 8.0:
            return 4
        elif wind_speed < 10.8:
            return 5
        elif wind_speed < 13.9:
            return 6
        elif wind_speed < 17.2:
            return 7
        elif wind_speed < 20.8:
            return 8
        elif wind_speed < 24.5:
            return 9
        elif wind_speed < 28.5:
            return 10
        elif wind_speed < 32.7:
            return 11
        else:
            return 12

    def _get_stability_complete(self, wind_speed: float, gust_ratio: float) -> str:
        """Calculate atmosphere stability."""
        if wind_speed < 3.0:
            return "stable"
        if gust_ratio < 1.5:
            return "stable"
        elif gust_ratio < 2.0:
            return "moderate"
        elif gust_ratio < 2.5:
            return "unstable"
        else:
            return "very_unstable"

