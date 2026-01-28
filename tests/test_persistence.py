"""Unit tests for Persistence Model."""

import pytest
from custom_components.local_weather_forecast.persistence import (
    calculate_persistence_forecast,
    get_persistence_confidence,
    get_current_condition_code,
)


class TestCalculatePersistenceForecast:
    """Test calculate_persistence_forecast() function."""
    
    def test_hour_0_returns_current_code(self):
        """Test that hour 0 returns exact current condition."""
        current_code = 5  # Fine weather
        result = calculate_persistence_forecast(current_code, lang_index=1, hours_ahead=0)
        
        assert result[1] == 5  # Same code
        assert result[3] == 0.98  # 98% confidence
    
    def test_hour_1_returns_current_code(self):
        """Test that hour 1 still returns current condition."""
        current_code = 12  # Cloudy
        result = calculate_persistence_forecast(current_code, lang_index=1, hours_ahead=1)
        
        assert result[1] == 12  # Same code
        assert result[3] == 0.95  # 95% confidence
    
    def test_forecast_text_from_unified_mapping(self):
        """Test that forecast text comes from unified mapping."""
        current_code = 0  # Settled fine
        result = calculate_persistence_forecast(current_code, lang_index=1, hours_ahead=0)
        
        assert isinstance(result[0], str)  # Text present
        assert len(result[0]) > 0  # Not empty
    
    def test_letter_code_generation(self):
        """Test letter code generation (A-Z)."""
        # Code 0-2 → A
        result = calculate_persistence_forecast(0, lang_index=1, hours_ahead=0)
        assert result[2] == 'A'
        
        # Code 21-23 → H
        result = calculate_persistence_forecast(21, lang_index=1, hours_ahead=0)
        assert result[2] == 'H'
    
    def test_confidence_decreases_with_time(self):
        """Test that confidence decreases as hours_ahead increases."""
        result_0h = calculate_persistence_forecast(5, lang_index=1, hours_ahead=0)
        result_1h = calculate_persistence_forecast(5, lang_index=1, hours_ahead=1)
        result_3h = calculate_persistence_forecast(5, lang_index=1, hours_ahead=3)
        
        assert result_0h[3] > result_1h[3]  # Hour 0 > Hour 1
        assert result_1h[3] > result_3h[3]  # Hour 1 > Hour 3


class TestGetPersistenceConfidence:
    """Test get_persistence_confidence() function."""
    
    def test_hour_0_highest_confidence(self):
        """Test hour 0 has 98% confidence."""
        assert get_persistence_confidence(0) == 0.98
    
    def test_hour_1_very_high_confidence(self):
        """Test hour 1 has 95% confidence."""
        assert get_persistence_confidence(1) == 0.95
    
    def test_hour_2_high_confidence(self):
        """Test hour 2 has 90% confidence."""
        assert get_persistence_confidence(2) == 0.90
    
    def test_hour_3_good_confidence(self):
        """Test hour 3 has 85% confidence."""
        assert get_persistence_confidence(3) == 0.85
    
    def test_confidence_decays_after_3h(self):
        """Test confidence decays for hours > 3."""
        conf_3h = get_persistence_confidence(3)
        conf_6h = get_persistence_confidence(6)
        conf_12h = get_persistence_confidence(12)
        
        assert conf_6h < conf_3h
        assert conf_12h < conf_6h
        assert conf_12h >= 0.60  # Minimum threshold
    
    def test_minimum_confidence_floor(self):
        """Test that confidence never goes below 60%."""
        # Test very long forecast
        conf_24h = get_persistence_confidence(24)
        conf_100h = get_persistence_confidence(100)
        
        assert conf_24h >= 0.60
        assert conf_100h >= 0.60


