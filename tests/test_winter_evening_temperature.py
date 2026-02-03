"""Test winter evening temperature prediction fix.

This test verifies that temperature predictions in winter evening hours
(after sunset) correctly account for:
1. Actual sunrise/sunset times (not fixed 06:00-18:00)
2. Shorter daylight duration in winter
3. Temperature cooling after sunset (not warming)
4. Hemisphere and seasonal amplitude adjustments
"""
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import pytest

from custom_components.local_weather_forecast.forecast_calculator import TemperatureModel


class MockSunEntity:
    """Mock sun.sun entity for testing."""
    
    def __init__(self, sunrise_hour: float = 6.0, sunset_hour: float = 15.5):
        """Initialize mock sun entity.
        
        Args:
            sunrise_hour: Sunrise time in hours (e.g., 6.0 = 06:00)
            sunset_hour: Sunset time in hours (e.g., 15.5 = 15:30)
        """
        self.sunrise_hour = sunrise_hour
        self.sunset_hour = sunset_hour
        
        # Create mock datetime strings
        sunrise_time = datetime(2026, 2, 3, int(sunrise_hour), int((sunrise_hour % 1) * 60), tzinfo=timezone.utc)
        sunset_time = datetime(2026, 2, 3, int(sunset_hour), int((sunset_hour % 1) * 60), tzinfo=timezone.utc)
        
        self.attributes = {
            "next_rising": sunrise_time.isoformat(),
            "next_setting": sunset_time.isoformat(),
        }
        self.state = "below_horizon"


@pytest.fixture
def mock_hass_winter():
    """Mock Home Assistant instance with winter sun times."""
    mock_hass = Mock()
    # Winter in Slovakia: sunrise ~06:00, sunset ~15:30
    mock_hass.states.get.return_value = MockSunEntity(sunrise_hour=6.0, sunset_hour=15.5)
    mock_hass.config.latitude = 48.72  # Košice, Slovakia
    mock_hass.config.longitude = 21.25
    return mock_hass


