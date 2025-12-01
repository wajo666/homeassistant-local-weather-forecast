# 🚀 Extended Sensors Feature Branch

**Branch:** `feature/extended-sensors`  
**Target Version:** 3.1.0  
**Status:** 🟡 In Development

---

## 📋 Overview

Táto vetva pridáva podporu pre rozšírené meteorologické senzory a pripravuje základ pre Weather Entity implementáciu.

### Hlavné funkcie:
- ✅ **Voliteľné vstupné senzory** (vlhkosť, rosný bod, oblačnosť, UV index, viditeľnosť, ...)
- ✅ **Pokročilé meteorologické výpočty** (heat index, wind chill, fog risk, ...)
- 🔜 **Nové vypočítané senzory** (comfort index, enhanced rain probability, ...)
- 🔜 **Weather Entity** s hodinovými predpoveďami
- ✅ **100% spätná kompatibilita** s verziou 3.0.x

---

## 🎯 Implementation Status

### ✅ Phase 1: Foundation (COMPLETED)

**Completed:**
- ✅ Extended constants in `const.py`
- ✅ Configuration keys for optional sensors
- ✅ Weather condition mapping (Zambretti → HA)
- ✅ Meteorological calculations library (`calculations.py`)
- ✅ Feature flags (enable_weather_entity, enable_extended_sensors)
- ✅ Roadmap documentation

**Files Modified:**
- `custom_components/local_weather_forecast/const.py`

**Files Created:**
- `custom_components/local_weather_forecast/calculations.py`
- `ROADMAP_EXTENDED_SENSORS.md`

---

### 🔜 Phase 2: Config Flow Updates (TODO)

**Tasks:**
- [ ] Extend config flow with optional sensor inputs
- [ ] Add "Advanced Sensors" step in setup
- [ ] Add "Features" step for toggles
- [ ] Update options flow for reconfiguration
- [ ] Add validation for sensor entities
- [ ] Migration logic for existing installations

**Files to Modify:**
- `custom_components/local_weather_forecast/config_flow.py`
- `custom_components/local_weather_forecast/strings.json`
- `custom_components/local_weather_forecast/translations/*.json`

---

### 🔜 Phase 3: Extended Sensor Entities (TODO)

**New Sensors to Create:**

1. **Humidity Sensor** (if not provided by user)
   - Calculated from dewpoint if available
   - State class: measurement
   - Device class: humidity

2. **Dew Point Sensor**
   - Calculated from temperature + humidity
   - Shows fog risk in attributes
   - State class: measurement
   - Device class: temperature

3. **Comfort Index Sensor**
   - Apparent temperature (feels like)
   - Heat index / wind chill
   - Comfort level attribute
   - State class: measurement
   - Device class: temperature

4. **Rain Probability Enhanced Sensor**
   - Combines Zambretti + Negretti + humidity + clouds
   - Shows confidence level
   - 1h, 3h, 6h, 12h forecasts in attributes
   - Unit: %

5. **Weather Condition Sensor**
   - HA standard condition (cloudy, rainy, sunny, etc.)
   - Based on forecast models + current observations
   - Icon from condition
   - Confidence attribute

6. **Forecast Trend Sensor**
   - Overall trend (improving/deteriorating/stable)
   - Individual trends for pressure, temp, humidity
   - Time to change estimate
   - Confidence level

**Files to Modify:**
- `custom_components/local_weather_forecast/sensor.py`

---

### 🔜 Phase 4: Weather Entity (TODO)

**Tasks:**
- [ ] Create `weather.py` platform
- [ ] Implement `LocalWeatherForecast` entity
- [ ] Add current conditions
- [ ] Generate forecast data (1h, 3h, 6h intervals)
- [ ] Implement `get_forecasts()` service
- [ ] Support hourly and daily forecast types
- [ ] Map Zambretti conditions to HA standards
- [ ] Add proper attribution

**Files to Create:**
- `custom_components/local_weather_forecast/weather.py`

**Files to Modify:**
- `custom_components/local_weather_forecast/__init__.py`
- `custom_components/local_weather_forecast/manifest.json`

---

### 🔜 Phase 5: Testing & Documentation (TODO)

**Tasks:**
- [ ] Unit tests for calculations.py
- [ ] Unit tests for new sensors
- [ ] Integration tests for weather entity
- [ ] Update README.md with new features
- [ ] Update WEATHER_CARDS.md with examples
- [ ] Create migration guide (3.0.x → 3.1.0)
- [ ] Add example configurations
- [ ] Performance testing

**Files to Create:**
- `tests/test_calculations.py`
- `tests/test_extended_sensors.py`
- `tests/test_weather_entity.py`
- `docs/MIGRATION_3.1.md`
- `docs/EXAMPLES.md`

**Files to Modify:**
- `README.md`
- `WEATHER_CARDS.md`
- `TESTING.md`

---

## 🧪 Available Calculations

The `calculations.py` module provides:

### Temperature Calculations:
```python
calculate_dewpoint(temperature, humidity) -> float
calculate_heat_index(temperature, humidity) -> float
calculate_wind_chill(temperature, wind_speed) -> float
calculate_apparent_temperature(temp, humidity, wind_speed) -> float
```

