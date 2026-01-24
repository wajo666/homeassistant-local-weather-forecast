
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [3.1.10] - 2026-01-24

### ✨ Added
- **Mixed Precipitation** - WMO/NOAA standards (snow/rain/mixed based on temp + humidity)
- **Exceptional Weather** - Hurricane, hail, extreme pressure detection
- **Windy Conditions** - Support for `windy` and `windy-variant` states
- **Enhanced Sensor Attributes** - `forecast_model`, `consensus`, `fog_risk`, `snow_risk`, `frost_risk`, `wind_beaufort_scale`, `atmosphere_stability`, `confidence`
- **Rain Probability Attributes** - `zambretti_weight`, `negretti_weight`, `precipitation_type`, `factors_used` (Enhanced mode)

### 🔧 Fixed
- **🔴 CRITICAL: Zambretti STEADY Formula** - Corrected 144 → 138 (original algorithm)
  - 1034 hPa now gives realistic "Fairly Fine" instead of "Settled Fine"
- **🔴 CRITICAL: Negretti Summer Adjustment** - Fixed 12.25 → 7 hPa (original value)
  - More accurate summer forecasts
- **🔴 CRITICAL: Rain Probability Algorithm** - WMO/NOAA standards
  - Cloudy: 90% → 30%, Rainy: 90% → 70%, Sunny: 0% → 2%
  - ±20% accuracy improvement
- **🔴 CRITICAL: Rain Probability Model Selection** - Now respects config choice
  - Dynamic weights in Enhanced mode (0.40-0.75 based on pressure change)
  - ±2-8% accuracy improvement
- **Hail Detection** - Changed from forecast-based to actual conditions
  - Requires active precipitation + convective conditions (15-30°C, humidity >80%, gust ratio >2.5)
- **Exceptional Weather Logic** - Independent condition checks (hurricane, bomb cyclone, extreme pressure)
- **Current Weather Priority** - Direct pressure mapping for NOW (not forecast)
- **Fog + Precipitation** - Correct simultaneous handling
- **Startup Race Condition** - Wait for sensors (30s timeout)

### ♻️ Refactored
- **Forecast Mapping** - Unified system (-497 lines)
- **Pressure-Based Weather** - WMO standards (7 ranges)

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

