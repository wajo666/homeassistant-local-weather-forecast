
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.2] - 2025-12-09

### ✨ Added

- **History Persistence for Change Sensors** (2025-12-09)
  - **PressureChange sensor** now saves and restores historical data across Home Assistant restarts
  - **TemperatureChange sensor** now saves and restores historical data across Home Assistant restarts
  - **Problem solved**: Previously, sensors lost all historical data on restart and had to wait 3 hours (pressure) or 1 hour (temperature) to recalculate accurate change values
  - **Solution**: History is now saved in `extra_state_attributes` and automatically restored on startup
  - **Benefits**:
    - ✅ Accurate pressure/temperature change values **immediately** after restart
    - ✅ No need to wait for new 3-hour/1-hour data collection period
    - ✅ Historical readings preserved with timestamps (up to 180 minutes for pressure, 60 minutes for temperature)
    - ✅ Maintains forecast accuracy even after Home Assistant reboots
  - **New sensor attributes** (visible in Developer Tools → States):
    - `history`: Array of [timestamp_iso, value] pairs - full historical data in ISO 8601 format
    - `history_count`: Number of historical readings currently stored (e.g., "35")
    - `oldest_reading`: ISO timestamp of oldest reading in history (e.g., "2025-12-09T12:00:00")
    - `newest_reading`: ISO timestamp of newest reading in history (e.g., "2025-12-09T15:00:00")
  - **Startup logging**: Log messages show restored history count on each restart
    - Example: `PressureChange: Restored 42 historical values from previous session`
    - Example: `TemperatureChange: Restored 18 historical values from previous session`
  - **Behavior**: Only adds new initial reading if history is empty (prevents duplicates)
  - **Technical details**: Uses `datetime.fromisoformat()` for timestamp parsing, validates all entries before restoring


---

## [3.1.1] - 2025-12-09

### ✨ Added - Auto-Detection & Improvements

- **Centralized Language Handling** (2025-12-09)
  - **NEW**: Created `language.py` module for centralized language detection and translation
  - Single source of truth for language mapping (HA language code → forecast_data.py index)
  - Eliminates duplicate language detection code in `sensor.py` and `weather.py`
  - All translations now in `forecast_data.py` with consistent array order: [German, English, Greek, Italian, Slovak]
  - Helper functions: `get_language_index()`, `get_wind_type()`, `get_visibility_estimate()`, `get_comfort_level_text()`, `get_fog_risk_text()`, `get_atmosphere_stability_text()`, `get_adjustment_text()`
  - **Complete multilingual support for all UI texts:**
    - Wind types (Beaufort scale 0-12)
    - Visibility estimates (fog risk based)
    - Comfort levels (very_cold to very_hot)
    - Fog risk levels (none to critical)
    - Atmosphere stability (stable, moderate, unstable, very_unstable)
    - Adjustment details (humidity, fog risk, atmosphere stability warnings)
  - **Fixed**: "Fine, Possibly showers. High humidity (97.0%), CRITICAL fog risk (spread 0.4°C)" now displays in user's language
  - **Fixed**: All hardcoded English texts in sensor states and attributes now translated
  - **Unit conversion in translated texts** - automatic conversion based on HA unit system:
    - Temperature spreads in adjustment texts: °C → °F for imperial users
    - Properly scales temperature DIFFERENCES (× 1.8 only, no +32 offset)
    - Example metric: "CRITICAL fog risk (spread 0.4°C)"
    - Example imperial: "CRITICAL fog risk (spread 0.7°F)"
    - Uses consistent conversion logic throughout the integration
  - Improved maintainability - all language logic in one place
  - Consistent language behavior across all components
  - Example Slovak metric: "Pekné počasie, možné prehánky. Vysoká vlhkosť (97.0%), KRITICKÉ riziko hmly (spread 0.4°C)"
  - Example Slovak imperial: "Pekné počasie, možné prehánky. Vysoká vlhkosť (97.0%), KRITICKÉ riziko hmly (spread 0.7°F)"

