
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.9] - 2026-01-21

### 🔧 Fixed
- Weather entity showing forecast (6-12h future) instead of current conditions
- Overcast (100% clouds) ignored by solar radiation sensor
- Snow conversion only worked for forecast predictions
- Priority order: Rain sensor → Fog → Solar → Pressure → Forecast

---

## [3.1.8] - 2026-01-19

### ✨ Added
- Solar-aware temperature forecasting with sun position, seasons, hemisphere

### 🔧 Fixed
- Incorrect rain forecast during anticyclones (high pressure >1030 hPa)

---

## [3.1.7] - 2026-01-19

### 🔧 Fixed
- Universal solar radiation calculation for any location
- Precipitation sensor snow icon false positives
- Lux to W/m² conversion for Xiaomi/Shelly sensors
- False cloudy detection at sunrise/sunset

---

## [3.1.6] - 2026-01-18

### 🔧 Fixed
- Forecast algorithms for extreme weather (winter high pressure, storm recovery)
- Precipitation sensor auto-update after Home Assistant restart
- Winter weather display (snow icon when temperature below freezing)

---

## [3.1.5] - 2026-01-17

### ✨ Added
- Precipitation probability with dynamic icon (rain/snow/mixed based on temperature)

---

## [3.1.4] - 2026-01-16

### ✨ Added
- Forecast model selection (Enhanced/Zambretti/Negretti-Zambra)
- Location-aware solar radiation with hemisphere support
- Pressure sensor changeable in options

### 🔧 Fixed
- Solar radiation for southern hemisphere
- Fog/humidity detection corrections
- Snow risk false positives
- Weather entity "pouring" during snow

---

