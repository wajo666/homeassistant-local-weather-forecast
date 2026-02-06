"""Test that sensor short-term temp uses forecast-aware temperature."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from custom_components.local_weather_forecast.combined_model import (
    calculate_weather_aware_temperature
)


def test_short_term_temp_sunny_vs_rainy():
    """Compare short-term temperature for sunny vs rainy forecasts."""
    print("\n🌡️ Short-Term Temperature: Sunny vs Rainy")
    
    # Same starting conditions
    current_temp = 10.0
    temp_trend = 0.1  # Slight warming trend
    current_hour = 12  # Noon
    hours_ahead = 6  # 6h forecast (typical for first_time)
    
    # Sunny forecast (code 2: "Fine")
    sunny_temp = calculate_weather_aware_temperature(
        hour=hours_ahead,
        current_temp=current_temp,
        temp_trend=temp_trend,
        forecast_code=2,  # Fine weather
        current_hour=current_hour
    )
    
    # Rainy forecast (code 21: "Rain, worsening")
    rainy_temp = calculate_weather_aware_temperature(
        hour=hours_ahead,
        current_temp=current_temp,
        temp_trend=temp_trend,
        forecast_code=21,  # Very wet
        current_hour=current_hour
    )
    
    print(f"  Starting: {current_temp}°C at {current_hour}:00")
    print(f"  Trend: {temp_trend:+.3f}°C/h")
    print(f"  Forecast period: {hours_ahead}h")
    print(f"\n  Sunny forecast (code 2):  {sunny_temp:.1f}°C")
    print(f"  Rainy forecast (code 21): {rainy_temp:.1f}°C")
    print(f"  Difference: {sunny_temp - rainy_temp:.1f}°C")
    
    # Sunny should be warmer than rainy
    assert sunny_temp > rainy_temp, \
        f"Sunny should be warmer: {sunny_temp}°C vs {rainy_temp}°C"
    
    # Difference should be meaningful
    difference = sunny_temp - rainy_temp
    assert difference >= 0.5, \
        f"Difference should be at least 0.5°C over 6h, got {difference:.1f}°C"
    
    print(f"\n✅ Short-term temp uses forecast bias correctly!")


def test_short_term_temp_progression():
    """Test that forecast bias affects temperatures over time."""
    print("\n📊 Short-Term Temperature Progression")
    
    current_temp = 8.0
    temp_trend = 0.0  # No historical trend - pure forecast effect
    current_hour = 9
    
    # Test at different time horizons
    scenarios = [
        (2, "☀️ Sunny"),
        (12, "☁️ Cloudy"),
        (21, "🌧️ Rainy")
    ]
    
    print(f"\n  Starting: {current_temp}°C, no historical trend")
    print(f"\n  Hours |   Sunny   |  Cloudy   |   Rainy   | Spread")
    print(f"  ------|-----------|-----------|-----------|-------")
    
    for hours in [3, 6, 9, 12]:
        temps = []
        for code, _ in scenarios:
            temp = calculate_weather_aware_temperature(
                hour=hours,
                current_temp=current_temp,
                temp_trend=temp_trend,
                forecast_code=code,
                current_hour=current_hour
            )
            temps.append(temp)
        
        spread = temps[0] - temps[2]  # Sunny - Rainy
        print(f"  {hours:3d}h  | {temps[0]:6.1f}°C  | {temps[1]:6.1f}°C  | {temps[2]:6.1f}°C  | {spread:5.1f}°C")
    
    # Verify that forecast bias has meaningful effect at all time periods
    # Spread varies with diurnal cycle but should always be present
    for hours in [3, 6, 9, 12]:
        sunny = calculate_weather_aware_temperature(hours, current_temp, temp_trend, 2, current_hour)
        rainy = calculate_weather_aware_temperature(hours, current_temp, temp_trend, 21, current_hour)
        
        assert sunny > rainy, \
            f"At {hours}h: Sunny should be warmer than rainy ({sunny:.1f}°C vs {rainy:.1f}°C)"
        
        spread = sunny - rainy
        assert spread >= 0.5, \
            f"At {hours}h: Spread should be at least 0.5°C, got {spread:.1f}°C"
    
    print(f"\n✅ Forecast bias works consistently across all time periods!")


if __name__ == "__main__":
    test_short_term_temp_sunny_vs_rainy()
    test_short_term_temp_progression()
    print("\n🎉 All short-term temperature tests passed!")
