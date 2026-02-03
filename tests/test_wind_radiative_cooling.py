"""Tests for wind speed effect on nighttime radiative cooling.

Wind mixing prevents temperature inversion and reduces surface cooling:
- Calm night (0-1 m/s): Maximum radiative cooling (strong inversion)
- Light breeze (1-3 m/s): Slight reduction (~10%)
- Moderate breeze (3-5 m/s): Noticeable reduction (~30%)
- Fresh breeze (5-8 m/s): Strong reduction (~50%)
- Strong wind (>8 m/s): Minimal cooling (~60%), well-mixed atmosphere

Based on: Oke (1987) "Boundary Layer Climates", Geiger et al. (2009)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from custom_components.local_weather_forecast.forecast_calculator import TemperatureModel


class TestWindRadiativeCooling:
    """Test wind speed effect on nighttime radiative cooling."""

    def _create_mock_hass(self, sunrise_hour: int = 6, sunset_hour: int = 18):
        """Create mock Home Assistant with sun entity."""
        mock_hass = Mock()
        
        # Mock sun entity with sunrise/sunset times
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        sunrise = today + timedelta(hours=sunrise_hour)
        sunset = today + timedelta(hours=sunset_hour)
        
        mock_sun = Mock()
        mock_sun.attributes = {
            "next_rising": sunrise.isoformat(),
            "next_setting": sunset.isoformat(),
        }
        
        mock_hass.states.get.return_value = mock_sun
        mock_hass.config.latitude = 48.0  # Mid-latitude
        mock_hass.config.longitude = 17.0
        mock_hass.config.time_zone = "Europe/Bratislava"
        
        return mock_hass

    @patch('custom_components.local_weather_forecast.forecast_calculator.datetime')
    def test_calm_night_maximum_cooling(self, mock_datetime):
        """Test calm night (0 m/s) produces maximum radiative cooling."""
        # Mock winter night at 22:00 (4 hours after sunset at 18:00)
        mock_now = datetime(2025, 2, 15, 22, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        mock_hass = self._create_mock_hass(sunrise_hour=7, sunset_hour=18)
        
        # Create model: clear sky, dry air, CALM wind
        calm_model = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            solar_radiation=0.0,
            cloud_cover=0.0,  # Clear sky
            humidity=50.0,     # Dry air
            wind_speed=0.0,    # CALM
            hass=mock_hass,
            latitude=48.0,
            longitude=17.0,
            hemisphere="north",
        )
        
        # Predict temperature 2 hours ahead (00:00 = 6 hours after sunset)
        calm_temp = calm_model.predict(hours_ahead=2)
        
        # Calm night should show strong cooling
        # Expected: ~0.5°C to 2.0°C
        assert calm_temp < 2.0, f"Calm night cooling insufficient: {calm_temp:.1f}°C"
        assert calm_temp > 0.0, f"Calm night cooling excessive: {calm_temp:.1f}°C"

    @patch('custom_components.local_weather_forecast.forecast_calculator.datetime')
    def test_windy_night_reduced_cooling(self, mock_datetime):
        """Test windy night (10 m/s) produces minimal radiative cooling."""
        # Mock winter night at 22:00 (4 hours after sunset at 18:00)
        mock_now = datetime(2025, 2, 15, 22, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        mock_hass = self._create_mock_hass(sunrise_hour=7, sunset_hour=18)
        
        # Create model: clear sky, dry air, STRONG wind
        windy_model = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            solar_radiation=0.0,
            cloud_cover=0.0,  # Clear sky
            humidity=50.0,     # Dry air
            wind_speed=10.0,   # STRONG WIND
            hass=mock_hass,
            latitude=48.0,
            longitude=17.0,
            hemisphere="north",
        )
        
        # Predict temperature 2 hours ahead (00:00 = 6 hours after sunset)
        windy_temp = windy_model.predict(hours_ahead=2)
        
        # Strong wind should prevent strong cooling (well-mixed atmosphere)
        # Expected: ~1.5°C to 2.5°C (warmer than calm night)
        assert windy_temp > 1.2, f"Windy night cooling too strong: {windy_temp:.1f}°C"
        assert windy_temp < 3.0, f"Windy night unrealistic warming: {windy_temp:.1f}°C"

    @patch('custom_components.local_weather_forecast.forecast_calculator.datetime')
    def test_wind_prevents_inversion_cooling(self, mock_datetime):
        """Test that wind prevents temperature inversion (calm < windy)."""
        # Mock winter night at 22:00
        mock_now = datetime(2025, 2, 15, 22, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        mock_hass = self._create_mock_hass(sunrise_hour=7, sunset_hour=18)
        
        # CALM night
        calm_model = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            solar_radiation=0.0,
            cloud_cover=0.0,
            humidity=50.0,
            wind_speed=0.5,  # Nearly calm
            hass=mock_hass,
            latitude=48.0,
            longitude=17.0,
        )
        
        # WINDY night
        windy_model = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            solar_radiation=0.0,
            cloud_cover=0.0,
            humidity=50.0,
            wind_speed=8.0,  # Strong wind
            hass=mock_hass,
            latitude=48.0,
            longitude=17.0,
        )
        
        # Predict 4 hours ahead (02:00 = 8 hours after sunset)
        calm_temp = calm_model.predict(hours_ahead=4)
        windy_temp = windy_model.predict(hours_ahead=4)
        
        # Calm night MUST be colder (stronger inversion cooling)
        cooling_difference = windy_temp - calm_temp
        assert cooling_difference > 0.2, \
            f"Wind should reduce cooling by >0.2°C, got {cooling_difference:.1f}°C difference"
        assert cooling_difference < 1.5, \
            f"Wind effect too strong: {cooling_difference:.1f}°C difference"

    @patch('custom_components.local_weather_forecast.forecast_calculator.datetime')
    def test_moderate_breeze_intermediate_cooling(self, mock_datetime):
        """Test moderate breeze (4 m/s) produces intermediate cooling."""
        # Mock winter night at 22:00
        mock_now = datetime(2025, 2, 15, 22, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        mock_hass = self._create_mock_hass(sunrise_hour=7, sunset_hour=18)
        
        # Create three models: calm, moderate, strong wind
        calm_model = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            cloud_cover=0.0,
            wind_speed=0.0,
            hass=mock_hass,
            latitude=48.0,
        )
        
        moderate_model = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            cloud_cover=0.0,
            wind_speed=4.0,  # Moderate breeze
            hass=mock_hass,
            latitude=48.0,
        )
        
        strong_model = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            cloud_cover=0.0,
            wind_speed=10.0,
            hass=mock_hass,
            latitude=48.0,
        )
        
        # Predict 3 hours ahead
        calm_temp = calm_model.predict(hours_ahead=3)
        moderate_temp = moderate_model.predict(hours_ahead=3)
        strong_temp = strong_model.predict(hours_ahead=3)
        
        # Moderate breeze should be between calm and strong wind
        assert calm_temp < moderate_temp < strong_temp, \
            f"Wind progression incorrect: calm={calm_temp:.1f}, moderate={moderate_temp:.1f}, strong={strong_temp:.1f}"

    @patch('custom_components.local_weather_forecast.forecast_calculator.datetime')
    def test_combined_wind_cloud_effect(self, mock_datetime):
        """Test combined wind and cloud cover effect on cooling."""
        # Mock winter night at 22:00
        mock_now = datetime(2025, 2, 15, 22, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        mock_hass = self._create_mock_hass(sunrise_hour=7, sunset_hour=18)
        
        # Scenario 1: Clear sky + calm = STRONG cooling
        clear_calm = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            cloud_cover=0.0,   # Clear
            wind_speed=0.0,    # Calm
            hass=mock_hass,
            latitude=48.0,
        )
        
        # Scenario 2: Cloudy + windy = MINIMAL cooling
        cloudy_windy = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            cloud_cover=80.0,  # Cloudy
            wind_speed=8.0,    # Windy
            hass=mock_hass,
            latitude=48.0,
        )
        
        # Predict 4 hours ahead
        clear_calm_temp = clear_calm.predict(hours_ahead=4)
        cloudy_windy_temp = cloudy_windy.predict(hours_ahead=4)
        
        # Clear+calm should be MUCH colder than cloudy+windy
        difference = cloudy_windy_temp - clear_calm_temp
        assert difference > 0.3, \
            f"Combined wind+cloud effect too weak: {difference:.1f}°C difference"
        assert difference < 2.0, \
            f"Combined wind+cloud effect too strong: {difference:.1f}°C difference"

    @patch('custom_components.local_weather_forecast.forecast_calculator.datetime')
    def test_no_wind_sensor_fallback(self, mock_datetime):
        """Test that model works without wind sensor (assumes calm)."""
        # Mock winter night at 22:00
        mock_now = datetime(2025, 2, 15, 22, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        mock_hass = self._create_mock_hass(sunrise_hour=7, sunset_hour=18)
        
        # Create model WITHOUT wind_speed (None)
        no_wind_model = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=-0.3,
            cloud_cover=0.0,
            wind_speed=None,  # No wind sensor
            hass=mock_hass,
            latitude=48.0,
        )
        
        # Should not raise exception
        temp = no_wind_model.predict(hours_ahead=3)
        
        # Should produce reasonable result (assumes calm conditions)
        assert -1.0 < temp < 2.5, \
            f"No wind sensor fallback unrealistic: {temp:.1f}°C"
