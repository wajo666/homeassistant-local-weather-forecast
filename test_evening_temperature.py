"""Test case for evening temperature behavior - should not rise after 16:00."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from custom_components.local_weather_forecast.forecast_calculator import TemperatureModel


def test_evening_temperature_should_not_rise():
    """
    Test that temperature does not rise in the evening even with positive trend.
    
    Situation: 14:00, temp=2.6°C, trend=+0.8°C/h
    Expected: Temperature should NOT rise after 16:00, should start cooling
    """
    with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
        # Current time: 14:00 (14:11 in user's case)
        mock_dt.now.return_value = datetime(2026, 2, 4, 14, 11, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Mock sun entity with realistic winter times
        mock_hass = Mock()
        mock_sun = Mock()
        mock_sun.attributes = {
            'next_rising': '2026-02-05T06:00:00+00:00',
            'next_setting': '2026-02-04T16:00:00+00:00'
        }
        mock_hass.states.get.return_value = mock_sun
        
        model = TemperatureModel(
            current_temp=2.6,
            change_rate_1h=0.8,  # Strong warming trend
            diurnal_amplitude=None,  # Auto-calculate from season
            hass=mock_hass,
            latitude=48.72,
            longitude=21.25
        )
        
        # Predictions
        temp_now = model.predict(0)  # 14:11
        temp_1h = model.predict(1)   # 15:11
        temp_2h = model.predict(2)   # 16:11
        temp_3h = model.predict(3)   # 17:11
        temp_4h = model.predict(4)   # 18:11
        temp_5h = model.predict(5)   # 19:11
        temp_6h = model.predict(6)   # 20:11
        
        print(f"\nTest results:")
        print(f"Current hour: {model.current_hour}")
        print(f"Diurnal amplitude: {model.diurnal_amplitude:.1f}°C")
        print(f"\n14:11 (now): {temp_now:.1f}°C")
        print(f"15:11 (+1h): {temp_1h:.1f}°C (Δ={temp_1h - temp_now:+.1f}°C)")
        print(f"16:11 (+2h): {temp_2h:.1f}°C (Δ={temp_2h - temp_1h:+.1f}°C)")
        print(f"17:11 (+3h): {temp_3h:.1f}°C (Δ={temp_3h - temp_2h:+.1f}°C)")
        print(f"18:11 (+4h): {temp_4h:.1f}°C (Δ={temp_4h - temp_3h:+.1f}°C)")
        print(f"19:11 (+5h): {temp_5h:.1f}°C (Δ={temp_5h - temp_4h:+.1f}°C)")
        print(f"20:11 (+6h): {temp_6h:.1f}°C (Δ={temp_6h - temp_5h:+.1f}°C)")
        
        # Key assertions:
        # 1. At 14:00, we're at or near maximum
        assert temp_now == 2.6, "Current temperature should match"
        
        # 2. After 16:00, temperature should be cooling or stable, NOT rising significantly
        # Allow small rise (+0.5°C max) from 15:11 to 16:11 due to slight lag
        assert temp_2h - temp_1h < 0.5, f"Temperature should not rise significantly after 16:00 (got {temp_2h - temp_1h:+.1f}°C)"
        
        # 3. Evening temperatures (17:00-20:00) should be lower than 16:00
        assert temp_3h < temp_2h + 0.3, f"17:11 should not be warmer than 16:11 (got {temp_3h:.1f} vs {temp_2h:.1f})"
        assert temp_4h < temp_2h + 0.3, f"18:11 should not be warmer than 16:11 (got {temp_4h:.1f} vs {temp_2h:.1f})"
        assert temp_5h < temp_2h + 0.5, f"19:11 should not be much warmer than 16:11 (got {temp_5h:.1f} vs {temp_2h:.1f})"
        
        # 4. Temperature at 20:00 should definitely not be 7°C (as in user's report)
        assert temp_6h < 5.0, f"Temperature at 20:11 is unrealistically high: {temp_6h:.1f}°C (expected < 5.0°C)"
        
        print("\n✓ Test passed: Temperature behaves realistically in the evening")


if __name__ == "__main__":
    test_evening_temperature_should_not_rise()
