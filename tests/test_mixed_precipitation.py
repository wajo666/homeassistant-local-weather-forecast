"""Test forecast code to condition mapping.

CURRENT BEHAVIOR:
- Forecast codes map to conditions based on pressure and weather patterns
- Temperature-based snow conversion is DISABLED (handled by rain sensor priority)
- See CODE_TO_CONDITION_SCIENTIFIC_VALIDATION.md for scientific validation
"""
import pytest
from custom_components.local_weather_forecast.forecast_mapping import (
    forecast_code_to_condition
)


class TestForecastConditionMapping:
    """Test forecast code to condition mapping (without temperature conversion)."""

    def test_rain_codes_stay_rainy(self):
        """Test rain codes return correct condition based on timeframe.

        NEW (v3.1.16):
        - Threshold lowered from 80% to 70% (code 16+ is rainy)
        - Code 15: 65% → cloudy (below threshold)
        - Codes 16+: 70%+ → rainy (above threshold)
        - Current state WITH rain sensor: cloudy (sensor determines rain)
        - Current state WITHOUT rain sensor: rainy (show forecast icon)
        """
        # Code 15 = Some Rain (65% probability) → cloudy (below 70% threshold)
        result = forecast_code_to_condition(15, is_night=False, temperature=10.0, is_current_state=True)
        assert result == "cloudy"

        # Same code for forecast → still cloudy
        result = forecast_code_to_condition(15, is_night=False, temperature=0.0, is_current_state=False)
        assert result == "cloudy"

        # Code 18 = Rain At Times (80% probability) → rainy
        # For CURRENT state WITHOUT rain sensor: show forecast icon (rainy)
        result_current = forecast_code_to_condition(18, is_night=False, temperature=-5.0, is_current_state=True, has_rain_sensor=False)
        assert result_current == "rainy"  # Current without sensor: show forecast icon

        # At -5°C, rain is converted to snow for forecast
        result_forecast = forecast_code_to_condition(18, is_night=False, temperature=-5.0, is_current_state=False)
        assert result_forecast == "snowy"  # Forecast: predicted snow (T ≤ 2°C)

    def test_lightning_stays_unchanged(self):
        """Test lightning-rainy is converted to snowy at low temperatures."""
        # Code 25 = Stormy → lightning-rainy, but converted to snowy at -5°C
        result = forecast_code_to_condition(25, is_night=False, temperature=-5.0)
        assert result == "snowy"

        result = forecast_code_to_condition(25, is_night=False, temperature=15.0)
        assert result == "lightning-rainy"

    def test_cloudy_no_conversion(self):
        """Test cloudy conditions stay cloudy."""
        # Code 13 = Cloudy → stays cloudy
        result = forecast_code_to_condition(13, is_night=False, temperature=-5.0)
        assert result == "cloudy"

        # Code 14 = Cloudy (showery) → stays cloudy
        result = forecast_code_to_condition(14, is_night=False, temperature=0.0)
        assert result == "cloudy"

    def test_no_temperature_provided(self):
        """Test behavior when temperature is None."""
        # Code 15 = Some Rain (later), no temp → cloudy (not raining yet)
        result = forecast_code_to_condition(15, is_night=False, temperature=None)
        assert result == "cloudy"

        # Code 20 = Rain At Times, Worse Later → rainy (for FORECAST)
        result_forecast = forecast_code_to_condition(20, is_night=False, temperature=None, is_current_state=False)
        assert result_forecast == "rainy"

        # Code 24 = Stormy → pouring (for FORECAST)
        result_forecast = forecast_code_to_condition(24, is_night=False, temperature=None, is_current_state=False)
        assert result_forecast == "pouring"

    def test_pouring_code(self):
        """Test pouring code returns pouring."""
        # Code 24 = Stormy, Improving → pouring
        result = forecast_code_to_condition(24, is_night=False, temperature=10.0)
        assert result == "pouring"

        # At -10°C, snow conversion changes pouring → snowy
        result = forecast_code_to_condition(24, is_night=False, temperature=-10.0)
        assert result == "snowy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
