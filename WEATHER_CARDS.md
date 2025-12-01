# Weather Card Examples

## ⚠️ Important: Attribute Formats

All forecast attributes use **list/array and tuple formats** internally for easy programmatic access.

**Note:** Home Assistant UI displays these as comma-separated strings, but they are proper lists/tuples in templates!

### Main Sensor Attributes (sensor.local_forecast):
- `forecast_zambretti` = `["Fine Weather!", 1, "B"]` 
  - **Displays as:** `"Fine Weather!, 1, B"`
  - **Access:** `forecast_zambretti[0]` → `"Fine Weather!"`
- `forecast_neg_zam` = `["Fine", 1, "B"]`
  - **Displays as:** `"Fine, 1, B"`
- `forecast_short_term` = `["Sunny", "High Pressure"]`
  - **Displays as:** `"Sunny, High Pressure"`
- `forecast_pressure_trend` = `["Rising", 1]`
  - **Displays as:** `"Rising, 1"`
- `forecast_temp_short` = `[18.5, 0]`
  - **Displays as:** `"18.5, 0"` (where interval: 0=6h, 1=12h)
- `wind_direction` = `[0, 45, "NE", 1]`
  - **Displays as:** `"0, 45, NE, 1"` (wind_fak, degrees, text, speed_fak)

### Detail Sensor Attributes (zambretti_detail / neg_zam_detail):
- `forecast` = `[1, 2]`
  - **Displays as:** `"1, 2"` (state_6h, state_12h where 0=sunny to 6=lightning)
- `rain_prob` = `[30, 60]`
  - **Displays as:** `"30, 60"` (probability_6h%, probability_12h%)
- `icons` = `("mdi:weather-sunny", "mdi:weather-cloudy")`
  - **Displays as:** `"mdi:weather-sunny, mdi:weather-cloudy"` (tuple: icon_now, icon_later)
- `first_time` = `["15:30", 180.5]`
  - **Displays as:** `"15:30, 180.5"` (time_string, minutes_to_change)
- `second_time` = `["21:30", 540.5]`
  - **Displays as:** `"21:30, 540.5"` (time_string, minutes_to_change)

### How to Access in Templates:
```yaml
# ✅ CORRECT - Direct array/list access (works in templates!)
{{ state_attr("sensor.local_forecast", "forecast_zambretti")[0] }}  # Returns: "Fine Weather!"
{{ state_attr("sensor.local_forecast", "forecast_zambretti")[1] }}  # Returns: 1
{{ state_attr("sensor.local_forecast_zambretti_detail", "rain_prob")[0] }}  # Returns: 30
{{ state_attr("sensor.local_forecast_zambretti_detail", "icons")[0] }}  # Returns: "mdi:weather-sunny"

# ❌ WRONG - Don't use string split (won't work correctly!)
{{ state_attr("sensor.local_forecast", "forecast_zambretti").split(', ')[0] }}  # DON'T DO THIS!
```

### Checking if Attribute is Valid:
```yaml
{% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
{% if fc and fc is iterable and fc is not string %}
  {{ fc[0] }}  # Safe to access as list
{% endif %}
```

### Why the Difference?
- **Internal Format:** Python lists and tuples (proper data structures)
- **UI Display:** Home Assistant converts to strings for visual display only
- **Template Access:** Works as lists/tuples - array indexing is fully supported
- **This is by design:** HA's UI simplifies display, but functionality remains

---

## 📋 Entity IDs Reference

After installation, your sensors will have these entity IDs (matching original YAML exactly):
- **Main Forecast:** `sensor.local_forecast` (friendly name: "Local forecast")
- **Pressure:** `sensor.local_forecast_pressure` (friendly name: "Local forecast Pressure")
- **Temperature:** `sensor.local_forecast_temperature` (friendly name: "Local forecast temperature")
- **Pressure Change:** `sensor.local_forecast_pressurechange` (friendly name: "Local forecast PressureChange")
- **Temperature Change:** `sensor.local_forecast_temperaturechange` (friendly name: "Local forecast TemperatureChange")
- **Zambretti Details:** `sensor.local_forecast_zambretti_detail` (friendly name: "Local forecast zambretti detail")
- **Negretti-Zambra Details:** `sensor.local_forecast_neg_zam_detail` (friendly name: "Local forecast neg_zam detail")

