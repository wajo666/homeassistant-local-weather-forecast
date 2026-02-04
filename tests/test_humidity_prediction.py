"""Test humidity prediction using Clausius-Clapeyron equation."""
import pytest
from custom_components.local_weather_forecast.calculations import calculate_future_humidity


class TestHumidityPrediction:
    """Test humidity prediction for forecasts."""
    
    def test_temperature_increase_decreases_humidity(self):
        """When temperature rises, relative humidity should fall (constant absolute humidity)."""
        # Scenario: Morning warming (5°C → 15°C)
        # 90% RH at 5°C should drop significantly as air warms
        result = calculate_future_humidity(
            current_temperature=5.0,
            current_humidity=90.0,
            future_temperature=15.0
        )
        
        assert result is not None
        assert result < 90.0, "RH should decrease when temperature rises"
        assert 40 < result < 50, f"Expected RH ~46%, got {result}%"
    
    def test_temperature_decrease_increases_humidity(self):
        """When temperature falls, relative humidity should rise (constant absolute humidity)."""
        # Scenario: Evening cooling (15°C → 5°C)
        # 50% RH at 15°C should rise significantly as air cools
        result = calculate_future_humidity(
            current_temperature=15.0,
            current_humidity=50.0,
            future_temperature=5.0
        )
        
        assert result is not None
        assert result > 50.0, "RH should increase when temperature falls"
        assert 95 < result <= 100, f"Expected RH ~98% (near saturation), got {result}%"
    
    def test_no_temperature_change_preserves_humidity(self):
        """When temperature stays constant, RH should remain constant."""
        result = calculate_future_humidity(
            current_temperature=15.0,
            current_humidity=70.0,
            future_temperature=15.0
        )
        
        assert result is not None
        assert abs(result - 70.0) < 1.0, f"RH should stay ~70%, got {result}%"
    
    def test_saturation_limit(self):
        """RH should never exceed 100% (saturation)."""
        # Start with high humidity and cool significantly
        result = calculate_future_humidity(
            current_temperature=20.0,
            current_humidity=95.0,
            future_temperature=5.0
        )
        
        assert result is not None
        assert result <= 100.0, f"RH cannot exceed 100%, got {result}%"
        assert result == 100.0, "Should reach saturation (100% RH)"
    
    def test_realistic_scenario_your_data(self):
        """Test with your actual data: 2.6°C, 94.2% RH, temp rising to 3.3°C."""
        # Your scenario: slight warming should slightly reduce RH
        result = calculate_future_humidity(
            current_temperature=2.6,
            current_humidity=94.2,
            future_temperature=3.3,
            pressure_change=-2.7  # Falling pressure
        )
        
        assert result is not None
        # Slight warming (0.7°C) → RH drops from 94.2% to ~91.5%
        # But falling pressure (-2.7 hPa → +0.27% RH) reduces drop
        # Final: ~91.5% + 0.27% = ~91.8% but clamped
        assert 88 < result < 92, f"Expected RH ~90%, got {result}%"
        assert result < 94.2, "RH should decrease slightly with warming"
    
    def test_winter_evening_condensation_risk(self):
        """Test evening cooling in winter - fog/frost risk."""
        # Scenario: Clear winter evening, temp drops from 5°C to -2°C
        # 75% RH should approach saturation
        result = calculate_future_humidity(
            current_temperature=5.0,
            current_humidity=75.0,
            future_temperature=-2.0
        )
        
        assert result is not None
        assert result > 95.0, "Should approach saturation (fog/frost risk)"
    
    def test_summer_afternoon_drying(self):
        """Test afternoon heating in summer - low humidity."""
        # Scenario: Morning 20°C, 80% RH → Afternoon 30°C
        # RH should drop significantly
        result = calculate_future_humidity(
            current_temperature=20.0,
            current_humidity=80.0,
            future_temperature=30.0
        )
        
        assert result is not None
        assert result < 50.0, f"Expected dry conditions (<50% RH), got {result}%"
    
    def test_pressure_effect(self):
        """Test adiabatic effect of pressure changes on humidity."""
        # Scenario: Constant temperature, but pressure changes
        
        # Rising pressure (compression) → slight RH reduction
        result_rising = calculate_future_humidity(
            current_temperature=15.0,
            current_humidity=70.0,
            future_temperature=15.0,
            pressure_change=+10.0  # +10 hPa
        )
        
        # Falling pressure (expansion) → slight RH increase
        result_falling = calculate_future_humidity(
            current_temperature=15.0,
            current_humidity=70.0,
            future_temperature=15.0,
            pressure_change=-10.0  # -10 hPa
        )
        
        assert result_rising is not None
        assert result_falling is not None
        assert result_rising < 70.0, "Rising pressure should reduce RH"
        assert result_falling > 70.0, "Falling pressure should increase RH"
        assert result_falling > result_rising, "Falling P → higher RH than rising P"
    
    def test_invalid_humidity(self):
        """Test error handling for invalid humidity values."""
        assert calculate_future_humidity(15.0, -10.0, 20.0) is None
        assert calculate_future_humidity(15.0, 110.0, 20.0) is None
        assert calculate_future_humidity(15.0, 0.0, 20.0) is None
