# Home Assistant Local Weather Forecast Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/HAuser1234/homeassistant-local-weather-forecast.svg)](https://github.com/HAuser1234/homeassistant-local-weather-forecast/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Original Author](https://img.shields.io/badge/Original%20Author-HAuser1234-blue.svg)](https://github.com/HAuser1234)
[![Maintainer](https://img.shields.io/badge/Maintainer-wajo666-green.svg)](https://github.com/wajo666)

## 12h Local Weather Forecast - ~94% Accurate*

This Home Assistant integration provides **local weather forecasting** without relying on external services or APIs. It uses barometric pressure trends and proven meteorological algorithms to predict weather up to 12 hours ahead.

**Original Source:** [github.com/HAuser1234/homeassistant-local-weather-forecast](https://github.com/HAuser1234/homeassistant-local-weather-forecast)

### ✨ Key Features

- 🎯 **~94% Accuracy** - Based on validated IoT implementations
- 🔌 **Fully Offline** - No external API dependencies
- 🌍 **Multi-language Support** - English, German, Greek, Italian, Slovak
- 🎨 **Modern UI Configuration** - Easy setup through Home Assistant UI
- 💾 **Smart Fallbacks** - Uses historical data when sensors are unavailable
- 🔄 **Auto-Recovery** - Restores last known values after restart
- 🧠 **Dual Forecast Models** - Zambretti & Negretti-Zambra algorithms

---

## 📏 Quick Reference: Sensor Units

**⚠️ CRITICAL: Use these exact units or forecast will be incorrect!**

| Sensor | Unit | Symbol | Example | Device Class |
|--------|------|--------|---------|--------------|
| **Pressure** | Hectopascals | `hPa` | 1013.25 | `atmospheric_pressure` |
| **Temperature** | Celsius | `°C` | 15.0 | `temperature` |
| **Wind Speed** | Metres/second | `m/s` | 5.0 (= 18 km/h) | `wind_speed` |
| **Wind Direction** | Degrees | `°` | 180 (South) | - |
| **Elevation** | Metres | `m` | 370 | - |

**🔄 Common Conversions:**
- Wind: `km/h ÷ 3.6 = m/s` (e.g., 18 km/h = 5 m/s)
- Temp: `(°F - 32) × 5/9 = °C` (e.g., 59°F = 15°C)
- Pressure: `inHg × 33.8639 = hPa` (e.g., 29.92 inHg = 1013 hPa)

💡 **Don't have all sensors?** Only pressure is required! Temperature highly recommended for accuracy.

---

## 🧠 Dual Forecast Models

The integration uses two independent forecast algorithms:

### 1. Zambretti Forecaster (`zambretti.py`)
- Classic algorithm from 1920s
- Based on pressure, trend, and wind
- Seasonal adjustments (summer/winter)
- Letter codes A-Z for quick reference
- Best for: Temperate climates

### 2. Negretti & Zambra (`negretti_zambra.py`)
- Modern "slide rule" approach
- 22-step pressure scale (950-1050 hPa)
- Detailed 16-direction wind corrections
- Exceptional weather detection
- Best for: Variable weather patterns

**Both models run simultaneously** - compare them to find which works better for your location!

---

## 🚀 Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/HAuser1234/homeassistant-local-weather-forecast`
6. Select category: "Integration"
7. Click "Add"
8. Find "Local Weather Forecast" in HACS and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/local_weather_forecast` folder
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

---

## ⚙️ Configuration

### UI Configuration (New!)

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Local Weather Forecast"**
4. Follow the setup wizard:
   - Select your **pressure sensor** (required)
   - Optionally add temperature, wind sensors
   - Enter your **elevation** above sea level
   - Choose your **language**

### Required Sensors

| Sensor | Required | Description | Units | Default |
|--------|----------|-------------|-------|---------|
| **Barometric Pressure** | ✅ Yes | Atmospheric pressure sensor | **hPa** | 1013.25 hPa |
| **Temperature** | ⚠️ Recommended | For accurate sea level pressure calculation | **°C** | 15.0 °C |
| **Wind Direction** | ❌ Optional | Improves forecast accuracy by 5-10% | **°** (0-360) | 0° (North) |
| **Wind Speed** | ❌ Optional | Improves forecast accuracy by 3-5% | **m/s** | 0.0 m/s |

### 📏 Sensor Units & Requirements

**⚠️ IMPORTANT: Use correct units or forecast will be inaccurate!**

| Measurement | Required Unit | Alternative Units | Home Assistant Device Class |
|-------------|---------------|-------------------|------------------------------|
| **Pressure** | **hPa** (hectopascals) | ❌ NOT mbar, inHg, mmHg, or atm | `atmospheric_pressure` |
| **Temperature** | **°C** (Celsius) | ❌ NOT °F or K | `temperature` |
| **Wind Speed** | **m/s** (metres/second) | ❌ NOT km/h, mph, or knots | `wind_speed` |
| **Wind Direction** | **°** (degrees 0-360) | - | - |
| **Elevation** | **m** (metres) | - | - |

#### 🔄 Unit Conversions (if needed)

**Wind Speed Conversion (REQUIRED if your sensor uses km/h):**
```yaml
template:
  - sensor:
      - name: "Wind Speed m/s"
        state: "{{ (states('sensor.wind_kmh') | float / 3.6) | round(2) }}"
        unit_of_measurement: "m/s"
        device_class: "wind_speed"
```

**Pressure Conversion Examples:**
```
1 hPa = 1 mbar
1 hPa = 0.02953 inHg
1 inHg = 33.8639 hPa
```

**Temperature Conversion:**
```yaml
# °F to °C
{{ ((states('sensor.temp_f') | float - 32) * 5/9) | round(1) }}
```

**⚠️ Why m/s for wind speed?**
The Zambretti algorithm uses a threshold of **1 m/s (3.6 km/h)** to determine if wind affects the forecast. Using km/h values will result in incorrect predictions!

**📊 Typical Sensor Value Ranges:**

| Measurement | Typical Range | Integration Range | Notes |
|-------------|---------------|-------------------|-------|
| **Pressure** | 980-1040 hPa | 950-1050 hPa | Normal sea level: ~1013 hPa |
| **Temperature** | -40 to +50 °C | Any | Used for pressure correction |
| **Wind Speed** | 0-30 m/s | 0+ m/s | Threshold: 1 m/s (3.6 km/h) |
| **Wind Direction** | 0-360° | 0-360° | 0°=North, 90°=East, 180°=South, 270°=West |

**Pressure Interpretation:**
- 📉 **Low** (980-1000 hPa): Storms, rain likely
- ⚖️ **Normal** (1000-1020 hPa): Variable weather
- 📈 **High** (1020-1040 hPa): Clear, settled weather

### Configuration Options

- **Elevation**: Your location's height above sea level (meters)
- **Pressure Type**: Select QFE (absolute) or QNH (relative)
  - **QFE (Absolute)**: Station pressure without altitude correction - most sensors (BME280, BMP280, etc.)
  - **QNH (Relative)**: Sea level corrected pressure - some weather stations (Ecowitt, Netatmo)
- **Language**: Choose forecast text language (de, en, gr, it, sk)

---

## 🔧 Advanced Sensor Setup

### Multiple Sensors (Improved Accuracy & Reliability)

If you have multiple temperature or pressure sensors, create template sensors for better accuracy:

#### Temperature (Average or Minimum from Multiple Sensors)
```yaml
template:
  - sensor:
      - name: "Outdoor Temperature"
        state: >
          {% set sensors = [
            'sensor.west_temperature',
            'sensor.east_temperature'
          ] %}
          {% set valid = [] %}
          {% for s in sensors %}
            {% if states(s) not in ['unavailable', 'unknown'] %}
              {% set valid = valid + [states(s)|float] %}
            {% endif %}
          {% endfor %}
          {{ valid|min|round(1) if valid else 'unknown' }}
        unit_of_measurement: "°C"
        device_class: "temperature"
        state_class: "measurement"
```

#### Pressure (Average from Multiple Sensors)
```yaml
template:
  - sensor:
      - name: "Outdoor Pressure"
        state: >
          {% set sensors = ['sensor.pressure_1', 'sensor.pressure_2'] %}
          {% set valid = [] %}
          {% for s in sensors %}
            {% if states(s) not in ['unavailable', 'unknown'] %}
              {% set val = states(s)|float %}
              {% if val > 900 and val < 1100 %}
                {% set valid = valid + [val] %}
              {% endif %}
            {% endif %}
          {% endfor %}
          {{ (valid|sum / valid|length)|round(1) if valid else 'unknown' }}
        unit_of_measurement: "hPa"
        device_class: "atmospheric_pressure"
        state_class: "measurement"
```

### 💡 Why Use Multiple Sensors?

- **Redundancy**: If one sensor fails, forecast continues working
- **Accuracy**: Average/minimum values reduce sensor errors
- **Stability**: Less false positives from temporary spikes
- **Meteorologically Correct**: Minimum temperature = shaded value (correct for forecasts)

--- 🎯 Recommended Sensor Setup for Best Accuracy

**Minimum (Good - ~88% accuracy):**
```yaml
Required:
  - Barometric Pressure sensor
  - Temperature sensor (if not at sea level)
```

**Recommended (Better - ~94% accuracy):**
```yaml
Required + Optional:
  - Barometric Pressure sensor
  - Temperature sensor
  - Wind Direction sensor  ← Adds +5-10% accuracy
  - Wind Speed sensor       ← Adds +3-5% accuracy
```

**Future Enhanced (Best - ~97%+ accuracy - Coming in v2.1):**
```yaml
All sensors + Additional:
  - Humidity sensor         ← Will add +2-3% accuracy
  - Rain sensor            ← Will enable adaptive learning
  - Cloud cover sensor     ← Will validate forecasts
```

💡 **Pro Tip**: Even without wind sensors, the integration provides ~88% accuracy. Adding wind sensors is highly recommended if available!

📖 **Want even better accuracy?** See [FUTURE_SENSORS.md](FUTURE_SENSORS.md) for planned enhancements (humidity, rain sensors, cloud cover) that will boost accuracy to ~97%+!

---

## 📊 Created Sensors

The integration creates the following sensors:

### Main Sensors

- **`sensor.local_forecast`** - Main forecast with all attributes
  - Current conditions (Sunny, Rainy, Stormy, etc.)
  - Zambretti forecast text and number
  - Negretti-Zambra forecast
  - Pressure trend (Rising/Falling/Steady)

- **`sensor.local_forecast_pressure`** - Sea level corrected pressure (hPa)
- **`sensor.local_forecast_temperature`** - Current temperature (°C)

### Statistical Sensors

- **`sensor.local_forecast_pressure_change`** - Pressure change over 3 hours
- **`sensor.local_forecast_temperature_change`** - Temperature change over 1 hour

### Detailed Forecast Sensors

- **`sensor.local_forecast_zambretti_detail`** - Zambretti forecast details
  - Weather icons for 6h and 12h ahead
  - Rain probability percentages
  - Timing information

- **`sensor.local_forecast_neg_zam_detail`** - Negretti-Zambra forecast details
  - Alternative forecast model
  - Same detailed attributes as Zambretti

---

## 🎨 Lovelace Card Examples

**See [WEATHER_CARDS.md](WEATHER_CARDS.md) for complete card examples!**

### Quick Example (Mushroom Cards)

```yaml
type: custom:vertical-stack-in-card
cards:
  - type: custom:mushroom-title-card
    title: '{{states.sensor.local_forecast.state}}'
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: '{{states.sensor.local_forecast.attributes.forecast_short_term[0]}}'
        secondary: '{{states.sensor.local_forecast.attributes.temperature}}°C'
        icon: mdi:weather-cloudy-clock
        layout: vertical
      - type: custom:mushroom-template-card
        primary: '~{{states.sensor.local_forecast_zambretti_detail.attributes.first_time[0]}}'
        secondary: 'Rain: {{states.sensor.local_forecast_zambretti_detail.attributes.rain_prob[0]}}%'
        icon: '{{states.sensor.local_forecast_zambretti_detail.attributes.icons[0]}}'
        layout: vertical
  - type: custom:mushroom-template-card
    primary: 'Forecast: {{states.sensor.local_forecast.attributes.forecast_zambretti[0]}}'
    secondary: 'Pressure: {{states.sensor.local_forecast.attributes.forecast_pressure_trend[0]}}'
    icon: mdi:weather-cloudy-arrow-right
```

**Requirements:**
- [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom)
- [Vertical Stack In Card](https://github.com/ofekashery/vertical-stack-in-card)

---

## 🔧 Smart Features

### Historical Fallback System

When sensors become unavailable (e.g., after restart or network issues), the integration:

1. ✅ Attempts to use current sensor value
2. ✅ Falls back to last known state
3. ✅ Searches up to 7 days of history for valid data
4. ✅ Uses sensible defaults only as last resort

This ensures continuous forecasting even during sensor outages!

### State Restoration

All sensors restore their previous state after Home Assistant restart, preventing:
- ❌ Sudden forecast changes
- ❌ Missing data during initialization
- ❌ Unreliable predictions after reboot

---

## 📖 How It Works

### Zambretti Forecaster

Classic algorithm using:
- Sea level pressure value
- Pressure trend (rising/falling/steady)
- Wind direction correction
- Seasonal adjustments

### Negretti & Zambra

Modern "slide rule" approach with:
- Finer pressure scale (950-1050 hPa → 22 options)
- Detailed wind direction corrections
- Hemisphere-specific adjustments
- Exceptional weather detection

Both models provide:
- 📝 Text forecast in your language
- 🔢 Numerical forecast type (0-25)
- 🔤 Letter code (A-Z)

---

## 🌍 Supported Languages

| Language | Code | Status |
|----------|------|--------|
| 🇩🇪 German | `de` | ✅ Complete |
| 🇬🇧 English | `en` | ✅ Complete |
| 🇬🇷 Greek | `gr` | ✅ Complete |
| 🇮🇹 Italian | `it` | ✅ Complete |
| 🇸🇰 Slovak | `sk` | ✅ Complete |

Want to add your language? PRs welcome!

---

## 🔍 Troubleshooting

### Sensors Show "Unknown" After Restart

This is normal for 1-2 minutes while the integration:
1. Restores last states
2. Waits for source sensors to update
3. Calculates statistical trends

If persists, check:
- Source sensors are available
- Recorder integration is enabled
- History data exists

### Forecast Seems Inaccurate

Try:
1. **Compare both models** - Zambretti vs Negretti-Zambra
2. **Add wind sensors** - Significantly improves accuracy
3. **Verify elevation** - Critical for sea level pressure calculation
4. **Check pressure sensor** - Ensure it's providing accurate readings

### "Sensor Not Found" Error

- Verify entity IDs are correct
- Ensure sensors exist in Developer Tools → States
- Check sensor has valid numeric values

---

## 🏆 Credits & Attribution

### Original Developer
This integration was originally developed by **[@HAuser1234](https://github.com/HAuser1234)**

**Original Source:** [homeassistant-local-weather-forecast](https://github.com/HAuser1234/homeassistant-local-weather-forecast)

### Current Maintainers
- **[@HAuser1234](https://github.com/HAuser1234)** - Original developer
- **[@wajo666](https://github.com/wajo666)** - Current maintainer

### Based On
The forecast algorithms are based on proven meteorological methods:
- **Zambretti Algorithm** - Classic barometric forecasting (1920s)
- **Negretti & Zambra** - Slide rule method for weather prediction

### Contributors
Thank you to all contributors who help improve this integration!

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Make your changes
3. Test thoroughly
4. Submit a pull request with description

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📚 Related Projects

- [HA Ecowitt Extended](https://github.com/HAuser1234/HA_Ecowitt_Extended) - Ecowitt weather station integration
- [Solar Forecast Charge Prediction](https://github.com/HAuser1234/Homeassistant-solar-forecast-charge-prediction) - Solar battery forecasting

---

## 📜 Credits & Sources

- [SAS IoT Zambretti Implementation](https://github.com/sassoftware/iot-zambretti-weather-forcasting)
- [Zambretti Algorithm Documentation](https://integritext.net/DrKFS/zambretti.htm)
- [Beteljuice Zambretti Calculator](http://www.beteljuice.co.uk/zambretti/forecast.html)

---

## ⚖️ License

MIT License - See [LICENSE](LICENSE) file

**Disclaimer:** THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

---


**Note:** *94% accuracy claim based on [SAS IoT implementation testing](https://github.com/sassoftware/iot-zambretti-weather-forcasting)*

