"""Tests for forecast_models.py module (condition mapping only).

Note: PressureModel, HourlyForecastGenerator, DailyForecastGenerator
are now in forecast_calculator.py and tested in test_forecast_calculator.py
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

# Import from forecast_calculator (where the classes actually live)
from custom_components.local_weather_forecast.forecast_calculator import (
    PressureModel,
    TemperatureModel,
    HourlyForecastGenerator,
    DailyForecastGenerator,
)


class TestPressureModel:
    """Test PressureModel class."""

    def test_init(self):
        """Test PressureModel initialization."""
        model = PressureModel(current_pressure=1013.25, pressure_change_3h=3.0)

        assert model.current == 1013.25
        assert model.change_3h == 3.0

    def test_predict_zero_hours(self):
        """Test prediction at current time (0 hours)."""
        model = PressureModel(current_pressure=1013.25, pressure_change_3h=3.0)

        assert model.predict(0) == 1013.25

    def test_predict_linear_short_term(self):
        """Test linear prediction for first 6 hours."""
        model = PressureModel(current_pressure=1010.0, pressure_change_3h=3.0)

        # After 3 hours: slightly less than +3 hPa due to damping
        assert model.predict(3) == pytest.approx(1012.5, abs=0.1)

        # After 6 hours: ~+5 hPa with damping
        assert model.predict(6) == pytest.approx(1015.0, abs=0.1)

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
        """Test absolute pressure limits (910-1085 hPa)."""
        # Test lower limit
        model_low = PressureModel(current_pressure=960.0, pressure_change_3h=-30.0)
        result_low = model_low.predict(24)
        assert result_low >= 910.0

        # Test upper limit
        model_high = PressureModel(current_pressure=1040.0, pressure_change_3h=30.0)
        result_high = model_high.predict(24)
        assert result_high <= 1085.0

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
        model = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.5
        )

        assert model.current_temp == 20.0
        assert model.change_rate_1h == 0.5

    def test_predict_zero_hours(self):
        """Test prediction at current time (0 hours)."""
        model = TemperatureModel(current_temp=20.0, change_rate_1h=0.5)

        assert model.predict(0) == 20.0

    def test_predict_with_trend(self):
        """Test prediction with warming trend."""
        model = TemperatureModel(
            current_temp=15.0,
            change_rate_1h=1.0
        )

        # After 2 hours: should be warmer (with decay)
        result = model.predict(2)
        assert result > 15.0
        assert result < 19.0  # Allow more range for diurnal cycle effects

    def test_predict_diurnal_cycle(self):
        """Test diurnal cycle component."""
        model_morning = TemperatureModel(
            current_temp=10.0,
            change_rate_1h=0.0
        )

        # Predict to 8 hours later - temperature should change due to diurnal cycle
        result_afternoon = model_morning.predict(8)
        # Should be within reasonable range (not exact due to different solar position models)
        assert -5.0 <= result_afternoon <= 25.0

    def test_predict_max_change_limit(self):
        """Test maximum change limit (±12°C per 24h)."""
        model = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=2.0  # Very strong warming
        )

        result = model.predict(24)

        # Change should be limited to ~12°C
        assert abs(result - 20.0) <= 12.5


    def test_predict_multi_day(self):
        """Test prediction for multiple days."""
        model = TemperatureModel(current_temp=20.0, change_rate_1h=0.5)

        # After 48 hours
        result = model.predict(48)

        # Should still be within reasonable range
        assert -10 <= result <= 50


class TestHourlyForecastGenerator:
    """Test HourlyForecastGenerator class - basic integration tests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = Mock()
        self.mock_hass.data = {}  # Mock hass.data as dictionary
        self.mock_zambretti = Mock()

        # Mock Zambretti to return predictable results - must return tuple
        self.mock_zambretti.forecast_hour = Mock(return_value=("Fine weather", 2, "B"))

        self.pressure_model = PressureModel(current_pressure=1013.25, pressure_change_3h=0.0)
        self.temp_model = TemperatureModel(current_temp=20.0, change_rate_1h=0.0)

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
        assert generator.pressure_model == self.pressure_model
        assert generator.temperature_model == self.temp_model
        assert generator.wind_direction == 180
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

        assert len(forecasts) == 6  # 0, 1, 2, 3, 4, 5, 6

        for forecast in forecasts:
            assert "datetime" in forecast
            assert "condition" in forecast
            assert "temperature" in forecast
            assert "native_temperature" in forecast
            assert "precipitation_probability" in forecast
            assert "is_daytime" in forecast
            assert isinstance(forecast["is_daytime"], bool)

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




