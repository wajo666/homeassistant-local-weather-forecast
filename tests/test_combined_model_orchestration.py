"""Unit tests for combined_model orchestration with Persistence + WMO Simple (v3.1.12)."""

import pytest
from datetime import datetime, timezone, timedelta
from custom_components.local_weather_forecast.combined_model import (
    generate_enhanced_hourly_forecast,
    calculate_temperature_at_hour,
)


class TestGenerateEnhancedHourlyForecast:
    """Test generate_enhanced_hourly_forecast() orchestration function."""
    
    def test_hour_0_uses_persistence(self):
        """Test that hour 0 uses Persistence model."""
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "temperature": 20.0,
            "pressure": 1020.0,
            "pressure_change": 0.0,
            "humidity": 65.0,
            "dewpoint": 13.0,
            "condition": "sunny",
            "zambretti_result": ["Fine weather", 5],
            "negretti_result": ["Settled fine", 3],
            "temperature_trend": 0.0,
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=3,
            lang_index=1
        )
        
        # Should have 4 forecasts (0-3 hours)
        assert len(forecasts) == 4
        
        # Hour 0 should have high confidence (Persistence)
        assert forecasts[0]["confidence"] >= 0.98
        
        # All forecasts should have required fields
        for forecast in forecasts:
            assert "datetime" in forecast
            assert "condition" in forecast
            assert "condition_code" in forecast
            assert "confidence" in forecast
            assert "temperature" in forecast
            assert "pressure" in forecast
    
    def test_hours_1_to_3_use_wmo_simple(self):
        """Test that hours 1-3 use WMO Simple model."""
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "temperature": 18.0,
            "pressure": 1010.0,
            "pressure_change": 2.5,  # Steady rise
            "humidity": 70.0,
            "dewpoint": 12.0,
            "condition": "cloudy",
            "zambretti_result": ["Fair weather", 8],
            "negretti_result": ["Fairly fine", 9],
            "temperature_trend": 0.2,
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=3,
            lang_index=1
        )
        
        # Should have 4 forecasts (0-3 hours)
        assert len(forecasts) == 4
        
        # Hours 1-3 should have WMO Simple confidence (90-95%)
        for i in range(1, 4):
            assert forecasts[i]["confidence"] >= 0.88  # WMO range
            assert forecasts[i]["confidence"] <= 0.98
    
    def test_hours_4_to_6_use_blended_transition(self):
        """Test that hours 4-6 use blended WMO→TIME DECAY."""
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "temperature": 20.0,
            "pressure": 1020.0,
            "pressure_change": 1.5,
            "humidity": 65.0,
            "dewpoint": 13.0,
            "condition": "sunny",
            "zambretti_result": ["Fine", 5],
            "negretti_result": ["Settled", 3],
            "temperature_trend": 0.0,
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=6,
            lang_index=1
        )
        
        # Should have 7 forecasts (0-6 hours)
        assert len(forecasts) == 7
        
        # Hours 4-6 should have blended confidence
        for i in range(4, 7):
            assert forecasts[i]["confidence"] >= 0.70
            assert forecasts[i]["confidence"] <= 0.95
    
    def test_hour_1_plus_uses_time_decay(self):
        """Test that hours 7+ use TIME DECAY."""
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "temperature": 18.0,
            "pressure": 1010.0,
            "pressure_change": 2.0,
            "humidity": 70.0,
            "dewpoint": 12.0,
            "condition": "cloudy",
            "zambretti_result": ["Fair weather", 8],
            "negretti_result": ["Fairly fine", 9],
            "temperature_trend": 0.2,
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=12,
            lang_index=1
        )
        
        # Should have 13 forecasts (0-12 hours)
        assert len(forecasts) == 13
        
        # Hours 7+ should have TIME DECAY confidence
        for i in range(7, 13):
            assert forecasts[i]["confidence"] < 0.95
            # Confidence should be reasonable (not too low)
            assert forecasts[i]["confidence"] >= 0.70
    
    def test_smooth_transition_across_all_models(self):
        """Test smooth transition: Persistence → WMO → Blend → TIME DECAY."""
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "temperature": 22.0,
            "pressure": 1025.0,
            "pressure_change": -1.0,
            "humidity": 55.0,
            "dewpoint": 13.0,
            "condition": "sunny",
            "zambretti_result": ["Fine", 4],
            "negretti_result": ["Settled", 2],
            "temperature_trend": -0.1,
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=10,
            lang_index=1
        )
        
        # Check hour 0 (Persistence)
        assert forecasts[0]["confidence"] == 0.98
        
        # Check hours 1-3 (WMO Simple)
        for i in range(1, 4):
            assert 0.85 <= forecasts[i]["confidence"] <= 0.98
        
        # Check hours 4-6 (Blend)
        for i in range(4, 7):
            assert 0.70 <= forecasts[i]["confidence"] <= 0.95
        
        # Check hours 7+ (TIME DECAY)
        for i in range(7, 11):
            assert 0.70 <= forecasts[i]["confidence"] <= 0.90
        
        # Check hour 0 (Persistence)
        assert forecasts[0]["confidence"] == 0.98
        
        # Check hours 1-3 (WMO Simple)
        for i in range(1, 4):
            assert 0.85 <= forecasts[i]["confidence"] <= 0.98
        
        # Check hours 4-6 (Blend)
        for i in range(4, 7):
            assert 0.70 <= forecasts[i]["confidence"] <= 0.95
        
        # Check hours 7+ (TIME DECAY)
        for i in range(7, 11):
            assert 0.70 <= forecasts[i]["confidence"] <= 0.90
    
    def test_datetime_progression(self):
        """Test that datetime values progress correctly."""
        start_time = datetime.now(timezone.utc)
        weather_data = {
            "start_time": start_time,
            "temperature": 15.0,
            "pressure": 1013.0,
            "pressure_change": 0.0,
            "humidity": 70.0,
            "dewpoint": 10.0,
            "condition": "cloudy",
            "zambretti_result": ["", 13],
            "negretti_result": ["", 12],
            "temperature_trend": 0.0,
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=5,
            lang_index=1
        )
        
        # Check datetime progression
        for i, forecast in enumerate(forecasts):
            expected_time = start_time + timedelta(hours=i)
            assert forecast["datetime"] == expected_time
    
    def test_handles_missing_optional_fields(self):
        """Test that function handles missing optional fields gracefully."""
        # Minimal weather data
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "zambretti_result": ["", 10],
            "negretti_result": ["", 11],
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=2,
            lang_index=1
        )
        
        # Should still generate forecasts with defaults
        assert len(forecasts) == 3
        
        # All forecasts should have values (using defaults)
        for forecast in forecasts:
            assert forecast["temperature"] is not None
            assert forecast["pressure"] is not None
            assert forecast["condition_code"] is not None


class TestCalculateTemperatureAtHour:
    """Test calculate_temperature_at_hour() function."""
    
    def test_no_trend(self):
        """Test temperature calculation with no trend."""
        temp = calculate_temperature_at_hour(
            hour=5,
            current_temp=20.0,
            temp_trend=0.0
        )
        
        assert temp == 20.0
    
    def test_warming_trend(self):
        """Test temperature calculation with warming trend."""
        temp = calculate_temperature_at_hour(
            hour=4,
            current_temp=15.0,
            temp_trend=0.5
        )
        
        # Should increase: 15 + (0.5 * 4) = 17°C
        assert temp == 17.0
    
    def test_cooling_trend(self):
        """Test temperature calculation with cooling trend."""
        temp = calculate_temperature_at_hour(
            hour=3,
            current_temp=25.0,
            temp_trend=-1.0
        )
        
        # Should decrease: 25 + (-1.0 * 3) = 22°C
        assert temp == 22.0
    
    def test_hour_zero(self):
        """Test temperature at hour 0 (current)."""
        temp = calculate_temperature_at_hour(
            hour=0,
            current_temp=18.5,
            temp_trend=0.3
        )
        
        # Should be current temperature
        assert temp == 18.5
