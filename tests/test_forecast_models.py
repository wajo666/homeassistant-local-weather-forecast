"""Tests for forecast_models.py module."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from custom_components.local_weather_forecast.forecast_models import (
    DailyForecastGenerator,
    HourlyForecastGenerator,
    PressureModel,
    TemperatureModel,
)


class TestPressureModel:
    """Test PressureModel class."""

    def test_init(self):
        """Test PressureModel initialization."""
        model = PressureModel(current_pressure=1013.25, pressure_change_3h=3.0)

        assert model.current == 1013.25
        assert model.change_3h == 3.0
        assert model.change_per_hour == 1.0  # 3.0 / 3

    def test_predict_zero_hours(self):
        """Test prediction at current time (0 hours)."""
        model = PressureModel(current_pressure=1013.25, pressure_change_3h=3.0)

        assert model.predict(0) == 1013.25

    def test_predict_linear_short_term(self):
        """Test linear prediction for first 6 hours."""
        model = PressureModel(current_pressure=1010.0, pressure_change_3h=3.0)

        # After 3 hours: +3 hPa
        assert model.predict(3) == pytest.approx(1013.0, abs=0.1)

        # After 6 hours: +6 hPa
        assert model.predict(6) == pytest.approx(1016.0, abs=0.1)

    def test_predict_exponential_decay_long_term(self):
        """Test exponential decay for 6-24 hours."""
        model = PressureModel(current_pressure=1010.0, pressure_change_3h=3.0)

        # After 12 hours: less than +12 hPa due to decay
        result_12h = model.predict(12)
        assert result_12h > 1010.0
        assert result_12h < 1022.0  # Would be 1022 without decay

    def test_predict_max_change_limit(self):
        """Test that change is limited to ±20 hPa."""
        # Extreme rising pressure
        model = PressureModel(current_pressure=1010.0, pressure_change_3h=30.0)
        result = model.predict(24)

        # Should be clamped to +20 hPa
        assert result <= 1030.0

    def test_predict_absolute_limits(self):
        """Test absolute pressure limits (950-1050 hPa)."""
        # Test lower limit
        model_low = PressureModel(current_pressure=960.0, pressure_change_3h=-30.0)
        result_low = model_low.predict(24)
        assert result_low >= 950.0

        # Test upper limit
        model_high = PressureModel(current_pressure=1040.0, pressure_change_3h=30.0)
        result_high = model_high.predict(24)
        assert result_high <= 1050.0

    def test_get_trend_rising(self):
        """Test trend detection for rising pressure."""
        model = PressureModel(current_pressure=1010.0, pressure_change_3h=6.0)

        trend = model.get_trend(3)
        assert trend == "rising"

    def test_get_trend_falling(self):
        """Test trend detection for falling pressure."""
        model = PressureModel(current_pressure=1020.0, pressure_change_3h=-6.0)

        trend = model.get_trend(3)
        assert trend == "falling"

    def test_get_trend_steady(self):
        """Test trend detection for steady pressure."""
        model = PressureModel(current_pressure=1013.0, pressure_change_3h=0.5)

        trend = model.get_trend(3)
        assert trend == "steady"


class TestTemperatureModel:
    """Test TemperatureModel class."""

    def test_init(self):
        """Test TemperatureModel initialization."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        model = TemperatureModel(
            current_temp=20.0,
            temp_change_1h=0.5,
            current_time=now
        )

        assert model.current == 20.0
        assert model.change_1h == 0.5
        assert model.time == now

    def test_predict_zero_hours(self):
        """Test prediction at current time (0 hours)."""
        model = TemperatureModel(current_temp=20.0, temp_change_1h=0.5)

        assert model.predict(0) == 20.0

    def test_predict_with_trend(self):
        """Test prediction with warming trend."""
        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        model = TemperatureModel(
            current_temp=15.0,
            temp_change_1h=1.0,
            current_time=now
        )

        # After 2 hours: should be warmer (with decay)
        result = model.predict(2)
        assert result > 15.0
        assert result < 17.0  # Less than +2°C due to decay

    def test_predict_diurnal_cycle(self):
        """Test diurnal cycle component."""
        # Morning (06:00)
        morning = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        model_morning = TemperatureModel(
            current_temp=10.0,
            temp_change_1h=0.0,
            current_time=morning
        )

        # Predict to afternoon (14:00) - should be warmer
        result_afternoon = model_morning.predict(8)
        assert result_afternoon > 10.0

    def test_predict_max_change_limit(self):
        """Test maximum change limit (±12°C per 24h)."""
        model = TemperatureModel(
            current_temp=20.0,
            temp_change_1h=2.0  # Very strong warming
        )

        result = model.predict(24)

        # Change should be limited to ~12°C
        assert abs(result - 20.0) <= 12.5

    def test_calculate_diurnal_effect_peak(self):
        """Test diurnal effect calculation at peak (14:00)."""
        model = TemperatureModel(current_temp=20.0, temp_change_1h=0.0)

        # From 14:00 to 14:00 (same hour)
        effect = model._calculate_diurnal_effect(14, 14)
        assert effect == pytest.approx(0.0, abs=0.1)

    def test_calculate_diurnal_effect_minimum(self):
        """Test diurnal effect from peak to minimum."""
        model = TemperatureModel(current_temp=20.0, temp_change_1h=0.0)

        # From 14:00 (peak) to 04:00 (minimum) - should be negative
        effect = model._calculate_diurnal_effect(14, 4)
        assert effect < 0

    def test_predict_multi_day(self):
        """Test prediction for multiple days."""
        model = TemperatureModel(current_temp=20.0, temp_change_1h=0.5)

        # After 48 hours
        result = model.predict(48)

        # Should still be within reasonable range
        assert -10 <= result <= 50