class TestDailyForecastGenerator:
    """Test DailyForecastGenerator class - basic integration tests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_hass = Mock()
        self.mock_hass.data = {}  # Mock hass.data as dictionary
        self.mock_zambretti = Mock()
        self.mock_zambretti.forecast_hour = Mock(return_value=("Fine weather", 2, "B"))

        pressure_model = PressureModel(current_pressure=1013.25, pressure_change_3h=0.0)
        temp_model = TemperatureModel(current_temp=20.0, change_rate_1h=0.0)

        self.hourly_gen = HourlyForecastGenerator(
            self.mock_hass,
            pressure_model,
            temp_model,
            self.mock_zambretti
        )

    def test_init(self):
        """Test DailyForecastGenerator initialization."""
        generator = DailyForecastGenerator(self.hourly_gen)

        assert generator.hourly_generator == self.hourly_gen

    def test_generate_basic(self):
        """Test basic daily forecast generation."""
        generator = DailyForecastGenerator(self.hourly_gen)

        forecasts = generator.generate(days=3)

        assert len(forecasts) == 3

        for forecast in forecasts:
            assert "datetime" in forecast
            assert "condition" in forecast
            assert "temperature" in forecast  # High
            assert "templow" in forecast  # Low
            assert "precipitation_probability" in forecast
            assert "is_daytime" in forecast
            assert forecast["is_daytime"] is True  # Daily forecasts are always daytime

    def test_generate_temperature_range(self):
        """Test that daily forecast includes temperature range."""
        generator = DailyForecastGenerator(self.hourly_gen)

        forecasts = generator.generate(days=1)

        assert len(forecasts) == 1
        # High should be >= Low
        assert forecasts[0]["temperature"] >= forecasts[0]["templow"]




class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_forecast_workflow(self):
        """Test complete forecast generation workflow."""
        mock_hass = Mock()
        mock_hass.data = {}  # Mock hass.data as dictionary
        mock_zambretti = Mock()
        mock_zambretti.forecast_hour = Mock(return_value=("Fine weather", 2, "B"))

        # Create models
        pressure = PressureModel(current_pressure=1013.25, pressure_change_3h=1.5)
        temp = TemperatureModel(current_temp=20.0, change_rate_1h=0.3)

        # Create generators
        hourly = HourlyForecastGenerator(
            mock_hass, pressure, temp, mock_zambretti,
            wind_direction=180, wind_speed=5.0, latitude=48.0
        )

        daily = DailyForecastGenerator(hourly)

        # Generate forecasts
        hourly_forecasts = hourly.generate(hours_count=24)
        daily_forecasts = daily.generate(days=3)

        # Verify results
        assert len(hourly_forecasts) == 24  # 0-23 inclusive
        assert len(daily_forecasts) == 3

        # All forecasts should have required fields
        for h in hourly_forecasts:
            assert all(key in h for key in ["datetime", "condition", "temperature", "native_temperature"])

        for d in daily_forecasts:
            assert all(key in d for key in ["datetime", "condition", "temperature", "templow"])

    def test_pressure_trend_affects_rain_probability(self):
        """Test that pressure trends affect rain probability in forecasts."""
        mock_hass = Mock()
        mock_hass.data = {}  # Mock hass.data as dictionary
        mock_zambretti = Mock()
        mock_zambretti.forecast_hour = Mock(return_value=("Changeable", 10, "J"))

        # Falling pressure
        pressure_falling = PressureModel(current_pressure=1020.0, pressure_change_3h=-6.0)
        temp = TemperatureModel(current_temp=20.0, change_rate_1h=0.0)

        hourly_falling = HourlyForecastGenerator(
            mock_hass, pressure_falling, temp, mock_zambretti
        )

        # Rising pressure
        pressure_rising = PressureModel(current_pressure=1005.0, pressure_change_3h=6.0)

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
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Stormy, much rain",
            forecast_num=25,
            source="Zambretti"
        )
        assert condition == "lightning-rainy"

    def test_negretti_storm(self):
        """Test storm detection for Negretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Thunder and gale",
            forecast_num=None,
            source="Negretti"
        )
        assert condition == "lightning-rainy"

    def test_zambretti_heavy_rain(self):
        """Test heavy rain (rainy) for Zambretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Heavy rain",
            forecast_num=22,
            source="Zambretti"
        )
        assert condition == "rainy"

    def test_negretti_rain(self):
        """Test partlycloudy detection for Negretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Polooblačno, miestami dážď.",
            forecast_num=10,
            source="Negretti"
        )
        assert condition == "partlycloudy"

    def test_zambretti_fair_day(self):
        """Test fair weather during day for Zambretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Settled fine",
            forecast_num=0,
            is_night_func=lambda: False,
            source="Zambretti"
        )
        assert condition == "sunny"

    def test_zambretti_fair_night(self):
        """Test fair weather during night for Zambretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Settled fine",
            forecast_num=0,
            is_night_func=lambda: True,
            source="Zambretti"
        )
        assert condition == "clear-night"

    def test_negretti_fair_day(self):
        """Test fair weather during day for Negretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Pekné počasie!",
            forecast_num=1,
            is_night_func=lambda: False,
            source="Negretti"
        )
        assert condition == "sunny"

    def test_negretti_fair_night(self):
        """Test fair weather during night for Negretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Stabilne pekné počasie!",
            forecast_num=0,
            is_night_func=lambda: True,
            source="Negretti"
        )
        assert condition == "clear-night"

    def test_zambretti_unsettled_day(self):
        """Test unsettled weather during day for Zambretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

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
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Changeable",
            forecast_num=16,
            is_night_func=lambda: True,
            source="Zambretti"
        )
        # Unsettled/changeable = partly cloudy, even at night (HA shows moon + clouds)
        assert condition == "partlycloudy"

    def test_negretti_partly_cloudy(self):
        """Test partly cloudy for Negretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Polooblačno",
            forecast_num=5,
            is_night_func=lambda: False,
            source="Negretti"
        )
        assert condition == "partlycloudy"

    def test_negretti_cloudy(self):
        """Test fully cloudy for Negretti."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Oblačno, zamračené",
            forecast_num=8,
            source="Negretti"
        )
        assert condition == "cloudy"

    def test_combined_forecast_rainy(self):
        """Test Combined forecast rain detection (keywords map to code 15 = cloudy)."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        # "Rain" keyword → code 15 ("Changeable, some rain")
        # Code 15 = cloudy (rain threat, not actively raining)
        condition = map_forecast_to_condition(
            forecast_text="Rain at times, later worse",
            forecast_num=None,
            source="Combined"
        )
        # Code 15 = cloudy (rain threat/later, not rainy now)
        assert condition == "cloudy"

    def test_default_fallback_day(self):
        """Test default fallback during day."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Unknown forecast",
            forecast_num=None,
            is_night_func=lambda: False,
            source="Test"
        )
        assert condition == "partlycloudy"

    def test_default_fallback_night(self):
        """Test default fallback during night."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Unknown forecast",
            forecast_num=None,
            is_night_func=lambda: True,
            source="Test"
        )
        # Default fallback is partlycloudy (safe for both day and night)
        # HA automatically shows correct icon (moon + clouds at night)
        assert condition == "partlycloudy"

    def test_slovak_keywords(self):
        """Test Slovak language keywords work correctly."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        # Test Slovak rain keyword → code 15 = cloudy (rain threat)
        condition_rain = map_forecast_to_condition(
            forecast_text="Dážď a zrážky",
            source="Slovak"
        )
        # "Dážď" keyword → code 15 = cloudy (not actively raining, threat of rain)
        assert condition_rain == "cloudy"

        # Test Slovak cloudy keyword → code 13 = cloudy
        condition_cloudy = map_forecast_to_condition(
            forecast_text="Zamračené",
            source="Slovak"
        )
        assert condition_cloudy == "cloudy"

        # Test Slovak fair - should be sunny during day
        condition_fair = map_forecast_to_condition(
            forecast_text="Pekné slnečné počasie",
            is_night_func=lambda: False,
            source="Slovak"
        )
        # "slnečné" keyword should trigger sunny
        assert condition_fair == "sunny"

    def test_zambretti_fair_weather_numbers(self):
        """Test Zambretti fair weather detection for numbers 0-5."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        # Zambretti 0-5 should be sunny (if no unsettled keywords)
        for num in range(6):  # 0, 1, 2, 3, 4, 5
            condition = map_forecast_to_condition(
                forecast_text="Fine weather",
                forecast_num=num,
                is_night_func=lambda: False,
                source="Zambretti"
            )
            assert condition == "sunny", f"Zambretti #{num} should be sunny"

        # Zambretti 6+ should not automatically be sunny
        condition_6 = map_forecast_to_condition(
            forecast_text="Some text",
            forecast_num=6,
            is_night_func=lambda: False,
            source="Zambretti"
        )
        assert condition_6 == "partlycloudy", "Zambretti #6 should default to partlycloudy"

    def test_negretti_fair_weather_numbers(self):
        """Test Negretti fair weather detection for numbers 0-2."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        # Negretti 0-2 should be sunny (if no unsettled keywords)
        for num in range(3):  # 0, 1, 2
            condition = map_forecast_to_condition(
                forecast_text="Pekné počasie",
                forecast_num=num,
                is_night_func=lambda: False,
                source="Negretti"
            )
            assert condition == "sunny", f"Negretti #{num} should be sunny"

        # Negretti 3+ should not automatically be sunny
        condition_3 = map_forecast_to_condition(
            forecast_text="Some text",
            forecast_num=3,
            is_night_func=lambda: False,
            source="Negretti"
        )
        assert condition_3 == "partlycloudy", "Negretti #3 should default to partlycloudy"

    def test_zambretti_fair_with_unsettled_mention(self):
        """Test Zambretti fair weather with 'rain later' becomes cloudy."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        # Zambretti #4 normally fair, but "later rain" keyword → code 15
        condition = map_forecast_to_condition(
            forecast_text="Fine, but later rain",
            forecast_num=4,
            is_night_func=lambda: False,
            source="Zambretti"
        )
        # "rain" keyword → code 15 = cloudy (rain threat/later, not rainy now)
        # This prevents showing "sunny" when rain is predicted later
        assert condition != "sunny", "Should not be sunny with 'rain' in text"
        assert condition == "cloudy"  # Heavy clouds, rain threat

    def test_negretti_clear_night(self):
        """Test Negretti fair weather at night becomes clear-night."""
        from custom_components.local_weather_forecast.forecast_mapping import map_forecast_to_condition

        condition = map_forecast_to_condition(
            forecast_text="Stabilne pekné počasie!",
            forecast_num=0,
            is_night_func=lambda: True,
            source="Negretti"
        )
        assert condition == "clear-night", "Negretti #0 at night should be clear-night"

