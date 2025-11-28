# Release v2.0.0 - Local Weather Forecast

## 🎉 Major Update: Complete Integration Refactor

This release represents a complete refactor and modernization of the Local Weather Forecast integration with UI configuration, multi-language support, and enhanced reliability.

---

## ✨ New Features

### 🎨 Modern UI Configuration
- **Config Flow UI** - Easy setup through Home Assistant UI (no more YAML editing!)
- **Options Flow** - Reconfigure integration without removing/re-adding
- **Entity Registry** - Proper entity management and customization
- **Device Info** - Integration appears as a device in HA

### 🌍 Multi-Language Support
- **5 Languages:** German (de), English (en), Greek (gr), Italian (it), Slovak (sk)
- **Forecast Texts** - Weather predictions in your language
- **UI Configuration** - Language selection in setup wizard

### 🔧 Advanced Pressure Handling
- **Pressure Type Selection** - Choose between:
  - **QFE (Absolute)** - Station pressure (most sensors: BME280, BMP280)
  - **QNH (Relative)** - Sea level pressure (weather stations: Ecowitt, Netatmo)
- **Automatic Conversion** - Correct sea level pressure calculation based on elevation

### 💾 Smart Fallbacks & Recovery
- **Historical Data Fallback** - Uses last 24h of data when sensors unavailable
- **Restore State** - Recovers last known values after restart
- **Graceful Degradation** - Continues operating with partial sensor data
- **Default Values** - Sensible defaults when sensors missing

### 🧠 Dual Forecast Models
Both algorithms run simultaneously for comparison:
- **Zambretti Forecaster** - Classic 1920s algorithm with seasonal adjustments
- **Negretti & Zambra** - Modern "slide rule" approach with detailed wind corrections

---

## 🔄 Breaking Changes

### Migration from v1.x

**Old (YAML configuration):**
```yaml
sensor:
  - platform: local_weather_forecast
    pressure: sensor.pressure
    temperature: sensor.temperature
```

**New (UI configuration):**
1. Remove old YAML configuration
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Local Weather Forecast"
5. Follow setup wizard

**Note:** Entity names have changed. Update your automations/scripts:
- `sensor.zambretti_forecast` → `sensor.local_forecast`
- Additional sensors created for pressure, temperature, trends

---

## 📊 New Sensors Created

The integration now creates 7 sensors:

1. **`sensor.local_forecast`** - Main forecast with all attributes
2. **`sensor.local_forecast_pressure`** - Sea level corrected pressure
3. **`sensor.local_forecast_temperature`** - Current temperature
4. **`sensor.local_forecast_pressure_change`** - 3-hour pressure trend
5. **`sensor.local_forecast_temperature_change`** - 1-hour temperature trend
6. **`sensor.local_forecast_zambretti_detail`** - Zambretti forecast details
7. **`sensor.local_forecast_neg_zam_detail`** - Negretti-Zambra forecast details

---

## 🐛 Bug Fixes

- ✅ Fixed async/await issues in sensor updates
- ✅ Fixed coroutine handling in wind speed calculations
- ✅ Fixed import errors (CONF_PRESSURE_TYPE)
- ✅ Fixed AttributeError (_get_historical_value method)
- ✅ Fixed entity unique IDs for proper entity management
- ✅ Fixed pressure trend calculations
- ✅ Fixed wind direction text mapping

---

## 📏 Sensor Units & Requirements

**Required Units (IMPORTANT!):**

| Sensor | Unit | Symbol | Example |
|--------|------|--------|---------|
| **Pressure** | Hectopascals | `hPa` | 1013.25 |
| **Temperature** | Celsius | `°C` | 15.0 |
| **Wind Speed** | Metres/second | `m/s` | 5.0 |
| **Wind Direction** | Degrees | `°` | 180 |

**Conversions:**
- Wind: `km/h ÷ 3.6 = m/s`
- Temp: `(°F - 32) × 5/9 = °C`
- Pressure: `inHg × 33.8639 = hPa`

See README.md for template examples if your sensors use different units.

---

## 🔧 Technical Improvements

### Code Quality
- ✅ Full Python 3.x async/await implementation
- ✅ Type hints throughout codebase
- ✅ Proper error handling and logging
- ✅ RestoreEntity support for state recovery
- ✅ Clean separation of concerns (models split into separate files)

### Architecture
- ✅ Config flow for UI configuration
- ✅ Options flow for reconfiguration
- ✅ Entity platform for proper sensor management
- ✅ Device info for integration grouping
- ✅ Unique IDs for all entities

