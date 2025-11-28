# 🧪 Testing Guide - Local Weather Forecast v2.0

## Pre-release Testing Checklist

### 1. File Structure Validation ✅

```bash
# Verify all files exist
custom_components/local_weather_forecast/
├── __init__.py                 ✅
├── config_flow.py             ✅
├── const.py                   ✅
├── forecast_data.py           ✅
├── manifest.json              ✅
├── negretti_zambra.py         ✅
├── sensor.py                  ✅
├── strings.json               ✅
├── zambretti.py               ✅
└── translations/
    ├── de.json               ✅ German
    ├── en.json               ✅ English
    ├── gr.json               ✅ Greek
    ├── it.json               ✅ Italian
    └── sk.json               ✅ Slovak
```

### 2. Code Validation

```bash
# Check for Python syntax errors
python3 -m py_compile custom_components/local_weather_forecast/*.py

# Check manifest.json is valid JSON
python3 -c "import json; json.load(open('custom_components/local_weather_forecast/manifest.json'))"

# Check translations are valid JSON
for file in custom_components/local_weather_forecast/translations/*.json; do
    python3 -c "import json; json.load(open('$file'))" && echo "$file ✅"
done
```

---

## Installation Testing

### Test 1: Fresh Installation

#### Steps:
1. Copy `custom_components/local_weather_forecast/` to HA config
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Local Weather Forecast"

#### Expected Results:
- ✅ Integration appears in search results
- ✅ Setup wizard opens
- ✅ All form fields visible with descriptions
- ✅ Entity selectors work

#### Test Configuration:
```yaml
Pressure Sensor: sensor.test_pressure (create dummy if needed)
Temperature Sensor: sensor.test_temperature
Elevation: 370
Language: English
```

#### Expected After Setup:
```
Created entities:
✅ sensor.local_weather_forecast_local_forecast
✅ sensor.local_weather_forecast_pressure
✅ sensor.local_weather_forecast_temperature
✅ sensor.local_weather_forecast_pressure_change
✅ sensor.local_weather_forecast_temperature_change
✅ sensor.local_weather_forecast_zambretti_detail
✅ sensor.local_weather_forecast_negretti_zambra_detail
```

---

### Test 2: Configuration Validation

#### Test 2.1: Missing Pressure Sensor
- Input: Non-existent sensor entity
- Expected: ❌ Error "Sensor entity not found"

#### Test 2.2: Invalid Elevation
- Input: -100 meters
- Expected: ❌ Error "Elevation must be between 0 and 9000 meters"

#### Test 2.3: Optional Sensors
- Input: Leave temperature/wind sensors empty
- Expected: ✅ Setup completes successfully

---

### Test 3: Sensor Values

Create test sensors in Developer Tools → States:

**⚠️ Important - Units:**
- Pressure must be in **hPa** (hectopascals)
- Temperature must be in **°C** (Celsius)
- Wind direction in **degrees** (0-360°)
- Wind speed in **km/h** or **m/s**

```yaml
# Create test pressure sensor
sensor.test_pressure:
  state: 1013.25
  attributes:
    unit_of_measurement: hPa
    device_class: atmospheric_pressure

# Create test temperature sensor  
sensor.test_temperature:
  state: 15.0
  attributes:
    unit_of_measurement: °C
    device_class: temperature
```

#### Expected Results:
After 1 minute:
- ✅ `sensor.local_weather_forecast_local_forecast` shows forecast title
- ✅ `sensor.local_weather_forecast_pressure` = ~1013.25 hPa
- ✅ `sensor.local_weather_forecast_temperature` = 15.0 °C
- ✅ `sensor.local_weather_forecast_local_forecast.attributes.p0` exists
- ✅ `sensor.local_weather_forecast_local_forecast.attributes.forecast_zambretti` has text

---

### Test 4: Restart Behavior

#### Steps:
1. Setup integration with test sensors
2. Wait for initial values (1-2 minutes)
3. Note current sensor values
4. Restart Home Assistant
5. Check sensors immediately after restart

#### Expected Results:
- ✅ Sensors restore to previous values
- ✅ No "unknown" or "unavailable" states
- ✅ Forecast continues without interruption
- ✅ Attributes preserved

---

### Test 5: Fallback System

#### Test 5.1: Sensor Becomes Unavailable

```yaml
# In Developer Tools → States, set:
sensor.test_pressure: unavailable
```

