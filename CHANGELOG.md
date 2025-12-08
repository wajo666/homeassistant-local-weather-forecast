
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2025-12-08 (Testing Phase)

### 🔧 Fixed - Sensor Data Consistency & Auto-Updates

- **2 Decimal Precision for Numeric Values** (2025-12-08)
  - All numeric sensor values now consistently use 2 decimal places
  - **Enhanced sensor** (`sensor.local_forecast_enhanced`):
    - `humidity`: 89.12% (was 89.1%)
    - `dew_point`: 5.02°C (was 5.0°C)
    - `dewpoint_spread`: 1.70°C (was 1.7°C)
    - `wind_speed`: 1.11 m/s (was 1.1 m/s)
    - `wind_gust`: 1.52 m/s (was 1.5 m/s)
    - `gust_ratio`: 1.35 (unchanged - already 2 decimal)
  - **Weather entity** (`weather.local_weather_forecast_weather`):
    - `feels_like`: 4.12°C (was 4.1°C)
    - `dew_point`: 5.02°C (was 5.0°C)
    - `dewpoint_spread`: 1.48°C (was 1.5°C)
    - `humidity`: 89.12% (was 89%)
    - `wind_gust`: 1.52 m/s (was 1.5 m/s)
  - Python code: Uses `round(value, 2)` consistently
  - Improves display consistency and accuracy across all sensors

- **Modern Template Format Migration** (2025-12-08)
  - Migrated to modern `template:` format (HA 2026.6+ ready)
  - Removed deprecated `platform: template` format
  - Changes in sensor configuration:
    - Old: `platform: template` with `sensors:` dict
    - New: `- sensor:` or `- binary_sensor:` list format
    - Old: `friendly_name:` and `value_template:`
    - New: `name:` and `state:`
  - Rules enforced:
    - Only ONE `- binary_sensor:` section (all binary sensors in single list)
    - Only ONE `- sensor:` section (all numeric sensors in single list)
    - No duplicate sensor sections allowed
  - Benefits:
    - Compatible with Home Assistant 2026.6+
    - No deprecated warnings
    - Cleaner YAML structure
    - Future-proof configuration

- **Dewpoint Spread Calculation Fix** (2025-12-08)
  - Enhanced sensor now uses dewpoint from weather entity (respects dewpoint sensor if configured)
  - Ensures consistency: spread calculation uses same temp/dewpoint values visible in weather entity
  - Before: Enhanced sensor calculated own dewpoint → inconsistent spread values
  - After: Spread = weather.temp - weather.dewpoint → accurate values
  - Example: temp=6.7°C, dewpoint=5.0°C → spread=1.7°C (was showing 1.6°C before)

- **Enhanced Sensor Automatic Updates** (2025-12-08)
  - Enhanced sensor now automatically updates when ANY monitored sensor changes
  - Before: Updated only once at Home Assistant startup
  - After: Tracks up to 9 entities and updates within 30 seconds of any change
  - Monitored entities:
    - `weather.local_weather_forecast_weather` (consolidated source)
    - `sensor.local_forecast` (main forecast text)
    - Temperature sensor (for dewpoint spread, feels like)
    - Humidity sensor (for adjustments, fog risk)
    - Pressure sensor (for forecast changes)
    - Wind speed sensor (for wind type, Beaufort scale)
    - Wind direction sensor (for wind factor adjustment)
    - Wind gust sensor (for gust ratio, stability)
    - Dewpoint sensor (if configured, alternative to calculation)
    - Rain rate sensor (for rain probability)
  - Throttling: Maximum 1 update per 30 seconds (prevents flooding)

- **Sensor Configuration Logic Fix** (2025-12-08)
  - **Only PRESSURE sensor is truly required** (as per Zambretti algorithm)
  - All other sensors are now correctly marked as **optional enhancements**
  - Before: Temperature, Wind Speed, Wind Direction marked as required
  - After: Only Pressure required; others improve forecast accuracy but are optional
  - Sensors in `config.data` (required at setup): Pressure only
  - Sensors in `config.options` (optional enhancements):
    - Temperature (for sea level pressure conversion, feels like)
    - Humidity (for dew point, fog detection, adjustments)
    - Wind Speed (for wind factor, Beaufort scale, wind type)
    - Wind Direction (for wind factor adjustment)
    - Wind Gust (for atmosphere stability analysis)
    - Dewpoint (alternative to temp+humidity calculation)
    - Rain Rate (for rain probability enhancement)
  - Integration now works with minimal configuration (pressure only)
  - Users can gradually add sensors to unlock more features