class TestHourlyForecastGenerator:
    """Test HourlyForecastGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = Mock()
        self.mock_zambretti = Mock()

        # Mock Zambretti to return predictable results
        self.mock_zambretti.forecast.return_value = ("Fine weather", 2, "B")

        self.pressure_model = PressureModel(1013.25, 0.0)

        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.temp_model = TemperatureModel(20.0, 0.0, now)

    def test_init(self):
        """Test HourlyForecastGenerator initialization."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti,
            wind_direction=180,
            wind_speed=5.0,
            latitude=48.0
        )

        assert generator.hass == self.mock_hass
        assert generator.pressure == self.pressure_model
        assert generator.temperature == self.temp_model
        assert generator.wind_dir == 180
        assert generator.wind_speed == 5.0

    def test_generate_basic(self):
        """Test basic hourly forecast generation."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        forecasts = generator.generate(hours_count=6, interval_hours=1)

        assert len(forecasts) == 7  # 0, 1, 2, 3, 4, 5, 6

        for forecast in forecasts:
            assert "datetime" in forecast
            assert "condition" in forecast
            assert "temperature" in forecast
            assert "pressure" in forecast
            assert "precipitation_probability" in forecast

    def test_generate_with_interval(self):
        """Test hourly forecast with 3-hour intervals."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        forecasts = generator.generate(hours_count=12, interval_hours=3)

        assert len(forecasts) == 5  # 0, 3, 6, 9, 12

    def test_map_to_condition_storm(self):
        """Test condition mapping for storm."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        condition = generator._map_to_condition(25, "Stormy, much rain")
        assert condition == "lightning-rainy"

    def test_map_to_condition_rain(self):
        """Test condition mapping for rain."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        condition = generator._map_to_condition(20, "Rain at times")
        assert condition == "rainy"

    def test_map_to_condition_pouring(self):
        """Test condition mapping for heavy rain."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        condition = generator._map_to_condition(22, "Heavy rain")
        assert condition == "pouring"

    def test_map_to_condition_sunny(self):
        """Test condition mapping for sunny."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        condition = generator._map_to_condition(0, "Settled fine")
        assert condition == "sunny"

    def test_map_to_condition_partlycloudy(self):
        """Test condition mapping for partly cloudy."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        condition = generator._map_to_condition(10, "Changeable")
        assert condition == "partlycloudy"

    def test_calculate_rain_probability_low(self):
        """Test rain probability calculation for low chance."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        prob = generator._calculate_rain_probability(2, 1020.0, "rising")
        assert 0 <= prob <= 20

    def test_calculate_rain_probability_medium(self):
        """Test rain probability calculation for medium chance."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        prob = generator._calculate_rain_probability(10, 1010.0, "steady")
        assert 20 <= prob <= 70

    def test_calculate_rain_probability_high(self):
        """Test rain probability calculation for high chance."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        prob = generator._calculate_rain_probability(22, 990.0, "falling")
        assert prob >= 60

    def test_calculate_rain_probability_pressure_adjustment(self):
        """Test rain probability pressure adjustments."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        # Low pressure increases probability
        prob_low = generator._calculate_rain_probability(10, 990.0, "steady")
        prob_normal = generator._calculate_rain_probability(10, 1013.0, "steady")

        assert prob_low > prob_normal

    def test_calculate_rain_probability_trend_adjustment(self):
        """Test rain probability trend adjustments."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        # Falling pressure increases probability
        prob_falling = generator._calculate_rain_probability(10, 1013.0, "falling")
        prob_rising = generator._calculate_rain_probability(10, 1013.0, "rising")

        assert prob_falling > prob_rising

    def test_calculate_rain_probability_clamped(self):
        """Test that rain probability is clamped to 0-100."""
        generator = HourlyForecastGenerator(
            self.mock_hass,
            self.pressure_model,
            self.temp_model,
            self.mock_zambretti
        )

        # Should never exceed 100
        prob_max = generator._calculate_rain_probability(25, 980.0, "falling")
        assert 0 <= prob_max <= 100

        # Should never go below 0
        prob_min = generator._calculate_rain_probability(0, 1040.0, "rising")
        assert 0 <= prob_min <= 100


