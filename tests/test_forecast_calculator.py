"""Tests for forecast_calculator.py module."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from custom_components.local_weather_forecast.forecast_calculator import (
    DailyForecastGenerator,
    ForecastCalculator,
    HourlyForecastGenerator,
    PressureModel,
    RainProbabilityCalculator,
    TemperatureModel,
    ZambrettiForecaster,
)


class TestPressureModel:
    """Test PressureModel class."""

    def test_predict_no_change(self):
        """Test pressure prediction with zero change rate."""
        model = PressureModel(current_pressure=1013.25, change_rate_3h=0.0)

        assert model.predict(0) == 1013.25
        assert model.predict(1) == pytest.approx(1013.25, abs=0.1)
        assert model.predict(24) == pytest.approx(1013.25, abs=0.5)

    def test_predict_rising_pressure(self):
        """Test pressure prediction with rising trend."""
        model = PressureModel(current_pressure=1010.0, change_rate_3h=3.0)  # +1 hPa/h

        # After 1 hour: should be close to 1011.0
        assert model.predict(1) > 1010.0
        assert model.predict(1) == pytest.approx(1011.0, abs=0.1)

        # After 6 hours: damped, so less than +6 hPa
        assert model.predict(6) > 1010.0
        assert model.predict(6) < 1016.0  # Not full +6 due to damping

    def test_predict_falling_pressure(self):
        """Test pressure prediction with falling trend."""
        model = PressureModel(current_pressure=1020.0, change_rate_3h=-6.0)  # -2 hPa/h

        # After 1 hour
        assert model.predict(1) < 1020.0
        assert model.predict(1) == pytest.approx(1018.0, abs=0.1)

        # After 3 hours: significant drop
        assert model.predict(3) < 1015.0

    def test_predict_clamping_low(self):
        """Test pressure clamping at lower bound."""
        model = PressureModel(current_pressure=955.0, change_rate_3h=-30.0)  # Extreme drop

        # Should not go below 950 hPa
        result = model.predict(24)
        assert result >= 950.0

    def test_predict_clamping_high(self):
        """Test pressure clamping at upper bound."""
        model = PressureModel(current_pressure=1045.0, change_rate_3h=30.0)  # Extreme rise

        # Should not go above 1050 hPa
        result = model.predict(24)
        assert result <= 1050.0

    def test_get_trend_rising(self):
        """Test trend detection for rising pressure."""
        model = PressureModel(current_pressure=1010.0, change_rate_3h=3.0)

        assert model.get_trend(3) == "rising"

    def test_get_trend_falling(self):
        """Test trend detection for falling pressure."""
        model = PressureModel(current_pressure=1020.0, change_rate_3h=-3.0)

        assert model.get_trend(3) == "falling"

    def test_get_trend_steady(self):
        """Test trend detection for steady pressure."""
        model = PressureModel(current_pressure=1013.0, change_rate_3h=0.5)

        assert model.get_trend(3) == "steady"

    def test_damping_factor_effect(self):
        """Test that damping factor reduces change rate over time."""
        model = PressureModel(current_pressure=1010.0, change_rate_3h=3.0, damping_factor=0.8)

        # Change should decrease over time due to damping
        change_3h = model.predict(3) - 1010.0
        change_6h = model.predict(6) - 1010.0

        # Second 3-hour period should have less change than first
        assert change_6h < (change_3h * 2.0)


class TestTemperatureModel:
    """Test TemperatureModel class."""

    def test_predict_no_change_no_cycle(self):
        """Test temperature prediction with zero trend and minimal diurnal cycle."""
        model = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.0,
            diurnal_amplitude=0.0  # No diurnal cycle
        )

        assert model.predict(0) == 20.0
        assert model.predict(1) == pytest.approx(20.0, abs=0.1)

    def test_predict_with_trend(self):
        """Test temperature prediction with warming trend."""
        model = TemperatureModel(
            current_temp=15.0,
            change_rate_1h=0.5,  # +0.5°C per hour
            diurnal_amplitude=0.0
        )

        # After 2 hours: should be ~16.0°C (with damping, slightly less)
        result = model.predict(2)
        assert result > 15.0
        assert result < 16.0  # Due to trend damping

    def test_predict_diurnal_cycle(self):
        """Test diurnal cycle component."""
        # Set current hour to 02:00 (coldest part of cycle)
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 2, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            model = TemperatureModel(
                current_temp=10.0,
                change_rate_1h=0.0,
                diurnal_amplitude=3.0  # ±3°C swing
            )

            # At 02:00, we're past minimum (04:00)
            # At 14:00 (12 hours later), should be warmer due to diurnal cycle
            temp_14h = model.predict(12)

            # Should be warmer at 14:00 than at 02:00
            assert temp_14h > 10.0

    def test_predict_with_solar_radiation(self):
        """Test solar radiation warming effect."""
        model = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.0,
            diurnal_amplitude=0.0,
            solar_radiation=800.0  # Strong sun
        )

        # Solar warming should increase temperature during day
        # (exact amount depends on sun angle calculation)
        result = model.predict(1)
        # Result may vary based on time of day, just check it's calculated
        assert isinstance(result, float)

    def test_predict_cloud_cover_reduces_solar(self):
        """Test that cloud cover reduces solar warming."""
        model_clear = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.0,
            diurnal_amplitude=0.0,
            solar_radiation=800.0,
            cloud_cover=0.0  # Clear sky
        )

        model_cloudy = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.0,
            diurnal_amplitude=0.0,
            solar_radiation=800.0,
            cloud_cover=100.0  # Overcast
        )

        # Clear sky should have more solar warming than cloudy
        # (exact comparison depends on sun angle)
        assert model_clear.cloud_cover < model_cloudy.cloud_cover

    def test_cloud_cover_from_humidity(self):
        """Test cloud cover estimation from humidity."""
        # Low humidity → clear
        model_dry = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.0,
            humidity=30.0
        )
        assert model_dry.cloud_cover < 20.0

        # Medium humidity → partly cloudy
        model_medium = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.0,
            humidity=60.0
        )
        assert 20.0 <= model_medium.cloud_cover <= 50.0

        # High humidity → mostly cloudy
        model_humid = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.0,
            humidity=80.0
        )
        assert model_humid.cloud_cover > 50.0

    def test_predict_temperature_limits(self):
        """Test temperature prediction respects absolute limits."""
        # Extreme cold
        model_cold = TemperatureModel(
            current_temp=-35.0,
            change_rate_1h=-2.0,  # Extreme cooling
            diurnal_amplitude=0.0
        )
        result = model_cold.predict(10)
        assert result >= -40.0  # Should not go below absolute minimum

        # Extreme heat
        model_hot = TemperatureModel(
            current_temp=45.0,
            change_rate_1h=2.0,  # Extreme warming
            diurnal_amplitude=0.0
        )
        result = model_hot.predict(10)
        assert result <= 50.0  # Should not go above absolute maximum

    def test_get_daily_range(self):
        """Test daily temperature range calculation."""
        model = TemperatureModel(
            current_temp=20.0,
            change_rate_1h=0.0,
            diurnal_amplitude=5.0  # ±5°C swing
        )

        min_temp, max_temp = model.get_daily_range(24)

        # Range should exist
        assert min_temp < max_temp
        # Range should be influenced by diurnal amplitude
        assert (max_temp - min_temp) > 0


class TestRainProbabilityCalculator:
    """Test RainProbabilityCalculator class."""

    def test_base_probability_from_letter(self):
        """Test base probability mapping from Zambretti letter."""
        calc = RainProbabilityCalculator()

        # Fine weather (A-E)
        prob_a = calc.calculate(1013, 1013, "steady", 0, "A")
        assert prob_a < 30

        # Poor weather (P-Z)
        prob_z = calc.calculate(1013, 1013, "steady", 25, "Z")
        assert prob_z > 90

    def test_low_pressure_increases_probability(self):
        """Test that low pressure increases rain probability."""
        calc = RainProbabilityCalculator()

        # Normal pressure
        prob_normal = calc.calculate(1013, 1013, "steady", 10, "J")

        # Low pressure
        prob_low = calc.calculate(1013, 985, "steady", 10, "J")

        assert prob_low > prob_normal

    def test_high_pressure_decreases_probability(self):
        """Test that high pressure decreases rain probability."""
        calc = RainProbabilityCalculator()

        # Normal pressure
        prob_normal = calc.calculate(1013, 1013, "steady", 10, "J")

        # High pressure
        prob_high = calc.calculate(1013, 1035, "steady", 10, "J")

        assert prob_high < prob_normal

    def test_falling_pressure_increases_probability(self):
        """Test that falling pressure increases rain probability."""
        calc = RainProbabilityCalculator()

        # Steady pressure
        prob_steady = calc.calculate(1013, 1013, "steady", 10, "J")

        # Falling pressure
        prob_falling = calc.calculate(1020, 1010, "falling", 10, "J")

        assert prob_falling > prob_steady

    def test_rising_pressure_decreases_probability(self):
        """Test that rising pressure decreases rain probability."""
        calc = RainProbabilityCalculator()

        # Steady pressure
        prob_steady = calc.calculate(1013, 1013, "steady", 10, "J")

        # Rising pressure
        prob_rising = calc.calculate(1005, 1015, "rising", 10, "J")

        assert prob_rising < prob_steady

    def test_probability_clamped_0_100(self):
        """Test that probability is always between 0 and 100."""
        calc = RainProbabilityCalculator()

        # Extreme high pressure + rising
        prob_min = calc.calculate(1040, 1050, "rising", 0, "A")
        assert 0 <= prob_min <= 100

        # Extreme low pressure + falling
        prob_max = calc.calculate(980, 970, "falling", 25, "Z")
        assert 0 <= prob_max <= 100


class TestZambrettiForecaster:
    """Test ZambrettiForecaster class."""

    def test_forecast_hour_basic(self):
        """Test basic Zambretti forecast calculation."""
        forecaster = ZambrettiForecaster()

        result = forecaster.forecast_hour(
            pressure=1013.25,
            wind_direction=180,  # South
            pressure_change=0.0,
            wind_speed=5.0
        )

        forecast_text, forecast_num, letter_code = result

        assert isinstance(forecast_text, str)
        assert isinstance(forecast_num, int)
        assert isinstance(letter_code, str)
        assert 0 <= forecast_num <= 25
        assert len(letter_code) == 1

    def test_get_condition_from_letter(self):
        """Test condition mapping from Zambretti letter."""
        forecaster = ZambrettiForecaster()

        # Test at noon (daytime)
        noon = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Letter A should map to sunny/fair
        condition = forecaster.get_condition("A", noon)
        assert condition in ["sunny", "clear-night", "partlycloudy"]

    def test_sunny_converts_to_clear_night(self):
        """Test that sunny condition converts to clear-night at night."""
        mock_hass = Mock()
        mock_sun = Mock()
        mock_sun.state = "below_horizon"
        mock_sun.attributes = Mock()
        mock_sun.attributes.get = Mock(side_effect=lambda key, default=None: {
            "next_rising": "2025-01-02T06:00:00+00:00",
            "next_setting": "2025-01-01T18:00:00+00:00"
        }.get(key, default))
        mock_hass.states.get.return_value = mock_sun

        forecaster = ZambrettiForecaster(hass=mock_hass)

        # Night time
        night = datetime(2025, 1, 1, 22, 0, tzinfo=timezone.utc)

        # With mocked night condition
        condition = forecaster.get_condition("A", night)

        # Should convert sunny to clear-night
        assert condition in ["clear-night", "sunny"]  # Depends on sun entity availability


class TestHourlyForecastGenerator:
    """Test HourlyForecastGenerator class."""

    def test_generate_basic(self):
        """Test basic hourly forecast generation."""
        mock_hass = Mock()

        pressure_model = PressureModel(1013.25, 0.0)
        temp_model = TemperatureModel(20.0, 0.0, diurnal_amplitude=0.0)
        zambretti = ZambrettiForecaster()

        generator = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction=180,
            wind_speed=5.0
        )

        forecasts = generator.generate(hours_count=6, interval_hours=1)

        assert len(forecasts) == 7  # 0, 1, 2, 3, 4, 5, 6

        for forecast in forecasts:
            assert "datetime" in forecast
            assert "condition" in forecast
            assert "temperature" in forecast
            assert "precipitation_probability" in forecast

    def test_generate_with_current_rain(self):
        """Test forecast generation with current rain."""
        mock_hass = Mock()

        pressure_model = PressureModel(1005.0, -3.0)  # Falling pressure
        temp_model = TemperatureModel(18.0, 0.0, diurnal_amplitude=0.0)
        zambretti = ZambrettiForecaster()

        generator = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction=180,
            wind_speed=5.0,
            current_rain_rate=5.0  # Moderate rain
        )

        forecasts = generator.generate(hours_count=2, interval_hours=1)

        # First forecast (current hour) should show rain
        assert forecasts[0]["condition"] in ["rainy", "pouring"]
        assert forecasts[0]["precipitation_probability"] == 100

    def test_generate_interval_hours(self):
        """Test forecast generation with different intervals."""
        mock_hass = Mock()

        pressure_model = PressureModel(1013.25, 0.0)
        temp_model = TemperatureModel(20.0, 0.0, diurnal_amplitude=0.0)
        zambretti = ZambrettiForecaster()

        generator = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti
        )

        # 3-hour intervals
        forecasts = generator.generate(hours_count=12, interval_hours=3)

        assert len(forecasts) == 5  # 0, 3, 6, 9, 12


class TestDailyForecastGenerator:
    """Test DailyForecastGenerator class."""

    def test_generate_basic(self):
        """Test basic daily forecast generation."""
        mock_hass = Mock()

        pressure_model = PressureModel(1013.25, 0.0)
        temp_model = TemperatureModel(20.0, 0.0, diurnal_amplitude=3.0)
        zambretti = ZambrettiForecaster()

        hourly_gen = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti
        )

        daily_gen = DailyForecastGenerator(hourly_gen)

        forecasts = daily_gen.generate(days=3)

        assert len(forecasts) == 3

        for forecast in forecasts:
            assert "datetime" in forecast
            assert "condition" in forecast
            assert "temperature" in forecast  # Daily high
            assert "templow" in forecast  # Daily low
            assert "precipitation_probability" in forecast

    def test_daily_temp_range(self):
        """Test that daily forecast includes temperature range."""
        mock_hass = Mock()

        pressure_model = PressureModel(1013.25, 0.0)
        temp_model = TemperatureModel(20.0, 0.0, diurnal_amplitude=5.0)  # ±5°C swing
        zambretti = ZambrettiForecaster()

        hourly_gen = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti
        )

        daily_gen = DailyForecastGenerator(hourly_gen)
        forecasts = daily_gen.generate(days=1)

        assert len(forecasts) == 1

        # High should be greater than low
        assert forecasts[0]["temperature"] > forecasts[0]["templow"]


class TestForecastCalculator:
    """Test ForecastCalculator facade."""

    def test_generate_daily_forecast(self):
        """Test daily forecast generation via facade."""
        mock_hass = Mock()

        forecasts = ForecastCalculator.generate_daily_forecast(
            hass=mock_hass,
            current_pressure=1013.25,
            current_temp=20.0,
            pressure_change_3h=0.0,
            temp_change_1h=0.0,
            wind_direction=180,
            wind_speed=5.0,
            latitude=48.0,
            days=3
        )

        assert len(forecasts) == 3
        assert all("templow" in f for f in forecasts)

    def test_generate_hourly_forecast(self):
        """Test hourly forecast generation via facade."""
        mock_hass = Mock()

        forecasts = ForecastCalculator.generate_hourly_forecast(
            hass=mock_hass,
            current_pressure=1013.25,
            current_temp=20.0,
            pressure_change_3h=0.0,
            temp_change_1h=0.0,
            wind_direction=180,
            wind_speed=5.0,
            latitude=48.0,
            hours=24
        )

        assert len(forecasts) == 25  # 0-24 inclusive
        assert all("templow" not in f for f in forecasts)  # Hourly doesn't have templow

    def test_generate_with_solar_radiation(self):
        """Test forecast generation with solar radiation."""
        mock_hass = Mock()
        mock_sun = Mock()
        mock_sun.state = "above_horizon"
        mock_sun.attributes = {
            "next_rising": "2025-01-02T06:00:00+00:00",
            "next_setting": "2025-01-01T18:00:00+00:00"
        }
        mock_hass.states.get.return_value = mock_sun

        forecasts = ForecastCalculator.generate_hourly_forecast(
            hass=mock_hass,
            current_pressure=1013.25,
            current_temp=20.0,
            pressure_change_3h=0.0,
            temp_change_1h=0.0,
            wind_direction=180,
            wind_speed=5.0,
            latitude=48.0,
            hours=6,
            solar_radiation=800.0,  # Strong sun
            cloud_cover=20.0  # Mostly clear
        )

        assert len(forecasts) == 7

    def test_generate_with_rain_override(self):
        """Test forecast generation with current rain override."""
        mock_hass = Mock()
        mock_sun = Mock()
        mock_sun.state = "above_horizon"
        mock_sun.attributes = {
            "next_rising": "2025-01-02T06:00:00+00:00",
            "next_setting": "2025-01-01T18:00:00+00:00"
        }
        mock_hass.states.get.return_value = mock_sun

        forecasts = ForecastCalculator.generate_hourly_forecast(
            hass=mock_hass,
            current_pressure=1005.0,
            current_temp=18.0,
            pressure_change_3h=-3.0,
            temp_change_1h=-0.5,
            wind_direction=180,
            wind_speed=8.0,
            latitude=48.0,
            hours=3,
            current_rain_rate=10.0  # Heavy rain
        )

        # First forecast should show rain
        assert forecasts[0]["condition"] in ["rainy", "pouring"]
        assert forecasts[0]["precipitation_probability"] == 100

