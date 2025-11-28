# 🎉 Local Weather Forecast v2.0.2

**Major Update** - Detail Sensors, Historical Fallback, and Enhanced Weather Cards!

---

## ✨ What's New

### 🌟 Detail Sensors Fully Implemented
- **Zambretti Detail Sensor** - Provides detailed 6h and 12h forecasts
  - Rain probability estimation (10%, 15%, etc.)
  - Dynamic weather icons (22 different types)
  - Forecast times and letter codes
- **Negretti-Zambra Detail Sensor** - Alternative forecast model with same features

### 📊 Enhanced Change Tracking
- **Temperature Change Sensor** - Tracks temperature changes over 1 hour
- **Pressure Change Sensor** - Now initializes immediately with current value
- Both sensors now start tracking from first startup

### 🔄 Historical Data Fallback
- Sensors automatically fetch historical values when unavailable after restart
- No more "unknown" values after Home Assistant restart
- Seamless recovery from temporary sensor outages

---

## 🐛 Bug Fixes

### Critical Fixes
- ✅ Fixed all entity ID tracking issues (sensors now use correct IDs)
- ✅ Fixed Negretti-Zambra detail sensor unavailable state
- ✅ Fixed forecast format (arrays → comma-separated strings)
- ✅ Fixed pressure/temperature change sensors initialization

### Sensor Fixes
| Sensor | Before | After |
|--------|--------|-------|
| Pressure | unknown | 1017.9 hPa ✅ |
| Temperature | unknown | 3.0°C ✅ |
| Zambretti Detail | unknown / ['Fine', 1, 'B'] | "Fine" + attributes ✅ |
| Negretti-Zambra Detail | unavailable | "Settled Fine" + attributes ✅ |
| Pressure Change | 0.0 (no history) | Initializes correctly ✅ |
| Temperature Change | 0.0 (no history) | Tracks from startup ✅ |

---

## 📚 Documentation

### New Documentation Files
- **WEATHER_CARDS.md** - Complete weather card examples
  - 🎨 Basic Mushroom Card
  - 🌟 Advanced Mushroom Card (with rain probability & temperature trends)
  - 📱 Compact Mobile Card
  - 🎯 Mini Card
  - 📊 Comparison Card
- **CHANGELOG.md** - Full changelog
- **Sensor Unit Documentation** - Required units for all input sensors

### Updated Documentation
- ✅ README with original developer attribution
- ✅ Configuration options (pressure type selection)
- ✅ Multi-language support details
- ✅ Installation instructions

---

## 🎨 Weather Card Examples

### Advanced Mushroom Card Features:
```yaml
┌──────────────┬──────────────┬──────────────┐
│   🏠 Now     │   🌤️ ~6h    │   🌥️ ~12h   │
│   Mixed      │  10% rain    │  15% rain    │
│   3°C        │  ↘ ~-4.8°C  │  ↘ ~-12.6°C │
│   → Fine     │              │              │
└──────────────┴──────────────┴──────────────┘

┌─────────────────────────────────────┐
│  📊 1017.8 hPa  🌡️ 3°C              │
│  📉 -0.1 hPa    🌡️↘ -1.3°C/h        │
└─────────────────────────────────────┘
```

**Features:**
- ✅ Rain probability for 6h and 12h
- ✅ Temperature trend estimation
- ✅ Dynamic weather icons
- ✅ Pressure and temperature change tracking
- ✅ Color-coded by forecast severity

---

## 🔧 Technical Details

### Icon Mapping
22 different weather icons mapped to forecast types:
- ☀️ Settled fine, Fine weather
- ⛅ Becoming fine, Partly cloudy
- ☁️ Fairly fine, Cloudy
- 🌦️ Showery conditions
- 🌧️ Rainy, Unsettled
- ⛈️ Stormy conditions

### Rain Probability Algorithm
Estimates rain probability based on forecast number (0-21):
- 0-1: 5-15% (Settled fine)
- 4-7: 30-50% (Possible showers)
- 10-14: 50-70% (Likely showers)
- 15-21: 70-95% (Rain/storms)

---

## 📋 Required Sensor Units

Make sure your input sensors use these units:
- **Temperature**: °C (Celsius)
- **Pressure**: hPa (hectopascals)
- **Wind Speed**: m/s (meters per second)
- **Wind Direction**: degrees (0-360°)

---

## 🚀 Installation

### HACS (Recommended)
1. Add custom repository: `wajo666/homeassistant-local-weather-forecast`
2. Download via HACS
3. Restart Home Assistant
4. Add integration via UI

### Manual
1. Copy `custom_components/local_weather_forecast` to your config folder
2. Restart Home Assistant
3. Add integration via UI (Settings → Devices & Services → Add Integration)

---

## ⚙️ Configuration

### UI Configuration Options:
- ✅ Temperature sensor
- ✅ Pressure sensor (relative or absolute)
- ✅ Wind direction sensor
- ✅ Wind speed sensor
- ✅ Elevation (for sea level pressure calculation)
- ✅ Language (EN, DE, GR, IT, SK)

---

## 🎯 What You Get

### 7 Sensors:
1. **Main Forecast** - 12hr forecast with all data
2. **Pressure** - Sea level pressure (hPa)
3. **Temperature** - Current temperature (°C)
4. **Pressure Change** - 3-hour pressure trend
5. **Temperature Change** - 1-hour temperature trend
6. **Zambretti Detail** - Detailed forecast with rain probability
7. **Negretti-Zambra Detail** - Alternative forecast model

### Sensor Attributes:
- Forecast texts (short-term, Zambretti, Negretti-Zambra)
- Pressure trend (Steady, Rising, Falling)
- Wind direction (N, S, E, W, etc.)
- Language index
- Weather icons
- Rain probability (6h, 12h)
- Forecast times
- Letter codes

---

## 🙏 Credits

### Original Developer
- **HAuser1234** - Original integration development
- Repository: https://github.com/HAuser1234/homeassistant-local-weather-forecast

### Current Maintainer
- **wajo666** - Enhanced version with detail sensors and improvements

### Forecast Algorithms
- **Zambretti Algorithm** - Weather forecasting based on pressure trends
- **Negretti & Zambra** - Alternative barometer-based forecasting

---

## 📝 Changelog

See [CHANGELOG.md](https://github.com/wajo666/homeassistant-local-weather-forecast/blob/main/CHANGELOG.md) for full changelog.

---

## 🐛 Bug Reports

Report issues at: https://github.com/wajo666/homeassistant-local-weather-forecast/issues

---

## 📄 License

MIT License - See [LICENSE](https://github.com/wajo666/homeassistant-local-weather-forecast/blob/main/LICENSE)

---

## 🎊 Enjoy Your Local Weather Forecast!

All 7 sensors are now fully functional and ready to use! 🌤️

Check out **WEATHER_CARDS.md** for beautiful dashboard examples! 📊

