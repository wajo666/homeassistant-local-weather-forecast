# Additional Sensors Reference

This document lists potential sensors that can improve forecast accuracy when added to the Local Weather Forecast integration.

---

## 🎯 Priority Sensors (High Impact)

### 1. Humidity Sensor ⭐⭐⭐⭐⭐
**Entity ID:** `sensor.outdoor_humidity`  
**Type:** Relative Humidity  
**Unit:** %  
**Range:** 0-100  

**Impact on Forecast:**
- ✅ Enables dew point calculation
- ✅ Improves rain probability (±15%)
- ✅ Enables fog risk assessment
- ✅ Improves comfort index
- ✅ Enables visibility estimation

**Recommended Hardware:**
- DHT22/AM2302 (±2% accuracy)
- BME280 (±3% accuracy)
- SHT31 (±2% accuracy)
- Any weather station with humidity

---

### 2. Cloud Coverage Sensor ⭐⭐⭐⭐
**Entity ID:** `sensor.cloud_coverage`  
**Type:** Cloud Coverage  
**Unit:** %  
**Range:** 0-100  

**Impact on Forecast:**
- ✅ Improves rain probability (±10%)
- ✅ Better current condition detection
- ✅ Improves short-term forecast (1-3h)
- ✅ Helps determine "sunny" vs "cloudy"

**Sources:**
- Weather API integrations (Met.no, OpenWeatherMap)
- Sky camera + image analysis
- Manual observation

---

### 3. Dew Point Sensor ⭐⭐⭐
**Entity ID:** `sensor.outdoor_dewpoint`  
**Type:** Temperature  
**Unit:** °C  
**Range:** -40 to +40  

**Impact on Forecast:**
- ✅ Direct fog risk calculation (no need for humidity)
- ✅ Saturation detection
- ✅ Better comfort index

**Note:** Can be calculated from Temperature + Humidity if not available

**Recommended Hardware:**
- Ecowitt weather stations
- Ambient Weather stations
- Davis Vantage Pro2

---

## 📊 Medium Priority Sensors

### 4. Wind Gust Sensor ⭐⭐⭐
**Entity ID:** `sensor.wind_gust`  
**Type:** Wind Speed (peak)  
**Unit:** km/h  
**Range:** 0-200+  

**Impact on Forecast:**
- ✅ Storm/severe weather detection
- ✅ Better wind chill calculation
- ✅ Indicates atmospheric instability
- ✅ Helps predict weather changes

**Recommended Hardware:**
- Anemometer with gust measurement
- Most weather stations include this

---

### 5. Rain Rate Sensor ⭐⭐⭐
**Entity ID:** `sensor.rain_rate`  
**Type:** Precipitation Rate  
**Unit:** mm/h  
**Range:** 0-100+  

**Impact on Forecast:**
- ✅ Current precipitation detection
- ✅ Storm intensity
- ✅ Short-term forecast validation
- ✅ Helps distinguish drizzle/rain/downpour

**Recommended Hardware:**
- Tipping bucket rain gauge
- Optical rain sensor
- Weather stations with rain sensor

---

### 6. UV Index Sensor ⭐⭐
**Entity ID:** `sensor.uv_index`  
**Type:** UV Index  
**Unit:** index  
**Range:** 0-11+  

**Impact on Forecast:**
- ➕ Supplementary information
- ➕ Cloud coverage indication (indirect)
- ➕ Solar radiation correlation
- ➕ User info (not used in calculations)

**Recommended Hardware:**
- UV sensor (VEML6070, ML8511)
- Weather stations with UV
- Weather API

---

### 7. Visibility Sensor ⭐⭐
**Entity ID:** `sensor.visibility`  
**Type:** Distance  
**Unit:** km  
**Range:** 0-50+  

**Impact on Forecast:**
- ➕ Fog detection
- ➕ Precipitation detection
- ➕ Air quality indication
- ➕ Confirms calculated visibility

**Sources:**
- Weather API
- Optical sensors
- Manual observation

---

## 🔬 Advanced Sensors (Low Priority)

### 8. Precipitation 24h Total ⭐
**Entity ID:** `sensor.precipitation_24h`  
**Type:** Accumulated Precipitation  
**Unit:** mm  
**Range:** 0-500+  

**Impact on Forecast:**
- ➕ Historical context
- ➕ Helps track wet/dry periods
- ➕ Soil saturation indicator

---

### 9. Solar Radiation
**Entity ID:** `sensor.solar_radiation`  
**Type:** Irradiance  
**Unit:** W/m²  
**Range:** 0-1400  

**Impact on Forecast:**
- ➕ Cloud coverage indication
- ➕ Weather type confirmation
- ➕ Evaporation rate

---

### 10. Soil Temperature
**Entity ID:** `sensor.soil_temperature`  
**Type:** Temperature  
**Unit:** °C  
**Range:** -20 to +50  

**Impact on Forecast:**
- ➕ Frost prediction
- ➕ Seasonal trends

---

## 📋 Summary Table

