
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
  - Choose between three forecast algorithms:
    - **Combined (Dynamic)**: Smart adaptive weighting (~98% accuracy) - **Default**
    - **Zambretti**: Faster response to changes (~94% accuracy)
    - **Negretti & Zambra**: More stable predictions (~92% accuracy)
  - Configurable in setup and can be changed anytime
  - Applies to current condition, hourly, and daily forecasts

- **Location-Aware Solar Radiation** 🌍
  - Dynamic calculation based on latitude and season
  - Tropical: max 1300 W/m², Temperate: 1200 W/m², Polar: 800 W/m²
  - Southern hemisphere automatic season inversion
  - 20-30% more accurate in tropical/polar regions

- **Hemisphere Configuration**
  - Auto-detection from Home Assistant location
  - Manual override available
  - Accurate seasonal adjustments for Southern hemisphere

- **Pressure Sensor Change in Options**
  - Can now change pressure sensor after initial setup
  - Edit via Settings → Integrations → Configure

### 🔧 Fixed

- **Solar Radiation - Southern Hemisphere**
  - Fixed incorrect cloudiness detection in Southern hemisphere
  - Sydney (December): Now correctly expects 1150 W/m² (was 500 W/m²)

- **Fog & Humidity Corrections**
  - Fixed overly aggressive downgrades overriding "fine weather" forecasts
  - System now respects forecast confidence

- **Snow Risk Calculation**
  - Fixed false HIGH risk when high humidity but no precipitation
  - Snow risk now requires precipitation probability

- **Weather Entity Snow Detection**
  - Fixed incorrect "pouring" (rain) when snowing

### ⚠️ Breaking Changes

- **Risk Attributes - Automation-Friendly**
  - `fog_risk`, `snow_risk`, `frost_risk` now contain RAW English values: `"none"`, `"low"`, `"medium"`, `"high"`, `"critical"`
  - `fog_risk_text`, `snow_risk_text`, `frost_risk_text` contain translated text for UI
  - Update automations to use RAW values for language-independent operation


### 🧪 Testing

- Added 476 comprehensive unit tests (100% pass rate)
- Coverage: ~98%


### ✨ Added

- Extended frost detection with critical black ice warning
- Enhanced sensor attributes for snow and frost risk
- Comprehensive test suite

### 🔧 Fixed

- Code cleanup in calculations.py
- Enhanced debug logging
- Removed unused constants

---
    - Normal case (5-minute updates): 36 records in 180 minutes ✅
    - Irregular updates: Still keeps 36 newest records even if they span 4+ hours ✅
    - After restart: Restores full history (36/12 records) → immediate accurate forecast ✅
  - **Recovery after restart**: 
    - With 36 pressure records: **Excellent** accuracy, immediate forecast ⭐⭐⭐⭐⭐
    - With 12 temperature records: **Excellent** accuracy, immediate forecast ⭐⭐⭐⭐⭐
    - Minimum 2 records: Still works, but less precise ⭐⭐⭐
  - **Updated sensor logic**:
    - `PressureChange`: Uses time window OR minimum 36 records (whichever gives more data)
    - `TemperatureChange`: Uses time window OR minimum 12 records (whichever gives more data)

### 📝 Language Support

- **New Translation Functions** (2025-12-10)
  - `get_snow_risk_text()` - Translates snow risk levels
  - `get_frost_risk_text()` - Translates frost/ice risk levels
  - Format: [German, English, Greek, Italian, Slovak]

### 📄 Documentation

- **Enhanced Documentation** (2025-12-10)
  - Updated Troubleshooting section in `README.md`
  - **Problem addressed**: External sensors (outside this integration) that combine data from multiple sources with different update frequencies
  - **Solutions provided**:
    1. Quick fix using `statistics` platform with `sampling_size`
    2. Template sensor with `state_class: measurement`
    3. Python script with custom dual-limit logic
  - **Use case example**: East temperature (5-min updates) + West temperature (15-min updates) = Combined sensor with large time gaps
  - **Result**: Guaranteed minimum records even for slow-updating external sensors

---