- **Automatic Unit Conversion** (2025-12-09)
  - **NEW**: Sensors can now use any standard unit - automatic conversion to required units
  - **Integrated into all sensor readings and weather entity** - Pressure, Temperature, Wind Speed, Wind Gust, Humidity, Rain Rate, Dew Point
  - **Weather entity properties**: All native properties (temperature, pressure, wind_speed, wind_gust_speed, dew_point) now convert units
  - **Pressure sensors**: Supports hPa, mbar, inHg, mmHg, kPa, Pa, psi → converts to hPa
    - Example: 29.92 inHg → automatically converted to 1013.25 hPa
  - **Temperature sensors**: Supports °C, °F, K → converts to °C
    - Example: 68°F → automatically converted to 20°C
  - **Wind speed sensors**: Supports m/s, km/h, mph, knots, ft/s → converts to m/s
    - Example: 36 km/h → automatically converted to 10 m/s
  - **Rain rate sensors**: Supports mm, mm/h, in, in/h → converts to mm or mm/h
    - Example: 0.5 in/h → automatically converted to 12.7 mm/h (USA rain gauges)
  - **Reverse conversion implemented**: `format_for_ui()` can convert SI units back to user's preferred units
    - Example: 1013.25 hPa → 29.92 inHg for imperial users
    - Utility function for future UI enhancements
  - Config flow logs detected units: "Pressure sensor: sensor.barometer | Value: 29.92 inHg | Will be converted to hPa"
  - Debug logging shows conversion: "Converted sensor.barometer: 29.92 inHg → 1013.25 hPa"
  - Works with USA (inHg, °F, mph, in/h), European (hPa, °C, km/h, mm/h), and other unit systems
  - No more manual unit checking or template sensors required!

- **Automatic Language Detection from Home Assistant UI** (2025-12-09)
  - **BREAKING CHANGE**: Removed manual language selection from integration config
  - Language is now automatically detected from Home Assistant UI settings
  - Supports languages: Slovak (sk), English (en), German (de), Italian (it), Greek (el/gr)
  - Wind type names (Beaufort scale) now use HA UI language:
    - Slovak: "Ticho", "Slabý vánok", "Búrka", "Hurikán", etc.
    - English: "Calm", "Light air", "Gale", "Hurricane", etc.
    - German: "Windstille", "Leiser Zug", "Sturm", "Orkan", etc.
    - Italian: "Calmo", "Bava di vento", "Burrasca", "Uragano", etc.
    - Greek: "Νηνεμία", "Ελαφρύ αεράκι", "Θύελλα", "Τυφώνας", etc.
  - Forecast texts automatically use correct language
  - Change language in HA: `Settings → System → General → Language`
  - No migration needed - existing installations will use HA UI language automatically

- **Rain Rate Sensor Startup Reliability** (2025-12-09)
  - Added entity availability waiting during Home Assistant restart
  - Fixes "entity not available" errors for WeatherFlow stations and similar sensors
  - Waits up to 15 seconds with 0.5s intervals for rain sensor availability
  - Prevents integration failures during HA boot sequence
  - New helper method: `_wait_for_entity()` for graceful sensor loading


- **Weather Entity - Complete Details Card** (2025-12-09)
  - **NEW**: Card 8 in WEATHER_CARDS.md - displays ALL weather entity attributes
  - Shows 25+ attributes that are hidden in standard HA weather UI
  - Organized into sections: Current Conditions, Wind & Atmospheric, Fog & Visibility, Rain, Forecasts, Quality
  - Includes: feels_like, comfort_level, wind_gust, gust_ratio, atmosphere_stability, fog_risk, visibility_estimate
  - Also displays: dew_point, dewpoint_spread, rain_probability, forecast confidence, adjustments
  - Solves limitation of standard HA weather UI showing only 5 basic attributes
  - Custom Mushroom card layout with color-coded indicators
  - All data already available in weather entity attributes, now easily accessible in UI

### 🔧 Fixed