class TestGetCurrentConditionCode:
    """Test get_current_condition_code() function."""
    
    def test_snow_from_weather_sensor(self):
        """Test that snow is detected from weather_condition sensor."""
        code = get_current_condition_code(
            temperature=-2.0,
            pressure=1010.0,
            humidity=85.0,
            dewpoint=-4.0,
            weather_condition="snowy"
        )
        
        assert code == 19  # Snow code
    
    def test_mixed_precipitation_from_sensor(self):
        """Test mixed snow/rain detection."""
        code = get_current_condition_code(
            temperature=1.0,
            pressure=1005.0,
            humidity=90.0,
            dewpoint=0.0,
            weather_condition="snowy-rainy"
        )
        
        assert code == 20  # Mixed precipitation
    
    def test_rain_from_weather_sensor(self):
        """Test that rain is detected from weather_condition sensor."""
        code = get_current_condition_code(
            temperature=10.0,
            pressure=1000.0,
            humidity=85.0,
            dewpoint=8.0,
            weather_condition="rainy"
        )
        
        assert code == 18  # Rain code
    
    def test_heavy_rain_from_sensor(self):
        """Test heavy rain (pouring) detection."""
        code = get_current_condition_code(
            temperature=12.0,
            pressure=995.0,
            humidity=90.0,
            dewpoint=11.0,
            weather_condition="pouring"
        )
        
        assert code == 21  # Heavy rain
    
    def test_storm_from_weather_sensor(self):
        """Test storm detection from weather_condition sensor."""
        code = get_current_condition_code(
            temperature=12.0,
            pressure=975.0,
            humidity=90.0,
            dewpoint=11.0,
            weather_condition="lightning-rainy"
        )
        
        assert code == 24  # Storm code
    
    def test_cloudy_from_weather_sensor(self):
        """Test cloudy detection from sensor."""
        code = get_current_condition_code(
            temperature=15.0,
            pressure=1010.0,
            humidity=70.0,
            dewpoint=10.0,
            weather_condition="cloudy"
        )
        
        assert code == 13  # Cloudy
    
    def test_partly_cloudy_from_sensor(self):
        """Test partly cloudy detection."""
        code = get_current_condition_code(
            temperature=18.0,
            pressure=1018.0,
            humidity=60.0,
            dewpoint=10.0,
            weather_condition="partlycloudy"
        )
        
        assert code == 10  # Partly cloudy
    
    def test_sunny_from_weather_sensor(self):
        """Test sunny detection from sensor."""
        code = get_current_condition_code(
            temperature=22.0,
            pressure=1025.0,
            humidity=55.0,
            dewpoint=12.0,
            weather_condition="sunny"
        )
        
        assert code == 2  # Fine weather
    
    def test_fine_weather_detection(self):
        """Test detection of fine weather (high pressure) - fallback."""
        code = get_current_condition_code(
            temperature=20.0,
            pressure=1025.0,
            humidity=60.0,
            dewpoint=12.0,
            weather_condition=None  # No weather sensor
        )
        
        assert 0 <= code <= 7  # Fine weather range
    
    def test_rainy_weather_detection(self):
        """Test detection of rainy weather (low pressure) - fallback."""
        code = get_current_condition_code(
            temperature=15.0,
            pressure=995.0,
            humidity=85.0,
            dewpoint=13.0,
            weather_condition=None  # No weather sensor
        )
        
        assert 15 <= code <= 21  # Rainy weather range
    
    def test_stormy_weather_detection(self):
        """Test detection of stormy weather (very low pressure) - fallback."""
        code = get_current_condition_code(
            temperature=12.0,
            pressure=975.0,
            humidity=90.0,
            dewpoint=11.0,
            weather_condition=None  # No weather sensor
        )
        
        assert 22 <= code <= 25  # Storm range
    
    def test_returns_valid_code_range(self):
        """Test that code is always in valid range (0-25)."""
        # Test various conditions
        conditions = [
            (20.0, 1030.0, 50.0, 10.0),  # High pressure
            (15.0, 1013.0, 70.0, 10.0),  # Normal pressure
            (10.0, 990.0, 90.0, 9.0),    # Low pressure
        ]
        
        for temp, press, hum, dew in conditions:
            code = get_current_condition_code(temp, press, hum, dew)
            assert 0 <= code <= 25
    
    def test_without_weather_condition(self):
        """Test that function works without weather_condition parameter."""
        code = get_current_condition_code(
            temperature=18.0,
            pressure=1015.0,
            humidity=65.0,
            dewpoint=11.0
        )
        
        assert 0 <= code <= 25  # Valid code returned