### Reliability
- ✅ Fallback to historical data when sensors unavailable
- ✅ State restoration after restart
- ✅ Validation of sensor availability
- ✅ Graceful handling of missing optional sensors

---

## 📁 File Structure Changes

```
custom_components/local_weather_forecast/
├── __init__.py           (NEW - Integration setup)
├── config_flow.py        (NEW - UI configuration)
├── const.py              (NEW - Constants and defaults)
├── sensor.py             (UPDATED - Entity platform)
├── manifest.json         (UPDATED - v2.0.0)
├── strings.json          (NEW - UI translations)
├── forecast_data.py      (UPDATED - Multi-language data)
├── zambretti.py          (UPDATED - Zambretti algorithm)
├── negretti_zambra.py    (UPDATED - Negretti-Zambra algorithm)
└── translations/         (NEW - Language files)
    ├── de.json
    ├── en.json
    ├── gr.json
    ├── it.json
    └── sk.json
```

---

## 📖 Documentation

### Updated Documentation
- ✅ **README.md** - Complete rewrite with setup instructions
- ✅ **WEATHER_CARDS.md** - Lovelace card examples
- ✅ **CONTRIBUTING.md** - Contribution guidelines
- ✅ **TESTING.md** - Testing procedures

### New Documentation
- ✅ **Unit conversions** - Template examples for different units
- ✅ **Multi-language setup** - Language configuration guide
- ✅ **Advanced sensor setup** - Multiple sensor examples
- ✅ **Pressure type guide** - QFE vs QNH explanation

---

## 🎯 Accuracy

- **~94% Accuracy** - Based on validated IoT implementations
- **Dual Models** - Compare Zambretti and Negretti-Zambra forecasts
- **Weather-Dependent** - Higher accuracy in stable weather patterns
- **Location-Dependent** - Best results in temperate climates

---

## 🔗 Requirements

- **Home Assistant:** 2024.1.0 or newer
- **Python:** 3.11+ (provided by Home Assistant)
- **Required Sensor:** Barometric pressure (hPa)
- **Recommended Sensors:** Temperature (°C), Wind direction (°), Wind speed (m/s)

---

## 📦 Installation

### Via HACS (Recommended)
1. Open HACS → Integrations
2. Click ⋮ → Custom repositories
3. Add: `https://github.com/wajo666/homeassistant-local-weather-forecast`
4. Category: Integration
5. Click "Download"
6. Restart Home Assistant
7. Add integration via UI

### Manual Installation
1. Download `custom_components/local_weather_forecast` folder
2. Copy to `<config>/custom_components/`
3. Restart Home Assistant
4. Add integration via UI

---

## 🙏 Credits

**Original Author:** [@HAuser1234](https://github.com/HAuser1234)  
**Current Maintainer:** [@wajo666](https://github.com/wajo666)  
**Original Repository:** [HAuser1234/homeassistant-local-weather-forecast](https://github.com/HAuser1234/homeassistant-local-weather-forecast)

---

## 📝 Changelog

### Added
- UI configuration with config flow
- Options flow for reconfiguration
- Multi-language support (5 languages)
- Pressure type selection (QFE/QNH)
- Historical data fallback
- State restoration after restart
- 7 distinct sensors with proper device classes
- Dual forecast model support
- Translation files for UI
- Comprehensive documentation

### Changed
- Complete refactor to use entity platform
- Async/await implementation throughout
- Updated to modern Home Assistant standards
- Improved error handling and logging
- Better sensor state management

### Fixed
- Import errors with constants
- Async/await coroutine handling
- Wind speed calculation errors
- Pressure trend calculations
- Entity unique ID management
- State restoration after restart

### Removed
- YAML configuration (replaced with UI)
- Legacy platform setup

---

## 🐛 Known Issues

None currently reported. Please report issues at:
https://github.com/wajo666/homeassistant-local-weather-forecast/issues

---

## 🚀 What's Next?

See [FUTURE_SENSORS.md](FUTURE_SENSORS.md) for planned enhancements:
- Humidity sensor support
- Rain sensor integration
- Cloud cover detection
- Adaptive learning algorithms
- Target accuracy: ~97%+

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

**Full Documentation:** [README.md](README.md)  
**Installation Guide:** See above  
**Configuration Help:** [WEATHER_CARDS.md](WEATHER_CARDS.md)  

Thank you for using Local Weather Forecast! 🌤️

