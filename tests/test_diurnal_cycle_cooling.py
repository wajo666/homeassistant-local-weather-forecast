"""Test that diurnal cycle properly cools after afternoon maximum."""
import pytest
from custom_components.local_weather_forecast.combined_model import (
    calculate_weather_aware_temperature,
)


def test_temperature_decreases_after_3pm():
    """Verify temperature starts dropping after 3pm (15:00)."""
    current_temp = 10.0
    temp_trend = 0.0  # No trend to isolate diurnal effect
    forecast_code = 10  # Neutral weather
    current_hour = 9  # 9am
    
    # Calculate temperatures at different times
    temps = {}
    for hour_offset in [6, 7, 8, 9, 10]:  # 15:00, 16:00, 17:00, 18:00, 19:00
        temp = calculate_weather_aware_temperature(
            hour=hour_offset,
            current_temp=current_temp,
            temp_trend=temp_trend,
            forecast_code=forecast_code,
            current_hour=current_hour
        )
        future_hour = (current_hour + hour_offset) % 24
        temps[future_hour] = temp
        print(f"{future_hour:02d}:00 → {temp:.1f}°C")
    
    # Temperature should be lower at 19:00 than at peak (15:00-16:00)
    peak_temp = max(temps[15], temps[16])
    assert temps[18] <= peak_temp, \
        f"18:00 ({temps[18]:.1f}°C) should not be warmer than peak ({peak_temp:.1f}°C)"
    assert temps[19] < peak_temp, \
        f"19:00 ({temps[19]:.1f}°C) should be cooler than peak ({peak_temp:.1f}°C)"
    
    # And 19:00 should be noticeably cooler than 17:00
    assert temps[19] < temps[17] - 0.2, \
        f"19:00 ({temps[19]:.1f}°C) should be at least 0.2°C cooler than 17:00 ({temps[17]:.1f}°C)"
    
    print(f"\n✅ Temperature properly decreases after 15:00!")


def test_evening_cooling_continues():
    """Verify temperature continues dropping through evening."""
    current_temp = 15.0
    temp_trend = 0.0
    forecast_code = 10
    current_hour = 16  # 4pm
    
    temps = {}
    for hour_offset in range(1, 8):  # 17:00 to 23:00
        temp = calculate_weather_aware_temperature(
            hour=hour_offset,
            current_temp=current_temp,
            temp_trend=temp_trend,
            forecast_code=forecast_code,
            current_hour=current_hour
        )
        future_hour = (current_hour + hour_offset) % 24
        temps[future_hour] = temp
    
    print("\nEvening temperatures:")
    for h in sorted(temps.keys()):
        print(f"{h:02d}:00 → {temps[h]:.1f}°C")
    
    # Each hour should be cooler than previous (with small tolerance for rounding)
    hours = sorted(temps.keys())
    for i in range(len(hours) - 1):
        h1, h2 = hours[i], hours[i + 1]
        # Allow 0.1°C tolerance for rounding
        assert temps[h2] <= temps[h1] + 0.1, \
            f"{h2:02d}:00 ({temps[h2]:.1f}°C) should not be warmer than {h1:02d}:00 ({temps[h1]:.1f}°C)"
    
    print(f"✅ Evening cooling works correctly!")


def test_full_day_cycle_feb():
    """Test complete 24h cycle in February (winter)."""
    current_temp = 8.0
    temp_trend = 0.0
    forecast_code = 10
    current_hour = 6  # 6am - near minimum
    
    temps = []
    for hour_offset in range(0, 25, 2):  # Every 2 hours
        temp = calculate_weather_aware_temperature(
            hour=hour_offset,
            current_temp=current_temp,
            temp_trend=temp_trend,
            forecast_code=forecast_code,
            current_hour=current_hour
        )
        future_hour = (current_hour + hour_offset) % 24
        temps.append((future_hour, temp))
    
    print("\nFull day cycle (February):")
    print("Hour  | Temp")
    print("------|------")
    for h, t in temps:
        print(f"{h:02d}:00 | {t:5.1f}°C")
    
    # Find maximum
    max_temp = max(t for _, t in temps)
    max_hour = next(h for h, t in temps if t == max_temp)
    
    # Maximum should be between 14:00-16:00 (solar noon ~13:30 + 2h delay)
    assert 14 <= max_hour <= 16, \
        f"Maximum temperature should be 14:00-16:00, got {max_hour:02d}:00"
    
    # Temperature at 20:00 should be lower than at 15:00
    temp_15 = next(t for h, t in temps if h == 14)  # Closest to 15:00 in our 2h steps
    temp_20 = next(t for h, t in temps if h == 20)
    
    assert temp_20 < temp_15, \
        f"20:00 ({temp_20:.1f}°C) should be cooler than 15:00 ({temp_15:.1f}°C)"
    
    print(f"\n✅ Maximum at {max_hour:02d}:00, proper cooling afterwards!")


