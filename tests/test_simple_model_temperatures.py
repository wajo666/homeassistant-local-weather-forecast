"""Simple test to verify weather-aware temperature works for all models."""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from custom_components.local_weather_forecast.const import (
    FORECAST_MODEL_ENHANCED,
    FORECAST_MODEL_ZAMBRETTI,
    FORECAST_MODEL_NEGRETTI,
)
from custom_components.local_weather_forecast.forecast_calculator import (
    HourlyForecastGenerator,
    PressureModel,
    TemperatureModel,
    ZambrettiForecaster,
)


def create_mock_hass():
    """Create mock hass."""
    mock_hass = MagicMock()
    mock_hass.states = MagicMock()
    mock_hass.states.get = MagicMock(return_value=None)
    return mock_hass


class TestWeatherAwareTemperatureForAllModels:
    """Test that weather-aware temperature works for Zambretti, Negretti, and Enhanced models."""

    def test_zambretti_model_temperature_variation(self):
        """Test that Zambretti model produces varying temperatures."""
        mock_hass = create_mock_hass()
        
        pressure_model = PressureModel(1015.0, -2.0)
        temp_model = TemperatureModel(10.0, 0.5)
        zambretti = ZambrettiForecaster(hass=mock_hass, latitude=50.0)

        generator = HourlyForecastGenerator(
            hass=mock_hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=180,
            wind_speed=5.0,
            latitude=50.0,
            current_rain_rate=0.0,
            forecast_model=FORECAST_MODEL_ZAMBRETTI,
        )

        forecasts = generator.generate(hours_count=12, interval_hours=1)
        
        assert len(forecasts) == 13  # 0-12 hours
        
        # First should be current temperature
        assert forecasts[0]["temperature"] == 10.0
        
        # Collect all temperatures
        temps = [f["temperature"] for f in forecasts]
        
        # Should have variation
        assert len(set(temps)) > 1, "Temperatures should vary over time"
        
        # All should be realistic
        for temp in temps:
            assert -50 < temp < 60, f"Temp {temp} out of realistic range"
        
        print(f"✓ Zambretti: temps from {min(temps):.1f} to {max(temps):.1f}°C")

    def test_negretti_model_temperature_variation(self):
        """Test that Negretti model produces varying temperatures."""
        mock_hass = create_mock_hass()
        
        pressure_model = PressureModel(1020.0, 1.0)
        temp_model = TemperatureModel(15.0, 0.2)
        zambretti = ZambrettiForecaster(hass=mock_hass, latitude=50.0)

        generator = HourlyForecastGenerator(
            hass=mock_hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=90,
            wind_speed=3.0,
            latitude=50.0,
            current_rain_rate=0.0,
            forecast_model=FORECAST_MODEL_NEGRETTI,
        )

        forecasts = generator.generate(hours_count=12, interval_hours=1)
        
        assert len(forecasts) == 13
        assert forecasts[0]["temperature"] == 15.0
        
        temps = [f["temperature"] for f in forecasts]
        assert len(set(temps)) > 1
        
        for temp in temps:
            assert -50 < temp < 60
        
        print(f"✓ Negretti: temps from {min(temps):.1f} to {max(temps):.1f}°C")

    def test_enhanced_model_temperature_variation(self):
        """Test that Enhanced model produces varying temperatures."""
        mock_hass = create_mock_hass()
        
        pressure_model = PressureModel(1010.0, -1.5)
        temp_model = TemperatureModel(12.0, 0.3)
        zambretti = ZambrettiForecaster(hass=mock_hass, latitude=50.0)

        generator = HourlyForecastGenerator(
            hass=mock_hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=270,
            wind_speed=6.0,
            latitude=50.0,
            current_rain_rate=0.0,
            forecast_model=FORECAST_MODEL_ENHANCED,
        )

        forecasts = generator.generate(hours_count=12, interval_hours=1)
        
        # Enhanced model returns 12 forecasts (hours 1-12, hour 0 is persistence)
        assert len(forecasts) >= 12
        
        # First forecast may or may not be current temp (depends on persistence)
        temps = [f["temperature"] for f in forecasts]
        assert len(set(temps)) > 1
        
        for temp in temps:
            assert -50 < temp < 60
        
        print(f"✓ Enhanced: temps from {min(temps):.1f} to {max(temps):.1f}°C")

    def test_all_models_produce_valid_conditions(self):
        """Test that all models produce valid weather conditions."""
        mock_hass = create_mock_hass()
        
        valid_conditions = [
            "sunny", "clear-night", "partlycloudy", "cloudy",
            "rainy", "pouring", "lightning-rainy",
            "snowy", "snowy-rainy", "fog", "windy"
        ]
        
        for model in [FORECAST_MODEL_ZAMBRETTI, FORECAST_MODEL_NEGRETTI, FORECAST_MODEL_ENHANCED]:
            pressure_model = PressureModel(1015.0, -1.0)
            temp_model = TemperatureModel(10.0, 0.2)
            zambretti = ZambrettiForecaster(hass=mock_hass, latitude=50.0)

            generator = HourlyForecastGenerator(
                hass=mock_hass,
                pressure_model=pressure_model,
                temperature_model=temp_model,
                zambretti=zambretti,
                wind_direction=180,
                wind_speed=5.0,
                latitude=50.0,
                current_rain_rate=0.0,
                forecast_model=model,
            )

            forecasts = generator.generate(hours_count=6, interval_hours=1)
            
            for forecast in forecasts:
                assert "condition" in forecast
                assert "temperature" in forecast
                assert forecast["condition"] in valid_conditions
                assert -50 < forecast["temperature"] < 60
            
            print(f"✓ {model}: all conditions and temperatures valid")