| Sensor | Priority | Improves | Impact | Easy to Get |
|--------|----------|----------|--------|-------------|
| Humidity | ⭐⭐⭐⭐⭐ | Rain prob, Fog, Comfort | High | ✅ Yes |
| Cloud Coverage | ⭐⭐⭐⭐ | Rain prob, Condition | High | ⚠️ API |
| Dew Point | ⭐⭐⭐ | Fog risk | Medium | ⚠️ Calculate |
| Wind Gust | ⭐⭐⭐ | Severe weather | Medium | ✅ Yes |
| Rain Rate | ⭐⭐⭐ | Current precip | Medium | ✅ Yes |
| UV Index | ⭐⭐ | Info only | Low | ✅ Yes |
| Visibility | ⭐⭐ | Fog confirm | Low | ⚠️ API |
| Precipitation 24h | ⭐ | Context | Low | ✅ Yes |
| Solar Radiation | ⭐ | Clouds indirect | Low | ⚠️ Hardware |
| Soil Temp | ⭐ | Frost | Very Low | ⚠️ Hardware |

---

## 🛒 Recommended Hardware Packages

### Budget Option (~€30-50)
**BME280 + Wind Sensor**
- Temperature ✅
- Pressure ✅
- Humidity ✅
- Wind (optional add-on)

**Pros:** Cheap, I2C/ESPHome compatible  
**Cons:** Limited features

---

### Mid-Range Option (~€100-200)
**Ecowitt GW1000 + Sensors**
- Temperature ✅
- Pressure ✅
- Humidity ✅
- Wind Speed/Direction ✅
- Wind Gust ✅
- Rain Rate ✅
- Precipitation ✅
- UV ✅

**Pros:** Complete package, WiFi, good integration  
**Cons:** Proprietary

---

### Professional Option (~€500+)
**Davis Vantage Pro2**
- All above sensors ✅
- Solar Radiation ✅
- High accuracy
- Proven reliability

**Pros:** Best accuracy, professional grade  
**Cons:** Expensive

---

### API Alternative (Free/Cheap)
**Weather APIs**
- Met.no (free, excellent for Europe)
- OpenWeatherMap (free tier available)
- WeatherAPI (free tier available)

**Provides:**
- Cloud Coverage ✅
- Visibility ✅
- UV Index ✅
- Current conditions ✅

**Pros:** No hardware needed  
**Cons:** Not local, internet dependent

---

## 🔌 Integration Examples

### ESPHome Example (BME280):
```yaml
sensor:
  - platform: bme280
    temperature:
      name: "Outdoor Temperature"
      id: outdoor_temp
    humidity:
      name: "Outdoor Humidity"
      id: outdoor_humidity
    pressure:
      name: "Outdoor Pressure"
      id: outdoor_pressure
    address: 0x76
    update_interval: 60s
```

### Ecowitt Integration:
```yaml
# Install via HACS: Ecowitt
# Configure via UI
# Automatically creates all sensors
```

### Met.no Integration:
```yaml
# Built into HA
weather:
  - platform: met
    
# Use template sensors to extract attributes:
template:
  - sensor:
      - name: "Cloud Coverage"
        state: "{{ state_attr('weather.home', 'cloudiness') }}"
        unit_of_measurement: "%"
```

---

## 🎯 Recommended Setup Progression

### Stage 1: Minimum (Current)
```
✅ Pressure
✅ Temperature
✅ Wind Direction
✅ Wind Speed
```
**Forecast Quality:** 60%

---

### Stage 2: Add Humidity
```
✅ Pressure
✅ Temperature
✅ Wind Direction
✅ Wind Speed
✨ Humidity
```
**Forecast Quality:** 75% (+15%)  
**New Features:** Dew point, Fog risk, Better rain probability

---

### Stage 3: Add Weather API
```
✅ Pressure
✅ Temperature
✅ Wind Direction
✅ Wind Speed
✨ Humidity
✨ Cloud Coverage (API)
✨ UV Index (API)
✨ Visibility (API)
```
**Forecast Quality:** 85% (+10%)  
**New Features:** Current condition, Enhanced rain probability

---

### Stage 4: Add Local Rain
```
✅ Pressure
✅ Temperature
✅ Wind Direction
✅ Wind Speed
✨ Humidity
✨ Cloud Coverage
✨ UV Index
✨ Visibility
✨ Wind Gust
✨ Rain Rate
✨ Precipitation 24h
```
**Forecast Quality:** 95% (+10%)  
**New Features:** Storm detection, Precipitation tracking

---

## 💡 Tips

### For Best Results:
1. **Humidity is #1 priority** - Biggest accuracy improvement
2. **Combine local + API** - Local pressure/temp/humidity + API clouds
3. **Placement matters** - Sensors must be properly sited
4. **Regular calibration** - Check accuracy against official stations

### Sensor Placement:
- **Temperature/Humidity:** 1.5-2m height, shaded, ventilated
- **Pressure:** Indoor is fine (will be corrected)
- **Wind:** 10m height, clear of obstructions
- **Rain:** Open area, away from trees

### Common Mistakes:
- ❌ Humidity sensor in direct sun → false readings
- ❌ Anemometer too low → understated wind
- ❌ Pressure uncalibrated → wrong forecasts
- ❌ Temperature near heat source → too high

---

## 🔮 Future Sensors (Under Consideration)

Potential additions for future versions:

- **Soil Moisture** - Drought/flood conditions
- **Lightning Detector** - Storm tracking
- **Air Quality (PM2.5)** - Pollution correlation
- **Snow Depth** - Winter conditions
- **Leaf Wetness** - Dew/frost detection
- **Evapotranspiration** - Agricultural focus

---

**Last Updated:** 2025-12-01  
**Version:** 3.1.0-dev  
**Status:** Planning Document