def test_full_day_cycle_july():
    """Test complete 24h cycle in July (summer) - larger amplitude."""
    current_temp = 18.0
    temp_trend = 0.0
    forecast_code = 2  # Sunny
    current_hour = 6  # 6am - near minimum
    
    temps = []
    for hour_offset in range(0, 25, 1):  # Every hour
        temp = calculate_weather_aware_temperature(
            hour=hour_offset,
            current_temp=current_temp,
            temp_trend=temp_trend,
            forecast_code=forecast_code,
            current_hour=current_hour,
            current_month=7  # July for summer amplitude
        )
        future_hour = (current_hour + hour_offset) % 24
        temps.append((future_hour, temp))
    
    print("\nFull day cycle (July - sunny):")
    print("Hour  | Temp   | Change")
    print("------|--------|--------")
    for i, (h, t) in enumerate(temps[:-1]):  # Skip last (duplicate of start)
        if i > 0:
            prev_temp = temps[i-1][1]
            change = t - prev_temp
            symbol = "↑" if change > 0.1 else "↓" if change < -0.1 else "→"
            print(f"{h:02d}:00 | {t:5.1f}°C | {change:+5.1f}°C {symbol}")
        else:
            print(f"{h:02d}:00 | {t:5.1f}°C | ")
    
    # Find maximum and minimum
    max_temp = max(t for _, t in temps[:-1])
    min_temp = min(t for _, t in temps[:-1])
    max_hour = next(h for h, t in temps if t == max_temp)
    min_hour = next(h for h, t in temps if t == min_temp)
    
    amplitude = max_temp - min_temp
    
    print(f"\n📊 Statistics:")
    print(f"   Minimum: {min_temp:.1f}°C at {min_hour:02d}:00")
    print(f"   Maximum: {max_temp:.1f}°C at {max_hour:02d}:00")
    print(f"   Amplitude: {amplitude:.1f}°C (daily range)")
    
    # Summer should have large amplitude (6-10°C range)
    assert amplitude >= 6.0, \
        f"Summer amplitude should be at least 6°C, got {amplitude:.1f}°C"
    
    # Maximum should be 14:00-17:00
    assert 14 <= max_hour <= 17, \
        f"Maximum should be 14:00-17:00, got {max_hour:02d}:00"
    
    # Temperature must drop after maximum
    max_index = next(i for i, (h, t) in enumerate(temps) if t == max_temp)
    
    # Check 3 hours after max
    three_hours_later = (max_index + 3) % 24
    temp_3h_later = temps[three_hours_later][1]
    
    assert temp_3h_later < max_temp - 1.0, \
        f"Temp 3h after max ({temp_3h_later:.1f}°C) should be at least 1°C cooler than max ({max_temp:.1f}°C)"
    
    # Evening (20:00) should be significantly cooler than afternoon (15:00)
    temp_15 = next(t for h, t in temps if h == 15)
    temp_20 = next(t for h, t in temps if h == 20)
    
    assert temp_20 < temp_15 - 2.0, \
        f"20:00 ({temp_20:.1f}°C) should be at least 2°C cooler than 15:00 ({temp_15:.1f}°C)"
    
    print(f"\n✅ Summer diurnal cycle works correctly!")
    print(f"   Temperature properly drops after {max_hour:02d}:00")
    print(f"   Evening cooling: {temp_15:.1f}°C (15:00) → {temp_20:.1f}°C (20:00) = {temp_20-temp_15:.1f}°C")
