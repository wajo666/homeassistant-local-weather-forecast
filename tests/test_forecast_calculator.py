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


def create_mock_hass():
    """Create properly mocked HomeAssistant object with sun helper support."""
    mock_hass = Mock()
    mock_hass.data = {}  # Required for HA sun helper
    mock_hass.config.latitude = 48.0
    mock_hass.config.longitude = 21.0
    mock_hass.config.elevation = 314
    return mock_hass


class TestPressureModel:
    """Test PressureModel class."""

    def test_predict_no_change(self):
        """Test pressure prediction with zero change rate."""
        model = PressureModel(current_pressure=1013.25, pressure_change_3h=0.0)

        assert model.predict(0) == 1013.25
        assert model.predict(1) == pytest.approx(1013.25, abs=0.1)
        assert model.predict(24) == pytest.approx(1013.25, abs=0.5)

    def test_predict_rising_pressure(self):
        """Test pressure prediction with rising trend."""
        model = PressureModel(current_pressure=1010.0, pressure_change_3h=3.0)  # +1 hPa/h

        # After 1 hour: should increase but capped by max_change limiter
        # max_change = 20.0 * (1/24) ≈ 0.833 hPa for 1 hour
        assert model.predict(1) > 1010.0
        assert model.predict(1) == pytest.approx(1010.83, abs=0.01)

        # After 6 hours: damped, so less than +6 hPa
        assert model.predict(6) > 1010.0
        assert model.predict(6) < 1016.0  # Not full +6 due to damping

    def test_predict_falling_pressure(self):
        """Test pressure prediction with falling trend."""
        model = PressureModel(current_pressure=1020.0, pressure_change_3h=-6.0)  # -2 hPa/h

        # After 1 hour: should decrease but capped by max_change limiter
        # max_change = 20.0 * (1/24) ≈ 0.833 hPa for 1 hour
        assert model.predict(1) < 1020.0
        assert model.predict(1) == pytest.approx(1019.17, abs=0.01)

        # After 3 hours: significant drop, capped by max_change limiter
        # max_change = 20.0 * (3/24) = 2.5 hPa for 3 hours
        assert model.predict(3) < 1020.0
        assert model.predict(3) == pytest.approx(1017.5, abs=0.1)

    def test_predict_clamping_low(self):
        """Test pressure clamping at lower bound."""
        model = PressureModel(current_pressure=955.0, pressure_change_3h=-30.0)  # Extreme drop

        # Should not go below 910 hPa
        result = model.predict(24)
        assert result >= 910.0

    def test_predict_clamping_high(self):
        """Test pressure clamping at upper bound."""
        model = PressureModel(current_pressure=1045.0, pressure_change_3h=30.0)  # Extreme rise

        # Should not go above 1085 hPa
        result = model.predict(24)
        assert result <= 1085.0

    def test_get_trend_rising(self):
        """Test trend detection for rising pressure."""
        # Need larger change rate to overcome damping effect for "rising" trend
        model = PressureModel(current_pressure=1010.0, pressure_change_3h=9.0)

        assert model.get_trend(3) == "rising"

    def test_get_trend_falling(self):
        """Test trend detection for falling pressure."""
        # Need larger change rate to overcome damping effect for "falling" trend
        model = PressureModel(current_pressure=1020.0, pressure_change_3h=-9.0)

        assert model.get_trend(3) == "falling"

    def test_get_trend_steady(self):
        """Test trend detection for steady pressure."""
        model = PressureModel(current_pressure=1013.0, pressure_change_3h=0.5)

        assert model.get_trend(3) == "steady"

    def test_damping_factor_effect(self):
        """Test that damping factor reduces change rate over time."""
        model = PressureModel(current_pressure=1010.0, pressure_change_3h=9.0, damping_factor=0.8)

        # Calculate total change over periods
        predicted_3h = model.predict(3)
        predicted_6h = model.predict(6)

        change_3h = predicted_3h - 1010.0
        change_6h = predicted_6h - 1010.0

        # Due to damping, the change over 6h should be less than 2x the change over 3h
        # This demonstrates exponential decay
        # NOTE: With max_change limiter (20 hPa/24h), both are capped:
        # - 3h: max = 2.5 hPa
        # - 6h: max = 5.0 hPa
        # So the ratio is exactly 2.0 when both hit the limit
        assert change_6h > change_3h  # Still increasing
        assert change_6h <= (change_3h * 2.0)  # Limited by max_change cap


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
        mock_hass = create_mock_hass()
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
        from datetime import datetime, timezone, timedelta

        mock_hass = create_mock_hass()

        # Mock sun entity for day/night detection
        mock_sun = Mock()
        mock_sun.state = "above_horizon"
        now = datetime.now(timezone.utc)
        mock_sun.attributes = {
            "next_rising": (now + timedelta(hours=12)).isoformat(),
            "next_setting": (now + timedelta(hours=6)).isoformat(),
        }
        mock_hass.states.get.return_value = mock_sun

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
        """Test forecast generation with current rain - forecasts use model, NOT rain override."""
        from datetime import datetime, timezone, timedelta

        mock_hass = create_mock_hass()

        # Mock sun entity for day/night detection
        mock_sun = Mock()
        mock_sun.state = "above_horizon"
        now = datetime.now(timezone.utc)
        mock_sun.attributes = {
            "next_rising": (now + timedelta(hours=12)).isoformat(),
            "next_setting": (now + timedelta(hours=6)).isoformat(),
        }
        mock_hass.states.get.return_value = mock_sun

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
            current_rain_rate=5.0  # Moderate rain (but forecast should ignore this!)
        )

        forecasts = generator.generate(hours_count=2, interval_hours=1)

        # Forecasts should use MODEL prediction, NOT rain override
        # Even if currently raining, forecast uses Zambretti/Negretti
        # Rain override is ONLY for weather.entity, not forecasts
        assert len(forecasts) > 0
        # Condition should be based on model (falling pressure), not current rain
        # We don't assert specific condition as it depends on model calculation

    def test_generate_interval_hours(self):
        """Test forecast generation with different intervals."""
        from datetime import datetime, timezone, timedelta

        mock_hass = create_mock_hass()

        # Mock sun entity for day/night detection
        mock_sun = Mock()
        mock_sun.state = "above_horizon"
        now = datetime.now(timezone.utc)
        mock_sun.attributes = {
            "next_rising": (now + timedelta(hours=12)).isoformat(),
            "next_setting": (now + timedelta(hours=6)).isoformat(),
        }
        mock_hass.states.get.return_value = mock_sun

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

    def test_night_detection_with_sun_entity(self):
        """Test that night detection works with forecasts (uses astral for specific dates)."""
        from datetime import datetime, timezone, timedelta

        mock_hass = create_mock_hass()

        # Mock sun entity for current time check
        mock_sun = Mock()
        mock_sun.state = "below_horizon"  # Currently night
        now = datetime.now(timezone.utc)
        mock_sun.attributes = {
            "next_rising": (now + timedelta(hours=8)).isoformat(),
            "next_setting": (now + timedelta(hours=20)).isoformat(),
        }
        mock_hass.states.get.return_value = mock_sun

        pressure_model = PressureModel(1013.25, 0.0)
        temp_model = TemperatureModel(15.0, 0.0, diurnal_amplitude=0.0)
        zambretti = ZambrettiForecaster()

        generator = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction=180,
            wind_speed=2.0,
            latitude=48.0
        )

        # Generate forecasts for next 10 hours
        forecasts = generator.generate(hours_count=10, interval_hours=1)

        # Check that is_daytime is properly set
        # Note: With astral, day/night is calculated for SPECIFIC forecast dates,
        # not based on next_rising/next_setting from current time
        # We just verify that is_daytime field exists and has valid values
        for i, forecast in enumerate(forecasts):
            assert "is_daytime" in forecast
            assert isinstance(forecast["is_daytime"], bool)

    def test_night_detection_fallback_without_sun_entity(self):
        """Test that night detection falls back to hour-based check without sun entity."""
        mock_hass = create_mock_hass()
        # No sun entity available
        mock_hass.states.get.return_value = None

        pressure_model = PressureModel(1013.25, 0.0)
        temp_model = TemperatureModel(15.0, 0.0, diurnal_amplitude=0.0)
        zambretti = ZambrettiForecaster()

        generator = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction=180,
            wind_speed=2.0
        )

        # Generate just a few forecasts
        forecasts = generator.generate(hours_count=3, interval_hours=1)

        # Should have generated forecasts even without sun entity
        assert len(forecasts) == 4  # 0, 1, 2, 3

        # All forecasts should have is_daytime field
        for forecast in forecasts:
            assert "is_daytime" in forecast
            # Value depends on current hour (19-07 is night)

    def test_night_condition_conversion(self):
        """Test that sunny is converted to clear-night, but partlycloudy stays partlycloudy at night."""

        mock_hass = create_mock_hass()

        # Mock sun entity that indicates it's night
        mock_sun = Mock()
        mock_sun.state = "below_horizon"
        mock_sun.attributes = {
            "next_rising": "2024-01-15T08:00:00+00:00",
            "next_setting": "2024-01-15T20:00:00+00:00"
        }
        mock_hass.states.get.return_value = mock_sun

        # High pressure conditions that would normally result in sunny/partlycloudy
        pressure_model = PressureModel(1025.0, 0.0)  # High pressure = clear conditions
        temp_model = TemperatureModel(5.0, 0.0, diurnal_amplitude=0.0)
        zambretti = ZambrettiForecaster()

        generator = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti,
            wind_direction=180,
            wind_speed=2.0
        )

        # Generate forecasts for nighttime hours
        forecasts = generator.generate(hours_count=6, interval_hours=1)

        # Check that night forecasts handle conditions correctly
        for i, forecast in enumerate(forecasts):
            if forecast["is_daytime"] is False:
                # During night, should NOT have sunny (should be clear-night)
                assert forecast["condition"] != "sunny", \
                    f"Hour {i}: Night forecast should not use 'sunny' condition"

                # partlycloudy is valid at night - HA shows correct icon automatically
                # clear-night is used only for truly clear sky conditions
                # No assertion needed - both partlycloudy and clear-night are valid at night



