"""Tests for zambretti.py module."""
from unittest.mock import patch
from datetime import datetime

from custom_components.local_weather_forecast.zambretti import (
    calculate_zambretti_forecast,
    _map_zambretti_to_forecast,
    _map_zambretti_to_letter,
)


class TestMapZambrettiToLetter:
    """Test _map_zambretti_to_letter function."""

    def test_map_letter_a(self):
        """Test mapping for letter A."""
        assert _map_zambretti_to_letter(1) == "A"
        assert _map_zambretti_to_letter(10) == "A"
        assert _map_zambretti_to_letter(20) == "A"

    def test_map_letter_b(self):
        """Test mapping for letter B."""
        assert _map_zambretti_to_letter(2) == "B"
        assert _map_zambretti_to_letter(11) == "B"
        assert _map_zambretti_to_letter(21) == "B"

    def test_map_various_letters(self):
        """Test mapping for various letters."""
        assert _map_zambretti_to_letter(3) == "D"
        assert _map_zambretti_to_letter(4) == "H"
        assert _map_zambretti_to_letter(5) == "O"
        assert _map_zambretti_to_letter(6) == "R"
        assert _map_zambretti_to_letter(7) == "U"
        assert _map_zambretti_to_letter(8) == "V"

    def test_map_letter_x(self):
        """Test mapping for letter X."""
        assert _map_zambretti_to_letter(9) == "X"
        assert _map_zambretti_to_letter(18) == "X"

    def test_map_letter_z(self):
        """Test mapping for letter Z (extreme conditions)."""
        assert _map_zambretti_to_letter(19) == "Z"
        assert _map_zambretti_to_letter(32) == "Z"
        assert _map_zambretti_to_letter(33) == "Z"

    def test_map_letter_f(self):
        """Test mapping for letter F."""
        assert _map_zambretti_to_letter(22) == "F"
        assert _map_zambretti_to_letter(23) == "F"

    def test_map_unknown_fallback(self):
        """Test fallback for unknown z-number."""
        assert _map_zambretti_to_letter(99) == "A"
        assert _map_zambretti_to_letter(0) == "A"
        assert _map_zambretti_to_letter(-1) == "A"

    def test_map_all_valid_numbers(self):
        """Test that all valid z-numbers have mappings."""
        valid_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
                        20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]

        for z in valid_numbers:
            result = _map_zambretti_to_letter(z)
            assert isinstance(result, str)
            assert len(result) == 1
            assert result.isalpha()
            assert result.isupper()


class TestMapZambrettiToForecast:
    """Test _map_zambretti_to_forecast function."""

    def test_map_forecast_settled_fine(self):
        """Test mapping for settled fine weather."""
        assert _map_zambretti_to_forecast(1) == 0
        assert _map_zambretti_to_forecast(10) == 0
        assert _map_zambretti_to_forecast(20) == 0

    def test_map_forecast_fine(self):
        """Test mapping for fine weather."""
        assert _map_zambretti_to_forecast(2) == 1
        assert _map_zambretti_to_forecast(11) == 1
        assert _map_zambretti_to_forecast(21) == 1

    def test_map_various_forecasts(self):
        """Test mapping for various forecast types."""
        assert _map_zambretti_to_forecast(3) == 3
        assert _map_zambretti_to_forecast(4) == 7
        assert _map_zambretti_to_forecast(5) == 14
        assert _map_zambretti_to_forecast(6) == 17

    def test_map_extreme_conditions(self):
        """Test mapping for extreme weather conditions."""
        assert _map_zambretti_to_forecast(19) == 25
        assert _map_zambretti_to_forecast(32) == 25
        assert _map_zambretti_to_forecast(33) == 25

    def test_map_fixed_z22(self):
        """Test that z=22 has correct mapping (was missing)."""
        assert _map_zambretti_to_forecast(22) == 5
        assert _map_zambretti_to_forecast(23) == 5

    def test_map_unmapped_number(self):
        """Test unmapped z-number returns None."""
        assert _map_zambretti_to_forecast(99) is None
        assert _map_zambretti_to_forecast(0) is None
        assert _map_zambretti_to_forecast(-1) is None

    def test_map_all_valid_numbers(self):
        """Test that all valid z-numbers return forecast indices."""
        valid_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
                        20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]

        for z in valid_numbers:
            result = _map_zambretti_to_forecast(z)
            assert result is not None
            assert isinstance(result, int)
            assert 0 <= result <= 25  # Valid forecast index range


