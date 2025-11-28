# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.2] - 2025-11-28

### Added
- ✅ **Detail Sensors Implemented**: Zambretti and Negretti-Zambra detail sensors now fully functional
  - Rain probability estimation (6h and 12h forecasts)
  - Dynamic weather icon mapping (22 forecast types)
  - Forecast times and letter codes
- ✅ **Historical Data Fallback**: Sensors now fetch historical values when unavailable after restart
- ✅ **Temperature Change Tracking**: New sensor tracking temperature changes over 1 hour
- ✅ **Pressure Change Initialization**: Pressure change sensor now initializes with current value

### Fixed
- 🐛 **Entity ID Corrections**: All sensors now track correct entity IDs
  - Fixed: `sensor.local_forecast` → `sensor.local_weather_forecast_local_forecast`
  - Fixed: `sensor.local_forecast_pressure` → `sensor.local_weather_forecast_pressure`
  - Fixed: `sensor.local_forecast_temperature` → `sensor.local_weather_forecast_temperature`
- 🐛 **Forecast Format**: Converted forecast outputs from arrays to comma-separated strings for easier parsing
- 🐛 **Negretti-Zambra Detail Sensor**: Fixed unavailable state, now updates correctly on startup
- 🐛 **Pressure Change Sensor**: Added initial value to history for immediate tracking
- 🐛 **Temperature Change Sensor**: Added initial value to history for immediate tracking

### Changed
- 📝 **Weather Card Templates**: Updated all weather card examples to use string splitting instead of array indexing
- 📝 **README**: Added original developer attribution and improved documentation
- 🌍 **Translations**: Updated Slovak translations, removed Czech

### Documentation
- 📚 **WEATHER_CARDS.md**: Complete weather card examples with Mushroom Cards
  - Basic Mushroom Card
  - Advanced Mushroom Card (with rain probability and temperature trends)
  - Compact Mobile Card
  - Mini Card
  - Comparison Card (both forecast models)
- 📚 **Sensor Units**: Documented required sensor units (°C, hPa, m/s, degrees)
- 📚 **Configuration Options**: Documented pressure type selection (relative/absolute)

### Technical
- 🔧 **Icon Mapping**: Added comprehensive weather icon mapping for 22 forecast types
- 🔧 **Rain Probability Estimation**: Implemented algorithm based on forecast numbers
- 🔧 **Initial Updates**: All sensors now update immediately on startup
- 🔧 **Error Handling**: Improved error handling for unavailable sensors

## [2.0.1] - 2024-XX-XX

### Initial Release
- Basic weather forecast functionality
- Zambretti and Negretti-Zambra algorithms
- Config flow UI integration
- Multi-language support (German, English, Greek, Italian, Slovak)

---

## Release Links

- [v2.0.2](https://github.com/wajo666/homeassistant-local-weather-forecast/releases/tag/2.0.2)
- [v2.0.1](https://github.com/wajo666/homeassistant-local-weather-forecast/releases/tag/2.0.1)

