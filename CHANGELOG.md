
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [3.1.9] - 2026-01-21

### 🔧 Fixed
- **Current Weather Detection** - Shows real-time conditions instead of 6-12h forecast
  - Priority: Rain sensor → Fog → Solar radiation → Pressure → Forecast
  - Solar radiation uses WMO standard thresholds for cloudiness
  - Snow conversion works for both forecast and actual precipitation

---

## [3.1.8] - 2026-01-19

### ✨ Added
- Solar-aware temperature forecasting

### 🔧 Fixed
- Incorrect rain forecast during high pressure

---

## [3.1.7] - 2026-01-19

### 🔧 Fixed
- Solar radiation calculation for any location
- Precipitation sensor snow icon issues
- Lux to W/m² conversion
- False cloudy detection at sunrise/sunset

---

## [3.1.6] - 2026-01-18

### 🔧 Fixed
- Forecast algorithms for extreme weather
- Precipitation sensor auto-update
- Winter weather display

---

## [3.1.5] - 2026-01-17

### ✨ Added
- Precipitation probability with dynamic icon (rain/snow/mixed)

---

## [3.1.4] - 2026-01-16

### ✨ Added
- Forecast model selection
- Location-aware solar radiation
- Pressure sensor changeable in options

### 🔧 Fixed
- Southern hemisphere solar radiation
- Fog/humidity detection
- Snow risk false positives

---

