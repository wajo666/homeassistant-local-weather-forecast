"""Test anticyclone forecast accuracy after 3.1.8 fix."""
import pytest
from datetime import datetime, timezone

from custom_components.local_weather_forecast.forecast_calculator import (
    HourlyForecastGenerator,
    DailyForecastGenerator,
    PressureModel,
    TemperatureModel,
    ZambrettiForecaster,
    RainProbabilityCalculator,
)
from custom_components.local_weather_forecast.const import (
    FORECAST_MODEL_ENHANCED,
    FORECAST_MODEL_ZAMBRETTI,
    FORECAST_MODEL_NEGRETTI,
)


class TestAnticycloneForecast:
    """Test forecast accuracy in stable anticyclone conditions."""

    def test_enhanced_uses_negretti_in_stable_anticyclone(self, hass):
        """Test that Enhanced model gives priority to Negretti in stable anticyclone."""
        # Anticyclone conditions: high pressure, minimal change
        pressure = 1038.0  # High pressure
        pressure_change = 0.3  # Very stable (< 0.5 hPa)
        temperature = -5.0
        temp_change = -0.1

        # Create models
        pressure_model = PressureModel(pressure, pressure_change)
        temp_model = TemperatureModel(temperature, temp_change)
        zambretti = ZambrettiForecaster(hass=hass, latitude=48.7)

        # Create hourly generator with ENHANCED model
        hourly_gen = HourlyForecastGenerator(
            hass=hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=270,
            wind_speed=0.8,
            latitude=48.7,
            elevation=314.0,
            current_rain_rate=0.0,
            forecast_model=FORECAST_MODEL_ENHANCED
        )

        # Generate 6-hour forecast
        forecasts = hourly_gen.generate(hours_count=6, interval_hours=1)

        assert len(forecasts) > 0, "Should generate forecasts"

        # Check that rain probability is LOW in anticyclone
        for i, forecast in enumerate(forecasts):
            rain_prob = forecast.get("precipitation_probability", 100)

            # In stable anticyclone, rain probability should be < 10%
            assert rain_prob < 10, (
                f"Hour +{i}: Rain probability too high in anticyclone: {rain_prob}% "
                f"(should be < 10% for pressure={pressure} hPa, change={pressure_change} hPa)"
            )

            # Condition should be sunny or partlycloudy (not rainy!)
            condition = forecast.get("condition", "unknown")
            assert condition in ["sunny", "partlycloudy", "clear-night"], (
                f"Hour +{i}: Wrong condition in anticyclone: {condition} "
                f"(should be sunny/partlycloudy, not rainy)"
            )

    def test_rain_probability_reduction_in_anticyclone(self):
        """Test that rain probability is correctly reduced in high pressure."""
        calc = RainProbabilityCalculator()

        # Test case 1: Strong anticyclone (1038 hPa), stable
        result1 = calc.calculate(
            current_pressure=1037.0,
            future_pressure=1038.0,
            pressure_trend="steady",
            zambretti_code=1,  # "Fine weather"
            zambretti_letter="B"  # Base probability: 10%
        )

        # Should be significantly reduced:
        # Base 10% - 20% (anticyclone) - 15% (stable) = 0% (clamped)
        assert result1 <= 5, f"Strong anticyclone should have very low rain: {result1}%"

        # Test case 2: Very strong anticyclone (1040 hPa)
        result2 = calc.calculate(
            current_pressure=1039.0,
            future_pressure=1040.0,
            pressure_trend="steady",
            zambretti_code=0,  # "Settled fine"
            zambretti_letter="A"  # Base probability: 5%
        )

        # Should be near zero
        assert result2 <= 2, f"Very strong anticyclone should have minimal rain: {result2}%"

        # Test case 3: Moderate high pressure (1028 hPa)
        result3 = calc.calculate(
            current_pressure=1027.0,
            future_pressure=1028.0,
            pressure_trend="steady",
            zambretti_code=3,  # "Fine, becoming less settled"
            zambretti_letter="D"  # Base probability: 20%
        )

        # Should be reduced but not zero (20% - 15% = 5%)
        assert result3 < 15, f"Moderate high pressure should reduce rain: {result3}%"

    def test_daily_forecast_aggregation_in_anticyclone(self, hass):
        """Test that daily forecast correctly aggregates hourly anticyclone forecasts."""
        # Anticyclone conditions
        pressure = 1038.0
        pressure_change = 0.5  # Borderline stable
        temperature = -5.0
        temp_change = -0.1

        # Create models
        pressure_model = PressureModel(pressure, pressure_change)
        temp_model = TemperatureModel(temperature, temp_change)
        zambretti = ZambrettiForecaster(hass=hass, latitude=48.7)

        # Create generators
        hourly_gen = HourlyForecastGenerator(
            hass=hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=270,
            wind_speed=0.8,
            latitude=48.7,
            elevation=314.0,
            current_rain_rate=0.0,
            forecast_model=FORECAST_MODEL_ENHANCED
        )

        daily_gen = DailyForecastGenerator(hourly_gen)

        # Generate 3-day forecast
        daily_forecasts = daily_gen.generate(days=3)

        assert len(daily_forecasts) > 0, "Should generate daily forecasts"

        # Check first day (most accurate)
        first_day = daily_forecasts[0]
        daily_rain_prob = first_day.get("precipitation_probability", 100)

        # Daily average should also be low in anticyclone
        assert daily_rain_prob < 15, (
            f"Daily rain probability too high in anticyclone: {daily_rain_prob}% "
            f"(should be < 15% average)"
        )

        # Condition should be favorable
        daily_condition = first_day.get("condition", "unknown")
        assert daily_condition in ["sunny", "partlycloudy"], (
            f"Daily condition wrong in anticyclone: {daily_condition}"
        )

    def test_comparison_zambretti_vs_negretti_in_anticyclone(self, hass):
        """Test that Negretti is more accurate than Zambretti in stable conditions."""
        # Stable anticyclone
        pressure = 1038.0
        pressure_change = 0.2  # Very stable
        temperature = -5.0
        temp_change = -0.1

        # Create models
        pressure_model = PressureModel(pressure, pressure_change)
        temp_model = TemperatureModel(temperature, temp_change)
        zambretti = ZambrettiForecaster(hass=hass, latitude=48.7)

        # Test 1: Zambretti model (optimized for pressure changes)
        zambretti_gen = HourlyForecastGenerator(
            hass=hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=270,
            wind_speed=0.8,
            latitude=48.7,
            elevation=314.0,
            current_rain_rate=0.0,
            forecast_model=FORECAST_MODEL_ZAMBRETTI
        )

        zambretti_forecasts = zambretti_gen.generate(hours_count=6, interval_hours=1)
        zambretti_rain_avg = sum(
            f.get("precipitation_probability", 0) for f in zambretti_forecasts
        ) / len(zambretti_forecasts)

        # Test 2: Negretti model (optimized for stable conditions)
        negretti_gen = HourlyForecastGenerator(
            hass=hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=270,
            wind_speed=0.8,
            latitude=48.7,
            elevation=314.0,
            current_rain_rate=0.0,
            forecast_model=FORECAST_MODEL_NEGRETTI
        )

        negretti_forecasts = negretti_gen.generate(hours_count=6, interval_hours=1)
        negretti_rain_avg = sum(
            f.get("precipitation_probability", 0) for f in negretti_forecasts
        ) / len(negretti_forecasts)

        # Test 3: Enhanced model (should be close to Negretti in stable conditions)
        enhanced_gen = HourlyForecastGenerator(
            hass=hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            wind_direction=270,
            wind_speed=0.8,
            latitude=48.7,
            elevation=314.0,
            current_rain_rate=0.0,
            forecast_model=FORECAST_MODEL_ENHANCED
        )

        enhanced_forecasts = enhanced_gen.generate(hours_count=6, interval_hours=1)
        enhanced_rain_avg = sum(
            f.get("precipitation_probability", 0) for f in enhanced_forecasts
        ) / len(enhanced_forecasts)

        # Assertions
        # After Zambretti mapping fix (z=9 → F instead of X), both models should give LOW rain probability
        # in stable anticyclone
        assert zambretti_rain_avg < 15, (
            f"Zambretti rain probability too high in anticyclone: {zambretti_rain_avg:.1f}% "
            f"(should be < 15% after mapping fix)"
        )

        assert negretti_rain_avg < 15, (
            f"Negretti rain probability too high in anticyclone: {negretti_rain_avg:.1f}% "
            f"(should be < 15%)"
        )

        # Enhanced should be close to Negretti (90% weight in stable anticyclone)
        diff = abs(enhanced_rain_avg - negretti_rain_avg)
        assert diff < 5, (
            f"Enhanced should follow Negretti in stable conditions: "
            f"Enhanced={enhanced_rain_avg:.1f}% vs Negretti={negretti_rain_avg:.1f}% "
            f"(diff={diff:.1f}%)"
        )
