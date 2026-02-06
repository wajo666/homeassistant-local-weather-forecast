"""Tests for weather-aware temperature model."""
import pytest
from datetime import datetime
from custom_components.local_weather_forecast.combined_model import (
    calculate_weather_aware_temperature,
    _get_weather_temperature_adjustment,
    _get_diurnal_amplitude,
    _get_sun_angle_factor,
)


class TestWeatherAwareTemperature:
    """Test weather-aware temperature calculations."""
    
    def test_hour_zero_returns_current_temp(self):
        """Test that hour 0 returns current temperature."""
        temp = calculate_weather_aware_temperature(
            hour=0,
            current_temp=20.0,
            temp_trend=0.5,
            forecast_code=2,
            current_hour=12,
            latitude=48.72,
            longitude=21.25
        )
        assert temp == 20.0
    
    def test_sunny_daytime_warming(self):
        """Test that sunny conditions cause daytime warming."""
        # Sunny forecast (code 2) at midday (13:00)
        temp_sunny = calculate_weather_aware_temperature(
            hour=3,
            current_temp=20.0,
            temp_trend=0.0,
            forecast_code=2,  # Fine
            current_hour=10,  # Will be 13:00
            latitude=48.72,
            longitude=21.25,
            solar_radiation=800.0
        )
        
        # Cloudy forecast (code 15) at same time
        temp_cloudy = calculate_weather_aware_temperature(
            hour=3,
            current_temp=20.0,
            temp_trend=0.0,
            forecast_code=15,  # Unsettled
            current_hour=10,
            latitude=48.72,
            longitude=21.25
        )
        
        # Sunny should be warmer
        assert temp_sunny > temp_cloudy
    
    def test_rainy_cooling(self):
        """Test that rain causes cooling."""
        # Heavy rain (code 23)
        temp_rain = calculate_weather_aware_temperature(
            hour=2,
            current_temp=20.0,
            temp_trend=0.0,
            forecast_code=23,  # Storm
            current_hour=12,
            latitude=48.72,
            longitude=21.25
        )
        
        # Clear (code 2)
        temp_clear = calculate_weather_aware_temperature(
            hour=2,
            current_temp=20.0,
            temp_trend=0.0,
            forecast_code=2,  # Fine
            current_hour=12,
            latitude=48.72,
            longitude=21.25
        )
        
        # Rain should be cooler
        assert temp_rain < temp_clear
    
    def test_diurnal_cycle_maximum_afternoon(self):
        """Test that temperature peaks in afternoon."""
        # Morning (08:00)
        temp_morning = calculate_weather_aware_temperature(
            hour=0,
            current_temp=15.0,
            temp_trend=0.0,
            forecast_code=10,
            current_hour=8,
            latitude=48.72,
            longitude=21.25
        )
        
        # Afternoon (14:00) - 6 hours later
        temp_afternoon = calculate_weather_aware_temperature(
            hour=6,
            current_temp=15.0,
            temp_trend=0.0,
            forecast_code=10,
            current_hour=8,
            latitude=48.72,
            longitude=21.25
        )
        
        # Afternoon should be warmer due to diurnal cycle
        assert temp_afternoon > temp_morning
    
    def test_trend_damping(self):
        """Test that forecast-based temperature trend dampens over time."""
        # Sunny forecast (strong warming bias)
        # Use morning hours to avoid diurnal cycle interference
        temp_2h = calculate_weather_aware_temperature(
            hour=2,
            current_temp=15.0,
            temp_trend=0.0,  # Historical trend ignored
            forecast_code=0,  # Sunny: +0.08°C/h
            current_hour=6,  # Starting at 6 AM
            latitude=48.72,
            longitude=21.25
        )
        
        temp_10h = calculate_weather_aware_temperature(
            hour=10,
            current_temp=15.0,
            temp_trend=0.0,  # Historical trend ignored
            forecast_code=0,  # Sunny: +0.08°C/h
            current_hour=6,  # Starting at 6 AM
            latitude=48.72,
            longitude=21.25
        )
        
        # 10h should be warmer due to forecast bias accumulation
        assert temp_10h > temp_2h
        
        # But trend should be capped (±6°C over 48h)
        # Even with strong warming, shouldn't exceed reasonable limits
        assert temp_10h < 30.0
    
    def test_temperature_limits(self):
        """Test that temperature stays within realistic limits."""
        # Extreme warming trend
        temp = calculate_weather_aware_temperature(
            hour=24,
            current_temp=40.0,
            temp_trend=5.0,  # Extreme trend
            forecast_code=2,
            current_hour=12,
            latitude=48.72,
            longitude=21.25
        )
        
        # Should not exceed 50°C
        assert temp <= 50.0
        
        # Extreme cooling trend
        temp = calculate_weather_aware_temperature(
            hour=24,
            current_temp=-30.0,
            temp_trend=-5.0,  # Extreme cooling
            forecast_code=23,
            current_hour=12,
            latitude=48.72,
            longitude=21.25
        )
        
        # Should not go below -40°C
        assert temp >= -40.0