### Comfort & Risk Assessment:
```python
get_comfort_level(apparent_temperature) -> str
get_fog_risk(temperature, dewpoint) -> str
```

### Enhanced Forecasting:
```python
calculate_rain_probability_enhanced(
    zambretti_prob,
    negretti_prob,
    humidity,
    cloud_coverage,
    dewpoint_spread
) -> tuple[int, str]  # (probability, confidence)

interpolate_forecast(
    current_value,
    forecast_value,
    hours_to_forecast
) -> float
```

### Visibility:
```python
calculate_visibility_from_humidity(humidity, temperature) -> float
```

---

## 📊 New Configuration Schema

### Optional Sensors (Phase 2):
```yaml
humidity_sensor: sensor.outdoor_humidity  # Optional
dewpoint_sensor: sensor.outdoor_dewpoint  # Optional
cloud_coverage_sensor: sensor.cloud_coverage  # Optional
uv_index_sensor: sensor.uv_index  # Optional
visibility_sensor: sensor.visibility  # Optional
wind_gust_sensor: sensor.wind_gust  # Optional
rain_rate_sensor: sensor.rain_rate  # Optional
precipitation_sensor: sensor.precipitation_24h  # Optional
```

### Feature Flags (Phase 2):
```yaml
enable_weather_entity: false  # Enable weather.local_forecast
enable_extended_sensors: false  # Enable new calculated sensors
forecast_interval: 3  # Hours (1, 3, 6)
```

---

## 🔄 Backward Compatibility

### Guaranteed Compatibility:
- ✅ All existing sensors remain unchanged
- ✅ No breaking changes to sensor names
- ✅ No breaking changes to attributes
- ✅ Config from 3.0.x works without changes
- ✅ New features are opt-in only

### Migration Path:
1. Update to 3.1.0
2. Existing installation continues working
3. Optionally enable new features via config
4. Optionally add extended sensors
5. Optionally enable weather entity

**No action required for existing users!**

---

## 🎨 Example Weather Entity Output

```yaml
weather.local_forecast:
  state: "rainy"
  
  # Current conditions
  temperature: 4.0
  temperature_unit: "°C"
  pressure: 1014.0
  pressure_unit: "hPa"
  humidity: 75
  wind_speed: 5.2
  wind_speed_unit: "km/h"
  wind_bearing: 185
  dew_point: 2.5
  cloud_coverage: 85
  visibility: 8.5
  visibility_unit: "km"
  
  # Attribution
  attribution: "Zambretti & Negretti-Zambra algorithms"
  
  # Forecast (3h intervals)
  forecast:
    - datetime: "2025-12-01T15:00:00+00:00"
      condition: "rainy"
      temperature: 3.5
      templow: 2.0
      precipitation_probability: 65
      pressure: 1013.2
      wind_speed: 8.0
      wind_bearing: 190
      cloud_coverage: 90
      
    - datetime: "2025-12-01T18:00:00+00:00"
      condition: "cloudy"
      temperature: 3.0
      templow: 1.8
      precipitation_probability: 45
      pressure: 1013.8
      wind_speed: 6.5
      wind_bearing: 185
      cloud_coverage: 75
```

---

## 🧮 Calculation Examples

### Dew Point:
```python
# Temperature: 20°C, Humidity: 60%
dewpoint = calculate_dewpoint(20, 60)
# Result: 12.0°C

# Fog risk
spread = 20 - 12  # 8°C
fog_risk = get_fog_risk(20, 12)
# Result: "none" (spread > 4°C)
```

### Apparent Temperature:
```python
# Hot day: 32°C, 70% humidity
feels_like = calculate_apparent_temperature(32, 70, None)
# Uses heat index: ~38°C

# Cold day: 2°C, 40% humidity, 25 km/h wind
feels_like = calculate_apparent_temperature(2, 40, 25)
# Uses wind chill: ~-3°C
```

### Enhanced Rain Probability:
```python
# Zambretti: 30%, Negretti: 40%
# Humidity: 85%, Clouds: 90%
prob, confidence = calculate_rain_probability_enhanced(
    30, 40, 85, 90, 3.5
)
# Result: 60%, "high"
```

---

## 📝 Development Notes

### Testing Locally:
```bash
# Copy to HA config
cp -r custom_components/local_weather_forecast /config/custom_components/

# Restart HA
ha core restart

# Check logs
ha core logs -f
```

### Code Style:
- Follow Home Assistant style guide
- Type hints on all functions
- Docstrings in Google format
- Black formatting
- Pylint compliance

### Performance Targets:
- Max 100ms per sensor update
- Max 500ms for weather entity forecast generation
- No blocking calls in event loop
- Efficient caching of calculations

---

## 🎯 Next Steps

1. **Start Phase 2**: Update config_flow.py
2. **Design UI**: Mockup config flow screens
3. **Implement first sensor**: Humidity tracking
4. **Test migration**: From 3.0.3 → 3.1.0-dev

---

## 🐛 Known Issues

None yet - branch just created!

---

## 📞 Questions?

Check `ROADMAP_EXTENDED_SENSORS.md` for detailed implementation plan.

---

**Last Updated:** 2025-12-01  
**Maintainer:** Development Team  
**Status:** Foundation complete, ready for Phase 2

