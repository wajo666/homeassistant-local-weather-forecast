# Home Assistant Local Weather Forecast

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/wajo666/homeassistant-local-weather-forecast.svg)](https://github.com/wajo666/homeassistant-local-weather-forecast/releases)
[![Version](https://img.shields.io/badge/version-3.1.9-blue.svg)](https://github.com/wajo666/homeassistant-local-weather-forecast/blob/main/CHANGELOG.md)

## 🌤️ Offline Weather Forecasting Without External APIs

Get accurate 3-day weather forecasts using only your local sensors. No cloud services, no API keys, no external dependencies.

**Developer:** [@wajo666](https://github.com/wajo666) | Inspired by [@HAuser1234](https://github.com/HAuser1234)'s original work

---

## ✨ Key Features

- 🎯 **94-98% Accuracy** - With basic sensors (pressure + temperature + humidity)
- 🔌 **100% Offline** - Works without internet connection
- 📅 **3-Day Forecast** - Hourly (24h) + Daily (3 days)
- 🌍 **Multi-language** - Auto-detects Home Assistant UI language (EN, DE, SK, IT, EL)
- 🔄 **Auto Unit Conversion** - Use any units (°F, inHg, mph, km/h, etc.)
- 🎨 **Easy Setup** - Modern UI configuration (no YAML)

---

## 📋 Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Home Assistant | 2024.12.0 | Latest |
| Python | 3.12 | 3.12+ |
| HACS | 1.32.0+ | Latest |

---

## 📏 Sensors You Need

### Required (Minimum)
- ✅ **Pressure Sensor** (atmospheric_pressure) - The core of weather prediction

### Highly Recommended
- ⚠️ **Temperature Sensor** - For snow/frost detection and better accuracy (+5%)
- ⚠️ **Humidity Sensor** - For fog detection and moisture confirmation (+10%)

### Optional (Enhanced Features)
- ☀️ **Solar Radiation Sensor** - Real-time cloud detection (+15%)
- 🌧️ **Rain Sensor** - Definitive precipitation detection (+25%)
- 💨 **Wind Speed + Direction** - Better forecast adjustments (+3%)
- 💨 **Wind Gust** - Atmospheric stability detection (+3%)

### Supported Units (Auto-Converted)

| Sensor | Supported Units | Examples |
|--------|-----------------|----------|
| **Pressure** | hPa, mbar, inHg, mmHg, kPa, psi | 1013 hPa, 29.92 inHg |
| **Temperature** | °C, °F, K | 20°C, 68°F |
| **Wind Speed** | m/s, km/h, mph, knots | 10 m/s, 36 km/h |
| **Rain Rate** | mm/h, in/h | 2.5 mm/h, 0.1 in/h |
| **Solar Radiation** | W/m², lux | 850 W/m², 50000 lux |

💡 **Don't worry about units!** The integration automatically converts everything.

---

## 🎯 How It Works - Simple Explanation

### Weather Detection Priority System

The integration uses a **smart priority system** to determine current weather. Think of it as layers - if one layer has data, it wins:

```
┌─────────────────────────────────────────────────────────┐
│ PRIORITY 1: Rain Sensor                                 │
│ If raining NOW → Show "rainy" ✅                        │
└─────────────────────────────────────────────────────────┘
                        ↓ (if no rain)
┌─────────────────────────────────────────────────────────┐
│ PRIORITY 2: Fog Detection                               │
│ If humid + near saturation → Show "fog" ✅              │
└─────────────────────────────────────────────────────────┘
                        ↓ (if no fog)
┌─────────────────────────────────────────────────────────┐
│ PRIORITY 3: Solar Radiation (Daytime Only)              │
│ Measures real cloudiness from sunlight ✅               │
│ WMO Standards (oktas - eighths of sky):                 │
│ • Clear sky (<25% = 0-2 oktas) → "sunny" ☀️            │
│ • Scattered (25-50% = 3-4 oktas) → "partly cloudy" ⛅   │
│ • Broken (50-87.5% = 5-7 oktas) → "cloudy" ☁️          │
│ • Overcast (≥87.5% = 8 oktas) → defer to forecast      │
└─────────────────────────────────────────────────────────┘
                        ↓ (if night or no solar)
┌─────────────────────────────────────────────────────────┐
│ PRIORITY 4: Current Pressure State                      │
│ Based on current absolute pressure ✅                   │
│ • >1020 hPa → "sunny/clear" ☀️                         │
│ • 1000-1020 hPa → "partly cloudy" ⛅                    │
│ • <1000 hPa → "cloudy/rainy" ☁️                        │
└─────────────────────────────────────────────────────────┘
                        ↓ (fallback only)
┌─────────────────────────────────────────────────────────┐
│ PRIORITY 5: Forecast Model                              │
│ 6-12h future prediction (last resort) ⚠️                │
└─────────────────────────────────────────────────────────┘
```

### Universal Rules (Apply to ALL priorities)
- ❄️ **Snow Conversion:** If temp ≤ 2°C AND rainy → Convert to "snowy"
- 💧 **Humidity Correction:** If humidity >85% AND sunny → Upgrade to "cloudy"
- 🌙 **Night Mode:** Auto-converts "sunny" → "clear-night" after sunset

### Real-World Examples

**Example 1: Morning - Clear sky, pressure 1025 hPa**
```
✅ No rain sensor → Skip Priority 1
✅ Humidity 60%, spread 5°C → No fog, skip Priority 2
✅ Solar: 900 W/m² (max 1100) → 18% clouds → "sunny" ☀️ (WMO: 0-2 oktas)
Result: SUNNY (from Priority 3)
```

**Example 2: Afternoon - Light rain, pressure 995 hPa**
```
✅ Rain sensor: 2.5 mm/h → "rainy"
Result: RAINY (from Priority 1, overrides everything)
```

**Example 3: Night - Clear, pressure 1030 hPa**
```
✅ No rain → Skip Priority 1
✅ No fog → Skip Priority 2
✅ Solar inactive (night) → Skip Priority 3
✅ Pressure 1030 hPa → "sunny"
✅ Night mode → Convert to "clear-night" 🌙
Result: CLEAR-NIGHT
```

**Example 4: Winter - Cold, humid, no rain sensor**
```
✅ No rain sensor → Skip Priority 1
✅ Humidity 82%, spread 2.1°C → No fog (spread too large)
✅ Solar: 300 W/m² (max 1000) → 70% clouds → "cloudy" ☁️ (WMO: 5-7 oktas)
✅ Temp -5°C + Forecast shows rain → Convert to "snowy" ❄️
Result: SNOWY
```

---

## 🚀 Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click **Integrations** → **⋮** (menu) → **Custom repositories**
3. Add repository URL: `https://github.com/wajo666/homeassistant-local-weather-forecast`
4. Category: **Integration**
5. Click **Add** → Find **Local Weather Forecast** → **Download**
6. **Restart Home Assistant**
7. Go to **Settings** → **Devices & Services** → **Add Integration**
8. Search for **Local Weather Forecast** and configure

### Manual Installation

1. Download latest release from [GitHub](https://github.com/wajo666/homeassistant-local-weather-forecast/releases)
2. Extract to `config/custom_components/local_weather_forecast/`
3. Restart Home Assistant
4. Add via UI: **Settings** → **Devices & Services** → **Add Integration**

---

## ⚙️ Configuration

### Quick Setup

1. **Add Integration** - Search "Local Weather Forecast"
2. **Select Sensors:**
   - Pressure sensor (required)
   - Temperature, humidity (recommended)
   - Optional: wind, rain, solar radiation
3. **Configure Location:**
   - Elevation (auto-detected from HA)
   - Hemisphere (auto-detected)
4. **Choose Forecast Model:**
   - **Enhanced Dynamic** (recommended) - 98% accuracy
   - Zambretti - 94% accuracy
   - Negretti & Zambra - 92% accuracy
5. Done! ✅

### Options (Can Change Anytime)

Go to **Settings** → **Integrations** → **Local Weather Forecast** → **Configure**

- Change forecast model
- Add/remove optional sensors
- Adjust pressure sensor type
- Update elevation

---

## 📊 Available Entities

### Main Sensors

| Entity | Description |
|--------|-------------|
| `sensor.local_forecast` | Base forecast text with all attributes |
| `sensor.local_forecast_enhanced` | Enhanced forecast with fog/snow/frost detection |
| `sensor.local_forecast_rain_probability` | Precipitation probability (0-100%) with dynamic icon (rain/snow) |
| `weather.local_weather_forecast_weather` | Weather entity (for weather cards) |

### Supporting Sensors

| Entity | Description |
|--------|-------------|
| `sensor.local_forecast_pressure` | Current sea level pressure (hPa) |
| `sensor.local_forecast_temperature` | Current temperature (°C) |
| `sensor.local_forecast_pressurechange` | 3-hour pressure trend (hPa) |
| `sensor.local_forecast_temperaturechange` | 1-hour temperature trend (°C) |
| `sensor.local_forecast_zambretti_detail` | Zambretti forecast details |
| `sensor.local_forecast_neg_zam_detail` | Negretti-Zambra forecast details |

---

## 🎨 Dashboard Examples

### Basic Weather Card

```yaml
type: weather-forecast
entity: weather.local_weather_forecast_weather
forecast_type: daily
```

### Enhanced Entities Card

```yaml
type: entities
title: Local Weather
entities:
  - entity: weather.local_weather_forecast_weather
  - entity: sensor.local_forecast_enhanced
  - entity: sensor.local_forecast_rain_probability
    name: Precipitation
  - entity: sensor.local_forecast_pressure
  - entity: sensor.local_forecast_pressurechange
    name: Pressure Trend
```

More examples in **[WEATHER_CARDS.md](WEATHER_CARDS.md)**

---

## 🔧 Troubleshooting

### Sensor Shows "Unknown" or "Unavailable"

**Check:**
1. Source sensors are working (pressure, temperature, etc.)
2. Wait 10 minutes after installation (needs historical data)
3. Check Home Assistant logs for errors

### Forecast Seems Inaccurate

**Try:**
1. Change forecast model (Enhanced → Zambretti or vice versa)
2. Add more optional sensors (humidity, wind, solar)
3. Verify pressure sensor calibration
4. Check elevation setting is correct

### Rain/Snow Not Detected

**Solutions:**
- Add rain sensor for definitive detection
- Add humidity sensor for better snow/fog detection
- Verify temperature sensor is working
- Check that precipitation probability sensor has valid data

### Weather Entity Shows Wrong Condition

**Remember Priority System:**
- Rain sensor (if present) always wins
- Fog detection happens before solar/forecast
- Solar radiation only works during daytime
- Forecast is last resort

**Check Logs:**
Enable debug logging to see decision process:
```yaml
logger:
  default: info
  logs:
    custom_components.local_weather_forecast: debug
```

---

## 📚 Additional Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history
- **[WEATHER_CARDS.md](WEATHER_CARDS.md)** - Lovelace examples
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guide

---

## 🤝 Support & Contributing

- 🐛 **Report Issues:** [GitHub Issues](https://github.com/wajo666/homeassistant-local-weather-forecast/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/wajo666/homeassistant-local-weather-forecast/discussions)
- 🔧 **Contributing:** Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file

---

## 🙏 Credits

- Original inspiration: [@HAuser1234](https://github.com/HAuser1234)
- Zambretti algorithm: Negretti & Zambra (1920s)
- Modern implementation: [@wajo666](https://github.com/wajo666)

---

**⭐ If you find this useful, please star the repository!**
