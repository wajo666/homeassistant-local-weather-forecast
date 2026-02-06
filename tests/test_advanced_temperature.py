"""Test advanced temperature features: humidity, wind chill, elevation, dynamic cloud cover."""
import pytest
from custom_components.local_weather_forecast.combined_model import (
    calculate_weather_aware_temperature,
)


class TestHumidityEffect:
    """Test humidity effects on temperature perception."""
    
    def test_high_humidity_warming(self):
        """High humidity (>70%) reduces cooling, feels warmer."""
        # 90% humidity should add warming effect
        temp_humid = calculate_weather_aware_temperature(
            hour=6,
            current_temp=20.0,
            temp_trend=0.0,
            forecast_code=10,
            current_hour=12,
            humidity=90.0
        )
        
        # Same conditions, low humidity
        temp_dry = calculate_weather_aware_temperature(
            hour=6,
            current_temp=20.0,
            temp_trend=0.0,
            forecast_code=10,
            current_hour=12,
            humidity=30.0
        )
        
        # High humidity should feel warmer (less cooling)
        assert temp_humid > temp_dry
        print(f"High humidity (90%): {temp_humid:.1f}°C")
        print(f"Low humidity (30%): {temp_dry:.1f}°C")
        print(f"Difference: {temp_humid - temp_dry:+.1f}°C")
    
    def test_low_humidity_cooling(self):
        """Low humidity (<40%) enhances cooling."""
        # Very dry air (20% humidity)
        temp_very_dry = calculate_weather_aware_temperature(
            hour=8,
            current_temp=15.0,
            temp_trend=0.0,
            forecast_code=5,
            current_hour=22,  # Night
            humidity=20.0
        )
        
        # Moderate humidity (50%)
        temp_moderate = calculate_weather_aware_temperature(
            hour=8,
            current_temp=15.0,
            temp_trend=0.0,
            forecast_code=5,
            current_hour=22,  # Night
            humidity=50.0
        )
        
        # Very dry should enhance cooling
        assert temp_very_dry < temp_moderate
        print(f"Very dry (20%): {temp_very_dry:.1f}°C")
        print(f"Moderate (50%): {temp_moderate:.1f}°C")


class TestWindChill:
    """Test wind chill effects in cold conditions."""
    
    def test_wind_chill_cold_windy(self):
        """Wind chill makes cold+windy conditions feel colder."""
        # Cold (5°C) with strong wind (10 m/s)
        temp_windy = calculate_weather_aware_temperature(
            hour=3,
            current_temp=5.0,
            temp_trend=0.0,
            forecast_code=10,
            current_hour=12,
            wind_speed=10.0  # 10 m/s = 36 km/h
        )
        
        # Same but calm (1 m/s)
        temp_calm = calculate_weather_aware_temperature(
            hour=3,
            current_temp=5.0,
            temp_trend=0.0,
            forecast_code=10,
            current_hour=12,
            wind_speed=1.0
        )
        
        # Windy should feel significantly colder
        assert temp_windy < temp_calm
        difference = temp_calm - temp_windy
        assert difference > 1.0  # At least 1°C difference
        print(f"Windy (10 m/s): {temp_windy:.1f}°C (feels like)")
        print(f"Calm (1 m/s): {temp_calm:.1f}°C")
        print(f"Wind chill effect: {difference:.1f}°C colder")
    
    def test_wind_chill_only_below_10c(self):
        """Wind chill only applies when T < 10°C."""
        # Warm day (15°C) - no wind chill
        temp_warm_windy = calculate_weather_aware_temperature(
            hour=2,
            current_temp=15.0,
            temp_trend=0.0,
            forecast_code=2,
            current_hour=12,
            wind_speed=10.0
        )
        
        temp_warm_calm = calculate_weather_aware_temperature(
            hour=2,
            current_temp=15.0,
            temp_trend=0.0,
            forecast_code=2,
            current_hour=12,
            wind_speed=1.0
        )
        
        # Should be very similar (no wind chill above 10°C)
        assert abs(temp_warm_windy - temp_warm_calm) < 0.5


class TestHeatIndex:
    """Test heat index in hot+humid conditions."""
    
    def test_heat_index_hot_humid(self):
        """Hot+humid conditions feel hotter (heat index)."""
        # Hot (30°C) + humid (80%)
        temp_humid = calculate_weather_aware_temperature(
            hour=2,
            current_temp=30.0,
            temp_trend=0.0,
            forecast_code=2,
            current_hour=12,
            humidity=80.0,
            wind_speed=2.0
        )
        
        # Hot but dry (30%)
        temp_dry = calculate_weather_aware_temperature(
            hour=2,
            current_temp=30.0,
            temp_trend=0.0,
            forecast_code=2,
            current_hour=12,
            humidity=30.0,
            wind_speed=2.0
        )
        
        # Humid should feel hotter
        assert temp_humid > temp_dry
        difference = temp_humid - temp_dry
        assert difference > 1.0  # Significant heat index effect
        print(f"Hot+humid (80%): {temp_humid:.1f}°C (feels like)")
        print(f"Hot+dry (30%): {temp_dry:.1f}°C")
        print(f"Heat index effect: {difference:+.1f}°C hotter")