- **Type Safety Improvements - All Files** (2025-12-09)
  - **sensor.py**: Fixed 4 type warnings
    - Line 264: Added explicit `str()` conversion for State objects before `float()` conversion
    - Line 172-178: Changed `_get_sensor_value()` return type from `float` to `float | None` to match actual behavior
    - Lines 1767, 2009: Added type guards for `calculate_dewpoint()` calls
    - Type guards: `isinstance(temp, (int, float)) and isinstance(humidity, (int, float))`
  - **weather.py**: Fixed 6 type warnings
    - Line 26: Added `DeviceInfo` import from `homeassistant.helpers.entity`
    - Line 102: Changed device_info from dict to proper `DeviceInfo` type
    - Lines 754-756, 764-766: Fixed `async_add_executor_job` calls to pass function and arguments separately
    - Lines 929, 1080: Added explicit type annotations for `forecasts` variables
  - **config_flow.py**: 4 false positive warnings remain (TypedDict → FlowResult)
    - These are IDE false positives - `async_create_entry()` and `async_show_form()` correctly return `FlowResult`
    - Runtime behavior is correct
  - Improves code safety - ensures values are valid before mathematical operations
  - No functional changes - purely type safety improvements
  - Better IDE/type checker compatibility (PyCharm, mypy, pyright)
  - Backward compatible - code logic unchanged

- **Translation Descriptions - Updated for Automatic Unit Conversion** (2025-12-09)
  - **Updated**: All sensor descriptions now reflect that integration automatically converts units
  - **Before**: "Must provide values in hPa" / "Must provide values in °C" (misleading - users thought they needed specific units)
  - **After**: "Supports hPa, mbar, inHg, mmHg - automatically converted" / "Supports °C, °F, K - automatically converted"
  - Updated sensors: pressure, temperature, wind_speed, wind_gust, dewpoint, rain_rate
  - Affects: strings.json, en.json, de.json, sk.json (gr.json, it.json partial)
  - Users can now use ANY unit their sensors provide - integration handles conversion automatically
  - More accurate representation of implemented UnitConverter functionality

- **Translation Files - Removed Obsolete Language Field** (2025-12-09)
  - **Fixed**: Removed `language` field from all translation files (strings.json + 5 language translations)
  - Language selection removed from config_flow UI - now uses Home Assistant UI language automatically
  - Affects: strings.json, en.json, de.json, gr.json, it.json, sk.json
  - Removed from both "user" step and "options" step
  - Language is now auto-detected via `get_language_index(hass)` function
  - No user action needed - translations match actual config_flow implementation

- **IDE Warning - 'SENSOR_DOMAIN is Final'** (2025-12-09)
  - **Fixed**: Changed import from `from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN` to `from homeassistant.components import sensor`
  - Changed all usages from `domain=SENSOR_DOMAIN` to `domain=sensor.DOMAIN`
  - Resolves IDE/type checker warning about reassigning Final constant
  - No functional change, just cleaner typing compliance
  - Affects: config_flow.py (4 occurrences in EntitySelectorConfig)

- **Code Cleanup - Unused Imports Removed** (2025-12-09)
  - **Fixed**: Removed all unused imports from Python files
  - `config_flow.py`: Removed CONF_NAME, HomeAssistant, cv, UnitConverter (4 unused imports)
  - `language.py`: Removed UnitConverter (not actually used after refactoring)
  - `unit_conversion.py`: Removed Any from typing
  - `weather.py`: Removed get_language_index, timedelta (2 unused imports)
  - `__init__.py`: Removed Any from typing
  - Result: Cleaner code, faster imports, no pyflakes warnings
  - All files still compile and pass syntax checks

- **Debug Log SI Units Consistency** (2025-12-09)
  - **Fixed**: All debug/info logs now consistently use SI units (same as calculations)
  - Wind speed logs: Added "m/s" unit (was missing)
  - Wind gust logs: Added "m/s" unit (was missing)
  - Rain rate logs: Added "mm/h" unit (was missing in one place)
  - Gust ratio: Added precision formatting (.2f) for consistency
  - Temperature, pressure, humidity already had correct SI units (°C, hPa, %)
  - Examples:
    - "Enhanced: Config wind gust sensor = ..., wind_speed = 1.67 m/s"
    - "Enhanced: Calculated gust_ratio=1.67 (gust=2.78 m/s, speed=1.67 m/s)"
    - "RainProb: Current rain rate = 0.0 mm/h"
  - Makes debug logs easier to understand and consistent with internal calculations

