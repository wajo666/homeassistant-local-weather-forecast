"""
Example usage of extended calculations for Local Weather Forecast.

This file demonstrates how to use the new meteorological calculations
introduced in version 3.1.0.
"""

from custom_components.local_weather_forecast.calculations import (
    calculate_dewpoint,
    calculate_heat_index,
    calculate_wind_chill,
    calculate_apparent_temperature,
    get_comfort_level,
    get_fog_risk,
    calculate_rain_probability_enhanced,
    interpolate_forecast,
    calculate_visibility_from_humidity,
)

# ============================================================================
# Example 1: Calculate Dew Point
# ============================================================================

print("=" * 60)
print("Example 1: Dew Point Calculation")
print("=" * 60)

temperature = 20.0  # °C
humidity = 60.0     # %

dewpoint = calculate_dewpoint(temperature, humidity)
print(f"Temperature: {temperature}°C")
print(f"Humidity: {humidity}%")
print(f"Dew Point: {dewpoint}°C")
print(f"Spread: {temperature - dewpoint:.1f}°C")
print()

# ============================================================================
# Example 2: Fog Risk Assessment
# ============================================================================

print("=" * 60)
print("Example 2: Fog Risk Assessment")
print("=" * 60)

scenarios = [
    (15.0, 14.0, "Very high fog risk"),
    (15.0, 13.0, "High fog risk"),
    (15.0, 12.0, "Medium fog risk"),
    (15.0, 10.0, "Low fog risk"),
    (15.0, 8.0, "No fog risk"),
]

for temp, dew, description in scenarios:
    risk = get_fog_risk(temp, dew)
    spread = temp - dew
    print(f"T={temp}°C, Td={dew}°C, Spread={spread:.1f}°C → {risk} ({description})")
print()

# ============================================================================
# Example 3: Heat Index (Hot Weather)
# ============================================================================

print("=" * 60)
print("Example 3: Heat Index Calculation")
print("=" * 60)

hot_scenarios = [
    (30.0, 50.0),
    (32.0, 60.0),
    (35.0, 70.0),
    (38.0, 40.0),
]

for temp, hum in hot_scenarios:
    heat_index = calculate_heat_index(temp, hum)
    if heat_index:
        feels_like_diff = heat_index - temp
        print(f"T={temp}°C, H={hum}% → Feels like {heat_index}°C (Δ{feels_like_diff:+.1f}°C)")
    else:
        print(f"T={temp}°C, H={hum}% → Heat index not applicable")
print()

# ============================================================================
# Example 4: Wind Chill (Cold Weather)
# ============================================================================

print("=" * 60)
print("Example 4: Wind Chill Calculation")
print("=" * 60)

cold_scenarios = [
    (5.0, 10.0),
    (0.0, 20.0),
    (-5.0, 30.0),
    (-10.0, 40.0),
]

for temp, wind in cold_scenarios:
    wind_chill = calculate_wind_chill(temp, wind)
    if wind_chill:
        feels_like_diff = wind_chill - temp
        print(f"T={temp}°C, Wind={wind}km/h → Feels like {wind_chill}°C (Δ{feels_like_diff:+.1f}°C)")
    else:
        print(f"T={temp}°C, Wind={wind}km/h → Wind chill not applicable")
print()

# ============================================================================
# Example 5: Apparent Temperature (Universal)
# ============================================================================

print("=" * 60)
print("Example 5: Apparent Temperature")
print("=" * 60)

all_scenarios = [
    (-5.0, 40.0, 25.0, "Cold & windy winter day"),
    (5.0, 60.0, 10.0, "Cool spring day"),
    (20.0, 50.0, 5.0, "Pleasant day"),
    (32.0, 70.0, 5.0, "Hot & humid summer day"),
]

for temp, hum, wind, description in all_scenarios:
    apparent = calculate_apparent_temperature(temp, hum, wind)
    comfort = get_comfort_level(apparent)
    print(f"{description}:")
    print(f"  Actual: {temp}°C → Feels like: {apparent}°C → {comfort}")
print()

# ============================================================================
# Example 6: Comfort Level Classification
# ============================================================================

print("=" * 60)
print("Example 6: Comfort Levels")
print("=" * 60)

comfort_temps = [-15, -5, 2, 10, 18, 22, 28, 32, 38]
for temp in comfort_temps:
    comfort = get_comfort_level(temp)
    print(f"{temp:>3}°C → {comfort}")
print()

# ============================================================================
# Example 7: Enhanced Rain Probability
# ============================================================================

print("=" * 60)
print("Example 7: Enhanced Rain Probability")
print("=" * 60)

