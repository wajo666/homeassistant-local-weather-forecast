"""Test enhanced temperature model features.

Tests for:
1. Radiative cooling with cloud cover and humidity
2. Latitude-based seasonal amplitude
3. Scientific accuracy of diurnal temperature range (DTR)
"""
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import pytest

from custom_components.local_weather_forecast.forecast_calculator import TemperatureModel


class MockSunEntity:
    """Mock sun.sun entity for testing."""
    
    def __init__(self, sunrise_hour: float = 6.0, sunset_hour: float = 18.0):
        """Initialize mock sun entity."""
        self.sunrise_hour = sunrise_hour
        self.sunset_hour = sunset_hour
        
        sunrise_time = datetime(2026, 2, 3, int(sunrise_hour), int((sunrise_hour % 1) * 60), tzinfo=timezone.utc)
        sunset_time = datetime(2026, 2, 3, int(sunset_hour), int((sunset_hour % 1) * 60), tzinfo=timezone.utc)
        
        self.attributes = {
            "next_rising": sunrise_time.isoformat(),
            "next_setting": sunset_time.isoformat(),
        }
        self.state = "below_horizon"


class TestRadiativeCooling:
    """Test radiative cooling with atmospheric conditions."""
    
    def test_clear_sky_faster_cooling(self):
        """Test that clear sky (low cloud cover) results in faster nighttime cooling."""
        mock_hass = Mock()
        mock_hass.states.get.return_value = MockSunEntity(sunrise_hour=6.0, sunset_hour=18.0)
        mock_hass.config.latitude = 45.0
        mock_hass.config.longitude = 0.0
        
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Evening: 19:00 (1 hour after sunset)
            mock_dt.now.return_value = datetime(2026, 6, 15, 19, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Clear sky (0% clouds)
            model_clear = TemperatureModel(
                current_temp=20.0,
                change_rate_1h=0.0,
                cloud_cover=0.0,
                hass=mock_hass,
                hemisphere="north"
            )
            
            # Cloudy sky (100% clouds)
            model_cloudy = TemperatureModel(
                current_temp=20.0,
                change_rate_1h=0.0,
                cloud_cover=100.0,
                hass=mock_hass,
                hemisphere="north"
            )
            
            # Predict temperature 4 hours later (23:00)
            temp_clear = model_clear.predict(4)
            temp_cloudy = model_cloudy.predict(4)
            
            # Clear sky should cool MORE than cloudy sky
            cooling_clear = 20.0 - temp_clear
            cooling_cloudy = 20.0 - temp_cloudy
            
            assert cooling_clear > cooling_cloudy, (
                f"Clear sky should cool faster than cloudy sky. "
                f"Clear cooling: {cooling_clear:.2f}°C, Cloudy cooling: {cooling_cloudy:.2f}°C"
            )
            
            # Clear sky cooling should be at least 2x faster (70% reduction with clouds)
            assert cooling_clear > cooling_cloudy * 1.5, (
                f"Clear sky cooling should be significantly faster. "
                f"Ratio: {cooling_clear / cooling_cloudy:.2f}x"
            )
    
    def test_high_humidity_slows_cooling(self):
        """Test that high humidity reduces radiative cooling rate."""
        mock_hass = Mock()
        mock_hass.states.get.return_value = MockSunEntity(sunrise_hour=6.0, sunset_hour=18.0)
        mock_hass.config.latitude = 45.0
        mock_hass.config.longitude = 0.0
        
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Evening: 19:00
            mock_dt.now.return_value = datetime(2026, 6, 15, 19, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Dry air (30% RH)
            model_dry = TemperatureModel(
                current_temp=20.0,
                change_rate_1h=0.0,
                cloud_cover=0.0,
                humidity=30.0,
                hass=mock_hass,
                hemisphere="north"
            )
            
            # Humid air (95% RH)
            model_humid = TemperatureModel(
                current_temp=20.0,
                change_rate_1h=0.0,
                cloud_cover=0.0,
                humidity=95.0,
                hass=mock_hass,
                hemisphere="north"
            )
            
            # Predict temperature 4 hours later
            temp_dry = model_dry.predict(4)
            temp_humid = model_humid.predict(4)
            
            # Dry air should cool MORE than humid air
            cooling_dry = 20.0 - temp_dry
            cooling_humid = 20.0 - temp_humid
            
            assert cooling_dry > cooling_humid, (
                f"Dry air should cool faster than humid air. "
                f"Dry cooling: {cooling_dry:.2f}°C, Humid cooling: {cooling_humid:.2f}°C"
            )
    
    def test_combined_cloud_humidity_effect(self):
        """Test combined effect of clouds and humidity on cooling."""
        mock_hass = Mock()
        mock_hass.states.get.return_value = MockSunEntity(sunrise_hour=6.0, sunset_hour=18.0)
        mock_hass.config.latitude = 45.0
        mock_hass.config.longitude = 0.0
        
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Evening: 19:00
            mock_dt.now.return_value = datetime(2026, 6, 15, 19, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Best cooling conditions: clear + dry
            model_best = TemperatureModel(
                current_temp=20.0,
                change_rate_1h=0.0,
                cloud_cover=0.0,
                humidity=30.0,
                hass=mock_hass,
                hemisphere="north"
            )
            
            # Worst cooling conditions: cloudy + humid
            model_worst = TemperatureModel(
                current_temp=20.0,
                change_rate_1h=0.0,
                cloud_cover=100.0,
                humidity=95.0,
                hass=mock_hass,
                hemisphere="north"
            )
            
            # Predict temperature 6 hours later (01:00)
            temp_best = model_best.predict(6)
            temp_worst = model_worst.predict(6)
            
            cooling_best = 20.0 - temp_best
            cooling_worst = 20.0 - temp_worst
            
            # Best conditions should cool MUCH more than worst
            # Expected: ~3-5°C difference based on literature
            assert cooling_best > cooling_worst + 2.0, (
                f"Clear+dry should cool significantly more than cloudy+humid. "
                f"Difference: {cooling_best - cooling_worst:.2f}°C"
            )


class TestLatitudeBasedAmplitude:
    """Test latitude-dependent seasonal amplitude."""
    
    def test_tropical_minimal_seasonal_variation(self):
        """Test that tropical latitudes have minimal seasonal variation."""
        # Tropical location (Singapore: 1.3°N)
        model_tropical_winter = TemperatureModel(
            current_temp=27.0,
            change_rate_1h=0.0,
            latitude=1.3,
            longitude=103.8,
            hemisphere="north"
        )
        
        # Check amplitude in "winter" (January)
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Recreate model to trigger amplitude calculation with new date
            model_tropical_winter_actual = TemperatureModel(
                current_temp=27.0,
                change_rate_1h=0.0,
                latitude=1.3,
                longitude=103.8,
                hemisphere="north"
            )
            winter_amp = model_tropical_winter_actual.diurnal_amplitude
        
        # Check amplitude in "summer" (July)
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model_tropical_summer = TemperatureModel(
                current_temp=28.0,
                change_rate_1h=0.0,
                latitude=1.3,
                longitude=103.8,
                hemisphere="north"
            )
            summer_amp = model_tropical_summer.diurnal_amplitude
        
        # Tropical: minimal difference between seasons
        # Expected: ~7-8°C both seasons (±1°C)
        assert abs(winter_amp - summer_amp) < 2.0, (
            f"Tropical locations should have minimal seasonal amplitude variation. "
            f"Winter: {winter_amp:.1f}°C, Summer: {summer_amp:.1f}°C"
        )
        assert 6.0 <= winter_amp <= 9.0, f"Tropical winter amplitude should be ~7-8°C, got {winter_amp:.1f}°C"
        assert 6.0 <= summer_amp <= 9.0, f"Tropical summer amplitude should be ~7-8°C, got {summer_amp:.1f}°C"
    
    def test_temperate_large_seasonal_variation(self):
        """Test that temperate latitudes have large seasonal variation."""
        # Temperate location (Košice: 48.7°N)
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Winter (February)
            mock_dt.now.return_value = datetime(2026, 2, 15, 12, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model_winter = TemperatureModel(
                current_temp=0.0,
                change_rate_1h=0.0,
                latitude=48.7,
                longitude=21.3,
                hemisphere="north"
            )
            winter_amp = model_winter.diurnal_amplitude
        
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Summer (July)
            mock_dt.now.return_value = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model_summer = TemperatureModel(
                current_temp=25.0,
                change_rate_1h=0.0,
                latitude=48.7,
                longitude=21.3,
                hemisphere="north"
            )
            summer_amp = model_summer.diurnal_amplitude
        
        # Temperate: large seasonal difference
        # Expected: winter ~3°C, summer ~12°C
        assert summer_amp > winter_amp * 2.5, (
            f"Temperate summer amplitude should be much larger than winter. "
            f"Winter: {winter_amp:.1f}°C, Summer: {summer_amp:.1f}°C, "
            f"Ratio: {summer_amp / winter_amp:.2f}x"
        )
        assert 2.0 <= winter_amp <= 5.0, f"Temperate winter amplitude should be ~3°C, got {winter_amp:.1f}°C"
        assert 10.0 <= summer_amp <= 15.0, f"Temperate summer amplitude should be ~12°C, got {summer_amp:.1f}°C"
    
    def test_polar_extreme_but_limited(self):
        """Test that polar latitudes have extreme seasons but limited by sun angle."""
        # Polar location (Tromsø: 69.6°N)
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Winter (January) - polar night
            mock_dt.now.return_value = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model_winter = TemperatureModel(
                current_temp=-15.0,
                change_rate_1h=0.0,
                latitude=69.6,
                longitude=18.9,
                hemisphere="north"
            )
            winter_amp = model_winter.diurnal_amplitude
        
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Summer (July) - midnight sun
            mock_dt.now.return_value = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model_summer = TemperatureModel(
                current_temp=15.0,
                change_rate_1h=0.0,
                latitude=69.6,
                longitude=18.9,
                hemisphere="north"
            )
            summer_amp = model_summer.diurnal_amplitude
        
        # Polar: winter very small (polar night), summer moderate (low sun angle despite 24h daylight)
        assert winter_amp < 3.0, f"Polar winter amplitude should be minimal, got {winter_amp:.1f}°C"
        assert summer_amp < 10.0, f"Polar summer amplitude limited by sun angle, got {summer_amp:.1f}°C"
        assert summer_amp > winter_amp, "Polar summer should have larger amplitude than winter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