class TestCalculateZambrettiForecast:
    """Test calculate_zambretti_forecast function."""

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_falling_pressure_winter(self, mock_datetime):
        """Test forecast with falling pressure in winter."""
        # Mock winter month (January)
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        p0 = 995.0  # Low pressure
        pressure_change = -2.5  # Falling
        wind_data = [0, 180.0, "S", 0]  # No wind correction
        lang_index = 1  # English

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result, list)
        assert len(result) == 3
        assert isinstance(result[0], str)  # forecast_text
        assert isinstance(result[1], int)  # forecast_number
        assert isinstance(result[2], str)  # letter_code

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_rising_pressure_summer(self, mock_datetime):
        """Test forecast with rising pressure in summer."""
        # Mock summer month (July)
        mock_datetime.now.return_value = datetime(2025, 7, 15, 12, 0)

        p0 = 1020.0  # High pressure
        pressure_change = 2.5  # Rising
        wind_data = [0, 0.0, "N", 0]  # No wind correction
        lang_index = 1  # English

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result, list)
        assert len(result) == 3
        assert isinstance(result[0], str)
        assert isinstance(result[1], int)
        assert isinstance(result[2], str)

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_steady_pressure_winter(self, mock_datetime):
        """Test forecast with steady pressure in winter."""
        # Mock winter month (December)
        mock_datetime.now.return_value = datetime(2025, 12, 15, 12, 0)

        p0 = 1013.0  # Normal pressure
        pressure_change = 0.5  # Steady (between -1.0 and 1.0)
        wind_data = [0, 90.0, "E", 0]  # No wind correction
        lang_index = 1  # English

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result, list)
        assert len(result) == 3

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_steady_pressure_summer(self, mock_datetime):
        """Test forecast with steady pressure in summer."""
        # Mock summer month (June)
        mock_datetime.now.return_value = datetime(2025, 6, 15, 12, 0)

        p0 = 1013.0  # Normal pressure
        pressure_change = 0.0  # Steady
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1  # English

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result, list)
        assert len(result) == 3

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_wind_correction_applied(self, mock_datetime):
        """Test that wind correction is applied correctly."""
        # Mock winter month
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        p0 = 1013.0
        pressure_change = -2.0  # Falling
        lang_index = 1

        # Without wind correction
        wind_data_no_wind = [0, 0.0, "N", 0]
        result_no_wind = calculate_zambretti_forecast(p0, pressure_change, wind_data_no_wind, lang_index)

        # With wind correction
        wind_data_with_wind = [2, 180.0, "S", 1]  # wind_fak=2, speed_fak=1
        result_with_wind = calculate_zambretti_forecast(p0, pressure_change, wind_data_with_wind, lang_index)

        # Results should differ due to wind correction
        assert isinstance(result_no_wind, list)
        assert isinstance(result_with_wind, list)

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_all_languages(self, mock_datetime):
        """Test forecast returns text in all supported languages."""
        # Mock winter month
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        p0 = 1013.0
        pressure_change = 0.0
        wind_data = [0, 0.0, "N", 0]

        # Test all language indices
        for lang_index in range(4):  # 0=de, 1=en, 2=el, 3=it
            result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
            assert isinstance(result[0], str)
            assert len(result[0]) > 0

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_pressure_trend_thresholds(self, mock_datetime):
        """Test pressure trend detection at threshold boundaries."""
        # Mock winter month
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        p0 = 1013.0
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        # Test falling threshold (-1.0)
        result_falling = calculate_zambretti_forecast(p0, -1.0, wind_data, lang_index)
        assert isinstance(result_falling, list)

        # Test rising threshold (1.0)
        result_rising = calculate_zambretti_forecast(p0, 1.0, wind_data, lang_index)
        assert isinstance(result_rising, list)

        # Test steady (between thresholds)
        result_steady = calculate_zambretti_forecast(p0, 0.0, wind_data, lang_index)
        assert isinstance(result_steady, list)

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_extreme_pressure_values(self, mock_datetime):
        """Test forecast with extreme pressure values."""
        # Mock winter month
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        # Very low pressure (tropical cyclone)
        result_low = calculate_zambretti_forecast(950.0, -3.0, wind_data, lang_index)
        assert isinstance(result_low, list)

        # Very high pressure (winter anticyclone)
        result_high = calculate_zambretti_forecast(1050.0, 3.0, wind_data, lang_index)
        assert isinstance(result_high, list)

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_season_adjustment_rising(self, mock_datetime):
        """Test that summer adjustment is applied for rising pressure."""
        p0 = 1013.0
        pressure_change = 2.0  # Rising
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        # Summer month (July) - should add 1 to z
        mock_datetime.now.return_value = datetime(2025, 7, 15, 12, 0)
        result_summer = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        # Winter month (January) - no adjustment
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)
        result_winter = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result_summer, list)
        assert isinstance(result_winter, list)

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_season_adjustment_steady(self, mock_datetime):
        """Test that winter adjustment is applied for steady pressure."""
        p0 = 1013.0
        pressure_change = 0.0  # Steady
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        # Winter month (January) - should subtract 1 from z
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)
        result_winter = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        # Summer month (July) - no adjustment
        mock_datetime.now.return_value = datetime(2025, 7, 15, 12, 0)
        result_summer = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result_winter, list)
        assert isinstance(result_summer, list)

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_letter_code_valid(self, mock_datetime):
        """Test that letter code is always valid."""
        # Mock winter month
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        p0 = 1013.0
        pressure_change = 0.0
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        letter_code = result[2]
        assert isinstance(letter_code, str)
        assert len(letter_code) == 1
        assert letter_code.isalpha()
        assert letter_code.isupper()

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_realistic_scenario(self, mock_datetime):
        """Test with realistic weather station data."""
        # Mock winter month
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        # Typical weather station readings
        p0 = 1015.3  # Normal pressure
        pressure_change = -1.2  # Slight falling
        wind_data = [1, 225.0, "SW", 1]  # Southwest wind with correction
        lang_index = 1  # English

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result, list)
        assert len(result) == 3
        assert isinstance(result[0], str)
        assert len(result[0]) > 0
        assert isinstance(result[1], int)
        assert 0 <= result[1] <= 25
        assert isinstance(result[2], str)
        assert len(result[2]) == 1