class TestWinterEveningTemperature:
    """Test temperature predictions for winter evening scenarios."""
    
    def test_winter_evening_cooling_after_sunset(self, mock_hass_winter):
        """Test that temperature decreases in winter evening (after sunset).
        
        Scenario: It's 16:00 (4pm) in February, temperature is 0°C.
        Sunset was at 15:30. Temperature should continue cooling, not warming.
        Prediction for 19:00 should be LOWER than current temperature.
        """
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Current time: 16:00 (4pm) - after sunset
            mock_dt.now.return_value = datetime(2026, 2, 3, 16, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model = TemperatureModel(
                current_temp=0.0,
                change_rate_1h=0.0,  # No trend
                hass=mock_hass_winter,
                hemisphere="north"
            )
            
            # Predict temperature 3 hours later (19:00)
            predicted_temp_19h = model.predict(3)
            
            # After sunset in winter with no warming trend, temperature should decrease
            # or at worst stay the same (due to diurnal cooling at night)
            assert predicted_temp_19h <= 0.5, (
                f"Temperature at 19:00 should not be significantly warmer than 16:00 "
                f"(current: 0.0°C, predicted: {predicted_temp_19h:.1f}°C). "
                f"After sunset in winter, temperature should cool down, not warm up."
            )
    
    def test_winter_evening_no_unrealistic_warming(self, mock_hass_winter):
        """Test that winter evening doesn't show unrealistic +5°C warming.
        
        Scenario from user report: Temperature all day ~0°C, but prediction for 
        19:00 shows 5.3°C. This is unrealistic after sunset in winter.
        """
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Current time: 16:00, temperature has been ~0°C all day
            mock_dt.now.return_value = datetime(2026, 2, 3, 16, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model = TemperatureModel(
                current_temp=0.0,
                change_rate_1h=0.1,  # Slight warming trend (unrealistic for evening)
                hass=mock_hass_winter,
                hemisphere="north"
            )
            
            # Predict temperature at 19:00 (3 hours later)
            predicted_temp_19h = model.predict(3)
            
            # Should NOT predict 5.3°C when current is 0°C and sun has set
            assert predicted_temp_19h < 3.0, (
                f"Temperature at 19:00 = {predicted_temp_19h:.1f}°C is unrealistic. "
                f"After sunset in winter, temperature should not rise by >3°C from 0°C."
            )
    
    def test_winter_daylight_duration_affects_amplitude(self, mock_hass_winter):
        """Test that shorter winter days reduce diurnal amplitude.
        
        Winter days (9.5h daylight) should have less temperature swing than
        summer days (16h daylight).
        """
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Morning: 08:00 (after sunrise at 06:00)
            mock_dt.now.return_value = datetime(2026, 2, 3, 8, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model = TemperatureModel(
                current_temp=0.0,
                change_rate_1h=0.0,
                hass=mock_hass_winter,
                hemisphere="north"
            )
            
            # Predict peak temperature (around 14:00)
            temp_at_peak = model.predict(6)  # 08:00 + 6h = 14:00
            
            # Predict evening temperature (19:00)
            temp_at_evening = model.predict(11)  # 08:00 + 11h = 19:00
            
            # Peak should be warmer than morning
            assert temp_at_peak > 0.0, "Peak temperature should be warmer than morning"
            
            # Evening (after sunset) should be cooling back down
            assert temp_at_evening < temp_at_peak, (
                f"Evening temp ({temp_at_evening:.1f}°C) should be cooler than "
                f"peak temp ({temp_at_peak:.1f}°C) after sunset"
            )
            
            # Total swing should be reasonable for winter (not >6°C in 9.5h daylight)
            total_swing = abs(temp_at_peak - 0.0)
            assert total_swing < 6.0, (
                f"Winter daylight (9.5h) should limit temperature swing to <6°C, "
                f"got {total_swing:.1f}°C"
            )
    
    def test_comparison_with_forecast_temp_short(self, mock_hass_winter):
        """Test that diurnal model aligns with forecast_temp_short expectations.
        
        If forecast_temp_short predicts 1.7°C and the temperature has been ~0°C
        all day, the diurnal model should not predict 5.3°C.
        """
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            # Current time: afternoon after sunset
            mock_dt.now.return_value = datetime(2026, 2, 3, 16, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Scenario: current temp ~0°C, minimal warming trend
            model = TemperatureModel(
                current_temp=0.2,
                change_rate_1h=0.05,  # Very slight warming (0.15°C over 3h)
                hass=mock_hass_winter,
                hemisphere="north"
            )
            
            # Predict 3 hours ahead (19:00)
            predicted = model.predict(3)
            
            # Expected: ~0.2 + 0.15 (trend) - some cooling (night) ≈ 0.0 to 1.0°C
            # Should be close to forecast_temp_short's 1.7°C, not 5.3°C
            assert -1.0 <= predicted <= 2.5, (
                f"Predicted {predicted:.1f}°C is inconsistent with forecast_temp_short (1.7°C). "
                f"Should be in range -1.0 to 2.5°C for winter evening with minimal trend."
            )
    
    def test_hemisphere_south_reverses_seasons(self):
        """Test that southern hemisphere reverses seasonal amplitude.
        
        February in southern hemisphere = summer (should have larger amplitude).
        """
        mock_hass_south = Mock()
        # Summer in southern hemisphere: longer days
        mock_hass_south.states.get.return_value = MockSunEntity(sunrise_hour=5.0, sunset_hour=19.0)
        mock_hass_south.config.latitude = -33.87  # Sydney, Australia
        mock_hass_south.config.longitude = 151.21
        
        with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 3, 8, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            model_south = TemperatureModel(
                current_temp=20.0,
                change_rate_1h=0.0,
                hass=mock_hass_south,
                hemisphere="south"
            )
            
            # Predict peak temperature
            temp_at_peak = model_south.predict(6)
            
            # Southern hemisphere February = summer, should have larger temperature swing
            swing = abs(temp_at_peak - 20.0)
            assert swing > 3.0, (
                f"Southern hemisphere summer should have larger diurnal swing, "
                f"got {swing:.1f}°C"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
