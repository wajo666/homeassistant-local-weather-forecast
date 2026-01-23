"""Test forecast code to condition mapping."""
import pytest
from custom_components.local_weather_forecast.forecast_mapping import (
    forecast_code_to_condition
)


class TestForecastCodeToCondition:
    """Test forecast code to weather condition mapping."""

    def test_code_7_partlycloudy(self):
        """Test Code 7 (Showery Later) at 1025 hPa → partlycloudy."""
        # Code 7: High pressure falling, showers later
        # Currently: Fair weather
        result = forecast_code_to_condition(7, is_night=False, temperature=15.0)
        assert result == "partlycloudy"

    def test_code_17_rainy(self):
        """Test Code 17 (Unsettled, Rain Later) at 1008 hPa → rainy."""
        # Code 17: Low pressure falling, unsettled conditions
        # "Unsettled" at 1008 hPa = already wet, not just cloudy
        result = forecast_code_to_condition(17, is_night=False, temperature=15.0)
        assert result == "rainy"

    def test_code_20_rainy(self):
        """Test Code 20 (Rain At Times, Worse Later) at 1000 hPa → rainy."""
        # Code 20: Low pressure, already raining
        result = forecast_code_to_condition(20, is_night=False, temperature=15.0)
        assert result == "rainy"

    def test_cloudy_range(self):
        """Test cloudy codes (11-14)."""
        for code in [11, 12, 13, 14]:
            result = forecast_code_to_condition(code, is_night=False, temperature=15.0)
            assert result == "cloudy", f"Code {code} should be cloudy"

    def test_rainy_range(self):
        """Test rainy codes (15-19, 23)."""
        rainy_codes = [15, 16, 17, 18, 19, 23]
        for code in rainy_codes:
            result = forecast_code_to_condition(code, is_night=False, temperature=15.0)
            assert result == "rainy", f"Code {code} should be rainy"

    def test_pressure_progression(self):
        """Test logical progression: high→partly, mid→rainy, low→rainy."""
        # Code 7: ~1025 hPa → partlycloudy (still fair)
        assert forecast_code_to_condition(7, False, 15.0) == "partlycloudy"

        # Code 17: ~1008 hPa → rainy (unsettled = wet)
        assert forecast_code_to_condition(17, False, 15.0) == "rainy"

        # Code 20: ~1000 hPa → rainy (definitely wet)
        assert forecast_code_to_condition(20, False, 15.0) == "rainy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