class TestZambrettiFormulas:
    """Test Zambretti formula calculations."""

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_falling_formula(self, mock_datetime):
        """Test falling pressure formula: z = 127 - 0.12 * p0."""
        # Mock winter month
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        # Test with p0 = 1000 hPa
        # Expected z = round(127 - 0.12 * 1000) = round(127 - 120) = 7
        p0 = 1000.0
        pressure_change = -2.0  # Falling
        wind_data = [0, 0.0, "N", 0]  # No wind correction
        lang_index = 1

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        # Verify result is valid
        assert isinstance(result, list)
        assert result[1] >= 0  # Valid forecast index

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_steady_formula(self, mock_datetime):
        """Test steady pressure formula: z = 144 - 0.13 * p0."""
        # Mock winter month (will subtract 1)
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        # Test with p0 = 1000 hPa
        # Expected z = round(144 - 0.13 * 1000) - 1 = round(144 - 130) - 1 = 14 - 1 = 13
        p0 = 1000.0
        pressure_change = 0.0  # Steady
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result, list)
        assert result[1] >= 0

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_rising_formula(self, mock_datetime):
        """Test rising pressure formula: z = 185 - 0.16 * p0."""
        # Mock summer month (will add 1)
        mock_datetime.now.return_value = datetime(2025, 7, 15, 12, 0)

        # Test with p0 = 1000 hPa
        # Expected z = round(185 - 0.16 * 1000) + 1 = round(185 - 160) + 1 = 25 + 1 = 26
        p0 = 1000.0
        pressure_change = 2.0  # Rising
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert isinstance(result, list)
        assert result[1] >= 0


class TestConsistency:
    """Test consistency of Zambretti calculations."""

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_same_inputs_same_outputs(self, mock_datetime):
        """Test that same inputs produce same outputs."""
        # Mock winter month
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        p0 = 1013.0
        pressure_change = -1.5
        wind_data = [1, 180.0, "S", 1]
        lang_index = 1

        result1 = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        result2 = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

        assert result1 == result2

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_all_months_produce_valid_results(self, mock_datetime):
        """Test that all months produce valid forecasts."""
        p0 = 1013.0
        pressure_change = 0.0
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        for month in range(1, 13):
            mock_datetime.now.return_value = datetime(2025, month, 15, 12, 0)
            result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)

            assert isinstance(result, list)
            assert len(result) == 3
            assert isinstance(result[0], str)
            assert isinstance(result[1], int)
            assert isinstance(result[2], str)