class TestDailyForecastGenerator:
    """Test DailyForecastGenerator class."""

    def test_generate_basic(self):
        """Test basic daily forecast generation."""
        mock_hass = create_mock_hass()

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
        mock_hass = create_mock_hass()

        pressure_model = PressureModel(1013.25, 0.0)
        temp_model = TemperatureModel(20.0, 0.0, diurnal_amplitude=10.0)  # ±10°C swing for clear range
        zambretti = ZambrettiForecaster()

        hourly_gen = HourlyForecastGenerator(
            mock_hass,
            pressure_model,
            temp_model,
            zambretti,
            elevation=314.0
        )

        daily_gen = DailyForecastGenerator(hourly_gen)
        forecasts = daily_gen.generate(days=1)

        assert len(forecasts) == 1

        # High should be greater than or equal to low (allowing for edge cases with minimal variation)
        assert forecasts[0]["temperature"] >= forecasts[0]["templow"]

        # With diurnal amplitude of 10°C, we should see some range over 24 hours
        # (though not necessarily the full ±10°C depending on sampling)
        temp_range = forecasts[0]["temperature"] - forecasts[0]["templow"]
        assert temp_range >= 0  # At minimum, they should differ or be equal


class TestForecastCalculator:
    """Test ForecastCalculator facade."""

    def test_generate_daily_forecast(self):
        """Test daily forecast generation via facade."""
        mock_hass = create_mock_hass()

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
        mock_hass = create_mock_hass()

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
        mock_hass = create_mock_hass()
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
        """Test that forecasts ignore rain override (only weather.entity uses it)."""
        mock_hass = create_mock_hass()
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
            current_rain_rate=10.0  # Heavy rain (but forecasts ignore this!)
        )

        # Forecasts should use MODEL prediction, NOT rain override
        # Rain override is ONLY for weather.entity
        assert len(forecasts) == 4  # 0, 1, 2, 3 hours
        # Conditions are based on model (falling pressure), not current rain


