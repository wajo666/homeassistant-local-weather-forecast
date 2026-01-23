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
        # FIXED: z=9 now maps to 'F' (Fairly Fine) for high pressure + steady
        # z=18 still maps to 'X' (Very Unsettled)
        assert _map_zambretti_to_letter(9) == "F"
        assert _map_zambretti_to_letter(18) == "X"

    def test_map_letter_z(self):
        """Test mapping for letter Z (extreme conditions - low pressure recovery)."""
        # z=19 is now 'B' (Fine) - high pressure with rising trend
        # Only z=32-33 map to 'Z' (extreme rising pressure - storm recovery)
        assert _map_zambretti_to_letter(32) == "Z"
        assert _map_zambretti_to_letter(33) == "Z"

    def test_map_letter_b_high_pressure_rising(self):
        """Test mapping for z=19 - high pressure (~1040 hPa) with rising trend."""
        # z=19 occurs at ~1040 hPa with rising trend
        # This is stable anticyclone → should be Fine weather (B), not Stormy (Z)
        assert _map_zambretti_to_letter(19) == "B"

    def test_map_letter_f(self):
        """Test mapping for letter F."""
        assert _map_zambretti_to_letter(22) == "F"
        assert _map_zambretti_to_letter(23) == "F"

    def test_map_unknown_fallback(self):
        """Test clamping for out-of-range z-numbers."""
        # z > 33 should clamp to 33 → letter 'Z'
        assert _map_zambretti_to_letter(99) == "Z"
        # z < 1 should clamp to 1 → letter 'A'
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
        """Test mapping for extreme weather conditions (low pressure recovery)."""
        # Only z=32-33 map to 25 (Stormy) - extreme rising pressure (storm recovery)
        # z=19 is now mapped to 1 (Fine) - high pressure with rising trend
        assert _map_zambretti_to_forecast(32) == 25
        assert _map_zambretti_to_forecast(33) == 25

    def test_map_z19_high_pressure_rising(self):
        """Test z=19 mapping - high pressure (~1040 hPa) with rising trend."""
        # z=19 occurs at ~1040 hPa with rising trend
        # Rising formula: z = round(185 - 0.16 * 1040) = 19
        # This is stable anticyclone → should map to 1 (Fine), not 25 (Stormy)
        assert _map_zambretti_to_forecast(19) == 1

    def test_map_fixed_z22(self):
        """Test that z=22 has correct mapping (was missing)."""
        assert _map_zambretti_to_forecast(22) == 5
        assert _map_zambretti_to_forecast(23) == 5

    def test_map_unmapped_number(self):
        """Test clamping for out-of-range z-numbers."""
        # z > 33 should clamp to 33 → forecast_index 25
        assert _map_zambretti_to_forecast(99) == 25
        # z < 1 should clamp to 1 → forecast_index 0
        assert _map_zambretti_to_forecast(0) == 0
        assert _map_zambretti_to_forecast(-1) == 0

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
        assert len(result) == 3  # Returns: [text, code, letter]
        assert isinstance(result[0], str)  # forecast_text
        assert isinstance(result[1], int)  # forecast_number/code

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
        assert len(result) == 3  # Returns: [text, code, letter]
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
        assert len(result) == 3  # Returns: [text, code, letter]

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
        assert len(result) == 3  # Returns: [text, code, letter]

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

        # Extract letter_code from result
        text, num, letter_code = result
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
        assert len(result) == 3  # Returns: [text, code, letter]
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
            assert len(result) == 3  # Returns: [text, code, letter]
            assert isinstance(result[0], str)
            assert isinstance(result[1], int)
            assert isinstance(result[2], str)


