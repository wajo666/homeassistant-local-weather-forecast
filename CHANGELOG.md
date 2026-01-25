
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [3.1.10] - 2026-01-25

### ✨ Added
- **Mixed Precipitation** - Automatic snow/rain/mixed detection based on temperature
- **Exceptional Weather** - Detection of hurricanes, hail, and extreme pressure events
- **Windy Conditions** - Added `windy` and `windy-variant` weather states
- **Enhanced Attributes** - New sensor data: fog risk, snow risk, frost risk, wind scale, atmosphere stability

### 🔧 Fixed
- **Visibility Calculation** - Now 100% WMO compliant (8 precision levels instead of 4)
- **Zambretti Formula** - Corrected steady pressure calculation for more accurate forecasts
- **Negretti Summer Adjustment** - Fixed seasonal calculations
- **Rain Probability** - Improved accuracy ±20% (WMO/NOAA standards)
- **Model Selection** - Enhanced mode now correctly uses dynamic weighting
- **Current Weather** - Fixed priority system for more accurate "now" conditions
- **Startup Issues** - Plugin now waits for sensors to be ready

---

## [3.1.9] - 2026-01-21
### 🔧 Fixed
- Current weather detection accuracy
- Solar radiation cloudiness calculations

---

## [3.1.8] - 2026-01-19
### ✨ Added
- Solar-aware temperature forecasting
### 🔧 Fixed
- Rain forecast accuracy during high pressure conditions

---

## [3.1.7] - 2026-01-19
### 🔧 Fixed
- Solar radiation calculations
- Sunrise/sunset detection
- Lux to W/m² conversion

---

## [3.1.6] - 2026-01-18
### 🔧 Fixed
- Extreme weather forecast algorithms
- Precipitation sensor auto-updates

---

## [3.1.5] - 2026-01-17
### ✨ Added
- Dynamic precipitation icons (automatically shows rain ☔ or snow ❄️ based on temperature)

---

## [3.1.4] - 2026-01-16
### ✨ Added
- Forecast model selection (Zambretti, Negretti, Enhanced)
- Location-aware solar radiation calculations
### 🔧 Fixed
- Southern hemisphere seasonal corrections
- Fog detection accuracy

---

