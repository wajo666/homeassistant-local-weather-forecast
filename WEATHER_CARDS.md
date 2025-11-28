# Weather Card Examples

## 📋 Entity IDs Reference

After installation, your sensors will have these entity IDs:
- **Main Forecast:** `sensor.local_weather_forecast_local_forecast`
- **Pressure:** `sensor.local_weather_forecast_pressure`
- **Temperature:** `sensor.local_weather_forecast_temperature`
- **Pressure Change:** `sensor.local_weather_forecast_pressure_change`
- **Temperature Change:** `sensor.local_weather_forecast_temperature_change`
- **Zambretti Details:** `sensor.local_weather_forecast_zambretti_detail`
- **Negretti-Zambra Details:** `sensor.local_weather_forecast_neg_zam_detail`

---

## 📋 Simple Entities Card (No custom cards needed)

```yaml
type: entities
title: Local Weather Forecast
entities:
  - entity: sensor.local_weather_forecast_local_forecast
    name: Forecast
  - type: attribute
    entity: sensor.local_weather_forecast_local_forecast
    attribute: forecast_short_term
    name: Current Conditions
  - entity: sensor.local_weather_forecast_pressure
    name: Sea Level Pressure
  - entity: sensor.local_weather_forecast_temperature
    name: Temperature
  - entity: sensor.local_weather_forecast_pressure_change
    name: Pressure Trend (3h)
  - type: attribute
    entity: sensor.local_weather_forecast_local_forecast
    attribute: forecast_zambretti
    name: Zambretti Forecast
  - type: attribute
    entity: sensor.local_weather_forecast_local_forecast
    attribute: forecast_pressure_trend
    name: Pressure Status
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
      {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti") %}
      {% if fc %}{{fc.split(', ')[0]}}{% else %}Weather Forecast{% endif %}
    subtitle: 'Local Weather Forecast'
  
  # Current conditions + Next 6h + Next 12h
  - type: horizontal-stack
    cards:
      # Current
      - type: custom:mushroom-template-card
        primary: "Now"
        secondary: |
          {% set st = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_short_term") %}
          {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti") %}
          {% if st %}{{st.split(', ')[0]}}{% endif %}
          {{states("sensor.local_weather_forecast_temperature")}}°C
          {% if fc %}→ {{fc.split(', ')[0]}}{% endif %}
        icon: mdi:weather-cloudy-clock
        icon_color: blue
        layout: vertical
        multiline_secondary: true
      
      # ~6 hours
      - type: custom:mushroom-template-card
        primary: "~6h"
        secondary: |
          {% set det = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_change = states("sensor.local_weather_forecast_temperature_change") | float(0) %}
          {% set current_temp = states("sensor.local_weather_forecast_temperature") | float(0) %}
          {% set est_temp = current_temp + (temp_change * 6) %}
          {% if det and ', ' in det %}{{det.split(', ')[0]}}% rain{% else %}?% rain{% endif %}
          {% if temp_change > 0.1 %}↗ ~{{est_temp | round(1)}}°C{% elif temp_change < -0.1 %}↘ ~{{est_temp | round(1)}}°C{% else %}→ ~{{est_temp | round(1)}}°C{% endif %}
        icon: |
          {% set det = state_attr("sensor.local_weather_forecast_zambretti_detail", "icons") %}
          {% if det and ', ' in det %}{{det.split(', ')[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: amber
        layout: vertical
        multiline_secondary: true
      
      # ~12 hours
      - type: custom:mushroom-template-card
        primary: "~12h"
        secondary: |
          {% set det = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_change = states("sensor.local_weather_forecast_temperature_change") | float(0) %}
          {% set current_temp = states("sensor.local_weather_forecast_temperature") | float(0) %}
          {% set est_temp = current_temp + (temp_change * 12) %}
          {% if det and ', ' in det %}{{det.split(', ')[1]}}% rain{% else %}?% rain{% endif %}
          {% if temp_change > 0.1 %}↗ ~{{est_temp | round(1)}}°C{% elif temp_change < -0.1 %}↘ ~{{est_temp | round(1)}}°C{% else %}→ ~{{est_temp | round(1)}}°C{% endif %}
        icon: |
          {% set det = state_attr("sensor.local_weather_forecast_zambretti_detail", "icons") %}
          {% if det and ', ' in det %}{{det.split(', ')[1]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: orange
        layout: vertical
        multiline_secondary: true
  
  # Detailed forecast text
  - type: custom:mushroom-template-card
    primary: |
      {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti") %}
      {% if fc %}{{fc.split(', ')[0]}}{% else %}Loading forecast...{% endif %}
    secondary: |
      {% set pt = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_pressure_trend") %}
      {% if pt %}Pressure: {{pt.split(', ')[0]}}{% else %}Pressure: ...{% endif %}
      Change: {{states("sensor.local_weather_forecast_pressure_change")}} hPa/3h
    icon: mdi:weather-cloudy-arrow-right
    icon_color: grey
    multiline_secondary: true
  
  # Pressure details
  - type: custom:mushroom-chips-card
    chips:
      - type: template
        icon: mdi:gauge
        content: '{{states("sensor.local_weather_forecast_pressure")}} hPa'
      - type: template
        icon: mdi:thermometer
        content: '{{states("sensor.local_weather_forecast_temperature")}}°C'
      - type: template
        icon: |
          {% set change = states("sensor.local_weather_forecast_pressure_change") | float(0) %}
          {% if change > 0 %}mdi:trending-up
          {% elif change < 0 %}mdi:trending-down
          {% else %}mdi:trending-neutral
          {% endif %}
        content: '{{states("sensor.local_weather_forecast_pressure_change")}} hPa'
        icon_color: |
          {% set change = states("sensor.local_weather_forecast_pressure_change") | float(0) %}
          {% if change > 2 %}green
          {% elif change < -2 %}red
          {% else %}grey
          {% endif %}
      - type: template
        icon: |
          {% set change = states("sensor.local_weather_forecast_temperature_change") | float(0) %}
          {% if change > 0 %}mdi:thermometer-chevron-up
          {% elif change < 0 %}mdi:thermometer-chevron-down
          {% else %}mdi:thermometer-lines
          {% endif %}
        content: '{{states("sensor.local_weather_forecast_temperature_change")}}°C'
        icon_color: |
          {% set change = states("sensor.local_weather_forecast_temperature_change") | float(0) %}
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
      {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti") %}
      {% if fc %}{{fc.split(', ')[0]}}{% else %}Loading...{% endif %}
  
  # Main info row
  - type: horizontal-stack
    cards:
      # Current conditions
      - type: custom:mushroom-template-card
        primary: 'Now'
        secondary: |
          {% set st = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_short_term") %}
          {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti") %}
          {% if st %}{{st.split(', ')[0]}}{% endif %} ({{states("sensor.local_weather_forecast_temperature")}}°C)
          {% if fc %}→ {{fc.split(', ')[0]}}{% endif %}
        icon: mdi:weather-cloudy-clock
        icon_color: |
          {% set pressure = states("sensor.local_weather_forecast_pressure") | float(1013) %}
          {% if pressure < 1000 %}red
          {% elif pressure < 1020 %}amber
          {% else %}green
          {% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_weather_forecast_local_forecast
      
      # 6h forecast
      - type: custom:mushroom-template-card
        primary: '~6h'
        secondary: |
          {% set rp = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_change = states("sensor.local_weather_forecast_temperature_change") | float(0) %}
          {% set current_temp = states("sensor.local_weather_forecast_temperature") | float(0) %}
          {% set est_temp = current_temp + (temp_change * 6) %}
          {% if rp and ', ' in rp %}☔ {{rp.split(', ')[0]}}% rain{% else %}☔ ?%{% endif %}
          {% if temp_change > 0.1 %}🌡️ ↗ ~{{est_temp | round(1)}}°C{% elif temp_change < -0.1 %}🌡️ ↘ ~{{est_temp | round(1)}}°C{% else %}🌡️ → ~{{est_temp | round(1)}}°C{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_weather_forecast_zambretti_detail", "icons") %}
          {% if icons and ', ' in icons %}{{icons.split(', ')[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set rp = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
          {% if rp and ', ' in rp %}
            {% set rain = rp.split(', ')[0] | int(0) %}
            {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
      
      # 12h forecast
      - type: custom:mushroom-template-card
        primary: '~12h'
        secondary: |
          {% set rp = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
          {% set temp_change = states("sensor.local_weather_forecast_temperature_change") | float(0) %}
          {% set current_temp = states("sensor.local_weather_forecast_temperature") | float(0) %}
          {% set est_temp = current_temp + (temp_change * 12) %}
          {% if rp and ', ' in rp %}☔ {{rp.split(', ')[1]}}% rain{% else %}☔ ?%{% endif %}
          {% if temp_change > 0.1 %}🌡️ ↗ ~{{est_temp | round(1)}}°C{% elif temp_change < -0.1 %}🌡️ ↘ ~{{est_temp | round(1)}}°C{% else %}🌡️ → ~{{est_temp | round(1)}}°C{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_weather_forecast_zambretti_detail", "icons") %}
          {% if icons and ', ' in icons %}{{icons.split(', ')[1]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: |
          {% set rp = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
          {% if rp and ', ' in rp %}
            {% set rain = rp.split(', ')[1] | int(0) %}
            {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
  
  # Forecast text
  - type: custom:mushroom-template-card
    primary: |
      {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti") %}
      {% if fc %}{{fc.split(', ')[0]}}{% else %}Loading forecast...{% endif %}
    secondary: |
      {% set pt = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_pressure_trend") %}
      {% if pt %}Pressure {{pt.split(', ')[0]}}{% else %}Pressure ...{% endif %}
      {{states("sensor.local_weather_forecast_pressure_change")}} hPa in 3h
    icon: mdi:weather-cloudy-arrow-right
    icon_color: grey
    multiline_secondary: true
  
  # Metrics chips
  - type: custom:mushroom-chips-card
    alignment: center
    chips:
      - type: template
        icon: mdi:gauge
        content: '{{states("sensor.local_weather_forecast_pressure")}} hPa'
        tap_action:
          action: more-info
          entity: sensor.local_weather_forecast_pressure
      - type: template
        icon: mdi:thermometer
        content: '{{states("sensor.local_weather_forecast_temperature")}}°C'
        tap_action:
          action: more-info
          entity: sensor.local_weather_forecast_temperature
      - type: template
        icon: |
          {% set change = states("sensor.local_weather_forecast_pressure_change") | float(0) %}
          {% if change > 0 %}mdi:trending-up
          {% elif change < 0 %}mdi:trending-down
          {% else %}mdi:trending-neutral
          {% endif %}
        content: '{{states("sensor.local_weather_forecast_pressure_change")}} hPa'
        icon_color: |
          {% set change = states("sensor.local_weather_forecast_pressure_change") | float(0) %}
          {% if change > 2 %}green
          {% elif change < -2 %}red
          {% else %}grey
          {% endif %}
        tap_action:
          action: more-info
          entity: sensor.local_weather_forecast_pressure_change
      - type: template
        icon: |
          {% set change = states("sensor.local_weather_forecast_temperature_change") | float(0) %}
          {% if change > 0 %}mdi:thermometer-chevron-up
          {% elif change < 0 %}mdi:thermometer-chevron-down
          {% else %}mdi:thermometer-lines
          {% endif %}
        content: '{{states("sensor.local_weather_forecast_temperature_change")}}°C/h'
        icon_color: |
          {% set change = states("sensor.local_weather_forecast_temperature_change") | float(0) %}
          {% if change > 1 %}red
          {% elif change < -1 %}blue
          {% else %}grey
          {% endif %}
        tap_action:
          action: more-info
          entity: sensor.local_weather_forecast_temperature_change
  
  # Alternative forecast model
  - type: custom:mushroom-template-card
    primary: 'Negretti-Zambra Alternative'
    secondary: |
      {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_neg_zam") %}
      {% if fc %}{{fc.split(', ')[0]}}{% else %}Loading...{% endif %}
    icon: mdi:weather-cloudy
    icon_color: purple
    multiline_secondary: true
    tap_action:
      action: more-info
      entity: sensor.local_weather_forecast_neg_zam_detail
```

