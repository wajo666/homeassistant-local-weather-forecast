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

    def test_code_17_cloudy(self):
        """Test Code 17 (Unsettled, Rain LATER) → cloudy (not rainy yet)."""
        # Code 17: "Nestále, neskôr dážď" = Unsettled, rain LATER (3-6h)
        # Currently: Heavy clouds (rain threat), but NOT raining yet
        # Rain sensor determines if actually precipitating
        result = forecast_code_to_condition(17, is_night=False, temperature=15.0)
        assert result == "cloudy"  # Heavy clouds, rain comes LATER

    def test_code_20_rainy(self):
        """Test Code 20 (Rain At Times, Worse Later) at 1000 hPa → rainy."""
        # Code 20: "Občasný dážď, neskôr zhoršenie" = Rain NOW, worse later
        # For current state (0h): cloudy (rain sensor determines precipitation)
        # For forecast (1-24h): rainy (predicted active rain)
        result_current = forecast_code_to_condition(20, is_night=False, temperature=15.0, is_current_state=True)
        assert result_current == "cloudy"  # Current: sensor determines rain

        result_forecast = forecast_code_to_condition(20, is_night=False, temperature=15.0, is_current_state=False)
        assert result_forecast == "rainy"  # Forecast: predicted rain

    def test_cloudy_range(self):
        """Test cloudy codes (11-17) - unsettled weather with rain threat."""
        # 11-14: Unsettled/changeable
        # 15-17: Unsettled with "rain LATER" (not raining yet)
        for code in [11, 12, 13, 14, 15, 16, 17]:
            result = forecast_code_to_condition(code, is_night=False, temperature=15.0)
            assert result == "cloudy", f"Code {code} should be cloudy"

    def test_rainy_range(self):
        """Test rainy codes (18-23) - ACTIVE rain predictions for FORECAST."""
        # 18-23: "Rain at times", "Frequent rain", "Rain now"
        # For FORECAST (not current state): show predicted precipitation
        rainy_codes = [18, 19, 20, 21, 22, 23]
        for code in rainy_codes:
            result = forecast_code_to_condition(code, is_night=False, temperature=15.0, is_current_state=False)
            assert result == "rainy", f"Code {code} should be rainy for forecast"

    def test_pressure_progression(self):
        """Test logical progression: high→partly, mid→cloudy, low→rainy (forecast)."""
        # Code 7: ~1025 hPa → partlycloudy (still fair)
        assert forecast_code_to_condition(7, False, 15.0) == "partlycloudy"

        # Code 17: ~1008 hPa → cloudy (unsettled, rain LATER, not yet)
        assert forecast_code_to_condition(17, False, 15.0) == "cloudy"

        # Code 20: ~1000 hPa → rainy (for FORECAST, not current state)
        assert forecast_code_to_condition(20, False, 15.0, is_current_state=False) == "rainy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