class TestDailyForecastGenerator:
    """Test DailyForecastGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = Mock()
        self.mock_zambretti = Mock()
        self.mock_zambretti.forecast.return_value = ("Fine weather", 2, "B")

        pressure_model = PressureModel(1013.25, 0.0)

        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        temp_model = TemperatureModel(20.0, 0.0, now)

        self.hourly_gen = HourlyForecastGenerator(
            self.mock_hass,
            pressure_model,
            temp_model,
            self.mock_zambretti
        )

    def test_init(self):
        """Test DailyForecastGenerator initialization."""
        generator = DailyForecastGenerator(self.hourly_gen)

        assert generator.hourly == self.hourly_gen

    def test_generate_basic(self):
        """Test basic daily forecast generation."""
        generator = DailyForecastGenerator(self.hourly_gen)

        forecasts = generator.generate(days_count=3)

        assert len(forecasts) == 3

        for forecast in forecasts:
            assert "datetime" in forecast
            assert "condition" in forecast
            assert "temperature" in forecast  # High
            assert "templow" in forecast  # Low
            assert "precipitation_probability" in forecast

    def test_generate_temperature_range(self):
        """Test that daily forecast includes temperature range."""
        generator = DailyForecastGenerator(self.hourly_gen)

        forecasts = generator.generate(days_count=1)

        assert len(forecasts) == 1
        # High should be >= Low
        assert forecasts[0]["temperature"] >= forecasts[0]["templow"]

    def test_get_dominant_condition_empty(self):
        """Test dominant condition with empty list."""
        generator = DailyForecastGenerator(self.hourly_gen)

        condition = generator._get_dominant_condition([])
        assert condition == "partlycloudy"

    def test_get_dominant_condition_single(self):
        """Test dominant condition with single condition."""
        generator = DailyForecastGenerator(self.hourly_gen)

        hourly_points = [{"condition": "sunny"}]
        condition = generator._get_dominant_condition(hourly_points)

        assert condition == "sunny"

    def test_get_dominant_condition_majority(self):
        """Test dominant condition picks most common."""
        generator = DailyForecastGenerator(self.hourly_gen)

        hourly_points = [
            {"condition": "sunny"},
            {"condition": "sunny"},
            {"condition": "sunny"},
            {"condition": "rainy"},
            {"condition": "rainy"},
            {"condition": "partlycloudy"},
        ]

        condition = generator._get_dominant_condition(hourly_points)
        assert condition == "sunny"  # Most common (3 occurrences)

    def test_generate_precipitation_probability_average(self):
        """Test that daily precipitation probability is averaged."""
        generator = DailyForecastGenerator(self.hourly_gen)

        # Mock hourly generator to return specific probabilities
        with patch.object(self.hourly_gen, 'generate') as mock_generate:
            # Create hourly forecasts with known probabilities
            now = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
            mock_generate.return_value = [
                {
                    "datetime": (now + timedelta(hours=i)).isoformat(),
                    "condition": "sunny",
                    "temperature": 20.0,
                    "precipitation_probability": 50  # All 50%
                }
                for i in range(24)
            ]

            forecasts = generator.generate(days_count=1)

            # Average of all 50% should be 50%
            assert forecasts[0]["precipitation_probability"] == 50


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_forecast_workflow(self):
        """Test complete forecast generation workflow."""
        mock_hass = Mock()
        mock_zambretti = Mock()
        mock_zambretti.forecast.return_value = ("Fine weather", 2, "B")

        # Create models
        pressure = PressureModel(current_pressure=1013.25, pressure_change_3h=1.5)

        now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        temp = TemperatureModel(current_temp=20.0, temp_change_1h=0.3, current_time=now)

        # Create generators
        hourly = HourlyForecastGenerator(
            mock_hass, pressure, temp, mock_zambretti,
            wind_direction=180, wind_speed=5.0, latitude=48.0
        )

        daily = DailyForecastGenerator(hourly)

        # Generate forecasts
        hourly_forecasts = hourly.generate(hours_count=24)
        daily_forecasts = daily.generate(days_count=3)

        # Verify results
        assert len(hourly_forecasts) == 25  # 0-24 inclusive
        assert len(daily_forecasts) == 3

        # All forecasts should have required fields
        for h in hourly_forecasts:
            assert all(key in h for key in ["datetime", "condition", "temperature", "pressure"])

        for d in daily_forecasts:
            assert all(key in d for key in ["datetime", "condition", "temperature", "templow"])

    def test_pressure_trend_affects_rain_probability(self):
        """Test that pressure trends affect rain probability in forecasts."""
        mock_hass = Mock()
        mock_zambretti = Mock()
        mock_zambretti.forecast.return_value = ("Changeable", 10, "J")

        # Falling pressure
        pressure_falling = PressureModel(1020.0, -6.0)
        temp = TemperatureModel(20.0, 0.0)

        hourly_falling = HourlyForecastGenerator(
            mock_hass, pressure_falling, temp, mock_zambretti
        )

        # Rising pressure
        pressure_rising = PressureModel(1005.0, 6.0)

        hourly_rising = HourlyForecastGenerator(
            mock_hass, pressure_rising, temp, mock_zambretti
        )

        # Generate forecasts
        forecast_falling = hourly_falling.generate(hours_count=6)
        forecast_rising = hourly_rising.generate(hours_count=6)

        # Falling pressure should generally have higher rain probability
        avg_rain_falling = sum(f["precipitation_probability"] for f in forecast_falling) / len(forecast_falling)
        avg_rain_rising = sum(f["precipitation_probability"] for f in forecast_rising) / len(forecast_rising)

        assert avg_rain_falling > avg_rain_rising


class TestUniversalConditionMapping:
    """Test universal map_forecast_to_condition() function for all forecast models."""

    def test_zambretti_storm(self):
        """Test storm detection for Zambretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Stormy, much rain",
            forecast_num=25,
            source="Zambretti"
        )
        assert condition == "lightning-rainy"

    def test_negretti_storm(self):
        """Test storm detection for Negretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Thunder and gale",
            forecast_num=None,
            source="Negretti"
        )
        assert condition == "lightning-rainy"

    def test_zambretti_heavy_rain(self):
        """Test heavy rain (pouring) for Zambretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Heavy rain",
            forecast_num=22,
            source="Zambretti"
        )
        assert condition == "pouring"

    def test_negretti_rain(self):
        """Test rain detection for Negretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Polooblačno, miestami dážď.",
            forecast_num=10,
            source="Negretti"
        )
        assert condition == "rainy"

    def test_zambretti_fair_day(self):
        """Test fair weather during day for Zambretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Settled fine",
            forecast_num=0,
            is_night_func=lambda: False,
            source="Zambretti"
        )
        assert condition == "sunny"

    def test_zambretti_fair_night(self):
        """Test fair weather during night for Zambretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Settled fine",
            forecast_num=0,
            is_night_func=lambda: True,
            source="Zambretti"
        )
        assert condition == "clear-night"

    def test_negretti_fair_day(self):
        """Test fair weather during day for Negretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Pekné počasie!",
            forecast_num=1,
            is_night_func=lambda: False,
            source="Negretti"
        )
        assert condition == "sunny"

    def test_negretti_fair_night(self):
        """Test fair weather during night for Negretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Stabilne pekné počasie!",
            forecast_num=0,
            is_night_func=lambda: True,
            source="Negretti"
        )
        assert condition == "clear-night"

    def test_zambretti_unsettled_day(self):
        """Test unsettled weather during day for Zambretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        # Test text WITHOUT rain keywords -> partlycloudy
        condition = map_forecast_to_condition(
            forecast_text="Unsettled weather",
            forecast_num=17,
            is_night_func=lambda: False,
            source="Zambretti"
        )
        assert condition == "partlycloudy"

    def test_zambretti_unsettled_night(self):
        """Test unsettled weather during night for Zambretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Changeable",
            forecast_num=16,
            is_night_func=lambda: True,
            source="Zambretti"
        )
        assert condition == "clear-night"

    def test_negretti_partly_cloudy(self):
        """Test partly cloudy for Negretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Polooblačno",
            forecast_num=5,
            is_night_func=lambda: False,
            source="Negretti"
        )
        assert condition == "partlycloudy"

    def test_negretti_cloudy(self):
        """Test fully cloudy for Negretti."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Oblačno, zamračené",
            forecast_num=8,
            source="Negretti"
        )
        assert condition == "cloudy"

    def test_combined_forecast_rainy(self):
        """Test Combined forecast rain detection."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Rain at times, later worse",
            forecast_num=None,
            source="Combined"
        )
        assert condition == "rainy"

    def test_default_fallback_day(self):
        """Test default fallback during day."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Unknown forecast",
            forecast_num=None,
            is_night_func=lambda: False,
            source="Test"
        )
        assert condition == "partlycloudy"

    def test_default_fallback_night(self):
        """Test default fallback during night."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Unknown forecast",
            forecast_num=None,
            is_night_func=lambda: True,
            source="Test"
        )
        assert condition == "clear-night"

    def test_slovak_keywords(self):
        """Test Slovak language keywords work correctly."""
        from custom_components.local_weather_forecast.forecast_models import map_forecast_to_condition

        # Test Slovak rain
        condition_rain = map_forecast_to_condition(
            forecast_text="Dážď a zrážky",
            source="Slovak"
        )
        assert condition_rain == "rainy"

        # Test Slovak cloudy
        condition_cloudy = map_forecast_to_condition(
            forecast_text="Zamračené",
            source="Slovak"
        )
        assert condition_cloudy == "cloudy"

        # Test Slovak fair
        condition_fair = map_forecast_to_condition(
            forecast_text="Pekné slnečné počasie",
            is_night_func=lambda: False,
            source="Slovak"
        )
        assert condition_fair == "sunny"

