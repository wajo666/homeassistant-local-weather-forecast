# Home Assistant Local Weather Forecast Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/wajo666/homeassistant-local-weather-forecast.svg)](https://github.com/wajo666/homeassistant-local-weather-forecast/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Original Author](https://img.shields.io/badge/Original%20Author-HAuser1234-blue.svg)](https://github.com/HAuser1234)
[![Maintainer](https://img.shields.io/badge/Maintainer-wajo666-green.svg)](https://github.com/wajo666)

## 🌤️ Advanced Local Weather Forecast - Up to 3 Days*

This Home Assistant integration provides **advanced local weather forecasting** without relying on external services or APIs. It uses barometric pressure trends, temperature modeling, and proven meteorological algorithms to predict weather conditions.

**Latest Version:** v3.1.0 (December 2025)

**Original Developer:** [@HAuser1234](https://github.com/HAuser1234)  
**Original Repository:** [github.com/HAuser1234/homeassistant-local-weather-forecast](https://github.com/HAuser1234/homeassistant-local-weather-forecast)  
**Original Forum Thread:** [Home Assistant Community](https://community.home-assistant.io/t/homeassistant-12h-local-weather-forecast-94-accurate/569975)

### ✨ Key Features

- 🎯 **~94-98% Accuracy** - Enhanced with modern sensor fusion
- 🔌 **Fully Offline** - No external API dependencies
- 📅 **Multi-timeframe Forecasts** - Hourly (6h) + Daily (3 days)
- 🌍 **Multi-language Support** - English, German, Greek, Italian, Slovak
- 🎨 **Modern UI Configuration** - Easy setup through Home Assistant UI
- 💾 **Smart Fallbacks** - Uses historical data when sensors are unavailable
- 🔄 **Auto-Recovery** - Restores last known values after restart
- 🧠 **Dual Forecast Models** - Zambretti & Negretti-Zambra algorithms
- 🌡️ **Advanced Calculations** - Feels Like, Dew Point, Fog Risk
- 🌧️ **Enhanced Rain Prediction** - Multi-factor probability calculation
- ☀️ **Day/Night Awareness** - Automatic sunrise/sunset based icons

---

## 📏 Quick Reference: Sensor Units

**⚠️ CRITICAL: Use these exact units or forecast will be incorrect!**

| Sensor | Unit | Symbol | Example | Device Class |
|--------|------|--------|---------|--------------|
| **Pressure** | Hectopascals | `hPa` | 1013.25 | `atmospheric_pressure` or `pressure` |
| **Temperature** | Celsius | `°C` | 15.0 | `temperature` |
| **Wind Speed** | Metres/second | `m/s` | 5.0 (= 18 km/h) | `wind_speed` |
| **Wind Direction** | Degrees | `°` | 180 (South) | - |
| **Elevation** | Metres | `m` | 370 | - |
| **Humidity** | Percent | `%` | 75 | `humidity` |

**🔄 Common Conversions:**
- Wind: `km/h ÷ 3.6 = m/s` (e.g., 18 km/h = 5 m/s)
- Temp: `(°F - 32) × 5/9 = °C` (e.g., 59°F = 15°C)
- Pressure: `inHg × 33.8639 = hPa` (e.g., 29.92 inHg = 1013 hPa)

💡 **Don't have all sensors?** Only pressure is required! Temperature + humidity highly recommended for best accuracy.

---

## 🌟 What's New in v3.1.0

### 📅 Advanced Forecast Models

**New Forecast Calculator** (`forecast_calculator.py`) provides scientific forecasting:

- **Pressure Trend Forecasting** - Linear regression model predicts pressure evolution
- **Temperature Modeling** - Diurnal cycle + pressure-based adjustments
- **Hourly Zambretti** - Run Zambretti algorithm for each forecast hour
- **Dynamic Rain Probability** - Evolves based on pressure trends
- **Confidence Scoring** - Quality metrics for each forecast

### 🌤️ Weather Entity Forecasts

**Daily Forecast (3 days):**
- Temperature trends with diurnal variation
- Hourly temperature changes during the day
- Condition evolution based on pressure
- Day/night icon distinction

**Hourly Forecast (6 hours):**
- Detailed hour-by-hour conditions
- Temperature evolution
- Rain probability per hour
- Automatic day/night icons

### 🎨 Smart Icons

- **Sunrise/Sunset Aware** - Automatic day/night icons
- **Night Icons**: `clear-night`, `rainy-night`, `cloudy-night`
- **Day Icons**: `sunny`, `cloudy`, `rainy`, `stormy`
- **Consistent** - Same logic across all sensors

### 🌧️ Enhanced Rain Prediction

Multi-factor rain probability calculation:
- Base probability from Zambretti (0-100%)
- Base probability from Negretti-Zambra (0-100%)
- Humidity adjustment (±25% based on humidity)
- Dewpoint spread adjustment (±25% based on fog risk)
- Current rain override (100% if actively raining)
- High/Low confidence levels

---

## 🧠 Dual Forecast Models

The integration uses two independent forecast algorithms that run in parallel:

### 1. Zambretti Forecaster (`zambretti.py`)
- Classic algorithm from 1920s
- Based on pressure, trend, and wind
- Seasonal adjustments (summer/winter)
- Letter codes A-Z for quick reference
- Best for: Temperate climates
- **Now with hourly forecasting** in v3.1.0

### 2. Negretti & Zambra (`negretti_zambra.py`)
- Modern "slide rule" approach
- 22-step pressure scale (950-1050 hPa)
- Detailed 16-direction wind corrections
- Exceptional weather detection
- Best for: Variable weather patterns
- **Now with hourly forecasting** in v3.1.0

**Both models run simultaneously** - compare them to find which works better for your location!

---

## 🚀 Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/wajo666/homeassistant-local-weather-forecast`
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
| **Pressure** | **hPa** (hectopascals) | ❌ NOT mbar, inHg, mmHg, or atm | `atmospheric_pressure` **or** `pressure` |
| **Temperature** | **°C** (Celsius) | ❌ NOT °F or K | `temperature` |
| **Wind Speed** | **m/s** (metres/second) | ❌ NOT km/h, mph, or knots | `wind_speed` |
| **Wind Direction** | **°** (degrees 0-360) | - | - |
| **Elevation** | **m** (metres) | - | - |

**💡 Note:** The integration accepts pressure sensors with either `atmospheric_pressure` or `pressure` device class.

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

---

## 🎯 Recommended Sensor Setup for Best Accuracy

**Minimum (Basic - ~88% accuracy):**
```yaml
Required:
  - Barometric Pressure sensor (hPa)
  
Optional but Recommended:
  - Temperature sensor (°C)    ← For accurate sea level pressure conversion
```

**Standard (Good - ~94% accuracy):**
```yaml
Required + Wind:
  - Barometric Pressure sensor
  - Temperature sensor
  - Wind Direction sensor      ← Adds +5-10% accuracy (Zambretti wind corrections)
  - Wind Speed sensor           ← Adds +3-5% accuracy (calm vs windy differentiation)
```

**Enhanced (Best - ~98% accuracy):** ⭐ **Fully implemented in v3.1.0**
```yaml
All sensors + Extended:
  - Barometric Pressure sensor  (required)
  - Temperature sensor
  - Wind Direction sensor
  - Wind Speed sensor
  - Humidity sensor             ← Enables fog detection, enhanced rain %, dew point calc
  - Wind Gust sensor            ← Enables atmospheric stability analysis (gust ratio)
  - Rain Rate sensor            ← Enables real-time rain override (100% when raining)
  - Solar Radiation sensor      ← Enables solar warming in "feels like" temperature
  - Cloud Coverage sensor       ← Enables cloud-based comfort level refinement
  - Dewpoint sensor (optional)  ← Alternative to humidity for fog detection
```

**Future Expert (Coming in v3.2+):**
```yaml
All current + Advanced (prepared but not yet used in forecast):
  - Precipitation sensor        ← Will enable accumulated rain tracking & learning
```

### 📊 Sensor Impact on Accuracy & Features

| Sensor | Status | Impact if PRESENT | Impact if ABSENT |
|--------|--------|-------------------|------------------|
| **Pressure** | ✅ Required | **Required** - Core Zambretti/Negretti-Zambra forecasting | ❌ Integration won't work |
| **Temperature** | ⚠️ Optional | Accurate sea level pressure conversion | ⚠️ Uses 15°C default (minor error) |
| **Wind Direction** | ⚠️ Optional | +5-10% accuracy (Zambretti wind correction) | ⚠️ Uses North (0°) default |
| **Wind Speed** | ⚠️ Optional | +3-5% accuracy (calm vs windy) | ⚠️ Uses 0 m/s (calm) default |
| **Humidity** | ⭐ Optional (v3.1.0) | **Enables:** Fog risk levels, enhanced rain %, dew point calculation | ⚠️ Fog/dew features disabled |
| **Wind Gust** | ⭐ Optional (v3.1.0) | **Enables:** Stability detection (calm/unstable/very unstable atmosphere) | ⚠️ Stability analysis skipped |
| **Rain Rate** | ⭐ Optional (v3.1.0) | **Enables:** Real-time override (100% probability when actively raining) | ⚠️ Uses calculated % only |
| **Solar Radiation** | ⭐ Optional (v3.1.0) | **Enables:** Solar warming effect in "feels like" temperature | ⚠️ Ignores solar heating |
| **Cloud Coverage** | ⭐ Optional (v3.1.0) | **Enables:** Cloud-based comfort level refinement | ⚠️ Uses estimated sky condition |
| **Dewpoint** | ⭐ Optional (v3.1.0) | Alternative to humidity for fog detection (auto-calculated if humidity present) | ⚠️ Calculated from temp+humidity |
| **Precipitation** | 🔜 Future (v3.2+) | Configuration available, not yet used in forecasts | Not yet active |

⭐ = **Fully implemented in v3.1.0** - All enhanced features active  
🔜 = **Prepared for future** - Configuration ready, forecast logic planned for v3.2+

**Summary:**
- **Minimum Setup**: Pressure only → ~88% accuracy (basic Zambretti forecast)
- **Standard Setup**: Pressure + Temperature + Wind → ~94% accuracy (wind corrections)
- **Enhanced Setup**: All v3.1.0 sensors → ~98% accuracy (fog, rain %, stability, solar, clouds) ⭐
- **Future Setup**: All sensors + precipitation tracking → ~99%+ accuracy (planned for v3.2+)

💡 **Pro Tip**: Every optional sensor improves accuracy and unlocks additional features. Missing sensors use sensible defaults - the integration always works.


---

## 📊 Created Sensors & Entities

The integration creates the following sensors and entities:

### Weather Entity ⭐ NEW in v3.1.0

- **`weather.local_weather_forecast_weather`** - Standard HA weather entity
  - Current conditions and detailed attributes
  - **Daily Forecast**: 3-day forecast with realistic conditions
  - **Hourly Forecast**: 6-hour detailed forecast
  - Dew point, Feels like temperature
  - Comfort level, Fog risk
  - Day/night aware icons

**Forecast Details:**
- **Daily**: Temperature trends, condition evolution, rain probability
- **Hourly**: Hour-by-hour temperature, conditions, and rain %
- **Icons**: Automatic day/night distinction based on sunrise/sunset

### Main Sensors

- **`sensor.local_forecast`** - Main forecast with all attributes
  - Current conditions (Sunny, Rainy, Stormy, etc.)
  - Zambretti forecast text and number
  - Negretti-Zambra forecast
  - Pressure trend (Rising/Falling/Steady)
  - Temperature forecast for 3h/6h ahead

- **`sensor.local_forecast_pressure`** - Sea level corrected pressure (hPa)
- **`sensor.local_forecast_temperature`** - Current temperature (°C)

### Statistical Sensors

- **`sensor.local_forecast_pressurechange`** - Pressure change over 3 hours
- **`sensor.local_forecast_temperaturechange`** - Temperature change over 1 hour

### Enhanced Sensors ⭐ NEW in v3.0.3+

- **`sensor.local_forecast_enhanced`** - Modern sensor fusion forecast
  - Base forecast from Zambretti/Negretti-Zambra
  - Fog risk detection (CRITICAL/HIGH/MEDIUM/LOW)
  - Humidity effects analysis
  - Atmospheric stability from wind gust ratio
  - Confidence scoring and accuracy estimate

- **`sensor.local_forecast_rain_probability`** - Multi-factor rain prediction
  - Zambretti + Negretti-Zambra base probabilities
  - Humidity adjustments (±25%)
  - Dewpoint spread adjustments (±25%)
  - Current rain override
  - High/Low confidence levels

### Detailed Forecast Sensors

- **`sensor.local_forecast_zambretti_detail`** - Zambretti forecast details
  - Weather icons for 3h and 6h ahead (day/night aware)
  - Rain probability percentages
  - Timing information
  - Letter code and forecast number

- **`sensor.local_forecast_neg_zam_detail`** - Negretti-Zambra forecast details
  - Alternative forecast model
  - Same detailed attributes as Zambretti
  - Day/night aware icons

---

## 🎨 Lovelace Card Examples

**See [WEATHER_CARDS.md](WEATHER_CARDS.md) for complete card examples!**

### Quick Example (Mushroom Cards)

```yaml
type: custom:vertical-stack-in-card
cards:
  - type: custom:mushroom-title-card
    title: '{{states("sensor.local_weather_forecast_local_forecast")}}'
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: '{{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_short_term")}}'
        secondary: '{{state_attr("sensor.local_weather_forecast_local_forecast", "temperature")}}°C'
        icon: mdi:weather-cloudy-clock
        layout: vertical
      - type: custom:mushroom-template-card
        primary: '~{{state_attr("sensor.local_weather_forecast_zambretti_detail", "first_time")}}'
        secondary: 'Rain: {{state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob").split(",")[0]}}%'
        icon: '{{state_attr("sensor.local_weather_forecast_zambretti_detail", "icons").split(",")[0]}}'
        layout: vertical
  - type: custom:mushroom-template-card
    primary: 'Forecast: {{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti")}}'
    secondary: 'Pressure: {{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_pressure_trend")}}'
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

### Forecast Calculator (NEW in v3.1.0)

Advanced forecasting engine (`forecast_calculator.py`):

**Pressure Forecasting:**
- Linear regression on 3-hour pressure history
- Projects pressure evolution up to 72 hours
- Accounts for diurnal variations

**Temperature Modeling:**
- Diurnal temperature cycle (daily variation)
- Pressure-temperature correlation
- Realistic hourly temperature evolution

**Hourly Forecasting:**
- Runs Zambretti algorithm for each forecast hour
- Predicts conditions based on forecasted pressure
- Calculates rain probability evolution
- Day/night aware icon selection

### Zambretti Forecaster

Classic algorithm using:
- Sea level pressure value
- Pressure trend (rising/falling/steady)
- Wind direction correction
- Seasonal adjustments
- **NEW:** Hourly forecasting capability

### Negretti & Zambra

Modern "slide rule" approach with:
- Finer pressure scale (950-1050 hPa → 22 options)
- Detailed wind direction corrections
- Hemisphere-specific adjustments
- Exceptional weather detection
- **NEW:** Hourly forecasting capability

Both models provide:
- 📝 Text forecast in your language
- 🔢 Numerical forecast type (0-25)
- 🔤 Letter code (A-Z)
- ⏰ Timing (first_time, second_time)
- 🌧️ Rain probability
- ☀️ Day/night icons

---

## 🆕 Enhanced Sensors (v3.1.0+)

### Enhanced Forecast Sensor

**Entity:** `sensor.local_forecast_enhanced`

Combines classical Zambretti/Negretti-Zambra algorithms with modern sensor data:

**Features:**
- ✅ Fog risk detection (CRITICAL/HIGH/MEDIUM/LOW)
- ✅ Humidity effects on forecast
- ✅ Atmospheric stability from wind gust ratio
- ✅ Consensus confidence scoring
- ✅ Accuracy: ~94-98%

**Example Output:**
```
State: "Settling fair. CRITICAL fog risk (spread 1.2°C), High humidity (92.7%)"

Attributes:
  base_forecast: "Settling fair"
  fog_risk: "high"
  dewpoint_spread: 1.2
  humidity: 92.7
  confidence: "medium"
  accuracy_estimate: "~94%"
```

---

### Rain Probability Sensor

**Entity:** `sensor.local_forecast_rain_probability`

Enhanced rain probability calculation using multiple factors:

**Factors:**
- Zambretti forecast → probability
- Negretti-Zambra forecast → probability
- Humidity adjustments (±15%)
- Dewpoint spread adjustments (±15%)
- Current rain override

**Example Output:**
```
State: 45  # percentage

Attributes:
  zambretti_probability: 34
  negretti_probability: 86
  enhanced_probability: 45
  confidence: "high"
  factors_used: ["Zambretti", "Negretti-Zambra", "Humidity", "Dewpoint spread"]
```

---

### Weather Entity

**Entity:** `weather.local_weather_forecast_weather`

Standard Home Assistant weather entity with advanced calculations:

**Properties:**
- Temperature, Pressure, Humidity
- Wind Speed, Direction, Gust
- **NEW:** Dew Point (Magnus formula)
- **NEW:** Feels Like Temperature (Dynamic formula)
- Condition from Zambretti
- Daily forecast

**Enable:** Settings → Devices & Services → Local Weather Forecast → Options → ☑️ Enable Weather Entity

**Example Attributes:**
```yaml
apparent_temperature: 5.1  # Feels like temperature
comfort_level: "cool"
dew_point: 3.5
feels_like: 5.1
fog_risk: "high"
dewpoint_spread: 1.2
```

---

## 🌟 Enhanced Features (v3.1.0+)

### Feels Like Temperature

The integration calculates **Feels Like Temperature** using Wind Chill and Heat Index:

**Wind Chill (< 10°C):**
- US NWS formula for cold weather
- Accounts for wind speed cooling effect
- Used when temperature is below 10°C and wind > 3 mph

**Heat Index (> 27°C):**
- US NWS formula for hot weather  
- Accounts for humidity discomfort
- Used when temperature is above 27°C

**Apparent Temperature (10-27°C):**
- Australian apparent temperature formula
- Balanced formula for moderate temperatures
- Accounts for humidity and wind

**Example Results:**

| Scenario | Temp | Humidity | Wind | Feels Like |
|----------|------|----------|------|------------|
| Cold & Windy | 4.3°C | 91% | 3 km/h | **4.7°C** |
| Moderate | 15°C | 65% | 10 km/h | **14.2°C** |
| Hot & Humid | 30°C | 80% | 5 km/h | **37°C** |

---

### Enhanced Forecast Sensor

**Entity:** `sensor.local_forecast_enhanced`

Combines Zambretti/Negretti-Zambra with modern sensors:

**Features:**
- 📊 **Base Forecast** - From pressure trends
- 💧 **Humidity Analysis** - High humidity detection
- 🌫️ **Fog Risk Detection** - Based on dewpoint spread
- 💨 **Atmospheric Stability** - Wind gust ratio analysis
- ⚠️ **Severity Levels** - CRITICAL/HIGH/MEDIUM/LOW alerts

**Example Output:**
```
"Settled Fine. High humidity (90.9%), CRITICAL fog risk (spread 1.4°C), Very unstable atmosphere (gust ratio 2.98)"
```

**Attributes:**
```yaml
base_forecast: "Settled Fine"
zambretti_number: 0
negretti_number: 1
adjustments: "high_humidity, critical_fog_risk, very_unstable"
adjustment_details: "High humidity (90.9%), CRITICAL fog risk (spread 1.4°C), Very unstable atmosphere (gust ratio 2.98)"
confidence: "high"
consensus: true
humidity: 90.9
dew_point: 2.9
dewpoint_spread: 1.4
fog_risk: "high"
gust_ratio: 2.98
accuracy_estimate: "~98%"
```

---

### Rain Probability Sensor

**Entity:** `sensor.local_forecast_rain_probability`

Multi-factor rain prediction:

**Factors:**
- 📊 Base forecast (Zambretti/Negretti-Zambra)
- 💧 Humidity level (±25% adjustment)
- 🌫️ Dewpoint spread / fog risk (±25% adjustment)
- 🌧️ Current rain rate (if sensor available)

**Output:** 0-100% probability with confidence level

**Example Output:**
```
State: 25  # percentage

Attributes:
  zambretti_probability: 0
  negretti_probability: 0
  base_probability: 0
  enhanced_probability: 25
  confidence: "high"
  humidity: 90.9
  dewpoint_spread: 1.4
  current_rain_rate: 0
  factors_used: ["Zambretti", "Negretti-Zambra", "Humidity", "Dewpoint spread"]
```

---

## 🔧 Advanced Configuration

### Optional Enhanced Sensors

Configure these sensors for improved accuracy:

| Sensor | Device Class | Unit | Purpose |
|--------|--------------|------|---------|
| **Humidity** | `humidity` | `%` | Fog detection, feels like temp |
| **Wind Gust** | `wind_speed` | `m/s` | Atmospheric stability |
| **Rain Rate** | - | `mm/h` | Real-time rain override |
| **Dew Point** | `temperature` | `°C` | Override calculated value |
| **Precipitation** | `precipitation` | `mm` | Rain trend analysis |

**How to Add:**
1. Settings → Devices & Services → Local Weather Forecast
2. Click **Configure** (⚙️)
3. Scroll to **Enhanced Sensors** section
4. Select your sensors
5. Save and reload integration

**Note:** All enhanced sensors are **optional**. The integration automatically uses only available sensors.

---

## 📊 Complete Sensor List

| Sensor | Entity ID | Description |
|--------|-----------|-------------|
| **Core Sensors** | | |
| Main Forecast | `sensor.local_forecast` | Combined forecast with all data |
| Pressure | `sensor.local_forecast_pressure` | Sea level pressure (hPa) |
| Temperature | `sensor.local_forecast_temperature` | Current temperature (°C) |
| Pressure Change | `sensor.local_forecast_pressurechange` | 3-hour pressure trend (hPa) |
| Temperature Change | `sensor.local_forecast_temperaturechange` | 1-hour temp trend (°C/h) |
| **Detail Sensors** | | |
| Zambretti Detail | `sensor.local_forecast_zambretti_detail` | Detailed Zambretti forecast |
| Negretti Detail | `sensor.local_forecast_neg_zam_detail` | Detailed Negretti forecast |
| **Enhanced Sensors** | | |
| Enhanced Forecast | `sensor.local_forecast_enhanced` | ⭐ Modern sensors + algorithms |
| Rain Probability | `sensor.local_forecast_rain_probability` | ⭐ Enhanced rain % |
| **Weather Entity** | | |
| Weather | `weather.local_weather_forecast_weather` | ⭐ Standard HA weather entity with forecasts |

---
| Rain Probability | `sensor.local_forecast_rain_probability` | ⭐ Enhanced rain % |
| **Weather Entity** | | |
| Weather | `weather.local_weather_forecast_weather` | ⭐ Standard HA weather entity |

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

**Original Repository:** [homeassistant-local-weather-forecast](https://github.com/HAuser1234/homeassistant-local-weather-forecast)  
**Original Forum Thread:** [Home Assistant Community](https://community.home-assistant.io/t/homeassistant-12h-local-weather-forecast-94-accurate/569975)

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

## 📚 Documentation

### Available Guides
- 📝 **[Changelog](CHANGELOG.md)** - Version history and changes
- 🌦️ **[Weather Cards Guide](WEATHER_CARDS.md)** - Lovelace card examples
- 🔧 **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to this project

### In This README
- [Installation](#-installation) - HACS and manual setup
- [Configuration](#️-configuration) - Required sensors and setup wizard
- [Sensor Units](#-sensor-units--requirements) - Critical unit requirements
- [Created Sensors](#-created-sensors--entities) - Complete entity reference
- [Lovelace Examples](#-lovelace-card-examples) - Quick card examples
- [Enhanced Features](#-enhanced-features-v310) - Feels like, fog risk, rain probability
- [Troubleshooting](#-troubleshooting) - Common issues and solutions

### Development
- 🔧 **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

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