**Note:** Entity IDs are now 100% identical to original YAML implementation!

---

## 📋 Simple Entities Card (No custom cards needed)

```yaml
type: entities
title: Local Weather Forecast
entities:
  - entity: sensor.local_forecast
    name: Forecast
  - entity: sensor.local_forecast_zambretti_detail
    name: Zambretti Forecast
  - entity: sensor.local_forecast_pressure
    name: Sea Level Pressure
  - entity: sensor.local_forecast_temperature
    name: Temperature
  - entity: sensor.local_forecast_pressurechange
    name: Pressure Trend (3h)
  - entity: sensor.local_forecast_temperaturechange
    name: Temperature Trend (1h)
```

---

## 🎨 Mushroom Cards (Recommended - Beautiful UI)

### Requirements:
Install via HACS:
1. [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom)
2. [Vertical Stack In Card](https://github.com/ofekashery/vertical-stack-in-card)

### Basic Mushroom Card:

```yaml
type: custom:vertical-stack-in-card
cards:
  # Title
  - type: custom:mushroom-title-card
    title: |
      {% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
      {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Weather Forecast{% endif %}
    subtitle: 'Local Weather Forecast'
  
  # Current conditions + Next 6h + Next 12h
  - type: horizontal-stack
    cards:
      # Current
      - type: custom:mushroom-template-card
        primary: "Now"
        secondary: |
          {% set st = state_attr("sensor.local_forecast", "forecast_short_term") %}
          {{states("sensor.local_forecast_temperature")}}°C
          {% if st and st is iterable and st is not string %}{{st[0]}} - {{st[1]}}{% endif %}
        icon: mdi:weather-cloudy-clock
        icon_color: blue
        layout: vertical
        multiline_secondary: true
      
      # ~6 hours
      - type: custom:mushroom-template-card
        primary: "~6h"
        secondary: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if det and det is iterable and det is not string %}{{det[0]}}% rain{% else %}?% rain{% endif %}
          {% if temp_fc and temp_fc is iterable and temp_fc is not string and temp_fc[1] == 0 %}
          ↗ ~{{temp_fc[0]}}°C
          {% else %}
          {% set temp_change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% set current_temp = states("sensor.local_forecast_temperature") | float(0) %}
          {% set est_temp = current_temp + (temp_change * 6) %}
          {% if temp_change > 0.1 %}↗ ~{{est_temp | round(1)}}°C{% elif temp_change < -0.1 %}↘ ~{{est_temp | round(1)}}°C{% else %}→ ~{{est_temp | round(1)}}°C{% endif %}
          {% endif %}
        icon: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if det and det is iterable and det is not string %}{{det[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: amber
        layout: vertical
        multiline_secondary: true
      
      # ~12 hours
      - type: custom:mushroom-template-card
        primary: "~12h"
        secondary: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if det and det is iterable and det is not string %}{{det[1]}}% rain{% else %}?% rain{% endif %}
          {% if temp_fc and temp_fc is iterable and temp_fc is not string and temp_fc[1] == 1 %}
          ↗ ~{{temp_fc[0]}}°C
          {% else %}
          {% set temp_change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% set current_temp = states("sensor.local_forecast_temperature") | float(0) %}
          {% set est_temp = current_temp + (temp_change * 12) %}
          {% if temp_change > 0.1 %}↗ ~{{est_temp | round(1)}}°C{% elif temp_change < -0.1 %}↘ ~{{est_temp | round(1)}}°C{% else %}→ ~{{est_temp | round(1)}}°C{% endif %}
          {% endif %}
        icon: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if det and det is iterable and det is not string %}{{det[1]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: orange
        layout: vertical
        multiline_secondary: true
  
  # Detailed forecast text
  - type: custom:mushroom-template-card
    primary: |
      {% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
      {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading forecast...{% endif %}
    secondary: |
      {% set pt = state_attr("sensor.local_forecast", "forecast_pressure_trend") %}
      {% if pt and pt is iterable and pt is not string %}Pressure: {{pt[0]}}{% else %}Pressure: ...{% endif %}
      Change: {{states("sensor.local_forecast_pressurechange")}} hPa/3h
    icon: mdi:weather-cloudy-arrow-right
    icon_color: grey
    multiline_secondary: true
  
  # Pressure details
  - type: custom:mushroom-chips-card
    chips:
      - type: template
        icon: mdi:gauge
        content: '{{states("sensor.local_forecast_pressure")}} hPa'
      - type: template
        icon: mdi:thermometer
        content: '{{states("sensor.local_forecast_temperature")}}°C'
      - type: template
        icon: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 0 %}mdi:trending-up
          {% elif change < 0 %}mdi:trending-down
          {% else %}mdi:trending-neutral
          {% endif %}
        content: '{{states("sensor.local_forecast_pressurechange")}} hPa'
        icon_color: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 2 %}green
          {% elif change < -2 %}red
          {% else %}grey
          {% endif %}
      - type: template
        icon: |
          {% set change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% if change > 0 %}mdi:thermometer-chevron-up
          {% elif change < 0 %}mdi:thermometer-chevron-down
          {% else %}mdi:thermometer-lines
          {% endif %}
        content: '{{states("sensor.local_forecast_temperaturechange")}}°C'
        icon_color: |
          {% set change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% if change > 1 %}red
          {% elif change < -1 %}blue
          {% else %}grey
          {% endif %}
```

---

## 🌟 Advanced Mushroom Card (Full Featured)

```yaml
type: custom:vertical-stack-in-card
cards:
  # Header with dynamic icon based on forecast
  - type: custom:mushroom-title-card
    title: 'Weather Forecast'
    subtitle: |
      {% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
      {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading...{% endif %}
  
  # Main info row
  - type: horizontal-stack
    cards:
      # Current conditions
      - type: custom:mushroom-template-card
        primary: 'Now'
        secondary: |
          {% set st = state_attr("sensor.local_forecast", "forecast_short_term") %}
          {% if st and st is iterable and st is not string %}{{st[0]}}{% endif %} ({{states("sensor.local_forecast_temperature")}}°C)
          {% set pt = state_attr("sensor.local_forecast", "forecast_pressure_trend") %}
          {% if pt and pt is iterable and pt is not string %}Trend: {{pt[0]}}{% endif %}
        icon: mdi:weather-cloudy-clock
        icon_color: |
          {% set pressure = states("sensor.local_forecast_pressure") | float(1013) %}
          {% if pressure < 1000 %}red
          {% elif pressure < 1020 %}amber
          {% else %}green
          {% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast
      
      # First interval forecast (calculated time)
      - type: custom:mushroom-template-card
        primary: |
          {% set ft = state_attr("sensor.local_forecast_zambretti_detail", "first_time") %}
          {% if ft and ft is iterable and ft is not string %}{{ft[0]}}{% else %}~3h{% endif %}
        secondary: |
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if rp and rp is iterable and rp is not string %}☔ {{rp[0]}}% rain{% else %}☔ ?%{% endif %}
          {% if temp_fc and temp_fc is iterable and temp_fc is not string and temp_fc[1] == 0 %}
          🌡️ ~{{temp_fc[0]}}°C
          {% else %}
          {% set temp_change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% set current_temp = states("sensor.local_forecast_temperature") | float(0) %}
          {% set ft = state_attr("sensor.local_forecast_zambretti_detail", "first_time") %}
          {% if ft and ft is iterable and ft is not string %}
          {% set hours = (ft[1] | float(180)) / 60 %}
          {% else %}
          {% set hours = 3 %}
          {% endif %}
          {% set est_temp = current_temp + (temp_change * hours) %}
          {% if temp_change > 0.1 %}🌡️ ↗ ~{{est_temp | round(1)}}°C{% elif temp_change < -0.1 %}🌡️ ↘ ~{{est_temp | round(1)}}°C{% else %}🌡️ → ~{{est_temp | round(1)}}°C{% endif %}
          {% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% if rp and rp is iterable and rp is not string %}
            {% set rain = rp[0] | int(0) %}
            {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
      
      # Second interval forecast (calculated time)
      - type: custom:mushroom-template-card
        primary: |
          {% set st = state_attr("sensor.local_forecast_zambretti_detail", "second_time") %}
          {% if st and st is iterable and st is not string %}{{st[0]}}{% else %}~9h{% endif %}
        secondary: |
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if rp and rp is iterable and rp is not string %}☔ {{rp[1]}}% rain{% else %}☔ ?%{% endif %}
          {% if temp_fc and temp_fc is iterable and temp_fc is not string and temp_fc[1] == 1 %}
          🌡️ ~{{temp_fc[0]}}°C
          {% else %}
          {% set temp_change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% set current_temp = states("sensor.local_forecast_temperature") | float(0) %}
          {% set st = state_attr("sensor.local_forecast_zambretti_detail", "second_time") %}
          {% if st and st is iterable and st is not string %}
          {% set hours = (st[1] | float(540)) / 60 %}
          {% else %}
          {% set hours = 9 %}
          {% endif %}
          {% set est_temp = current_temp + (temp_change * hours) %}
          {% if temp_change > 0.1 %}🌡️ ↗ ~{{est_temp | round(1)}}°C{% elif temp_change < -0.1 %}🌡️ ↘ ~{{est_temp | round(1)}}°C{% else %}🌡️ → ~{{est_temp | round(1)}}°C{% endif %}
          {% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[1]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% if rp and rp is iterable and rp is not string %}
            {% set rain = rp[1] | int(0) %}
            {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
  
  # Forecast text
  - type: custom:mushroom-template-card
    primary: |
      {% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
      {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading forecast...{% endif %}
    secondary: |
      {% set pt = state_attr("sensor.local_forecast", "forecast_pressure_trend") %}
      {% if pt and pt is iterable and pt is not string %}Pressure {{pt[0]}}{% else %}Pressure ...{% endif %}
      {{states("sensor.local_forecast_pressurechange")}} hPa in 3h
    icon: mdi:weather-cloudy-arrow-right
    icon_color: grey
    multiline_secondary: true
  
  # Metrics chips
  - type: custom:mushroom-chips-card
    alignment: center
    chips:
      - type: template
        icon: mdi:gauge
        content: '{{states("sensor.local_forecast_pressure")}} hPa'
        tap_action:
          action: more-info
          entity: sensor.local_forecast_pressure
      - type: template
        icon: mdi:thermometer
        content: '{{states("sensor.local_forecast_temperature")}}°C'
        tap_action:
          action: more-info
          entity: sensor.local_forecast_temperature
      - type: template
        icon: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 0 %}mdi:trending-up
          {% elif change < 0 %}mdi:trending-down
          {% else %}mdi:trending-neutral
          {% endif %}
        content: '{{states("sensor.local_forecast_pressurechange")}} hPa'
        icon_color: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 2 %}green
          {% elif change < -2 %}red
          {% else %}grey
          {% endif %}
        tap_action:
          action: more-info
          entity: sensor.local_forecast_pressurechange
      - type: template
        icon: |
          {% set change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% if change > 0 %}mdi:thermometer-chevron-up
          {% elif change < 0 %}mdi:thermometer-chevron-down
          {% else %}mdi:thermometer-lines
          {% endif %}
        content: '{{states("sensor.local_forecast_temperaturechange")}}°C/h'
        icon_color: |
          {% set change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% if change > 1 %}red
          {% elif change < -1 %}blue
          {% else %}grey
          {% endif %}
        tap_action:
          action: more-info
          entity: sensor.local_forecast_temperaturechange
  
  # Alternative forecast model
  - type: custom:mushroom-template-card
    primary: 'Negretti-Zambra Alternative'
    secondary: |
      {% set fc = state_attr("sensor.local_forecast", "forecast_neg_zam") %}
      {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading...{% endif %}
    icon: mdi:weather-cloudy
    icon_color: purple
    multiline_secondary: true
    tap_action:
      action: more-info
      entity: sensor.local_forecast_neg_zam_detail
```

---

## 🎯 Two-Row Comparison Card (Zambretti + Negretti-Zambra)

```yaml
type: custom:vertical-stack-in-card
cards:
  # Zambretti Forecast Row (Current + 6h + 12h with times)
  - type: custom:mushroom-title-card
    title: 'Zambretti Forecast'
    subtitle: |
      {% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
      {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading...{% endif %}
  
  - type: horizontal-stack
    cards:
      # Current - Zambretti
      - type: custom:mushroom-template-card
        primary: 'Teraz'
        secondary: |
          {% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
          {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading{% endif %}
          {{states("sensor.local_forecast_temperature")}}°C
          {{states("sensor.local_forecast_pressure")}} hPa
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set pressure = states("sensor.local_forecast_pressure") | float(1013) %}
          {% if pressure < 1000 %}red
          {% elif pressure < 1020 %}amber
          {% else %}green
          {% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast
      
      # 6h forecast with calculated time
      - type: custom:mushroom-template-card
        primary: |
          {% set ft = state_attr("sensor.local_forecast_zambretti_detail", "first_time") %}
          {% if ft and ft is iterable and ft is not string %}{{ft[0]}}{% else %}~6h{% endif %}
        secondary: |
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if rp and rp is iterable and rp is not string %}☔ {{rp[0]}}%{% else %}☔ ?%{% endif %}
          {% if temp_fc and temp_fc is iterable and temp_fc is not string and temp_fc[1] == 0 %}🌡️ {{temp_fc[0]}}°C{% else %}{% set temp_change = states("sensor.local_forecast_temperaturechange") | float(0) %}{% set current_temp = states("sensor.local_forecast_temperature") | float(0) %}{% set ft = state_attr("sensor.local_forecast_zambretti_detail", "first_time") %}{% if ft and ft is iterable and ft is not string %}{% set hours = (ft[1] | float(180)) / 60 %}{% else %}{% set hours = 3 %}{% endif %}{% set est_temp = current_temp + (temp_change * hours) %}🌡️ {{est_temp | round(1)}}°C{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% if rp and rp is iterable and rp is not string %}
            {% set rain = rp[0] | int(0) %}
            {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_zambretti_detail
      
      # 12h forecast with calculated time
      - type: custom:mushroom-template-card
        primary: |
          {% set st = state_attr("sensor.local_forecast_zambretti_detail", "second_time") %}
          {% if st and st is iterable and st is not string %}{{st[0]}}{% else %}~12h{% endif %}
        secondary: |
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if rp and rp is iterable and rp is not string %}☔ {{rp[1]}}%{% else %}☔ ?%{% endif %}
          {% if temp_fc and temp_fc is iterable and temp_fc is not string and temp_fc[1] == 1 %}🌡️ {{temp_fc[0]}}°C{% else %}{% set temp_change = states("sensor.local_forecast_temperaturechange") | float(0) %}{% set current_temp = states("sensor.local_forecast_temperature") | float(0) %}{% set st = state_attr("sensor.local_forecast_zambretti_detail", "second_time") %}{% if st and st is iterable and st is not string %}{% set hours = (st[1] | float(540)) / 60 %}{% else %}{% set hours = 9 %}{% endif %}{% set est_temp = current_temp + (temp_change * hours) %}🌡️ {{est_temp | round(1)}}°C{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[1]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% if rp and rp is iterable and rp is not string %}
            {% set rain = rp[1] | int(0) %}
            {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_zambretti_detail
  
  # Divider
  - type: custom:mushroom-template-card
    primary: ''
    icon: mdi:dots-horizontal
    icon_color: grey
    card_mod:
      style: |
        ha-card {
          box-shadow: none;
          margin: -16px 0;
        }
  
  # Negretti-Zambra Forecast Row (Current + 6h + 12h with times)
  - type: custom:mushroom-title-card
    title: 'Negretti-Zambra Forecast'
    subtitle: |
      {% set fc = state_attr("sensor.local_forecast", "forecast_neg_zam") %}
      {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading...{% endif %}
  
  - type: horizontal-stack
    cards:
      # Current - Negretti-Zambra
      - type: custom:mushroom-template-card
        primary: 'Teraz'
        secondary: |
          {% set fc = state_attr("sensor.local_forecast", "forecast_neg_zam") %}
          {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading{% endif %}
          {{states("sensor.local_forecast_temperature")}}°C
          {{states("sensor.local_forecast_pressure")}} hPa
        icon: |
          {% set icons = state_attr("sensor.local_forecast_neg_zam_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: purple
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast
      
      # 6h forecast with calculated time
      - type: custom:mushroom-template-card
        primary: |
          {% set ft = state_attr("sensor.local_forecast_neg_zam_detail", "first_time") %}
          {% if ft and ft is iterable and ft is not string %}{{ft[0]}}{% else %}~6h{% endif %}
        secondary: |
          {% set rp = state_attr("sensor.local_forecast_neg_zam_detail", "rain_prob") %}
          {% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if rp and rp is iterable and rp is not string %}☔ {{rp[0]}}%{% else %}☔ ?%{% endif %}
          {% if temp_fc and temp_fc is iterable and temp_fc is not string and temp_fc[1] == 0 %}🌡️ {{temp_fc[0]}}°C{% else %}{% set temp_change = states("sensor.local_forecast_temperaturechange") | float(0) %}{% set current_temp = states("sensor.local_forecast_temperature") | float(0) %}{% set ft = state_attr("sensor.local_forecast_neg_zam_detail", "first_time") %}{% if ft and ft is iterable and ft is not string %}{% set hours = (ft[1] | float(180)) / 60 %}{% else %}{% set hours = 3 %}{% endif %}{% set est_temp = current_temp + (temp_change * hours) %}🌡️ {{est_temp | round(1)}}°C{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_neg_zam_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set rp = state_attr("sensor.local_forecast_neg_zam_detail", "rain_prob") %}
          {% if rp and rp is iterable and rp is not string %}
            {% set rain = rp[0] | int(0) %}
            {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
          {% else %}purple{% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_neg_zam_detail
      
      # 12h forecast with calculated time
      - type: custom:mushroom-template-card
        primary: |
          {% set st = state_attr("sensor.local_forecast_neg_zam_detail", "second_time") %}
          {% if st and st is iterable and st is not string %}{{st[0]}}{% else %}~12h{% endif %}
        secondary: |
          {% set rp = state_attr("sensor.local_forecast_neg_zam_detail", "rain_prob") %}
          {% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if rp and rp is iterable and rp is not string %}☔ {{rp[1]}}%{% else %}☔ ?%{% endif %}
          {% if temp_fc and temp_fc is iterable and temp_fc is not string and temp_fc[1] == 1 %}🌡️ {{temp_fc[0]}}°C{% else %}{% set temp_change = states("sensor.local_forecast_temperaturechange") | float(0) %}{% set current_temp = states("sensor.local_forecast_temperature") | float(0) %}{% set st = state_attr("sensor.local_forecast_neg_zam_detail", "second_time") %}{% if st and st is iterable and st is not string %}{% set hours = (st[1] | float(540)) / 60 %}{% else %}{% set hours = 9 %}{% endif %}{% set est_temp = current_temp + (temp_change * hours) %}🌡️ {{est_temp | round(1)}}°C{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_neg_zam_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[1]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set rp = state_attr("sensor.local_forecast_neg_zam_detail", "rain_prob") %}
          {% if rp and rp is iterable and rp is not string %}
            {% set rain = rp[1] | int(0) %}
            {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
          {% else %}purple{% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_neg_zam_detail
  
  # Pressure trend chips at the bottom
  - type: custom:mushroom-chips-card
    alignment: center
    chips:
      - type: template
        icon: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 0 %}mdi:trending-up
          {% elif change < 0 %}mdi:trending-down
          {% else %}mdi:trending-neutral
          {% endif %}
        content: '{{states("sensor.local_forecast_pressurechange")}} hPa/3h'
        icon_color: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 2 %}green
          {% elif change < -2 %}red
          {% else %}grey
          {% endif %}
        tap_action:
          action: more-info
          entity: sensor.local_forecast_pressure
      - type: template
        icon: |
          {% set change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% if change > 0 %}mdi:thermometer-chevron-up
          {% elif change < 0 %}mdi:thermometer-chevron-down
          {% else %}mdi:thermometer-lines
          {% endif %}
        content: '{{states("sensor.local_forecast_temperaturechange")}}°C/h'
        icon_color: |
          {% set change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% if change > 1 %}red
          {% elif change < -1 %}blue
          {% else %}grey
          {% endif %}
        tap_action:
          action: more-info
          entity: sensor.local_forecast_temperature
```

---

## 📱 Compact Mobile Card

```yaml
type: custom:mushroom-template-card
primary: |
  {% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
  {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading forecast...{% endif %}
secondary: |
  {{states("sensor.local_forecast_temperature")}}°C | {{states("sensor.local_forecast_pressure")}} hPa
  {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
  {% if rp and rp is iterable and rp is not string %}Rain: {{rp[0]}}% (6h) | {{rp[1]}}% (12h){% else %}Rain: ?% (6h) | ?% (12h){% endif %}
icon: |
  {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
  {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
icon_color: |
  {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
  {% if rp and rp is iterable and rp is not string %}
    {% set rain = rp[0] | int(0) %}
    {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
  {% else %}green{% endif %}
multiline_secondary: true
tap_action:
  action: more-info
  entity: sensor.local_forecast
```

---

## 🎯 Mini Card (Sidebar/Badge)

```yaml
type: custom:mushroom-template-card
primary: '{{states("sensor.local_forecast_temperature")}}°C'
secondary: |
  {% set st = state_attr("sensor.local_forecast", "forecast_short_term") %}
  {% if st and st is iterable and st is not string %}{{st[0]}}{% else %}Loading...{% endif %}
icon: |
  {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
  {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
icon_color: blue
layout: horizontal
tap_action:
  action: more-info
  entity: sensor.local_forecast
```

---

## 📊 Comparison Card (Both Forecast Models)

```yaml
type: custom:vertical-stack-in-card
cards:
  - type: custom:mushroom-title-card
    title: 'Forecast Comparison'
  
  - type: horizontal-stack
    cards:
      # Zambretti
      - type: custom:mushroom-template-card
        primary: 'Zambretti'
        secondary: |
          {% set fc = state_attr("sensor.local_forecast", "forecast_zambretti") %}
          {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading...{% endif %}
          {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% if rp and rp is iterable and rp is not string %}Rain: {{rp[0]}}%{% else %}Rain: ?%{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: blue
        layout: vertical
        multiline_secondary: true
      
      # Negretti-Zambra
      - type: custom:mushroom-template-card
        primary: 'Negretti-Zambra'
        secondary: |
          {% set fc = state_attr("sensor.local_forecast", "forecast_neg_zam") %}
          {% if fc and fc is iterable and fc is not string %}{{fc[0]}}{% else %}Loading...{% endif %}
          {% set rp = state_attr("sensor.local_forecast_neg_zam_detail", "rain_prob") %}
          {% if rp and rp is iterable and rp is not string %}Rain: {{rp[0]}}%{% else %}Rain: ?%{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_neg_zam_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: purple
        layout: vertical
        multiline_secondary: true
```

---

## 🛠️ Installation Steps

### 1. Install Custom Cards (for Mushroom examples):

**Via HACS:**
1. Open HACS → Frontend
2. Search "Mushroom"
3. Install "Mushroom Cards"
4. Search "Vertical Stack In Card"
5. Install it
6. Restart Home Assistant

**Manual:**
```bash
# Download and place in www/community/
# Add to resources in Lovelace
```

### 2. Add Card to Dashboard:

1. Edit Dashboard
2. Add Card → Manual
3. Paste one of the YAML configs above
4. Save

### 3. Customize:

- Change colors (`icon_color`)
- Adjust thresholds (rain %, pressure)
- Add/remove sections
- Change icons (`mdi:*`)

---

## 💡 Tips

### Dynamic Icons Based on Conditions:
```yaml
icon: |
  {% set pressure = states("sensor.local_forecast_pressure") | float(1013) %}
  {% if pressure < 1000 %}mdi:weather-pouring
  {% elif pressure < 1010 %}mdi:weather-rainy
  {% elif pressure < 1020 %}mdi:weather-partly-cloudy
  {% else %}mdi:weather-sunny
  {% endif %}
```

### Color Based on Pressure Trend:
```yaml
icon_color: |
  {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
  {% if change > 3 %}green
  {% elif change > 1 %}lime
  {% elif change > -1 %}grey
  {% elif change > -3 %}orange
  {% else %}red
  {% endif %}
```

### Rain Probability Warning:
```yaml
secondary: |
  {% set rp = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
  {% if rp and rp is iterable and rp is not string %}
    {% set rain = rp[0] | int(0) %}
    {% if rain > 70 %}⚠️ High rain chance!
    {% elif rain > 40 %}☔ Possible rain
    {% else %}✅ Low rain chance
    {% endif %}
    {{rain}}% in 6h
  {% else %}
    Rain data unavailable
  {% endif %}
```

### Using Forecast States Directly:
```yaml
# Access forecast states (0-6: sunny, partly cloudy, partly rainy, cloudy, rainy, pouring, lightning)
{% set forecast_states = state_attr("sensor.local_forecast_zambretti_detail", "forecast") %}
{% if forecast_states and forecast_states is iterable and forecast_states is not string %}
  {% set state_6h = forecast_states[0] %}
  {% set state_12h = forecast_states[1] %}
  {% if state_6h >= 4 %}
    ☔ Expect rain in 6h
  {% endif %}
{% endif %}
```

### Display Forecast Timing:
```yaml
# Show exact time and minutes to forecast
{% set first_time = state_attr("sensor.local_forecast_zambretti_detail", "first_time") %}
{% if first_time and first_time is iterable and first_time is not string %}
  Next change at {{first_time[0]}} (in {{first_time[1] | round(0)}} min)
{% endif %}
```

### Using Temperature Forecast:
```yaml
# Display short-term temperature prediction
{% set temp_fc = state_attr("sensor.local_forecast", "forecast_temp_short") %}
{% if temp_fc and temp_fc is iterable and temp_fc is not string %}
  {% if temp_fc[1] == 0 %}
    Expected temp in 6h: {{temp_fc[0]}}°C
  {% elif temp_fc[1] == 1 %}
    Expected temp in 12h: {{temp_fc[0]}}°C
  {% endif %}
{% endif %}
```

---

## 📸 Card Preview Ideas

### Weather Station Style:
```yaml
# Large numbers, minimal text
primary: '{{states("sensor.local_forecast_pressure")}} hPa'
secondary: '{{states("sensor.local_forecast_temperature")}}°C'
```

### Forecast Timeline:
```yaml
# Show progression: Now → 6h → 12h
horizontal-stack with 3 cards showing timeline
```

### Alarm Style:
```yaml
# Red/Yellow/Green based on conditions
Use conditional cards for severe weather
```

---

## 🎨 Example: Full Dashboard Section

```yaml
# Add to your dashboard
views:
  - title: Weather
    cards:
      # Main forecast
      - type: custom:vertical-stack-in-card
        cards:
          # ... (use Advanced Mushroom Card from above)
      
      # Pressure graph (if you have history)
      - type: history-graph
        entities:
          - entity: sensor.local_forecast_pressure
        hours_to_show: 24
      
      # Temperature graph
      - type: history-graph
        entities:
          - entity: sensor.local_forecast_temperature
        hours_to_show: 24
```

---

**Choose based on your needs:**
- 🎯 **Simple**: Entities Card
- 🎨 **Beautiful**: Basic Mushroom Card
- 🌟 **Full Featured**: Advanced Mushroom Card
- 📱 **Mobile**: Compact Card
- 📊 **Compare**: Comparison Card