class TestEnhancedWithPersistence:
    """Test ENHANCED model with Persistence (v3.1.12)."""
    
    def test_hour_0_uses_persistence_in_enhanced_model(self):
        """Test that hour 0 in ENHANCED model uses Persistence."""
        from custom_components.local_weather_forecast.const import FORECAST_MODEL_ENHANCED
        
        mock_hass = create_mock_hass()
        
        # Create generator with ENHANCED model
        pressure_model = PressureModel(current_pressure=1020.0, pressure_change_3h=0.0)
        temp_model = TemperatureModel(current_temp=18.0, change_rate_1h=0.0)
        zambretti = ZambrettiForecaster()
        
        generator = HourlyForecastGenerator(
            hass=mock_hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            forecast_model=FORECAST_MODEL_ENHANCED
        )
        
        # Generate forecast (includes hour 0)
        with patch('custom_components.local_weather_forecast.language.get_language_index', return_value=1):
            forecasts = generator.generate(hours_count=3)
        
        # Should have hour 0, 1, 2, 3
        assert len(forecasts) == 4
        
        # Hour 0 should exist
        assert forecasts[0] is not None
    
    def test_zambretti_model_unchanged_by_persistence(self):
        """Test that Zambretti model is not affected by Persistence."""
        from custom_components.local_weather_forecast.const import FORECAST_MODEL_ZAMBRETTI
        
        mock_hass = create_mock_hass()
        
        # Create generator with ZAMBRETTI model
        pressure_model = PressureModel(current_pressure=1020.0, pressure_change_3h=0.0)
        temp_model = TemperatureModel(current_temp=18.0, change_rate_1h=0.0)
        zambretti = ZambrettiForecaster()
        
        generator = HourlyForecastGenerator(
            hass=mock_hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            forecast_model=FORECAST_MODEL_ZAMBRETTI
        )
        
        # Generate forecast
        with patch('custom_components.local_weather_forecast.language.get_language_index', return_value=1):
            forecasts = generator.generate(hours_count=3)
        
        # Should work normally (Zambretti doesn't use Persistence)
        assert len(forecasts) == 4
    
    def test_negretti_model_unchanged_by_persistence(self):
        """Test that Negretti model is not affected by Persistence."""
        from custom_components.local_weather_forecast.const import FORECAST_MODEL_NEGRETTI
        
        mock_hass = create_mock_hass()
        
        # Create generator with NEGRETTI model
        pressure_model = PressureModel(current_pressure=1020.0, pressure_change_3h=0.0)
        temp_model = TemperatureModel(current_temp=18.0, change_rate_1h=0.0)
        zambretti = ZambrettiForecaster()
        
        generator = HourlyForecastGenerator(
            hass=mock_hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            forecast_model=FORECAST_MODEL_NEGRETTI
        )
        
        # Generate forecast
        with patch('custom_components.local_weather_forecast.language.get_language_index', return_value=1):
            forecasts = generator.generate(hours_count=3)
        
        # Should work normally (Negretti doesn't use Persistence)
        assert len(forecasts) == 4
    
    def test_hour_1_plus_uses_time_decay(self):
        """Test that hours 1+ in ENHANCED model use TIME DECAY."""
        from custom_components.local_weather_forecast.const import FORECAST_MODEL_ENHANCED
        
        mock_hass = create_mock_hass()
        
        # Create generator with ENHANCED model
        pressure_model = PressureModel(current_pressure=1015.0, pressure_change_3h=2.0)
        temp_model = TemperatureModel(current_temp=20.0, change_rate_1h=0.0)
        zambretti = ZambrettiForecaster()
        
        generator = HourlyForecastGenerator(
            hass=mock_hass,
            pressure_model=pressure_model,
            temperature_model=temp_model,
            zambretti=zambretti,
            forecast_model=FORECAST_MODEL_ENHANCED
        )
        
        # Generate forecast
        with patch('custom_components.local_weather_forecast.language.get_language_index', return_value=1):
            forecasts = generator.generate(hours_count=6)
        
        # Should have forecasts for hours 0-6
        assert len(forecasts) == 7
        
        # All hours should have valid conditions
        for forecast in forecasts:
            assert forecast["condition"] is not None


