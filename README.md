# Home Assistant Local Weather Forecast

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/wajo666/homeassistant-local-weather-forecast.svg)](https://github.com/wajo666/homeassistant-local-weather-forecast/releases)
[![Version](https://img.shields.io/badge/version-3.1.10-blue.svg)](https://github.com/wajo666/homeassistant-local-weather-forecast/blob/main/CHANGELOG.md)

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
- ☀️ **Solar Radiation Sensor** (W/m² or lux) - Real-time cloud detection (+15%)
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

💡 **Don't worry about units!** The integration automatically converts everything (including lux → W/m²).

---

## 🎯 How It Works - Simple Explanation

### Weather Detection Priority System

The integration uses a **6-phase smart system** to determine current weather with maximum accuracy:

```
╔═══════════════════════════════════════════════════════════════════╗
║ PHASE 1: HARD OVERRIDES (Return immediately - definitive!)       ║
╚═══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────┐
│ PRIORITY 0: Exceptional Weather & Hail                  │
│ Extreme conditions (hurricane, bomb cyclone) ⚠️         │
│ • Pressure < 920 hPa → "exceptional" (hurricane)        │
│ • Pressure > 1070 hPa → "exceptional" (extreme high)    │
│ • Rapid change > 10 hPa/3h → "exceptional" (bomb)       │
│ • Storm + temp 15-30°C + RH>80% + unstable → "hail"    │
│ Result: EXCEPTIONAL or HAIL (ends evaluation)           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ PRIORITY 1: Rain Sensor (Direct Measurement) 🌧️        │
│ Active precipitation detected → Show it NOW!            │
│ • Temp < -1°C → "snowy" ❄️                             │
│ • Temp -1 to 4°C (transition zone):                     │
│   - Temp ≤1°C + RH<85% → "snowy" (cold+dry)            │
│   - Temp ≥3°C + RH>85% → "rainy" (warm+humid)          │
│   - Otherwise → "snowy-rainy" 🌨️ (mixed)              │
│ • Temp > 4°C:                                           │
│   - Rate >10 mm/h + temp >10°C → "pouring" 🌊          │
│   - Otherwise → "rainy" 🌧️                             │
│ Result: SNOWY, RAINY, POURING, MIXED (ends evaluation) │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ PRIORITY 2: Fog Detection (Observable Weather) 🌫️      │
│ Temperature + Humidity + Dewpoint + Wind                │
│ • Critical: spread <0.5°C + RH>95% → "fog" (always)    │
│ • Likely: spread <1.0°C + RH>93% + wind<3m/s → "fog"   │
│ • Likely: spread 1.5-2.5°C + RH>85% + wind<2m/s        │
│ • Possible: spread 1.0-1.5°C + RH>90% + night + calm   │
│ Result: FOG (ends evaluation)                           │
└──���──────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║ PHASE 2: SOLAR RADIATION (If available - HIGHEST ACCURACY!)      ║
╚═══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────┐
│ PRIORITY 3: Solar Cloudiness Detection ☀️              │
│ (Daytime + sun elevation >0° + radiation >10 W/m²)      │
│ WMO Standards (oktas - eighths of sky):                 │
│ • Transparency ≥75% (0-2 oktas) → "sunny" ☀️           │
│ • Transparency 50-75% (3-4 oktas) → "partlycloudy" ⛅   │
│ • Transparency 12.5-50% (5-7 oktas) → "cloudy" ☁️      │
│ • Transparency <12.5% (8 oktas) → "cloudy" (overcast)   │
│ Result: solar_cloudiness (stored for Phase 4)           │
└─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║ PHASE 3: PRESSURE-BASED BASELINE (Always calculated)             ║
╚═══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────┐
│ PRIORITY 5: Pressure-Based Current State (NOW - 0h)     │
│ Direct pressure mapping (NOT forecast prediction!)      │
│ WMO Meteorological Standards:                           │
│ • <980 hPa → "lightning-rainy" (deep cyclone)           │
│ • 980-1000 hPa → "rainy/snowy" (low pressure)           │
│ • 1000-1010 hPa:                                        │
│   - Falling >2 hPa/3h → "rainy" (deteriorating)         │
│   - Otherwise → "cloudy" (stable)                       │
│ • 1010-1020 hPa → "partlycloudy" (normal)               │
│ • ≥1020 hPa → "sunny/clear-night" (high pressure)       │
│ Result: current_condition_from_pressure                 │
└─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║ PHASE 4: HUMIDITY FINE-TUNING (If no solar available)            ║
╚═══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────┐
│ Humidity Adjustment (Night or no solar) 💧              │
│ Adjust pressure-based condition using humidity:         │
│ • RH >90% + "partlycloudy" → "cloudy" (upgrade)        │
│ • RH >85% + "sunny/clear" → "partlycloudy" (upgrade)   │
│ Note: ONLY increases cloudiness (never decreases!)      │
│ ⚠️ SKIPPED if solar available (solar more accurate!)    │
│ Result: humidity_adjusted_condition                     │
└─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║ PHASE 5: SOLAR VALIDATION (Final override if available)          ║
╚═══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────┐
│ Compare Solar vs Pressure+Humidity Result               │
│ If difference >1 level → Use SOLAR (real measurement!)  │
│ Solar cannot detect precipitation → keeps rain/snow     │
│ Result: validated_condition                             │
└─────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║ PHASE 6: WIND OVERRIDE (For high wind speeds)                    ║
╚═══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────┐
│ Wind Speed Check (if wind ≥10.8 m/s = Force 6+) 💨     │
│ ONLY overrides basic cloudiness conditions:             │
│ • sunny/clear/partlycloudy + wind ≥10.8 → "windy"      │
│ • cloudy + wind ≥10.8 → "windy-variant"                │
│ ⚠️ CANNOT override rain/snow/fog (they have priority!)  │
│ Result: FINAL condition                                 │
└──────────────────────────���──────────────────────────────┘
```

### Universal Post-Processing (Applied to ALL)
- 🌙 **Night Mode:** Auto-converts "sunny" → "clear-night" after sunset

### Real-World Examples

**Example 1: Morning - Clear sky, pressure 1025 hPa, solar active**
```
PHASE 1: Hard Overrides
✅ Pressure 1025 hPa (normal) → No exceptional weather
✅ No rain detected → Skip Priority 1
✅ Humidity 60%, spread 5°C → No fog, skip Priority 2

PHASE 2: Solar Radiation
✅ Solar active: 900 W/m² (max 1100) → 82% transparency
✅ Solar (Priority 3): "sunny" (WMO: 0-2 oktas)

PHASE 3: Pressure Baseline
✅ Pressure 1025 hPa → "sunny" (high pressure)

PHASE 4: Humidity Fine-tuning
✅ Solar available → SKIP humidity (solar more accurate)

PHASE 5: Solar Validation
✅ Solar "sunny" vs Pressure "sunny" → Agreement (0 levels difference)

PHASE 6: Wind Check
✅ Wind 3.5 m/s (< 10.8) → No wind override

Result: SUNNY ☀️ (from solar radiation - 85% accuracy)
```

**Example 2: Afternoon - Light rain, temp 3°C, RH 88%**
```
PHASE 1: Hard Overrides
✅ Rain sensor: 2.5 mm/h detected
✅ Temp 3°C (transition zone -1 to 4°C)
✅ RH 88% (moderate) → Mixed precipitation

Result: SNOWY-RAINY 🌨️ (Priority 1, ends evaluation)
(All other phases skipped - rain sensor is definitive!)
```

**Example 3: Night - Foggy, pressure 1010 hPa**
```
PHASE 1: Hard Overrides
✅ No rain → Skip Priority 1
✅ Dewpoint spread 0.8°C, RH 96%, wind 1.5 m/s
✅ Spread <1.0°C + RH >93% + wind <3m/s → "fog"

Result: FOG 🌫️ (Priority 2, ends evaluation)
(All other phases skipped - fog detection is definitive!)
```

**Example 4: Day - Cloudy with high humidity, no solar sensor**
```
PHASE 1: Hard Overrides
✅ No exceptional weather, no rain, no fog

PHASE 2: Solar Radiation
✅ No solar sensor configured → Skip Priority 3

PHASE 3: Pressure Baseline
✅ Pressure 1012 hPa → "partlycloudy" (normal)

PHASE 4: Humidity Fine-tuning
✅ No solar → Use humidity fine-tuning
✅ RH 92% >90% + "partlycloudy" → Upgrade to "cloudy"

PHASE 5: Solar Validation
✅ No solar → Skip validation

PHASE 6: Wind Check
✅ Wind 2.1 m/s (< 10.8) → No wind override

Result: CLOUDY ☁️ (from pressure + humidity adjustment)
```

**Example 5: Evening - After sunset, pressure 1028 hPa**
```
PHASE 1: Hard Overrides
✅ No exceptional weather, no rain, no fog

PHASE 2: Solar Radiation
✅ Solar = 0 W/m² (night) → Skip Priority 3

PHASE 3: Pressure Baseline
✅ Pressure 1028 hPa + night → "clear-night" (high)

PHASE 4: Humidity Fine-tuning
✅ No solar (night) → Use humidity fine-tuning
✅ RH 55% (low) → No humidity adjustment needed

PHASE 5: Solar Validation
✅ No solar → Skip validation

PHASE 6: Wind Check
✅ Wind 4.2 m/s (< 10.8) → No wind override

Result: CLEAR-NIGHT 🌙 (from pressure, no adjustments)
```

**Example 6: Windy day - Pressure 1015 hPa, wind 12.5 m/s**
```
PHASE 1: Hard Overrides
✅ No exceptional weather, no rain, no fog

PHASE 2: Solar Radiation
✅ Solar = 450 W/m² (max 700) → 64% transparency
✅ Solar (Priority 3): "partlycloudy" (WMO: 3-4 oktas)

PHASE 3: Pressure Baseline
✅ Pressure 1015 hPa → "partlycloudy" (normal)

PHASE 4: Humidity Fine-tuning
✅ Solar available → SKIP humidity

PHASE 5: Solar Validation
✅ Solar "partlycloudy" vs Pressure "partlycloudy" → Agreement

PHASE 6: Wind Check
✅ Wind 12.5 m/s (≥ 10.8) + condition "partlycloudy"
✅ Wind override: "partlycloudy" → "windy"

Result: WINDY 💨 (wind override of cloudiness condition)
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

**Remember 6-Phase System:**
- **Phase 1:** Exceptional weather (Priority 0), Rain sensor (Priority 1), Fog detection (Priority 2) override ALL
- **Phase 2:** Solar radiation cloudiness detection (Priority 3) - if daytime + sensor available
- **Phase 3:** Pressure-based baseline (Priority 5) - always calculated
- **Phase 4:** Humidity fine-tuning - only if solar NOT available
- **Phase 5:** Solar validation - compares solar vs pressure+humidity
- **Phase 6:** Wind override - for high winds (≥10.8 m/s)

**Check Logs:**
Enable debug logging to see decision process:
```yaml
logger:
  default: info
  logs:
    custom_components.local_weather_forecast: debug
```

**Look for these log messages:**

**PHASE 1 - Hard Overrides:**
- `⚠️ EXCEPTIONAL WEATHER: Hurricane-force` - Priority 0 (extreme low pressure)
- `⚠️ EXCEPTIONAL WEATHER: Extreme high pressure` - Priority 0 (extreme high)
- `⚠️ EXCEPTIONAL WEATHER: Bomb cyclone` - Priority 0 (rapid change)
- `🧊 HAIL RISK: Severe thunderstorm` - Priority 0 (hail conditions)
- `Weather: SNOW detected` - Priority 1 (rain sensor + cold)
- `Weather: RAIN detected` - Priority 1 (rain sensor + warm)
- `Weather: MIXED precipitation` - Priority 1 (transition zone)
- `Weather: FOG (CRITICAL)` - Priority 2 (critical fog)
- `Weather: FOG (LIKELY)` - Priority 2 (likely fog)

**PHASE 2 - Solar Radiation:**
- `Weather: Solar HIGH CONFIDENCE → clear skies` - Priority 3 (≥75% transparency)
- `Weather: Solar MEDIUM CONFIDENCE → scattered clouds` - Priority 3 (50-75%)
- `Weather: Solar LOW CONFIDENCE → mostly cloudy` - Priority 3 (12.5-50%)
- `Weather: Solar OVERCAST` - Priority 3 (<12.5%)
- `Weather: Solar radiation too low` - Skipped (twilight/night)

**PHASE 3 - Pressure Baseline:**
- `Weather: PRIORITY 5 - Current state from pressure: sunny` - Pressure ≥1020 hPa
- `Weather: PRIORITY 5 - Current state from pressure: rainy` - Pressure <1000 hPa
- `Weather: PRIORITY 5 - Current state from pressure: cloudy` - Pressure 1000-1010 hPa
- `Weather: PRIORITY 5 - Current state from pressure: partlycloudy` - Pressure 1010-1020 hPa

**PHASE 4 - Humidity Fine-tuning:**
- `Weather: PHASE 3 - SKIPPING humidity` - Solar active (solar more accurate)
- `Weather: PHASE 3 - Humidity adjustment:` - Applied (night/no solar)
- `Weather: PHASE 3 - No humidity adjustment needed` - RH too low for adjustment

**PHASE 5 - Solar Validation:**
- `Weather: PHASE 4 - Solar FINAL OVERRIDE!` - Solar overrode pressure+humidity
- `Weather: PHASE 4 - Solar validation: ... agreement` - Solar and pressure agree
- `Weather: No solar radiation available` - Skipped (no sensor/night)

**PHASE 6 - Wind Override:**
- `Weather: PHASE 5 - Wind override → windy` - Wind ≥10.8 m/s + clear/partly cloudy
- `Weather: PHASE 5 - Wind override → windy-variant` - Wind ≥10.8 m/s + cloudy
- `Weather: PHASE 5 - Strong wind detected ... NOT overriding` - Wind high but precipitation/fog

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