- **Weather Card Translation Display** (2025-12-09)
  - **Fixed**: Weather cards now correctly display translated `atmosphere_stability` and `fog_risk` values
  - **Problem**: Cards used hardcoded English comparisons (`== "stable"`) which failed for translated values ("Mierne nestabilná")
  - **Solution**: Cards now use translated values directly and match by keywords (`"nestabilná" in stability`)
  - **Effect**: Slovak cards show "Mierne nestabilná" instead of "Unknown", colors work correctly
  - Affected cards: Advanced Mushroom Card (Card 3), Complete Weather Analysis (Card 7)
  - Works for all languages (German, English, Greek, Italian, Slovak)

- **Negretti-Zambra Debug Logging** (2025-12-09)
  - **Added**: Comprehensive debug logging to diagnose Negretti calculation failures
  - Logs input parameters: pressure, pressure_change, wind_data, elevation
  - Logs intermediate calculations: season, trend, z_hp adjustments, z_option
  - Logs final result: forecast_number, letter_code, forecast_text
  - Helps identify why Negretti returns 0% when Zambretti gives forecast
  - Example log: "Negretti: RESULT - forecast_number=17, letter_code=R, text='Nestálé, neskôr dážď'"

- **Fog Detection Logic** (2025-12-09)
  - **Fixed**: Fog can now be detected anytime (day or night) when conditions are met
  - Removed incorrect daytime restriction that prevented fog detection during daylight hours
  - Fog is now detected based solely on meteorological conditions:
    - Dewpoint spread < 1.5°C AND humidity > 85% → FOG
    - Dewpoint spread < 1.0°C AND humidity > 80% → FOG (near saturation)
  - Real-world example: Dense fog at 12:00 with spread=0.4°C, humidity=97% is now correctly detected
  - Fog can persist throughout the day in stable atmospheric conditions

- **Enhanced Sensor Attribute Translations** (2025-12-09)
  - **Fixed**: `atmosphere_stability` attribute now translated to user's language (was English only)
    - Example: "stable" → "Stabilná" (Slovak), "Stabil" (German)
  - **Fixed**: `fog_risk` attribute now translated to user's language (was English only)
    - Example: "high" → "Vysoké riziko hmly" (Slovak), "Hohes Nebelrisiko" (German)
  - Uses centralized `get_atmosphere_stability_text()` and `get_fog_risk_text()` helpers

- **Sensor Device Classes Added** (2025-12-09)
  - **Fixed**: `LocalForecastPressureChangeSensor` now has `ATMOSPHERIC_PRESSURE` device class
    - Enables proper unit conversion (hPa ↔ inHg) based on HA settings
  - **Fixed**: `LocalForecastTemperatureChangeSensor` now has `TEMPERATURE` device class
    - Enables proper unit conversion (°C ↔ °F) based on HA settings
  - **Fixed**: Added `state_class = MEASUREMENT` to PressureChange and TemperatureChange sensors
    - Enables historical statistics recording (graphs, long-term statistics)
    - Now shows data points every 5 minutes in history graphs like other sensors
  - Improves consistency with Home Assistant unit system

- **Weather Entity Language Detection** (2025-12-09)
  - Fixed weather entity ignoring Home Assistant UI language setting
  - Removed hardcoded Slovak translations for wind types and visibility estimates
  - Weather entity now uses automatic language detection like sensors
  - Wind type descriptions (Beaufort scale) now in correct language
  - Visibility estimates now in correct language
  - Supports: German, English, Greek, Italian, Slovak (defaults to English)
  - Consistent language behavior across all sensors and weather entity

- **Language Order Consistency** (2025-12-09)
  - Fixed wind type language array order to match `forecast_data.py` format
  - Correct order: [German, English, Greek, Italian, Slovak]
  - Ensures English fallback works correctly for unsupported languages
  - Previously had inconsistent ordering between forecast texts and wind types

- **Zambretti & Negretti-Zambra Number Mapping** (2025-12-09)
  - Fixed unmapped Zambretti number 33 warning for extreme rising pressure
  - Added mapping: z=33 → forecast index 25 (letter "Z" - very fine weather)
  - Fixed missing z=22 mapping (letter "F" - settling fair)
  - Occurs during rapid pressure increases (anticyclone formation)
  - Applied to both Zambretti and Negretti-Zambra algorithms
  - No more `WARNING: Unmapped Zambretti number: 33` in logs

## [3.1.0] - 2025-12-08

### 🔧 Fixed - Sensor Data Consistency & Auto-Updates
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