---

## 📱 Compact Mobile Card

```yaml
type: custom:mushroom-template-card
primary: |
  {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti") %}
  {% if fc %}{{fc.split(', ')[0]}}{% else %}Loading forecast...{% endif %}
secondary: |
  {{states("sensor.local_weather_forecast_temperature")}}°C | {{states("sensor.local_weather_forecast_pressure")}} hPa
  {% set rp = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
  {% if rp and ', ' in rp %}Rain: {{rp.split(', ')[0]}}% (6h) | {{rp.split(', ')[1]}}% (12h){% else %}Rain: ?% (6h) | ?% (12h){% endif %}
icon: |
  {% set icons = state_attr("sensor.local_weather_forecast_zambretti_detail", "icons") %}
  {% if icons and ', ' in icons %}{{icons.split(', ')[0]}}{% else %}mdi:weather-cloudy{% endif %}
icon_color: |
  {% set rp = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
  {% if rp and ', ' in rp %}
    {% set rain = rp.split(', ')[0] | int(0) %}
    {% if rain > 70 %}blue{% elif rain > 40 %}amber{% else %}green{% endif %}
  {% else %}green{% endif %}
multiline_secondary: true
tap_action:
  action: more-info
  entity: sensor.local_weather_forecast_local_forecast
```