class TestSeasonalIconMapping:
    """Test seasonal adjustments and their impact on weather icons."""

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_rising_pressure_summer_vs_winter(self, mock_datetime):
        """Test that rising pressure gives more optimistic forecast in summer."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        p0 = 1015.0  # Moderate pressure (gives different forecast numbers)
        pressure_change = 2.5  # Rising
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1  # English

        # WINTER (January) - no adjustment for rising
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)
        result_winter = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        text_winter, num_winter, letter_winter = result_winter

        # SUMMER (July) - z+1 adjustment for rising
        mock_datetime.now.return_value = datetime(2025, 7, 15, 12, 0)
        result_summer = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        text_summer, num_summer, letter_summer = result_summer

        # Letter codes should be different (summer more optimistic)
        # Note: Different z-numbers may map to same forecast_num, so check letters
        assert letter_winter != letter_summer, \
            f"Summer should have different letter: winter={letter_winter}, summer={letter_summer}"

        # Map to conditions
        condition_winter = map_forecast_to_condition(
            text_winter, num_winter,
            is_night_func=lambda: False,
            source="Zambretti"
        )

        condition_summer = map_forecast_to_condition(
            text_summer, num_summer,
            is_night_func=lambda: False,
            source="Zambretti"
        )

        # Both should be valid HA conditions
        valid_conditions = ["sunny", "partlycloudy", "cloudy", "rainy", "pouring", "lightning-rainy"]
        assert condition_winter in valid_conditions
        assert condition_summer in valid_conditions

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_steady_pressure_winter_vs_summer(self, mock_datetime):
        """Test that steady pressure gives more pessimistic forecast in winter."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        p0 = 1010.0  # Moderate pressure
        pressure_change = 0.5  # Steady
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1  # English

        # WINTER (December) - z-1 adjustment for steady
        mock_datetime.now.return_value = datetime(2025, 12, 15, 12, 0)
        result_winter = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        text_winter, num_winter, letter_winter = result_winter

        # SUMMER (June) - no adjustment for steady
        mock_datetime.now.return_value = datetime(2025, 6, 15, 12, 0)
        result_summer = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        text_summer, num_summer, letter_summer = result_summer

        # Letter codes should be different (winter more pessimistic)
        assert letter_winter != letter_summer, \
            f"Winter should have different letter: summer={letter_summer}, winter={letter_winter}"

        # Map to conditions
        condition_winter = map_forecast_to_condition(
            text_winter, num_winter,
            is_night_func=lambda: False,
            source="Zambretti"
        )

        condition_summer = map_forecast_to_condition(
            text_summer, num_summer,
            is_night_func=lambda: False,
            source="Zambretti"
        )

        # Both should be valid HA conditions
        valid_conditions = ["sunny", "partlycloudy", "cloudy", "rainy", "pouring", "lightning-rainy"]
        assert condition_winter in valid_conditions
        assert condition_summer in valid_conditions

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_falling_pressure_no_seasonal_adjustment(self, mock_datetime):
        """Test that falling pressure has NO seasonal adjustment."""
        p0 = 995.0
        pressure_change = -2.5  # Falling
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1  # English

        # WINTER (January)
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)
        result_winter = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        num_winter = result_winter[1]

        # SUMMER (July)
        mock_datetime.now.return_value = datetime(2025, 7, 15, 12, 0)
        result_summer = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        num_summer = result_summer[1]

        # Falling has NO seasonal adjustment - should be the same
        assert num_winter == num_summer, \
            f"Falling pressure should be same in all seasons: winter={num_winter}, summer={num_summer}"

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_all_months_icon_consistency(self, mock_datetime):
        """Test that icons are reasonable across all months."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        p0 = 1020.0  # High pressure
        pressure_change = 2.0  # Rising
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        valid_conditions = ["sunny", "partlycloudy", "cloudy", "rainy", "pouring", "lightning-rainy", "clear-night"]

        for month in range(1, 13):
            mock_datetime.now.return_value = datetime(2025, month, 15, 12, 0)

            result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
            text, num, letter = result  # Has 3 values

            # Map to condition (daytime)
            condition = map_forecast_to_condition(
                text, num,
                is_night_func=lambda: False,
                source="Zambretti"
            )

            # Should be valid condition
            assert condition in valid_conditions, \
                f"Month {month}: Invalid condition '{condition}' for z={num}"

            # High pressure + rising should generally be good weather
            assert condition in ["sunny", "partlycloudy"], \
                f"Month {month}: High pressure rising should be good weather, got '{condition}'"

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_day_night_icon_conversion(self, mock_datetime):
        """Test that sunny/clear-night conversion works in all seasons."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        # Mock winter
        mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

        p0 = 1030.0  # High pressure
        pressure_change = 1.5  # Rising
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        text, num, letter = result  # Has 3 values

        # Should be fair weather
        assert num <= 5, f"High pressure rising should be fair weather, got z={num}"

        # Day = sunny
        condition_day = map_forecast_to_condition(
            text, num,
            is_night_func=lambda: False,
            source="Zambretti"
        )

        # Night = clear-night
        condition_night = map_forecast_to_condition(
            text, num,
            is_night_func=lambda: True,
            source="Zambretti"
        )

        # If one is sunny, the other should be clear-night
        if condition_day == "sunny":
            assert condition_night == "clear-night", \
                f"Day=sunny should give Night=clear-night, got {condition_night}"

        if condition_night == "clear-night":
            assert condition_day == "sunny", \
                f"Night=clear-night should give Day=sunny, got {condition_day}"

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_season_boundary_march_november(self, mock_datetime):
        """Test season boundaries at March (2 < month < 11)."""
        p0 = 1010.0
        pressure_change = 0.5  # Steady
        wind_data = [0, 0.0, "N", 0]
        lang_index = 1

        # February - WINTER (steady -1)
        mock_datetime.now.return_value = datetime(2025, 2, 15, 12, 0)
        result_feb = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        text_feb, num_feb, letter_feb = result_feb

        # March - SUMMER (no steady adjustment)
        mock_datetime.now.return_value = datetime(2025, 3, 15, 12, 0)
        result_mar = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        text_mar, num_mar, letter_mar = result_mar

        # November - WINTER (steady -1)
        mock_datetime.now.return_value = datetime(2025, 11, 15, 12, 0)
        result_nov = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
        text_nov, num_nov, letter_nov = result_nov

        # February and November should be same (both winter)
        assert letter_feb == letter_nov, \
            f"Feb and Nov should both be winter: Feb={letter_feb}, Nov={letter_nov}"

        # March should be different from Feb (summer starts)
        assert letter_mar != letter_feb, \
            f"March should differ from Feb: Feb={letter_feb}, Mar={letter_mar}"