#### Expected:
- ✅ Integration continues using last known value
- ✅ Log message: "Sensor unavailable, attempting to fetch from history"
- ✅ If history exists: Uses historical value
- ✅ If no history: Uses default with warning

#### Test 5.2: Restore from History

1. Run integration for 1 hour with valid sensors
2. Remove test sensors
3. Restart Home Assistant
4. Check if integration finds historical values

#### Expected:
- ✅ Searches up to 7 days back
- ✅ Finds last valid value
- ✅ Log: "Found historical value from [timestamp]"

---

### Test 6: Multi-Language

#### Test Each Language:

```
English (en):
- ✅ Setup wizard in English
- ✅ Forecast text: "Fine, Possibly showers"

German (de):
- ✅ Setup wizard in German
- ✅ Forecast text: "Schön, Regenschauer möglich."

Greek (gr):
- ✅ Setup wizard in Greek
- ✅ Forecast text: "Πιθανή βροχή."

Italian (it):
- ✅ Setup wizard in Italian
- ✅ Forecast text: "Bello, possibili rovesci"

Slovak (sk):
- ✅ Setup wizard in Slovak
- �� Forecast text: "Pekné, možné prehánky."
```

---

### Test 7: Options Flow

#### Steps:
1. Go to Settings → Devices & Services
2. Find "Local Weather Forecast"
3. Click "Configure"

#### Expected:
- ✅ Options dialog opens
- ✅ Can change temperature sensor
- ✅ Can change wind sensors
- ✅ Can change elevation
- ✅ Can change language
- ✅ Changes apply immediately

#### Test Scenario:
- Change elevation from 370 to 500
- Expected: `p0` value recalculates

---

### Test 8: Statistics Sensors

#### Test Pressure Change:

1. Set initial pressure: 1010 hPa
2. Wait 1 minute
3. Change to 1012 hPa
4. Wait 1 minute
5. Change to 1015 hPa

#### Expected:
- ✅ `sensor.local_weather_forecast_pressure_change` updates
- ✅ Shows difference between oldest and newest (1015 - 1010 = 5 hPa)
- ✅ Keeps data for 180 minutes

---

### Test 9: Forecast Algorithms

#### Test Case: High Pressure, Rising

```yaml
Pressure: 1030 hPa
Pressure Change: +3 hPa over 3h
Wind: North, 5 km/h
```

#### Expected:
- ✅ Zambretti forecast: "Settled Fine" or similar
- ✅ Forecast number: 0-5 (good weather)
- ✅ Letter code: A, B, or C

#### Test Case: Low Pressure, Falling

```yaml
Pressure: 990 hPa
Pressure Change: -5 hPa over 3h
Wind: South, 20 km/h
```

#### Expected:
- ✅ Zambretti forecast: "Stormy" or "Very Unsettled"
- ✅ Forecast number: 20-25 (bad weather)
- ✅ Letter code: X, Y, or Z

---

### Test 10: Lovelace Card

#### Create Test Card:

```yaml
type: entities
title: Test Local Weather Forecast
entities:
  - entity: sensor.local_weather_forecast_local_forecast
  - entity: sensor.local_weather_forecast_pressure
  - entity: sensor.local_weather_forecast_temperature
  - type: attribute
    entity: sensor.local_weather_forecast_local_forecast
    attribute: forecast_zambretti
    name: Forecast
```

#### Expected:
- ✅ All entities display
- ✅ No errors in browser console
- ✅ Values update when sensors change

---

## Performance Testing

### Test 11: CPU Usage

```bash
# Monitor HA CPU during operation
top -p $(pgrep -f home-assistant)
```

#### Expected:
- ✅ Minimal CPU usage (<1%)
- ✅ No spikes during sensor updates
- ✅ No continuous polling

### Test 12: Memory Usage

Check in Home Assistant logs:
- ✅ No memory leaks over 24 hours
- ✅ History arrays properly cleaned up

### Test 13: Database Impact

```sql
-- Check number of state changes
SELECT COUNT(*) FROM states 
WHERE entity_id LIKE 'sensor.local_weather_forecast%';
```

#### Expected:
- ✅ Reasonable number of state changes
- ✅ No excessive updates

---

## Error Handling Testing

### Test 14: Invalid Sensor Values

```yaml
# Set invalid values
sensor.test_pressure: "abc"  # Non-numeric
sensor.test_temperature: null
```

