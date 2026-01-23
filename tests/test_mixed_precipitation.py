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
        """Test rain codes return rainy regardless of temperature.

        Temperature-based conversion is disabled - only rain sensor determines
        actual precipitation type (rain/snow/mixed).
        """
        # Code 15 = Some Rain → rainy
        result = forecast_code_to_condition(15, is_night=False, temperature=10.0)
        assert result == "rainy"

        # Same result at freezing temperature (conversion disabled)
        result = forecast_code_to_condition(15, is_night=False, temperature=0.0)
        assert result == "rainy"

        # Code 18 = Rain At Times → rainy
        result = forecast_code_to_condition(18, is_night=False, temperature=-5.0)
        assert result == "rainy"

    def test_lightning_stays_unchanged(self):
        """Test lightning-rainy stays regardless of temperature."""
        # Code 25 = Stormy → lightning-rainy
        result = forecast_code_to_condition(25, is_night=False, temperature=-5.0)
        assert result == "lightning-rainy"

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
        # Code 15 = Some Rain, no temp → rainy
        result = forecast_code_to_condition(15, is_night=False, temperature=None)
        assert result == "rainy"

        # Code 20 = Rain At Times, Worse Later → rainy
        result = forecast_code_to_condition(20, is_night=False, temperature=None)
        assert result == "rainy"

        # Code 24 = Stormy → pouring
        result = forecast_code_to_condition(24, is_night=False, temperature=None)
        assert result == "pouring"

    def test_pouring_code(self):
        """Test pouring code returns pouring."""
        # Code 24 = Stormy, Improving → pouring
        result = forecast_code_to_condition(24, is_night=False, temperature=10.0)
        assert result == "pouring"

        result = forecast_code_to_condition(24, is_night=False, temperature=-10.0)
        assert result == "pouring"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
