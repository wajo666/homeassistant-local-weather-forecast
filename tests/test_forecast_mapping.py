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
        """Test Code 17 (Unsettled, Rain LATER) → rainy (70% threshold)."""
        # Code 17: "Nestále, neskôr dážď" = Unsettled, rain LATER (75% probability)
        # NEW: Threshold lowered to 70%, so code 16+ is rainy
        # For forecast: Show predicted precipitation
        result = forecast_code_to_condition(17, is_night=False, temperature=15.0, is_current_state=False)
        assert result == "rainy"  # Forecast: predicted rain (75% probability)

    def test_code_20_rainy(self):
        """Test Code 20 (Rain At Times, Worse Later) at 1000 hPa → rainy."""
        # Code 20: "Občasný dážď, neskôr zhoršenie" = Rain NOW, worse later
        # For current state WITH rain sensor: cloudy (sensor determines precipitation)
        # For current state WITHOUT rain sensor: rainy (show forecast icon)
        # For forecast (1-24h): rainy (predicted active rain)
        result_current_with_sensor = forecast_code_to_condition(20, is_night=False, temperature=15.0, is_current_state=True, has_rain_sensor=True)
        assert result_current_with_sensor == "cloudy"  # Current with sensor: sensor determines rain

        result_current_no_sensor = forecast_code_to_condition(20, is_night=False, temperature=15.0, is_current_state=True, has_rain_sensor=False)
        assert result_current_no_sensor == "rainy"  # Current without sensor: show forecast icon

        result_forecast = forecast_code_to_condition(20, is_night=False, temperature=15.0, is_current_state=False)
        assert result_forecast == "rainy"  # Forecast: predicted rain

    def test_cloudy_range(self):
        """Test cloudy codes (11-15) - unsettled weather with rain threat."""
        # 11-14: Unsettled/changeable
        # 15: Changeable with some rain (65% probability) - still cloudy
        # NEW: Codes 16+ are rainy (70% threshold)
        for code in [11, 12, 13, 14, 15]:
            result = forecast_code_to_condition(code, is_night=False, temperature=15.0)
            assert result == "cloudy", f"Code {code} should be cloudy"

    def test_rainy_range(self):
        """Test rainy codes (16-23) - ACTIVE rain predictions for FORECAST."""
        # NEW: Threshold lowered from 18 to 16 (80% → 70%)
        # 16-23: "Rain", "Rain at times", "Frequent rain"
        # For FORECAST (not current state): show predicted precipitation
        rainy_codes = [16, 17, 18, 19, 20, 21, 22, 23]
        for code in rainy_codes:
            result = forecast_code_to_condition(code, is_night=False, temperature=15.0, is_current_state=False)
            assert result == "rainy", f"Code {code} should be rainy for forecast"

    def test_pressure_progression(self):
        """Test logical progression: high→partly, mid→cloudy, low→rainy (forecast)."""
        # Code 7: ~1025 hPa → partlycloudy (still fair)
        assert forecast_code_to_condition(7, False, 15.0) == "partlycloudy"

        # Code 15: ~1010 hPa → cloudy (unsettled, 65% rain)
        assert forecast_code_to_condition(15, False, 15.0) == "cloudy"

        # Code 17: ~1008 hPa → rainy (75% probability, above 70% threshold)
        assert forecast_code_to_condition(17, False, 15.0, is_current_state=False) == "rainy"

        # Code 20: ~1000 hPa → rainy (for FORECAST, not current state)
        assert forecast_code_to_condition(20, False, 15.0, is_current_state=False) == "rainy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