---

## 🎯 Mini Card (Sidebar/Badge)

```yaml
type: custom:mushroom-template-card
primary: '{{states("sensor.local_weather_forecast_temperature")}}°C'
secondary: |
  {% set st = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_short_term") %}
  {% if st %}{{st.split(', ')[0]}}{% else %}Loading...{% endif %}
icon: |
  {% set icons = state_attr("sensor.local_weather_forecast_zambretti_detail", "icons") %}
  {% if icons and ', ' in icons %}{{icons.split(', ')[0]}}{% else %}mdi:weather-cloudy{% endif %}
icon_color: blue
layout: horizontal
tap_action:
  action: more-info
  entity: sensor.local_weather_forecast_local_forecast
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
          {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti") %}
          {% if fc %}{{fc.split(', ')[0]}}{% else %}Loading...{% endif %}
          {% set rp = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
          {% if rp and ', ' in rp %}Rain: {{rp.split(', ')[0]}}%{% else %}Rain: ?%{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_weather_forecast_zambretti_detail", "icons") %}
          {% if icons and ', ' in icons %}{{icons.split(', ')[0]}}{% else %}mdi:weather-cloudy{% endif %}
        icon_color: blue
        layout: vertical
        multiline_secondary: true
      
      # Negretti-Zambra
      - type: custom:mushroom-template-card
        primary: 'Negretti-Zambra'
        secondary: |
          {% set fc = state_attr("sensor.local_weather_forecast_local_forecast", "forecast_neg_zam") %}
          {% if fc %}{{fc.split(', ')[0]}}{% else %}Loading...{% endif %}
          {% set rp = state_attr("sensor.local_weather_forecast_neg_zam_detail", "rain_prob") %}
          {% if rp and ', ' in rp %}Rain: {{rp.split(', ')[0]}}%{% else %}Rain: ?%{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_weather_forecast_neg_zam_detail", "icons") %}
          {% if icons and ', ' in icons %}{{icons.split(', ')[0]}}{% else %}mdi:weather-cloudy{% endif %}
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
  {% set pressure = states("sensor.local_weather_forecast_pressure") | float(1013) %}
  {% if pressure < 1000 %}mdi:weather-pouring
  {% elif pressure < 1010 %}mdi:weather-rainy
  {% elif pressure < 1020 %}mdi:weather-partly-cloudy
  {% else %}mdi:weather-sunny
  {% endif %}
```

