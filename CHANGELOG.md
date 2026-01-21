
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.9] - 2026-01-21

### 🔧 Fixed
- **Weather entity showing wrong current conditions** 🎯
  - Fixed weather entity displaying forecast predictions (6-12h future) instead of actual current state
  - Example: Clear sky with high pressure incorrectly showed "snowy"
  - Forecast now only used as last fallback when no measurements available
  
- **Current weather priority order corrected**:
  1. Rain sensor (if raining) → RAINY/SNOWY
  2. Fog detection (temp + humidity + dewpoint) → FOG
  3. Solar radiation (cloud cover) → SUNNY/PARTLYCLOUDY/CLOUDY
  4. Current pressure state → CLEAR/SUNNY
  5. Forecast model → fallback only
  
- **Snow conversion logic fixed**
  - Snow conversion now applies to ALL conditions (not just forecast predictions)
  - Correctly converts RAINY → SNOWY when temperature ≤ 2°C
  - Better winter weather accuracy for sensors that don't detect snow directly

- **Humidity corrections now universal**
  - Humidity corrections now apply to ALL weather conditions regardless of source
  - High humidity properly adjusts cloudiness even with solar/pressure data

### 📊 Impact
- Weather entity now shows actual current weather instead of future predictions ✅
- Clear sky no longer shows "snowy" just because it's cold ✅
- Forecast predictions stay in hourly/daily forecasts where they belong ✅

---

## [3.1.8] - 2026-01-19

### ✨ Added

- **Solar-Aware Temperature Forecasting** ☀️
  - Temperature predictions now use **real sun position** (uses Home Assistant's built-in sun helper)
  - Seasonal amplitude adjustments: Winter ±3°C, Spring ±6°C, Summer ±10°C, Autumn ±5°C
  - Hemisphere-aware with automatic season reversal for southern hemisphere
  - Solar radiation integration: Sunny days +30%, cloudy -30%
  - More accurate hourly and daily temperature forecasts

### 🔧 Fixed

- **Weather Forecast in Anticyclones** 🌤️
  - Fixed incorrect rain forecast during stable sunny weather (high pressure >1030 hPa)
  - Now correctly shows sunny ☀️ weather during anticyclones
  - Example: 1038 hPa now shows "Sunny" (was "Very Unsettled, Rain" ❌)

---

## [3.1.7] - 2026-01-19

### 🌍 Enhanced

- **Universal Solar Radiation Calculation** ☀️
  - Automatically uses your location from Home Assistant
  - Works accurately anywhere on Earth - from equator to poles
  - Accounts for latitude, elevation, season, and time of day
  - No configuration needed!

### 🔧 Fixed

- **Precipitation Sensor Snow Icon** ❄️
  - Fixed false snow icon when temperature is cold but no actual snow conditions
  - Now requires high humidity + saturation + precipitation probability

- **Solar Radiation Sensors in Lux**
  - Added automatic conversion from lux to W/m² (Xiaomi, Shelly sensors)
  - Config flow accepts both irradiance (W/m²) and illuminance (lux)

- **Sunrise/Sunset False Cloudy Detection** 🌅
  - Fixed false "cloudy" at sunrise/sunset when sky is clear
  - Solar detection now requires minimum 50 W/m²

---

## [3.1.6] - 2026-01-18

### 🔧 Fixed

- **Forecast Algorithms for Extreme Weather** 🌡️
  - Fixed incorrect predictions during high pressure in winter
  - Fixed overly optimistic forecasts during storm recovery
  - Seasonal adjustments now work across all pressure ranges (910-1085 hPa)

- **Precipitation Sensor Auto-Update** 🐛
  - Fixed sensor not updating after Home Assistant restart
  - Sensor now updates in real-time

- **Winter Weather Display** ❄️
  - Changed "Rain" to "Precipitation" in all languages
  - Correctly shows snow icon when temperature below freezing

---

## [3.1.5] - 2026-01-17

### ✨ Added

- **Precipitation Probability with Dynamic Icon** ❄️🌧️🌨️
  - Smart icon based on temperature: Rain >4°C, Snow ≤2°C, Mixed 2-4°C
  - New attributes: `temperature`, `precipitation_type`

---

## [3.1.4] - 2026-01-16

### ✨ Added

- **Forecast Model Selection** 🎯
  - Choose between three algorithms: Enhanced Dynamic (98%), Zambretti (94%), Negretti-Zambra (92%)
  - Change anytime via Settings → Configure

- **Location-Aware Solar Radiation** 🌍
  - Automatic latitude/season adjustments
  - Southern hemisphere support

- **Pressure Sensor in Options**
  - Can change pressure sensor after setup

### 🔧 Fixed

- **Solar Radiation** - Southern hemisphere cloudiness detection
- **Fog & Humidity** - Overly aggressive corrections
- **Snow Risk** - False high risk with low precipitation
- **Weather Entity** - Incorrect "pouring" when snowing

---

