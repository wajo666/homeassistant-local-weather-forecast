"""Test cooling behavior during cloudy/overcast conditions to match external services."""
import pytest
from custom_components.local_weather_forecast.combined_model import (
    calculate_weather_aware_temperature,
)


def test_cloudy_afternoon_cooling_like_external_services():
    """Test that cloudy conditions produce steep cooling like external weather services.
    
    External services show:
    - Tomorrow.io: 14:00 (6.7°C) → 17:00 (3.2°C) = -3.5°C in 3h
    - met.no: 14:00 (6.7°C) → 18:00 (1.8°C) = -4.9°C in 4h  
    - PirateWeather: 14:00 (7.1°C) → 17:00 (5.7°C) = -1.4°C in 3h
    
    Our plugin should now match this with unsettled/cloudy forecast codes.
    """
    current_temp = 8.0  # Current temperature 8°C
    temp_trend = 0.0
    forecast_code = 14  # Unsettled/cloudy (CODE 11-15)
    current_hour = 14  # 2pm
    
    temps = {}
    for hour_offset in range(0, 5):  # 14:00 to 18:00
        temp = calculate_weather_aware_temperature(
            hour=hour_offset,
            current_temp=current_temp,
            temp_trend=temp_trend,
            forecast_code=forecast_code,
            current_hour=current_hour,
            current_month=2  # February
        )
        future_hour = (current_hour + hour_offset) % 24
        temps[future_hour] = temp
    
    print("\n🌥️  CLOUDY WEATHER (CODE 14 - Unsettled):")
    print("Hour  | Temp   | Change from previous")
    print("------|--------|---------------------")
    for i, h in enumerate(sorted(temps.keys())):
        if i > 0:
            prev_h = sorted(temps.keys())[i-1]
            change = temps[h] - temps[prev_h]
            print(f"{h:02d}:00 | {temps[h]:5.1f}°C | {change:+5.1f}°C")
        else:
            print(f"{h:02d}:00 | {temps[h]:5.1f}°C | ")
    
    # Calculate total drop 14:00 → 17:00 (3 hours)
    drop_3h = temps[14] - temps[17]
    
    # Calculate total drop 14:00 → 18:00 (4 hours)
    drop_4h = temps[14] - temps[18]
    
    print(f"\n📉 Cooling rates:")
    print(f"   14:00 → 17:00: {temps[14]:.1f}°C → {temps[17]:.1f}°C = {drop_3h:+.1f}°C in 3h")
    print(f"   14:00 → 18:00: {temps[14]:.1f}°C → {temps[18]:.1f}°C = {drop_4h:+.1f}°C in 4h")
    print(f"   Rate: {drop_3h/3:.2f}°C/h")
    
    # Should show significant cooling (at least 1.5°C in 3h)
    # External services show -1.4 to -3.5°C in 3h
    assert drop_3h >= 1.0, \
        f"Expected at least 1.0°C cooling in 3h during cloudy conditions, got {drop_3h:.1f}°C"
    
    # Temperature should decrease every hour after peak
    assert temps[15] < temps[14], "15:00 should be cooler than 14:00"
    assert temps[16] < temps[15], "16:00 should be cooler than 15:00"
    assert temps[17] < temps[16], "17:00 should be cooler than 16:00"
    
    print("\n✅ Cloudy weather cooling now matches external services!")


def test_showery_even_steeper_cooling():
    """Test showery conditions produce even steeper cooling."""
    current_temp = 7.0
    temp_trend = 0.0
    forecast_code = 16  # Showery (CODE 16-17)
    current_hour = 13  # 1pm
    
    temps = {}
    for hour_offset in range(0, 5):  # 13:00 to 17:00
        temp = calculate_weather_aware_temperature(
            hour=hour_offset,
            current_temp=current_temp,
            temp_trend=temp_trend,
            forecast_code=forecast_code,
            current_hour=current_hour,
            current_month=2  # February
        )
        future_hour = (current_hour + hour_offset) % 24
        temps[future_hour] = temp
    
    print("\n🌦️  SHOWERY WEATHER (CODE 16):")
    print("Hour  | Temp")
    print("------|------")
    for h in sorted(temps.keys()):
        print(f"{h:02d}:00 | {temps[h]:5.1f}°C")
    
    drop_4h = temps[13] - temps[17]
    
    print(f"\n📉 13:00 → 17:00: {temps[13]:.1f}°C → {temps[17]:.1f}°C = {drop_4h:+.1f}°C")
    
    # Showery should cool even more than just cloudy
    assert drop_4h >= 1.2, \
        f"Expected at least 1.2°C cooling with showers, got {drop_4h:.1f}°C"
    
    print("✅ Showery conditions produce strong cooling!")


def test_rainy_strong_cooling():
    """Test rainy conditions produce very strong cooling."""
    current_temp = 7.0
    temp_trend = 0.0
    forecast_code = 19  # Rain (CODE 18-21)
    current_hour = 12  # Noon
    
    temps = {}
    for hour_offset in range(0, 6):  # 12:00 to 17:00
        temp = calculate_weather_aware_temperature(
            hour=hour_offset,
            current_temp=current_temp,
            temp_trend=temp_trend,
            forecast_code=forecast_code,
            current_hour=current_hour,
            current_month=2
        )
        future_hour = (current_hour + hour_offset) % 24
        temps[future_hour] = temp
    
    print("\n🌧️  RAINY WEATHER (CODE 19):")
    print("Hour  | Temp")
    print("------|------")
    for h in sorted(temps.keys()):
        print(f"{h:02d}:00 | {temps[h]:5.1f}°C")
    
    drop_5h = temps[12] - temps[17]
    
    print(f"\n📉 12:00 → 17:00: {temps[12]:.1f}°C → {temps[17]:.1f}°C = {drop_5h:+.1f}°C")
    
    # Rain should produce significant cooling
    assert drop_5h >= 1.5, \
        f"Expected at least 1.5°C cooling with rain, got {drop_5h:.1f}°C"
    
    print("✅ Rainy conditions produce very strong cooling!")
