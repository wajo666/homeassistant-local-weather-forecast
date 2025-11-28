# Release Notes - Version 3.0.0

**Release Date:** 2025-01-28

---

## 🎯 Major Release - 100% YAML Compatibility

This version achieves **complete feature parity** with the original YAML implementation with exact entity IDs and attribute formats.

---

## 🚨 Breaking Changes

### Entity IDs Changed
All entity IDs now match original YAML format exactly:

| Old Entity ID | New Entity ID |
|---------------|---------------|
| `sensor.local_weather_forecast_local_forecast` | `sensor.local_forecast` |
| `sensor.local_weather_forecast_pressure` | `sensor.local_forecast_pressure` |
| `sensor.local_weather_forecast_temperature` | `sensor.local_forecast_temperature` |
| `sensor.local_weather_forecast_pressure_change` | `sensor.local_forecast_pressurechange` ⚠️ no underscore! |
| `sensor.local_weather_forecast_temperature_change` | `sensor.local_forecast_temperaturechange` ⚠️ no underscore! |
| `sensor.local_weather_forecast_zambretti_detail` | `sensor.local_forecast_zambretti_detail` |
| `sensor.local_weather_forecast_neg_zam_detail` | `sensor.local_forecast_neg_zam_detail` |

### Friendly Names Changed
Device name prefix removed from all sensors:

- Before: `"Local Weather Forecast Local forecast"`
- After: `"Local forecast"`

All sensor names now match original YAML exactly.

### Attribute Formats Restored
All attributes now use original list/tuple/array formats instead of strings:

- `wind_direction`: List `[wind_fak, degrees, text, speed_fak]`
- `forecast_zambretti`: List `[text, number, letter]`
- `forecast_neg_zam`: List `[text, number, letter]`
- `forecast_short_term`: List `[condition, pressure_system]`
- `forecast_pressure_trend`: List `[text, index]`
- `rain_prob`: List `[prob_6h%, prob_12h%]`
- `icons`: Tuple `(icon_now, icon_later)`
- `first_time`/`second_time`: List `[time_string, minutes]`

---

## ✨ New Features

### 🌡️ Short-term Temperature Forecast
New `forecast_temp_short` attribute predicting temperature at next forecast interval:
- **Format:** `[predicted_temp, interval_index]`
- **Intervals:** 0=6h, 1=12h, -1=unavailable
- Uses temperature change rate and forecast timing for accurate calculation

### 🌤️ Forecast Weather States
Detail sensors now include weather state predictions:
- **Format:** `[state_6h, state_12h]`
- **States:** 
  - 0 = sunny
  - 1 = partly cloudy
  - 2 = partly rainy
  - 3 = cloudy
  - 4 = rainy
  - 5 = pouring
  - 6 = lightning
- Mapped from 26 Zambretti/Negretti-Zambra forecast types

### 🌙 Day/Night Icon Support
Automatic icon selection based on sun position:
- Uses `sun.sun` entity to determine day/night
- Different icons for sunny and partly cloudy states
- More accurate visual representation

### ⏱️ Dynamic Forecast Timing
Intelligent time calculations with aging correction:
- Tracks last update timestamp
- Adds correction if forecast is older than 6 hours
- Returns both formatted time (HH:MM) and minutes remaining

### 💧 Detailed Rain Probability
Precise calculations based on weather state transitions:
- **Zambretti:** 9 rules for different state combinations
- **Negretti-Zambra:** 4 simplified rules
- Returns probability for both 6h and 12h intervals

### 🔌 Extended Device Class Support
Now accepts both device classes for pressure sensors:
- `atmospheric_pressure` (original)
- `pressure` (new)
- Compatible with more weather stations and sensors

### 📊 Additional Detail Attributes
Easier access to forecast data:
- `forecast_text`: Explicit forecast text
- `forecast_number`: Forecast number 0-25
- `letter_code`: Zambretti letter code A-Z

---

## 🔧 Technical Changes

### Automatic Entity Migration
- Migration logic in `__init__.py` automatically renames entities on first load
- Seamless upgrade from v2.x to v3.0.0
- No manual intervention needed for existing installations

### Dynamic Entity Lookups
- All hardcoded entity IDs replaced with dynamic lookups
- Helper methods `_get_main_sensor_id()` and `_get_entity_id(suffix)`
- Supports both old and new entity ID formats during migration
- Detail sensors automatically find main sensor regardless of format