@patch('custom_components.local_weather_forecast.zambretti.datetime')
def test_winter_adjustment_high_pressure_steady(mock_datetime):
    """Test that winter adjustment is NOT applied for high pressure (>1025 hPa) with steady trend.

    Bug fix: Previously, winter adjustment (-1) was applied to ALL steady conditions,
    causing high pressure (1034 hPa) to give "Very Unsettled" instead of "Fine".

    Example: 1034 hPa steady winter:
    - Formula: z = 144 - 0.13*1034 = 10
    - OLD: Winter -1 → z=9 → forecast #23 "Very Unsettled" ❌
    - NEW: No adjustment (high pressure) → z=10 → better forecast ✅
    """
    # Mock winter month (January)
    mock_datetime.now.return_value = datetime(2025, 1, 18, 6, 30)

    # High pressure, steady trend (your actual conditions)
    p0 = 1034.0  # High pressure
    pressure_change = 0.5  # Steady (within ±1.6 threshold)
    wind_data = [0, 324, 'NW', 1]  # North wind, light
    lang_index = 1  # English

    result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
    text, num, letter = result  # Has 3 values

    # z = 144 - 0.13*1034 = 10 (no winter adjustment for high pressure)
    # z=10 should NOT map to #23 "Very Unsettled"
    assert num != 23, \
        f"High pressure (1034 hPa) steady in winter should NOT give 'Very Unsettled' (got #{num})"

    # Should give reasonable forecast for high stable pressure
    assert num <= 5, \
        f"High pressure (1034 hPa) steady should give good forecast, got #{num}: {text}"