class TestWeatherAdjustments:
    """Test weather-specific temperature adjustments."""
    
    def test_storm_cooling(self):
        """Test storm causes strong cooling."""
        adj = _get_weather_temperature_adjustment(
            forecast_code=24,  # Storm
            future_hour=14,
            solar_radiation=None,
            cloud_cover=None
        )
        assert adj < -2.0  # Strong cooling
    
    def test_rain_cooling(self):
        """Test rain causes moderate cooling."""
        adj = _get_weather_temperature_adjustment(
            forecast_code=20,  # Rain
            future_hour=14,
            solar_radiation=None,
            cloud_cover=None
        )
        assert adj < -1.0  # Moderate cooling
    
    def test_sunny_daytime_warming(self):
        """Test sunny conditions warm during day."""
        adj = _get_weather_temperature_adjustment(
            forecast_code=1,  # Fine
            future_hour=13,  # Midday
            solar_radiation=800.0,
            cloud_cover=10.0
        )
        assert adj > 1.0  # Warming
    
    def test_sunny_nighttime_neutral(self):
        """Test sunny conditions have no effect at night."""
        adj = _get_weather_temperature_adjustment(
            forecast_code=1,  # Fine
            future_hour=2,  # Night
            solar_radiation=0.0,
            cloud_cover=10.0
        )
        assert adj < 0.5  # Minimal effect
    
    def test_cloudy_neutral(self):
        """Test cloudy/unsettled conditions cause cooling (dynamic based on cloud cover)."""
        adj = _get_weather_temperature_adjustment(
            forecast_code=14,  # Unsettled
            future_hour=14,
            solar_radiation=None,
            cloud_cover=80.0
        )
        # Unsettled weather should cool (clouds block solar radiation)
        # Dynamic formula: -0.015 * cloud_cover
        # 80% clouds = -1.2°C cooling
        assert -1.5 <= adj <= -1.0  # Strong cooling with high cloud cover


class TestDiurnalAmplitude:
    """Test seasonal diurnal amplitude."""
    
    def test_summer_larger_amplitude(self):
        """Test summer has larger temperature swings."""
        summer = _get_diurnal_amplitude(current_month=7)  # July
        winter = _get_diurnal_amplitude(current_month=1)  # January
        assert summer > winter
    
    def test_amplitude_ranges(self):
        """Test amplitude is within realistic range."""
        for month in range(1, 13):
            amp = _get_diurnal_amplitude(current_month=month)
            assert 2.0 <= amp <= 10.0
    
    def test_spring_autumn_medium(self):
        """Test spring/autumn have medium amplitudes."""
        spring = _get_diurnal_amplitude(current_month=4)  # April
        autumn = _get_diurnal_amplitude(current_month=9)  # September
        summer = _get_diurnal_amplitude(current_month=7)  # July
        winter = _get_diurnal_amplitude(current_month=1)  # January
        
        assert winter < spring < summer
        assert winter < autumn < summer


class TestSunAngleFactor:
    """Test sun angle factor calculation."""
    
    def test_midnight_is_zero(self):
        """Test midnight has zero sun factor."""
        assert _get_sun_angle_factor(0) == 0.0
        assert _get_sun_angle_factor(23) == 0.0
    
    def test_noon_is_maximum(self):
        """Test solar noon has maximum factor."""
        assert _get_sun_angle_factor(13) == 1.0
        assert _get_sun_angle_factor(12) == 1.0
    
    def test_morning_evening_reduced(self):
        """Test morning/evening have reduced factor."""
        assert 0.0 < _get_sun_angle_factor(9) < 1.0
        assert 0.0 < _get_sun_angle_factor(17) < 1.0
    
    def test_early_morning_minimal(self):
        """Test early morning has minimal factor."""
        assert _get_sun_angle_factor(7) == 0.2


class TestIntegration:
    """Integration tests for complete temperature calculation."""
    
    def test_realistic_summer_day(self):
        """Test realistic summer day progression."""
        # Morning 6:00, 15°C, sunny
        temp_morning = calculate_weather_aware_temperature(
            hour=0,
            current_temp=15.0,
            temp_trend=0.5,
            forecast_code=1,  # Fine
            current_hour=6,
            latitude=48.72,
            longitude=21.25,
            solar_radiation=200.0
        )
        
        # Afternoon 14:00, should be warmer
        temp_afternoon = calculate_weather_aware_temperature(
            hour=8,
            current_temp=15.0,
            temp_trend=0.5,
            forecast_code=1,  # Fine
            current_hour=6,
            latitude=48.72,
            longitude=21.25,
            solar_radiation=800.0
        )
        
        # Evening 22:00, should cool down
        temp_evening = calculate_weather_aware_temperature(
            hour=16,
            current_temp=15.0,
            temp_trend=0.5,
            forecast_code=1,  # Fine
            current_hour=6,
            latitude=48.72,
            longitude=21.25,
            solar_radiation=0.0
        )
        
        # Expected: morning < afternoon, evening < afternoon
        assert temp_morning < temp_afternoon
        assert temp_evening < temp_afternoon
        
        # Peak should be reasonable (not extreme)
        assert 18.0 <= temp_afternoon <= 30.0
    
    def test_realistic_rainy_day(self):
        """Test realistic rainy day behavior."""
        # Rain starts, should cool down
        temp_before = calculate_weather_aware_temperature(
            hour=0,
            current_temp=18.0,
            temp_trend=0.0,
            forecast_code=10,  # Variable
            current_hour=12,
            latitude=48.72,
            longitude=21.25
        )
        
        temp_during = calculate_weather_aware_temperature(
            hour=2,
            current_temp=18.0,
            temp_trend=0.0,
            forecast_code=20,  # Rain
            current_hour=12,
            latitude=48.72,
            longitude=21.25
        )
        
        # Rain should cause cooling
        assert temp_during < temp_before
        # But not extreme cooling
        assert temp_during >= temp_before - 5.0