#### Expected:
- ✅ No crashes
- ✅ Falls back to default/history
- ✅ Warning in logs

### Test 15: Extreme Values

```yaml
# Test edge cases
Pressure: 850 hPa  # Very low
Pressure: 1100 hPa # Very high
Elevation: 8848 m  # Mount Everest
Temperature: -40°C # Arctic
```

#### Expected:
- ✅ Calculations don't crash
- ✅ Results within reasonable bounds

---

## Integration Testing

### Test 16: With Real Weather Station

#### Recommended Test Setup:
- Ecowitt weather station
- BME280 sensor
- Any WiFi weather station

#### Monitor for 24 hours:
- ✅ Forecast changes make sense
- ✅ Compare with actual weather
- ✅ No gaps in data

### Test 17: Multiple Instances

1. Add integration with sensor A
2. Add integration again with sensor B

#### Expected:
- ✅ Both instances work independently
- ✅ Unique entity IDs
- ✅ No conflicts

---

## Upgrade Testing (v1.x → v2.0)

### Test 18: Migration Path

#### Old Setup:
- YAML configuration in `weather_forecast.yaml`
- Statistics platform in `configuration.yaml`

#### Migration Steps:
1. Remove YAML config
2. Restart HA
3. Install v2.0
4. Configure via UI

#### Expected:
- ✅ Old entities removed
- ✅ New entities created
- ✅ Can update Lovelace cards

---

## HACS Testing

### Test 19: HACS Validation

```bash
# Run HACS validation locally
hacs validate custom_components/local_weather_forecast
```

#### Expected:
- ✅ No errors
- ✅ All required files present
- ✅ manifest.json valid

### Test 20: GitHub Actions

Push to GitHub and verify:
- ✅ Validate workflow runs
- ✅ Hassfest passes
- ✅ HACS action passes

---

## Acceptance Criteria

### Must Pass:
- [x] All 7 sensors created
- [x] UI configuration works
- [x] State restoration works
- [x] Fallback system functional
- [x] Multi-language support
- [x] No Python errors in logs
- [x] HACS validation passes

### Nice to Have:
- [ ] Tested with real weather station
- [ ] 24h stability test passed
- [ ] Multiple users tested
- [ ] Documented edge cases

---

## Bug Report Template

If you find issues during testing:

```markdown
**Issue:** Brief description

**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Behavior:**


**Actual Behavior:**


**Environment:**
- Home Assistant version: 
- Integration version: 2.0.0
- Installation method: HACS / Manual

**Logs:**
```
[Paste relevant logs]
```

**Configuration:**
- Pressure sensor: 
- Elevation: 
- Language: 
```

---

## Sign-off

Once all tests pass:

```
✅ Installation works
✅ Configuration validates correctly
✅ Sensors create and update
✅ Restart behavior correct
✅ Fallback system functional
✅ Multi-language works
✅ Performance acceptable
✅ Error handling robust
✅ HACS validation passes

🚀 READY FOR RELEASE!
```

---

## Quick Test Script

```bash
#!/bin/bash
# Quick validation script

echo "🧪 Testing Local Weather Forecast v2.0"

# 1. File structure
echo "📁 Checking file structure..."
[ -f "custom_components/local_weather_forecast/__init__.py" ] && echo "✅ __init__.py" || echo "❌ Missing __init__.py"
[ -f "custom_components/local_weather_forecast/config_flow.py" ] && echo "✅ config_flow.py" || echo "❌ Missing config_flow.py"
[ -f "custom_components/local_weather_forecast/sensor.py" ] && echo "✅ sensor.py" || echo "❌ Missing sensor.py"
[ -f "custom_components/local_weather_forecast/manifest.json" ] && echo "✅ manifest.json" || echo "❌ Missing manifest.json"

# 2. Syntax check
echo ""
echo "🐍 Checking Python syntax..."
python3 -m py_compile custom_components/local_weather_forecast/*.py && echo "✅ No syntax errors" || echo "❌ Syntax errors found"

# 3. JSON validation
echo ""
echo "📋 Validating JSON files..."
python3 -c "import json; json.load(open('custom_components/local_weather_forecast/manifest.json'))" && echo "✅ manifest.json valid" || echo "❌ manifest.json invalid"

echo ""
echo "🎉 Pre-flight checks complete!"
```

Save as `test.sh` and run:
```bash
chmod +x test.sh
./test.sh
```