### Color Based on Pressure Trend:
```yaml
icon_color: |
  {% set change = states("sensor.local_weather_forecast_pressure_change") | float(0) %}
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
  {% set rp = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob") %}
  {% if rp and ', ' in rp %}
    {% set rain = rp.split(', ')[0] | int(0) %}
    {% if rain > 70 %}⚠️ High rain chance!
    {% elif rain > 40 %}☔ Possible rain
    {% else %}✅ Low rain chance
    {% endif %}
    {{rain}}% in 6h
  {% else %}
    Rain data unavailable
  {% endif %}
```

---

## 📸 Card Preview Ideas

### Weather Station Style:
```yaml
# Large numbers, minimal text
primary: '{{states("sensor.local_weather_forecast_pressure")}} hPa'
secondary: '{{states("sensor.local_weather_forecast_temperature")}}°C'
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
          - entity: sensor.local_weather_forecast_pressure
        hours_to_show: 24
      
      # Temperature graph
      - type: history-graph
        entities:
          - entity: sensor.local_weather_forecast_temperature
        hours_to_show: 24
```

---

**Choose based on your needs:**
- 🎯 **Simple**: Entities Card
- 🎨 **Beautiful**: Basic Mushroom Card
- 🌟 **Full Featured**: Advanced Mushroom Card
- 📱 **Mobile**: Compact Card
- 📊 **Compare**: Comparison Card