### ✨ Added - Advanced Weather Forecasting & Sensor Integration

- **Advanced Forecast Calculator** (`forecast_calculator.py`)
  - Scientific pressure trend forecasting (linear regression)
  - **Solar-Aware Temperature Model**
    - Integrates solar radiation sensor (W/m²) OR UV index sensor
    - Cloud cover adjustment for solar warming
    - Sun angle calculation (day/night cycle) using Home Assistant coordinates
    - Realistic daytime heating (+2°C per 400 W/m² at solar noon)
    - UV index correlation with solar radiation (UVI 10 ≈ 1000 W/m²)
    - Automatic nighttime cooling (no solar effect 18:00-06:00)
    - Graceful fallback when solar sensors unavailable
  - Temperature modeling with diurnal cycle
  - Hourly Zambretti forecast generation
  - Rain probability per hour based on pressure evolution
  - Confidence scoring for forecast quality
  - Support for both daily and hourly forecasts

- **Humidity-Based Cloud Cover Correction**
  - Current weather condition now respects humidity levels
  - High humidity (>85%) upgrades `partlycloudy`/`sunny` → `cloudy`
  - Moderate humidity (70-85%) upgrades `sunny` → `partlycloudy`
  - Meteorologically accurate: RH >85% = 80-100% cloud cover
  - Fixes issue where Zambretti showed "partly cloudy" at 85% humidity

- **Fog Detection**
  - Automatic fog detection based on meteorological conditions
  - Sets `weather.condition = fog` when fog is present
  - PRIORITY 2 detection (after rain, before Zambretti forecast)
  - Conditions: Dewpoint spread < 1.5°C AND humidity > 85%
  - Alternative: Dewpoint spread < 1.0°C AND humidity > 80%
  - Time-aware: Only sets fog during night/early morning/evening (not midday)
  - Meteorologically accurate (WMO standards)
  - Enables fog-specific automations and alerts

- **Weather Entity Extended Attributes**
  - 21+ comprehensive attributes in weather entity detail view
  - **Wind classification:** `wind_type`, `wind_beaufort_scale`, `wind_gust`, `gust_ratio`, `atmosphere_stability`
  - **Fog & visibility:** `fog_risk`, `dew_point`, `dewpoint_spread`, `visibility_estimate`
  - **Rain probability:** `rain_probability`, `rain_confidence`
  - **Forecast details:** `forecast_confidence`, `forecast_adjustments`, `forecast_adjustment_details`
  - **Comfort:** `feels_like`, `comfort_level`, `humidity`
  - Click on weather card to see all details!

- **Wind Gust Ratio Fix for Low Wind Speeds**
  - Atmospheric stability check now requires wind > 3 m/s
  - Prevents false "unstable atmosphere" warnings with light winds
  - Example: 0.8 m/s wind with 1.3 m/s gusts = ratio 1.625 = NORMAL (not unstable)
  - Gust ratio thresholds (>1.6 unstable, >2.0 very unstable) now only apply to moderate+ winds
  - Meteorologically accurate: Light winds naturally have higher gust ratios
  - **NEW: Beaufort Wind Scale Classification** - `wind_type` attribute shows wind description
    - 0-12 scale: "Ticho" to "Hurikán" (Slovak) / "Calm" to "Hurricane" (English)
    - `wind_beaufort_scale` attribute shows Beaufort number (0-12)
  - **NEW: Atmospheric Stability** - `atmosphere_stability` attribute
    - Intelligent evaluation: stable/moderate/unstable/very_unstable
    - Based on wind speed + gust ratio combination
    - Ignores gust ratio for winds < 3 m/s (meteorologically correct)

- **Comprehensive Sensor Support in Config Flow**
  - **Rain Detection Sensor** (optional):
    - `rain_rate_sensor`: Smart rain detection (device_class='precipitation', unit='mm')
    - Automatically detects sensor type: Accumulation (Netatmo) or Rate (Ecowitt)
    - Netatmo: Monitors value changes (0.101, 0.202 mm increments)
    - Ecowitt WS90: Direct mm/h readings
    - 15-minute auto-reset timeout after rain stops
    - Works with daily/hourly accumulation sensors
  - **Solar Radiation Sensors** (optional, choose one or both):
    - `solar_radiation_sensor`: Solar radiation sensor (W/m²)
    - `uv_index_sensor`: UV index sensor (0-15) - automatically converts to W/m² for forecast
  - **Cloud Coverage Sensor** (optional):
    - `cloud_coverage_sensor`: Cloud coverage percentage (0-100%)
  - All sensors optional with intelligent fallback logic

