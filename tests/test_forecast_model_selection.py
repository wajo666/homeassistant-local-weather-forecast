"""Test forecast model selection functionality."""
import pytest
from unittest.mock import Mock, MagicMock

from custom_components.local_weather_forecast.const import (
    FORECAST_MODEL_ENHANCED,
    FORECAST_MODEL_ZAMBRETTI,
    FORECAST_MODEL_NEGRETTI,
)
from custom_components.local_weather_forecast.forecast_calculator import (
    ForecastCalculator,
    HourlyForecastGenerator,
    DailyForecastGenerator,
    PressureModel,
    TemperatureModel,
    ZambrettiForecaster,
)


def create_mock_hass():
    """Create a mock HomeAssistant instance with states."""
    mock_hass = MagicMock()
    mock_hass.states = MagicMock()
    mock_hass.states.get = MagicMock(return_value=None)
    # Mock config with real latitude/longitude for continentality calculation
    mock_hass.config = MagicMock()
    mock_hass.config.latitude = 48.0
    mock_hass.config.longitude = 17.0
    return mock_hass


class TestForecastModelIntegration:
    """Test forecast model selection in integration."""

    def test_hourly_generator_with_zambretti_model(self):
        """Test hourly generator with Zambretti model."""
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

        assert generator.forecast_model == FORECAST_MODEL_ZAMBRETTI
        forecasts = generator.generate(hours_count=24, interval_hours=1)
        assert len(forecasts) > 0

    def test_hourly_generator_with_negretti_model(self):
        """Test hourly generator with Negretti model."""
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

        assert generator.forecast_model == FORECAST_MODEL_NEGRETTI
        forecasts = generator.generate(hours_count=24, interval_hours=1)
        assert len(forecasts) > 0

    def test_hourly_generator_with_enhanced_model(self):
        """Test hourly generator with Enhanced model (default)."""
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

        assert generator.forecast_model == FORECAST_MODEL_ENHANCED
        forecasts = generator.generate(hours_count=24, interval_hours=1)
        assert len(forecasts) > 0

    def test_default_model_is_enhanced(self):
        """Test that default model is ENHANCED when not specified."""
        mock_hass = create_mock_hass()
        pressure_model = PressureModel(1015.0, 0.0)
        temp_model = TemperatureModel(10.0, 0.0)
        zambretti = ZambrettiForecaster(hass=mock_hass, latitude=50.0)

        generator = HourlyForecastGenerator(
            hass=mock_hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=0,
            wind_speed=0.0,
            latitude=50.0,
        )

        assert generator.forecast_model == FORECAST_MODEL_ENHANCED


class TestDailyForecastWithModel:
    """Test daily forecast generation with different models."""

    def test_daily_generator_with_different_models(self):
        """Test that daily generator works with different models."""
        mock_hass = create_mock_hass()
        pressure_model = PressureModel(1015.0, -2.0)
        temp_model = TemperatureModel(10.0, 0.5)
        zambretti = ZambrettiForecaster(hass=mock_hass, latitude=50.0)

        hourly_gen = HourlyForecastGenerator(
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

        daily_gen = DailyForecastGenerator(hourly_gen)
        forecasts = daily_gen.generate(days=5)

        assert len(forecasts) == 5
        assert all("datetime" in f for f in forecasts)
        assert all("templow" in f for f in forecasts)
        assert all("temperature" in f for f in forecasts)


class TestForecastCalculatorAPI:
    """Test ForecastCalculator API with model selection."""

    def test_generate_daily_forecast_with_zambretti(self):
        """Test daily forecast generation with Zambretti model."""
        mock_hass = create_mock_hass()

        forecasts = ForecastCalculator.generate_daily_forecast(
            hass=mock_hass,
            current_pressure=1015.0,
            current_temp=10.0,
            pressure_change_3h=-2.0,
            temp_change_1h=0.5,
            wind_direction=180,
            wind_speed=5.0,
            latitude=50.0,
            days=5,
            forecast_model=FORECAST_MODEL_ZAMBRETTI,
        )

        assert len(forecasts) == 5
        assert all(isinstance(f, dict) for f in forecasts)

    def test_generate_daily_forecast_with_negretti(self):
        """Test daily forecast generation with Negretti model."""
        mock_hass = create_mock_hass()

        forecasts = ForecastCalculator.generate_daily_forecast(
            hass=mock_hass,
            current_pressure=1020.0,
            current_temp=15.0,
            pressure_change_3h=1.0,
            temp_change_1h=0.2,
            wind_direction=90,
            wind_speed=3.0,
            latitude=50.0,
            days=3,
            forecast_model=FORECAST_MODEL_NEGRETTI,
        )

        assert len(forecasts) == 3
        assert all(isinstance(f, dict) for f in forecasts)

    def test_generate_daily_forecast_with_enhanced(self):
        """Test daily forecast generation with Enhanced model."""
        mock_hass = create_mock_hass()

        forecasts = ForecastCalculator.generate_daily_forecast(
            hass=mock_hass,
            current_pressure=1010.0,
            current_temp=12.0,
            pressure_change_3h=-1.5,
            temp_change_1h=0.3,
            wind_direction=270,
            wind_speed=6.0,
            latitude=50.0,
            days=7,
            forecast_model=FORECAST_MODEL_ENHANCED,
        )

        assert len(forecasts) == 7
        assert all(isinstance(f, dict) for f in forecasts)

    def test_generate_hourly_forecast_with_model(self):
        """Test hourly forecast generation respects model."""
        mock_hass = create_mock_hass()

        forecasts = ForecastCalculator.generate_hourly_forecast(
            hass=mock_hass,
            current_pressure=1015.0,
            current_temp=10.0,
            pressure_change_3h=-2.0,
            temp_change_1h=0.5,
            wind_direction=180,
            wind_speed=5.0,
            latitude=50.0,
            hours=24,
            forecast_model=FORECAST_MODEL_NEGRETTI,
        )

        assert len(forecasts) == 25  # 0-24 hours inclusive
        assert all(isinstance(f, dict) for f in forecasts)

    def test_default_model_used_when_not_specified(self):
        """Test that default model (ENHANCED) is used when not specified."""
        mock_hass = create_mock_hass()

        # Not specifying forecast_model should use ENHANCED
        forecasts = ForecastCalculator.generate_daily_forecast(
            hass=mock_hass,
            current_pressure=1013.0,
            current_temp=10.0,
            pressure_change_3h=0.0,
            temp_change_1h=0.0,
            wind_direction=0,
            wind_speed=0.0,
            latitude=50.0,
            days=3,
        )

        assert len(forecasts) == 3




