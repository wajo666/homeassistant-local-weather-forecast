
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [3.1.10] - 2026-01-23

### ✨ Added
- **Mixed Precipitation Detection** - WMO/NOAA standards for snow/rain/mixed based on temperature + humidity
- **Exceptional Weather States** - Hurricane, hail, extreme pressure detection
- **Windy Conditions** - Support for `windy` and `windy-variant` states
- **Weather Entity Properties** - Cloud coverage, visibility, UV index attributes

### 🔧 Fixed
- **Current Weather Priority** - Replaced forecast 0h with direct pressure mapping (more accurate for NOW)
- **Solar Override** - Fixed humidity overriding solar radiation during daytime
- **Fog + Precipitation** - Correct handling when both occur simultaneously
- **Startup Race Condition** - Wait for all configured sensors (30s timeout, auto-recovery)
- **Fog Detection** - Added light fog/mist detection (dewpoint spread 1.5-2.5°C)
- **Pressure Fallback** - Fixed None check in fallback logic
- **Code 17 Mapping** - Changed from cloudy to rainy (meteorologically correct)

### ♻️ Refactored
- **Pressure-Based Weather** - Upgraded to WMO standards (7 ranges, "Cloudy" translations added)
- **Forecast Mapping** - Unified system, removed 497 lines of duplicate code
- **Priority System** - Removed redundant forecast_short_term from weather.py

---

## [3.1.9] - 2026-01-21
### 🔧 Fixed
- Current weather detection priority system
- Solar radiation cloudiness detection

---

## [3.1.8] - 2026-01-19
### ✨ Added
- Solar-aware temperature forecasting
### 🔧 Fixed
- Rain forecast during high pressure

---

## [3.1.7] - 2026-01-19
### 🔧 Fixed
- Solar radiation calculations
- Lux to W/m² conversion
- Sunrise/sunset detection

---

## [3.1.6] - 2026-01-18
### 🔧 Fixed
- Extreme weather algorithms
- Precipitation sensor updates

---

## [3.1.5] - 2026-01-17
### ✨ Added
- Dynamic precipitation icons (rain/snow/mixed)

---

## [3.1.4] - 2026-01-16
### ✨ Added
- Forecast model selection
- Location-aware solar radiation
### 🔧 Fixed
- Southern hemisphere support
- Fog detection

---