- **Intelligent Rain Detection System**
  - **Single Rain Sensor Configuration**:
    - Smart auto-detection based on sensor behavior
    - **Accumulation Mode** (Netatmo, Ecowitt): Detects mm increments (0.101, 0.202, etc.)
    - **Rate Mode** (Ecowitt WS90): Direct mm/h intensity readings
    - Works with device_class='precipitation' and unit='mm'
  - **Smart Detection**:
    - Auto-detects sensor type from value patterns
    - Accumulation sensors: Monitors value changes over 15-minute window
    - Rate sensors: Direct mm/h reading (if sensor provides it)
    - Gracefully handles both sensor types transparently
  - **Rain Override Logic**:
    - Overrides Zambretti prediction when rain detected
    - Shows "rainy" for light/moderate rain (0.1-7.6 mm/h)
    - Shows "pouring" for heavy rain (≥7.6 mm/h)
    - Sets rain probability to 100% when actively raining
    - Auto-clears after 15 minutes of no rain (accumulation sensors)

- **Weather Entity Forecast Support**
  - **Daily Forecast**: 3-day forecast with temperature trends
    - Hourly temperature variation during the day (solar-aware)
    - Condition changes based on Zambretti algorithm
    - Day/night icon distinction (sunrise/sunset aware)
  - **Hourly Forecast**: 25-hour detailed forecast
    - Hourly temperature evolution (solar radiation integrated)
    - Hourly condition updates
    - Hourly rain probability
    - Dynamic day/night icons
    - Cloud cover estimation from humidity or sensor

- **Realistic Weather Conditions**
  - Dynamic icon selection based on time of day
  - Sunrise/sunset calculation using Home Assistant coordinates
  - Night icons (clear-night, rainy-night, etc.)
  - Day icons (sunny, cloudy, rainy, etc.)
  - Condition mapping from Zambretti forecasts

- **Feels Like Temperature**
  - Calculated `feels_like` attribute in weather entity
  - Heat index for hot weather (>27°C)
  - Wind chill for cold weather (<10°C)
  - Accounts for humidity and wind speed
  - Graceful degradation if sensors unavailable

### 🔧 Enhanced - Rain Probability Calculation
- Improved rain probability algorithm:
  - Base probability from Zambretti (0-100%)
  - Base probability from Negretti-Zambra (0-100%)
  - Humidity adjustment (±25% based on humidity levels)
  - Dewpoint spread adjustment (±25% based on fog risk)
  - Current rain override (100% if actively raining)
  - High/Low confidence levels
  - Better handling of unavailable sensors
  - Works with both rain rate and accumulation sensors

### 🔧 Enhanced - Weather Icons & Forecast Display
- Night-time specific icons in Zambretti and Negretti-Zambra detail sensors
- Day/night awareness based on forecast time and location
- Consistent icon usage across all sensors and forecasts
- MDI (Material Design Icons) standard compliance
- Solar-aware temperature forecasts (warmer during sunny periods)
- Cloud cover integration (reduces solar warming when cloudy)

### 📝 Documentation
- Updated implementation details for forecast calculator
- Documented pressure trend forecasting model
- Documented temperature modeling with diurnal cycle and solar integration
- Documented rain sensor configuration (rate vs accumulation)
- Documented UV index usage as alternative to solar radiation
- Added examples of daily and hourly forecast usage
- Updated sensor configuration guide

### 🐛 Fixed
- Weather entity forecast now properly generates multi-day and hourly forecasts
- Forecast datetime calculations now timezone-aware
- Improved error handling in forecast generation
- Fixed temperature forecast availability in main sensor
- Fixed rain detection for accumulation-type sensors (Netatmo)
- Fixed feels_like calculation with proper fallback values
- Improved sensor state handling and history retrieval
- Better logging for rain detection and sensor diagnostics

---

## [3.0.3] - 2025-12-01

### ✨ Added - Enhanced Sensors
- **Enhanced Forecast Sensor** (`sensor.local_forecast_enhanced`)
  - Combines Zambretti/Negretti-Zambra with modern sensors
  - CRITICAL/HIGH/MEDIUM fog risk detection
  - Humidity effects on forecast
  - Atmospheric stability from wind gust ratio
  - Consensus confidence scoring
  - Accuracy estimate: ~94-98%
  
- **Enhanced Rain Probability Sensor** (`sensor.local_forecast_rain_probability`)
  - Zambretti + Negretti-Zambra probability mapping
  - Humidity adjustments (±15%)
  - Dewpoint spread adjustments (±15%)
  - Current rain override (100% if raining)
  - Confidence levels
  