class TestElevationCorrection:
    """Test elevation lapse rate correction."""
    
    def test_elevation_cooling_1000m(self):
        """Elevation 1000m should be cooler by ~6.5°C."""
        # Sea level
        temp_sea = calculate_weather_aware_temperature(
            hour=4,
            current_temp=20.0,
            temp_trend=0.0,
            forecast_code=5,
            current_hour=12,
            elevation=0
        )
        
        # 1000m elevation
        temp_mountain = calculate_weather_aware_temperature(
            hour=4,
            current_temp=20.0,
            temp_trend=0.0,
            forecast_code=5,
            current_hour=12,
            elevation=1000.0
        )
        
        # Lapse rate: -0.65°C/100m = -6.5°C at 1000m
        expected_diff = -0.0065 * 1000
        actual_diff = temp_mountain - temp_sea
        
        assert abs(actual_diff - expected_diff) < 0.1
        print(f"Sea level: {temp_sea:.1f}°C")
        print(f"1000m elevation: {temp_mountain:.1f}°C")
        print(f"Difference: {actual_diff:.1f}°C (expected: {expected_diff:.1f}°C)")
    
    def test_elevation_200m_small_effect(self):
        """Low elevation (200m) has small but measurable effect."""
        temp_low = calculate_weather_aware_temperature(
            hour=3,
            current_temp=15.0,
            temp_trend=0.0,
            forecast_code=10,
            current_hour=14,
            elevation=0
        )
        
        temp_elevated = calculate_weather_aware_temperature(
            hour=3,
            current_temp=15.0,
            temp_trend=0.0,
            forecast_code=10,
            current_hour=14,
            elevation=200.0
        )
        
        # Should be ~1.3°C cooler
        diff = temp_elevated - temp_low
        assert -1.5 < diff < -1.0
        print(f"0m: {temp_low:.1f}°C")
        print(f"200m: {temp_elevated:.1f}°C")
        print(f"Difference: {diff:.1f}°C")


class TestDynamicCloudCover:
    """Test dynamic cloud cover feedback."""
    
    def test_cloud_cover_50_percent(self):
        """50% cloud cover should give moderate cooling."""
        from custom_components.local_weather_forecast.combined_model import (
            _get_weather_temperature_adjustment
        )
        
        adj_50 = _get_weather_temperature_adjustment(
            forecast_code=14,  # Unsettled
            future_hour=14,
            solar_radiation=None,
            cloud_cover=50.0
        )
        
        # 50% clouds: -0.015 * 50 = -0.75°C
        assert -0.8 <= adj_50 <= -0.7
        print(f"50% cloud cover: {adj_50:.2f}°C")
    
    def test_cloud_cover_100_percent(self):
        """100% cloud cover should give maximum cooling."""
        from custom_components.local_weather_forecast.combined_model import (
            _get_weather_temperature_adjustment
        )
        
        adj_100 = _get_weather_temperature_adjustment(
            forecast_code=13,  # Cloudy
            future_hour=13,
            solar_radiation=None,
            cloud_cover=100.0
        )
        
        # 100% clouds: -0.015 * 100 = -1.5°C
        assert -1.6 <= adj_100 <= -1.4
        print(f"100% cloud cover: {adj_100:.2f}°C")
    
    def test_cloud_cover_fallback(self):
        """No cloud cover sensor should use default value."""
        from custom_components.local_weather_forecast.combined_model import (
            _get_weather_temperature_adjustment
        )
        
        adj_default = _get_weather_temperature_adjustment(
            forecast_code=14,
            future_hour=12,
            solar_radiation=None,
            cloud_cover=None  # No sensor
        )
        
        # Should use fallback: -0.8°C
        assert adj_default == -0.8
        print(f"No cloud sensor (fallback): {adj_default:.2f}°C")


class TestCombinedEffects:
    """Test multiple effects working together."""
    
    def test_cold_windy_dry_winter(self):
        """Cold, windy, dry winter night - all effects combine."""
        temp = calculate_weather_aware_temperature(
            hour=6,
            current_temp=0.0,
            temp_trend=0.0,
            forecast_code=5,  # Clear
            current_hour=22,  # Night
            humidity=30.0,  # Dry → cooling
            wind_speed=8.0,  # 8 m/s → wind chill
            elevation=200.0  # → -1.3°C
        )
        
        print(f"Cold windy dry winter: {temp:.1f}°C")
        # Should feel significantly colder than 0°C
        assert temp < -3.0
    
    def test_hot_humid_summer_afternoon(self):
        """Hot, humid summer afternoon - heat index effect."""
        temp = calculate_weather_aware_temperature(
            hour=3,
            current_temp=32.0,
            temp_trend=0.0,
            forecast_code=2,  # Sunny
            current_hour=13,  # Afternoon
            humidity=75.0,  # High humidity → heat index
            wind_speed=2.0,  # Light breeze
            elevation=0.0,
            current_month=7  # July
        )
        
        print(f"Hot humid summer: {temp:.1f}°C")
        # Should feel hotter than 32°C due to heat index
        assert temp > 33.0