# Scenario 1: Low probability
print("Scenario 1: Dry conditions")
prob, conf = calculate_rain_probability_enhanced(
    zambretti_prob=20,
    negretti_prob=15,
    humidity=45,
    cloud_coverage=30,
    dewpoint_spread=8.0
)
print(f"  Zambretti: 20%, Negretti: 15%")
print(f"  Humidity: 45%, Clouds: 30%, Spread: 8°C")
print(f"  → Final: {prob}% (confidence: {conf})")
print()

# Scenario 2: High probability
print("Scenario 2: Wet conditions")
prob, conf = calculate_rain_probability_enhanced(
    zambretti_prob=60,
    negretti_prob=70,
    humidity=90,
    cloud_coverage=95,
    dewpoint_spread=1.5
)
print(f"  Zambretti: 60%, Negretti: 70%")
print(f"  Humidity: 90%, Clouds: 95%, Spread: 1.5°C")
print(f"  → Final: {prob}% (confidence: {conf})")
print()

# Scenario 3: Base models only
print("Scenario 3: Base models only (no extra sensors)")
prob, conf = calculate_rain_probability_enhanced(
    zambretti_prob=40,
    negretti_prob=35,
)
print(f"  Zambretti: 40%, Negretti: 35%")
print(f"  No additional sensors")
print(f"  → Final: {prob}% (confidence: {conf})")
print()

# ============================================================================
# Example 8: Forecast Interpolation
# ============================================================================

print("=" * 60)
print("Example 8: Forecast Interpolation")
print("=" * 60)

current_temp = 15.0
forecast_temp_12h = 8.0

print(f"Current temperature: {current_temp}°C")
print(f"Forecast (12h): {forecast_temp_12h}°C")
print()
print("Interpolated forecasts:")

for hours in [1, 3, 6, 9, 12]:
    interpolated = interpolate_forecast(current_temp, forecast_temp_12h, hours, 12)
    print(f"  +{hours:>2}h: {interpolated}°C")
print()

# ============================================================================
# Example 9: Visibility Estimation
# ============================================================================

print("=" * 60)
print("Example 9: Visibility from Humidity")
print("=" * 60)

visibility_scenarios = [
    (50, 20, "Clear day"),
    (70, 15, "Slight haze"),
    (85, 12, "Moderate haze"),
    (92, 8, "Poor visibility"),
    (98, 5, "Fog/mist"),
]

for hum, temp, description in visibility_scenarios:
    visibility = calculate_visibility_from_humidity(hum, temp)
    print(f"H={hum}%, T={temp}°C → Visibility: {visibility}km ({description})")
print()

# ============================================================================
# Example 10: Complete Weather Analysis
# ============================================================================

print("=" * 60)
print("Example 10: Complete Weather Analysis")
print("=" * 60)

# Current conditions
current = {
    "temperature": 18.0,
    "humidity": 75.0,
    "pressure": 1015.0,
    "wind_speed": 15.0,
    "wind_direction": 220,
}

# Calculate derived values
dewpoint = calculate_dewpoint(current["temperature"], current["humidity"])
apparent = calculate_apparent_temperature(
    current["temperature"],
    current["humidity"],
    current["wind_speed"]
)
comfort = get_comfort_level(apparent)
fog_risk = get_fog_risk(current["temperature"], dewpoint)
visibility = calculate_visibility_from_humidity(current["humidity"], current["temperature"])

print("Current Conditions:")
print(f"  Temperature: {current['temperature']}°C")
print(f"  Humidity: {current['humidity']}%")
print(f"  Pressure: {current['pressure']} hPa")
print(f"  Wind: {current['wind_speed']} km/h from {current['wind_direction']}°")
print()
print("Calculated Values:")
print(f"  Dew Point: {dewpoint}°C")
print(f"  Apparent Temperature: {apparent}°C")
print(f"  Comfort Level: {comfort}")
print(f"  Fog Risk: {fog_risk}")
print(f"  Estimated Visibility: {visibility} km")
print()

# Forecast with Zambretti/Negretti
zambretti_rain = 40
negretti_rain = 45

rain_prob, rain_conf = calculate_rain_probability_enhanced(
    zambretti_rain,
    negretti_rain,
    current["humidity"],
    None,  # No cloud sensor
    current["temperature"] - dewpoint
)

print("Forecast:")
print(f"  Zambretti Rain Probability: {zambretti_rain}%")
print(f"  Negretti Rain Probability: {negretti_rain}%")
print(f"  Enhanced Rain Probability: {rain_prob}% ({rain_conf} confidence)")
print()

print("=" * 60)
print("Examples Complete!")
print("=" * 60)

