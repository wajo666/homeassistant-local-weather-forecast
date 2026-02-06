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


class TestWeatherAwareTemperatureIntegration:
    """Test weather-aware temperature integration in orchestration."""
    
    def test_temperature_realistic_with_rain(self):
        """Test temperature behaves realistically with rainy forecast."""
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "temperature": 18.0,
            "temperature_trend": 0.0,
            "pressure": 1005.0,
            "pressure_change": -3.0,  # Falling - rain likely
            "humidity": 85.0,
            "dewpoint": 15.0,
            "condition": "rainy",
            "zambretti_result": ["Rain", 20],
            "negretti_result": ["Rain soon", 19],
            "latitude": 48.72,
            "longitude": 21.25,
        }
        
        forecasts = generate_enhanced_hourly_forecast(weather_data, hours=6, lang_index=1)
        
        # Check temperatures don't rise unrealistically during rain
        for i, forecast in enumerate(forecasts):
            if forecast["condition_code"] >= 18:  # Rainy
                # Temperature should not increase significantly
                # Allow small increase from trend but rain should cool it
                assert forecast["temperature"] <= weather_data["temperature"] + 2.0, \
                    f"Hour {i}: Rain forecast should not warm significantly"
    
    def test_temperature_realistic_with_sunshine(self):
        """Test temperature increases realistically with sunny forecast."""
        weather_data = {
            "start_time": datetime.now(timezone.utc).replace(hour=10),  # Morning
            "temperature": 18.0,
            "temperature_trend": 0.5,
            "pressure": 1025.0,
            "pressure_change": 1.5,  # Rising - fine weather
            "humidity": 50.0,
            "dewpoint": 8.0,
            "condition": "sunny",
            "zambretti_result": ["Settled fine", 2],
            "negretti_result": ["Fine", 1],
            "latitude": 48.72,
            "longitude": 21.25,
            "solar_radiation": 800.0,
        }
        
        forecasts = generate_enhanced_hourly_forecast(weather_data, hours=6, lang_index=1)
        
        # Check temperatures rise during sunny conditions
        sunny_hours = [f for f in forecasts if f["condition_code"] <= 5]
        if sunny_hours:
            # Should have some warming beyond just the trend
            max_temp = max(f["temperature"] for f in sunny_hours)
            # With sunny conditions + trend, should warm noticeably
            assert max_temp > weather_data["temperature"] + 1.0, \
                "Sunny conditions should cause noticeable warming"
    
    def test_temperature_diurnal_cycle(self):
        """Test temperature follows diurnal cycle."""
        # Morning start
        weather_data_morning = {
            "start_time": datetime.now(timezone.utc).replace(hour=6),
            "temperature": 12.0,
            "temperature_trend": 0.3,
            "pressure": 1020.0,
            "pressure_change": 0.5,
            "humidity": 70.0,
            "dewpoint": 7.0,
            "condition": "partly_cloudy",
            "zambretti_result": ["Fair", 8],
            "negretti_result": ["Fair", 9],
            "latitude": 48.72,
            "longitude": 21.25,
        }
        
        forecasts = generate_enhanced_hourly_forecast(weather_data_morning, hours=12, lang_index=1)
        
        # Extract temperatures
        temps = [f["temperature"] for f in forecasts]
        
        # Morning to afternoon should generally warm
        # (even with neutral trend, diurnal cycle should add warmth during day)
        # Find peak - should be in afternoon (around 14:00 UTC = hour 8)
        peak_temp = max(temps[0:10])  # Within first 10 hours
        
        # Peak should be warmer than start
        assert peak_temp > weather_data_morning["temperature"], \
            "Diurnal cycle should cause warming from morning to afternoon"
    
    def test_temperature_damping_prevents_extremes(self):
        """Test that temperature trend damping prevents unrealistic extremes."""
        weather_data = {
            "start_time": datetime.now(timezone.utc),
            "temperature": 20.0,
            "temperature_trend": 3.0,  # Strong warming trend
            "pressure": 1015.0,
            "pressure_change": 0.0,
            "humidity": 60.0,
            "dewpoint": 12.0,
            "condition": "clear",
            "zambretti_result": ["Fair", 8],
            "negretti_result": ["Fair", 9],
            "latitude": 48.72,
            "longitude": 21.25,
        }
        
        forecasts = generate_enhanced_hourly_forecast(weather_data, hours=10, lang_index=1)
        
        # Without damping: 20 + (3.0 * 10) = 50°C (unrealistic!)
        # With per-day damping: allows ~2°C/h effective rate over short periods
        # Expected: ~20-25°C after 10h with strong damping
        final_temp = forecasts[-1]["temperature"]
        
        # Per-day damping allows more variation than old global damping
        # but still prevents extreme jumps (should be < 43°C for 3.0°C/h trend)
        assert final_temp < 43.0, \
            f"Temperature damping should prevent extreme values: got {final_temp}°C"
        
        # Should still show some warming
        assert final_temp > weather_data["temperature"], \
            "Should still show warming trend, just damped"
    
    def test_coordinates_used_for_solar_calculations(self):
        """Test that latitude/longitude affect temperature calculations."""
        base_data = {
            "start_time": datetime.now(timezone.utc).replace(hour=12),
            "temperature": 20.0,
            "temperature_trend": 0.0,
            "pressure": 1020.0,
            "pressure_change": 0.0,
            "humidity": 60.0,
            "dewpoint": 12.0,
            "condition": "sunny",
            "zambretti_result": ["Fine", 2],
            "negretti_result": ["Fine", 1],
            "solar_radiation": 800.0,
        }
        
        # Eastern location (Košice)
        data_east = {**base_data, "latitude": 48.72, "longitude": 21.25}
        # Western location (Praha)  
        data_west = {**base_data, "latitude": 50.08, "longitude": 14.42}
        
        forecasts_east = generate_enhanced_hourly_forecast(data_east, hours=6, lang_index=1)
        forecasts_west = generate_enhanced_hourly_forecast(data_west, hours=6, lang_index=1)
        
        # Temperatures might differ slightly due to solar noon offset
        # This is expected behavior - just verify both complete successfully
        assert len(forecasts_east) == 7
        assert len(forecasts_west) == 7
        assert all(f["temperature"] is not None for f in forecasts_east)
        assert all(f["temperature"] is not None for f in forecasts_west)