### Attribute Format Standardization
- Lists for multi-value attributes
- Tuples for paired values (icons)
- Integers and floats with proper rounding
- Matches original YAML implementation exactly

---

## 🐛 Bug Fixes

- ✅ Detail sensors no longer show "unknown" state - now correctly display forecast text
- ✅ Temperature short forecast works correctly (was always showing "unavailable, -1")
- ✅ Rain probability and icons now use proper types (list/tuple instead of strings)
- ✅ Forecast timing now shows dynamic calculations instead of fixed values
- ✅ Pressure and temperature sensors now update correctly from main sensor
- ✅ Friendly names no longer include device name prefix

---

## 📝 Documentation Updates

### WEATHER_CARDS.md
- All examples updated to new entity IDs
- Direct array access instead of string splitting
- Updated entity ID reference
- Added examples for all new attributes

### README.md
- Updated device class requirements
- Both `atmospheric_pressure` and `pressure` now documented
- Added note about dual device class support

---

## 🔄 Migration Guide

### For Existing Python Integration Users

#### Option A: Clean Installation (Recommended)
1. Go to **Settings → Devices & Services**
2. Find "Local Weather Forecast" and click **Delete**
3. Restart Home Assistant
4. Update integration files to v3.0.0
5. Add integration again via **Settings → Devices & Services → Add Integration**

#### Option B: Automatic Migration
1. Update integration files to v3.0.0
2. Restart Home Assistant
3. Migration runs automatically - entity IDs are renamed
4. Go to **Settings → Devices & Services** and **Reload** the integration
5. Verify new entity IDs in **Settings → Entities**

### For YAML Users
**Zero changes needed!** 🎉

- Entity IDs are now identical to YAML
- Friendly names match exactly
- Seamless migration from YAML to Python integration
- All automations and dashboards will work without modification

---

## 💡 Important Notes

### About Attribute Display
Home Assistant UI displays lists as comma-separated strings, but they **ARE** proper lists internally:

```yaml
# In UI you see:
wind_direction: 0, 0, N, 0

# But in reality it is:
wind_direction: [0, 0, "N", 0]  # LIST

# Template access works correctly:
{{ state_attr("sensor.local_forecast", "wind_direction")[2] }}  # Returns "N"
```

### Verification After Upgrade
Check these to ensure successful migration:

1. **Entity IDs** (Developer Tools → States):
   - ✅ `sensor.local_forecast` (not `local_weather_forecast_local_forecast`)
   - ✅ `sensor.local_forecast_zambretti_detail`

2. **Friendly Names** (Settings → Entities):
   - ✅ "Local forecast" (not "Local Weather Forecast Local forecast")

3. **Detail Sensors** (Developer Tools → States):
   - ✅ State: Shows forecast text (not "unknown")
   - ✅ Attributes: All present (forecast, rain_prob, icons, first_time, etc.)

---

## 📊 What's Included

### Complete Feature Parity with YAML

| Feature | YAML | Python v3.0.0 | Status |
|---------|------|---------------|--------|
| Entity IDs | ✅ | ✅ | 100% identical |
| Friendly Names | ✅ | ✅ | 100% identical |
| Attributes | ✅ | ✅ | 100% identical formats |
| Calculations | ✅ | ✅ | 100% accurate |
| Algorithms | ✅ | ✅ | 100% same |

### Bonus Features (Not in YAML)

- ✅ UI Configuration (no YAML editing needed)
- ✅ Automatic entity migration
- ✅ Historical data fallback
- ✅ State restoration after restart
- ✅ Better error handling
- ✅ Extended device class support

---

## 🎊 Summary

Version 3.0.0 represents a **major milestone** in achieving complete compatibility with the original YAML implementation while adding modern conveniences:

- **For YAML users:** Seamless migration with zero configuration changes
- **For Python users:** Automatic migration with improved functionality
- **For all users:** More accurate forecasts with additional features

**Thank you for using Local Weather Forecast! 🌤️**

---

## 📚 Additional Resources

- [Full Changelog](CHANGELOG.md)
- [Weather Card Examples](WEATHER_CARDS.md)
- [Configuration Guide](README.md)
- [GitHub Repository](https://github.com/wajo666/homeassistant-local-weather-forecast)
- [Issue Tracker](https://github.com/wajo666/homeassistant-local-weather-forecast/issues)

---

**Version:** 3.0.0  
**Release Date:** 2025-01-28  
**Compatibility:** Home Assistant 2024.1.0+  
**Breaking Changes:** Yes (see above)  
**Migration:** Automatic