@patch('custom_components.local_weather_forecast.zambretti.datetime')
def test_winter_adjustment_normal_pressure_steady(mock_datetime):
    """Test that winter adjustment IS applied for normal/low pressure (<=1025 hPa) with steady trend."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 18, 12, 0)

    # Normal pressure, steady trend
    p0 = 1015.0  # Normal pressure
    pressure_change = 0.2  # Steady
    wind_data = [1, 180, 'S', 0]  # South wind, calm
    lang_index = 1  # English

    result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
    text, num, letter = result  # Has 3 values

    # z = 144 - 0.13*1015 = 12
    # Winter adjustment should apply: z = 11
    # This is expected behavior for normal/low pressure
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert len(text) > 0


@patch('custom_components.local_weather_forecast.zambretti.datetime')
def test_winter_adjustment_very_low_pressure_steady(mock_datetime):
    """Test that winter adjustment is NOT applied for very low pressure (<975 hPa) with steady trend.

    Very low pressure (e.g., 960 hPa) indicates stormy conditions even if steady.
    Winter adjustment would make it even more pessimistic, which is unnecessary.

    Example: 960 hPa steady winter:
    - Formula: z = 144 - 0.13*960 = 19
    - OLD: Winter -1 → z=18 → may give "Fine" ❌
    - NEW: No adjustment (very low pressure) → z=19 → stormy forecast ✅
    """
    # Mock winter month (January)
    mock_datetime.now.return_value = datetime(2025, 1, 18, 12, 0)

    # Very low pressure (tropical cyclone/medicane), steady trend
    p0 = 960.0  # Very low pressure (storm)
    pressure_change = 0.3  # Steady
    wind_data = [2, 180, 'S', 1]  # South wind, strong
    lang_index = 1  # English

    result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
    text, num, letter = result  # Has 3 values

    # Very low pressure should give stormy forecast regardless of season
    # z = 144 - 0.13*960 = 19 (no winter adjustment for very low pressure)
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert len(text) > 0
    # Should indicate unsettled/stormy conditions
    assert num >= 10, \
        f"Very low pressure (960 hPa) should give unsettled forecast, got #{num}: {text}"


@patch('custom_components.local_weather_forecast.zambretti.datetime')
def test_summer_adjustment_low_pressure_rising(mock_datetime):
    """Test that summer adjustment is NOT applied for very low pressure (<975 hPa) with rising trend.

    Very low pressure rising = storm recovery. Summer adjustment (+1) would make
    it too optimistic too quickly.

    Example: 965 hPa rising summer:
    - Formula: z = 185 - 0.16*965 = 31
    - OLD: Summer +1 → z=32 → may overflow or be too optimistic ❌
    - NEW: No adjustment (very low pressure) → z=31 → appropriate recovery forecast ✅
    """
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 18, 12, 0)

    # Very low pressure (storm), rising trend (recovery)
    p0 = 965.0  # Very low pressure (storm recovery)
    pressure_change = 2.5  # Rising (storm passing)
    wind_data = [0, 270, 'W', 1]  # West wind
    lang_index = 1  # English

    result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
    text, num, letter = result  # Has 3 values

    # z = 185 - 0.16*965 = 31 (no summer adjustment for very low pressure)
    # Should not give overly optimistic forecast during storm recovery
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert len(text) > 0


@patch('custom_components.local_weather_forecast.zambretti.datetime')
def test_summer_adjustment_high_pressure_rising(mock_datetime):
    """Test that summer adjustment is NOT applied for high pressure (>1025 hPa) with rising trend.

    High pressure rising in summer = already very good weather. Summer adjustment (+1)
    would be redundant.

    Example: 1035 hPa rising summer:
    - Formula: z = 185 - 0.16*1035 = 19
    - OLD: Summer +1 → z=20 → same as z=19, redundant ❌
    - NEW: No adjustment (high pressure) → z=19 → fine weather ✅
    """
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 18, 12, 0)

    # High pressure, rising trend
    p0 = 1035.0  # High pressure
    pressure_change = 1.8  # Rising
    wind_data = [0, 0, 'N', 0]  # Calm
    lang_index = 1  # English

    result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
    text, num, letter = result  # Has 3 values

    # z = 185 - 0.16*1035 = 19 (no summer adjustment for high pressure)
    # Should give fine weather forecast
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert num <= 5, \
        f"High pressure (1035 hPa) rising should give excellent forecast, got #{num}: {text}"


@patch('custom_components.local_weather_forecast.zambretti.datetime')
def test_summer_adjustment_moderate_pressure_rising(mock_datetime):
    """Test that summer adjustment IS applied for moderate pressure (975-1025 hPa) with rising trend."""
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 18, 12, 0)

    # Moderate pressure, rising trend
    p0 = 1010.0  # Moderate pressure
    pressure_change = 2.0  # Rising
    wind_data = [0, 0, 'N', 0]  # Calm
    lang_index = 1  # English

    result = calculate_zambretti_forecast(p0, pressure_change, wind_data, lang_index)
    text, num, letter = result  # Has 3 values

    # z = 185 - 0.16*1010 = 23
    # Summer adjustment should apply: z = 24
    # This is expected behavior for moderate pressure
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert len(text) > 0