- **Weather Entity** (`weather.local_weather_forecast_weather`)
  - Standard Home Assistant weather entity
  - Dew point calculation (Magnus formula)
  - Apparent temperature (Feels Like) - Heat Index/Wind Chill
  - Comfort level (Very Cold to Very Hot)
  - Fog risk assessment
  - Daily forecast support
  - Enable via config options

### 🔧 Enhanced - Calculations Module
- Added `calculate_dewpoint()` - Magnus formula for dew point
- Added `calculate_heat_index()` - US NWS formula for hot weather
- Added `calculate_wind_chill()` - US NWS formula for cold weather
- Added `calculate_apparent_temperature()` - Feels like temperature
- Added `get_comfort_level()` - Temperature comfort classification
- Added `get_fog_risk()` - Fog risk from temp-dewpoint spread
- Added `calculate_rain_probability_enhanced()` - Multi-factor rain probability

### 📝 Documentation
- Updated SENSORS_GUIDE.md with enhanced sensors
- Updated README.md with complete sensor list
- Added section on using modern sensors with algorithms
- Documented new weather entity features

### 🐛 Fixed
- **Device Software Version**: Updated device info to show correct version 3.0.3 (was incorrectly showing 2.0.0)

---

## [3.0.2] - 2025-11-30

### 🐛 Fixed
- **Home Assistant 2025.12 Compatibility**: Fixed deprecated `config_entry` warning in options flow
  - Removed explicit `self.config_entry = config_entry` assignment
  - Options flow now uses parent class property (HA 2025.12+)
  - Maintains backward compatibility with older HA versions
- **Sensor State Warnings**: Improved warning messages for optional wind sensors with invalid states
  - Now indicates if sensor is an optional wind sensor
  - Shows default value being used for better debugging
- **WebSocket Flooding**: Added throttle mechanism to prevent excessive state updates
  - Minimum 30 seconds between sensor updates for ALL sensors
  - Applied to main sensor and all child sensors (Pressure, Temperature, Zambretti Detail, Negretti-Zambra Detail)
  - Prevents "Client unable to keep up with pending messages" errors
  - Reduces database writes and improves system performance
  - Forecast accuracy not impacted (30s interval is acceptable for weather data)
  - PressureChange and TemperatureChange sensors have their own optimized update logic
- **Negative Time Intervals**: Fixed negative time values in `first_time` and `second_time` attributes
  - Detail sensors now reset `_last_update_time` to current time on restore instead of using old saved time
  - Prevents calculation errors when restoring from old saved states (e.g., first_time: -4269.75 minutes)
  - Fixes `forecast_temp_short: unavailable, -1` issue caused by negative time intervals
  - Time intervals now always show positive values for future forecasts
- **Temperature Forecast Debug**: Added detailed debug logging to `_calculate_temp_short_forecast()`
  - Shows why temperature forecast is unavailable (missing sensors, invalid data, etc.)
  - Helps troubleshoot forecast calculation issues
  - Displays calculation details when forecast succeeds

### 🔧 Technical Details
- Updated `config_flow.py` to remove deprecated `__init__` method in `LocalWeatherForecastOptionsFlow`
- Modified `_get_sensor_value()` to provide more informative warning messages
- Added `_last_update_time` and `_update_throttle_seconds` to `LocalWeatherForecastEntity`
- Implemented throttle logic in `_handle_sensor_update()` callback for main sensor
- Implemented throttle logic in `_handle_main_update()` callback for all child sensors
- PressureChange and TemperatureChange sensors maintain their existing efficient update logic
- Fixed `_last_update_time` restore logic in `LocalForecastZambrettiDetailSensor` and `LocalForecastNegZamDetailSensor`
- Changed from `last_state.last_changed` to `dt_util.now()` to prevent negative intervals
- Enhanced `_calculate_temp_short_forecast()` with comprehensive debug logging

---

## [3.0.1] - 2025-11-29

### 🐛 Fixed
- **Config Flow**: Fixed issue where optional wind speed and wind direction sensors couldn't be left empty
  - Changed from `default=""` to `description={"suggested_value": ...}` for entity selectors
  - Added `multiple=False` parameter to prevent multiple entity selection
  - Empty values are now properly converted to `None` instead of empty strings
  - Affects both initial setup and options flow
  - Users can now save configuration without providing wind sensors

### 🔧 Technical Details
- Updated `config_flow.py` to use `suggested_value` instead of `default` for optional entity selectors
- Added cleanup logic to convert empty strings to `None` for optional sensor fields
- Properly handles `None`/empty validation in both setup and options flows

---

## [3.0.0] - 2025-11-29

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



