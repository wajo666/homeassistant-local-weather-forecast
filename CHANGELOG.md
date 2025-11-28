# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.1] - 2025-11-29

### 🐛 Fixed
- **Timezone Bug**: Fixed `TypeError: can't subtract offset-naive and offset-aware datetimes` in detail sensors
  - Changed `datetime.now()` to `dt_util.now()` for timezone-aware datetime objects
  - Affects `LocalForecastZambrettiDetailSensor` and `LocalForecastNegZamDetailSensor`
  - Issue occurred when calculating `_calculate_interval_time()` with restored state from database
  - Thanks to user report for identifying this critical bug

### 🔧 Technical Details
- Added import: `from homeassistant.util import dt as dt_util`
- All datetime operations now use Home Assistant's timezone-aware utilities
- Ensures consistency between restored state timestamps (timezone-aware) and current time calculations

---

## [3.0.0] - 2025-11-28

### 🎯 Major Release - 100% YAML Compatibility

This version achieves complete feature parity with the original YAML implementation with exact entity IDs and attribute formats.

### 🚨 Breaking Changes
- **Entity IDs Changed**: All entity IDs now match original YAML format exactly
  - `sensor.local_weather_forecast_local_forecast` → `sensor.local_forecast`
  - `sensor.local_weather_forecast_pressure` → `sensor.local_forecast_pressure`
  - `sensor.local_weather_forecast_temperature` → `sensor.local_forecast_temperature`
  - `sensor.local_weather_forecast_pressure_change` → `sensor.local_forecast_pressurechange` (no underscore!)
  - `sensor.local_weather_forecast_temperature_change` → `sensor.local_forecast_temperaturechange` (no underscore!)
  - `sensor.local_weather_forecast_zambretti_detail` → `sensor.local_forecast_zambretti_detail`
  - `sensor.local_weather_forecast_neg_zam_detail` → `sensor.local_forecast_neg_zam_detail`
- **Friendly Names Changed**: Removed device name prefix
  - `"Local Weather Forecast Local forecast"` → `"Local forecast"`
  - All sensor names now match original YAML exactly
- **Attribute Formats Restored**: All attributes now use original list/tuple/array formats instead of strings
  - `wind_direction`: List `[wind_fak, degrees, text, speed_fak]`
  - `forecast_zambretti`: List `[text, number, letter]`
  - `rain_prob`: List `[prob_6h%, prob_12h%]`
  - `icons`: Tuple `(icon_now, icon_later)`
  - `first_time`/`second_time`: List `[time_string, minutes]`

### ✨ Added
- ✅ **Automatic Entity Migration**: Seamless migration from old entity IDs to new format
  - Migration logic in `__init__.py` automatically renames entities on first load
  - No manual intervention needed for existing installations
- ✅ **Short-term Temperature Forecast** (`forecast_temp_short`): New attribute predicting temperature at next forecast interval
  - Format: `[predicted_temp, interval_index]` where interval: 0=6h, 1=12h, -1=unavailable
  - Uses temperature change rate and forecast timing for calculation
- ✅ **Forecast Weather States** (`forecast`): Detail sensors now include weather state predictions
  - Format: `[state_6h, state_12h]` where states: 0=sunny, 1=partly cloudy, 2=partly rainy, 3=cloudy, 4=rainy, 5=pouring, 6=lightning
  - Mapped from 26 Zambretti/Negretti-Zambra forecast types
- ✅ **Day/Night Icon Support**: Automatic icon selection based on sun position
  - Uses `sun.sun` entity to determine day/night
  - Different icons for `sunny` and `partly cloudy` states
- ✅ **Dynamic Forecast Timing**: Intelligent time calculations with aging correction
  - Tracks last update timestamp
  - Adds correction if forecast is older than 6 hours
  - Returns both formatted time and minutes remaining
- ✅ **Detailed Rain Probability**: Precise calculations based on weather state transitions
  - Zambretti: 9 rules for different state combinations
  - Negretti-Zambra: 4 simplified rules
  - Returns probability for both 6h and 12h intervals
- ✅ **Device Class Support Extended**: Now accepts both `atmospheric_pressure` and `pressure` device classes
  - Compatible with more weather stations and sensors
- ✅ **Additional Detail Attributes**: 
  - `forecast_text`: Explicit forecast text (easier access)
  - `forecast_number`: Forecast number 0-25 (easier access)
  - `letter_code`: Zambretti letter code A-Z (easier access)

### 🔧 Changed
- **Entity Lookup Made Dynamic**: All hardcoded entity IDs replaced with dynamic lookups
  - Helper methods `_get_main_sensor_id()` and `_get_entity_id(suffix)` 
  - Supports both old and new entity ID formats during migration
  - Detail sensors automatically find main sensor regardless of format
- **has_entity_name Disabled**: Set to `False` to prevent device name prefix in friendly names
- **Attribute Formats Standardized**: All attributes now use proper Python types
  - Lists for multi-value attributes
  - Tuples for paired values (icons)
  - Integers and floats with proper rounding

### 🐛 Fixed
- Detail sensors showing "unknown" state (now correctly display forecast text)
- Temperature short forecast always showing "unavailable, -1"
- Rain probability and icons showing as strings instead of proper types
- Forecast timing showing fixed values instead of dynamic calculations
- Pressure and temperature sensors not updating from main sensor (wrong entity IDs)
- Friendly names including device name as prefix

### 📝 Documentation
- ✅ **WEATHER_CARDS.md**: All examples updated to new entity IDs
  - Direct array access instead of string splitting
  - Updated entity ID reference
  - Added examples for all new attributes
- ✅ **README.md**: Updated device class requirements
  - Both `atmospheric_pressure` and `pressure` now documented
  - Added note about dual device class support

### 🔄 Migration Guide
**For existing Python integration users:**
1. Update to version 3.0.0
2. Restart Home Assistant
3. Migration runs automatically - entity IDs are renamed
4. Check Settings → Entities to verify new entity IDs

**For YAML users:**
- Zero changes needed - entity IDs and friendly names are now identical to YAML!
- Seamless migration from YAML to Python integration

### 💡 Notes
- Home Assistant UI displays lists as comma-separated strings, but they ARE proper lists
- Template sensors and automations using array indexing will work correctly
- All calculations and algorithms match original YAML implementation exactly

---

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

## [2.0.1] - 2025-11-28

### Initial Release
- Basic weather forecast functionality
- Zambretti and Negretti-Zambra algorithms
- Config flow UI integration
- Multi-language support (German, English, Greek, Italian, Slovak)

---

## Release Links

- [v3.0.1](https://github.com/wajo666/homeassistant-local-weather-forecast/releases/tag/v3.0.1) - Bugfix Release
- [v3.0.0](https://github.com/wajo666/homeassistant-local-weather-forecast/releases/tag/v3.0.0) - Major Release
- [v2.0.2](https://github.com/wajo666/homeassistant-local-weather-forecast/releases/tag/2.0.2)
- [v2.0.1](https://github.com/wajo666/homeassistant-local-weather-forecast/releases/tag/2.0.1)

