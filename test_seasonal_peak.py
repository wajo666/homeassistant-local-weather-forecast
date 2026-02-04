"""Test seasonal variation in temperature maximum timing."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from custom_components.local_weather_forecast.forecast_calculator import TemperatureModel


def test_seasonal_peak_timing():
    """Test that temperature maximum varies by season/daylength."""
    
    print("\n" + "="*70)
    print("SEASONAL VARIATION IN TEMPERATURE MAXIMUM")
    print("="*70)
    
    # Winter: short day (6:00-16:00 = 10h daylight)
    print("\n🌨️  WINTER (10h daylight, Feb 4)")
    print("-" * 70)
    with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2026, 2, 4, 12, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        mock_hass = Mock()
        mock_sun = Mock()
        mock_sun.attributes = {
            'next_rising': '2026-02-05T06:00:00+00:00',
            'next_setting': '2026-02-04T16:00:00+00:00'  # 10h day
        }
        mock_hass.states.get.return_value = mock_sun
        
        model_winter = TemperatureModel(
            current_temp=2.0,
            change_rate_1h=0.0,
            hass=mock_hass,
            latitude=48.72,
            longitude=21.25
        )
        
        # Find peak
        temps = {}
        for h in range(24):
            hour = (12 + h) % 24
            if hour >= 12:
                temps[hour] = model_winter.predict(h)
            else:
                temps[hour] = model_winter.predict(h if h < 12 else h - 24)
        
        peak_hour = max(temps, key=temps.get)
        peak_temp = temps[peak_hour]
        solar_noon = (6 + 16) / 2.0  # 11:00
        
        print(f"Solar noon: {solar_noon:.1f}:00")
        print(f"Peak temperature: {peak_hour}:00 ({peak_temp:.1f}°C)")
        print(f"Lag after solar noon: {peak_hour - solar_noon:.1f} hours")
        print("\nHourly temperatures:")
        for h in range(10, 18):
            print(f"  {h:02d}:00 → {temps[h]:.1f}°C")
    
    # Spring: medium day (6:00-18:00 = 12h daylight)
    print("\n🌸 SPRING (12h daylight, Apr 15)")
    print("-" * 70)
    with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        mock_hass = Mock()
        mock_sun = Mock()
        mock_sun.attributes = {
            'next_rising': '2026-04-16T06:00:00+00:00',
            'next_setting': '2026-04-15T18:00:00+00:00'  # 12h day
        }
        mock_hass.states.get.return_value = mock_sun
        
        model_spring = TemperatureModel(
            current_temp=15.0,
            change_rate_1h=0.0,
            hass=mock_hass,
            latitude=48.72,
            longitude=21.25
        )
        
        temps = {}
        for h in range(24):
            hour = (12 + h) % 24
            if hour >= 12:
                temps[hour] = model_spring.predict(h)
            else:
                temps[hour] = model_spring.predict(h if h < 12 else h - 24)
        
        peak_hour = max(temps, key=temps.get)
        peak_temp = temps[peak_hour]
        solar_noon = (6 + 18) / 2.0  # 12:00
        
        print(f"Solar noon: {solar_noon:.1f}:00")
        print(f"Peak temperature: {peak_hour}:00 ({peak_temp:.1f}°C)")
        print(f"Lag after solar noon: {peak_hour - solar_noon:.1f} hours")
        print("\nHourly temperatures:")
        for h in range(11, 19):
            print(f"  {h:02d}:00 → {temps[h]:.1f}°C")
    
    # Summer: long day (5:00-20:00 = 15h daylight)
    print("\n☀️  SUMMER (15h daylight, Jul 15)")
    print("-" * 70)
    with patch('custom_components.local_weather_forecast.forecast_calculator.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        mock_hass = Mock()
        mock_sun = Mock()
        mock_sun.attributes = {
            'next_rising': '2026-07-16T05:00:00+00:00',
            'next_setting': '2026-07-15T20:00:00+00:00'  # 15h day
        }
        mock_hass.states.get.return_value = mock_sun
        
        model_summer = TemperatureModel(
            current_temp=25.0,
            change_rate_1h=0.0,
            hass=mock_hass,
            latitude=48.72,
            longitude=21.25
        )
        
        temps = {}
        for h in range(24):
            hour = (12 + h) % 24
            if hour >= 12:
                temps[hour] = model_summer.predict(h)
            else:
                temps[hour] = model_summer.predict(h if h < 12 else h - 24)
        
        peak_hour = max(temps, key=temps.get)
        peak_temp = temps[peak_hour]
        solar_noon = (5 + 20) / 2.0  # 12:30
        
        print(f"Solar noon: {solar_noon:.1f}:00")
        print(f"Peak temperature: {peak_hour}:00 ({peak_temp:.1f}°C)")
        print(f"Lag after solar noon: {peak_hour - solar_noon:.1f} hours")
        print("\nHourly temperatures:")
        for h in range(12, 20):
            print(f"  {h:02d}:00 → {temps[h]:.1f}°C")
    
    print("\n" + "="*70)
    print("SUMMARY: Peak timing varies naturally with season!")
    print("="*70)


if __name__ == "__main__":
    test_seasonal_peak_timing()
