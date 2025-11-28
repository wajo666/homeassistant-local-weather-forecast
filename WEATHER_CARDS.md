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
    title: '{{states("sensor.local_weather_forecast_local_forecast")}}'
    subtitle: 'Local Weather Forecast'
  
  # Current conditions + Next 6h + Next 12h
  - type: horizontal-stack
    cards:
      # Current
      - type: custom:mushroom-template-card
        primary: '{{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_short_term")[0]}}'
        secondary: |
          {{states("sensor.local_weather_forecast_temperature")}}°C
          {{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_short_term")[1]}}
        icon: mdi:weather-cloudy-clock
        icon_color: blue
        layout: vertical
        multiline_secondary: true
      
      # ~6 hours
      - type: custom:mushroom-template-card
        primary: |
          ~{{state_attr("sensor.local_weather_forecast_zambretti_detail", "first_time")[0]}}h
        secondary: |
          Rain: {{state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[0]}}%
        icon: '{{state_attr("sensor.local_weather_forecast_zambretti_detail", "icons")[0]}}'
        icon_color: amber
        layout: vertical
        multiline_secondary: true
      
      # ~12 hours
      - type: custom:mushroom-template-card
        primary: |
          ~{{state_attr("sensor.local_weather_forecast_zambretti_detail", "second_time")[0]}}h
        secondary: |
          Rain: {{state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[1]}}%
        icon: '{{state_attr("sensor.local_weather_forecast_zambretti_detail", "icons")[1]}}'
        icon_color: orange
        layout: vertical
        multiline_secondary: true
  
  # Detailed forecast text
  - type: custom:mushroom-template-card
    primary: '{{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti")[0]}}'
    secondary: |
      Pressure: {{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_pressure_trend")[0]}}
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
        icon: mdi:trending-up
        content: '{{states("sensor.local_weather_forecast_pressure_change")}} hPa'
```

---

## 🌟 Advanced Mushroom Card (Full Featured)

```yaml
type: custom:vertical-stack-in-card
cards:
  # Header with dynamic icon based on forecast
  - type: custom:mushroom-title-card
    title: 'Weather Forecast'
    subtitle: '{{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti")[0]}}'
  
  # Main info row
  - type: horizontal-stack
    cards:
      # Current conditions
      - type: custom:mushroom-template-card
        primary: 'Now'
        secondary: |
          {{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_short_term")[0]}}
          {{states("sensor.local_weather_forecast_temperature")}}°C
        icon: mdi:weather-cloudy-clock
        icon_color: |
          {% set pressure = states("sensor.local_weather_forecast_pressure") | float %}
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
        primary: '6h'
        secondary: |
          {{state_attr("sensor.local_weather_forecast_zambretti_detail", "first_time")[0]}}
          ☔ {{state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[0]}}%
        icon: '{{state_attr("sensor.local_weather_forecast_zambretti_detail", "icons")[0]}}'
        icon_color: |
          {% set rain = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[0] | int %}
          {% if rain > 70 %}blue
          {% elif rain > 40 %}amber
          {% else %}green
          {% endif %}
        layout: vertical
        multiline_secondary: true
      
      # 12h forecast
      - type: custom:mushroom-template-card
        primary: '12h'
        secondary: |
          {{state_attr("sensor.local_weather_forecast_zambretti_detail", "second_time")[0]}}
          ☔ {{state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[1]}}%
        icon: '{{state_attr("sensor.local_weather_forecast_zambretti_detail", "icons")[1]}}'
        icon_color: |
          {% set rain = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[1] | int %}
          {% if rain > 70 %}blue
          {% elif rain > 40 %}amber
          {% else %}green
          {% endif %}
        layout: vertical
        multiline_secondary: true
  
  # Forecast text
  - type: custom:mushroom-template-card
    primary: '{{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti")[0]}}'
    secondary: |
      Pressure {{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_pressure_trend")[0]}}
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
          entity: sensor.local_forecast_pressure
      - type: template
        icon: mdi:thermometer
        content: '{{states("sensor.local_weather_forecast_temperature")}}°C'
        tap_action:
          action: more-info
          entity: sensor.local_forecast_temperature
      - type: template
        icon: |
          {% set change = states("sensor.local_weather_forecast_pressure_change") | float %}
          {% if change > 0 %}mdi:trending-up
          {% elif change < 0 %}mdi:trending-down
          {% else %}mdi:trending-neutral
          {% endif %}
        content: '{{states("sensor.local_weather_forecast_pressure_change")}} hPa'
        icon_color: |
          {% set change = states("sensor.local_weather_forecast_pressure_change") | float %}
          {% if change > 2 %}green
          {% elif change < -2 %}red
          {% else %}grey
          {% endif %}
  
  # Alternative forecast model
  - type: custom:mushroom-template-card
    primary: 'Negretti-Zambra Alternative'
    secondary: '{{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_neg_zam")[0]}}'
    icon: mdi:weather-cloudy
    icon_color: purple
    multiline_secondary: true
    tap_action:
      action: more-info
      entity: sensor.local_forecast_neg_zam_detail
```

---

## 📱 Compact Mobile Card

```yaml
type: custom:mushroom-template-card
primary: '{{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti")[0]}}'
secondary: |
  {{states("sensor.local_weather_forecast_temperature")}}°C | {{states("sensor.local_weather_forecast_pressure")}} hPa
  Rain: {{state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[0]}}% (6h) | {{state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[1]}}% (12h)
icon: '{{state_attr("sensor.local_weather_forecast_zambretti_detail", "icons")[0]}}'
icon_color: |
  {% set rain = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[0] | int %}
  {% if rain > 70 %}blue
  {% elif rain > 40 %}amber
  {% else %}green
  {% endif %}
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
secondary: '{{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_short_term")[0]}}'
icon: '{{state_attr("sensor.local_weather_forecast_zambretti_detail", "icons")[0]}}'
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
          {{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_zambretti")[0]}}
          Rain: {{state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[0]}}%
        icon: '{{state_attr("sensor.local_weather_forecast_zambretti_detail", "icons")[0]}}'
        icon_color: blue
        layout: vertical
        multiline_secondary: true
      
      # Negretti-Zambra
      - type: custom:mushroom-template-card
        primary: 'Negretti-Zambra'
        secondary: |
          {{state_attr("sensor.local_weather_forecast_local_forecast", "forecast_neg_zam")[0]}}
          Rain: {{state_attr("sensor.local_weather_forecast_neg_zam_detail", "rain_prob")[0]}}%
        icon: '{{state_attr("sensor.local_weather_forecast_neg_zam_detail", "icons")[0]}}'
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
  {% set pressure = states("sensor.local_weather_forecast_pressure") | float %}
  {% if pressure < 1000 %}mdi:weather-pouring
  {% elif pressure < 1010 %}mdi:weather-rainy
  {% elif pressure < 1020 %}mdi:weather-partly-cloudy
  {% else %}mdi:weather-sunny
  {% endif %}
```

### Color Based on Pressure Trend:
```yaml
icon_color: |
  {% set change = states("sensor.local_weather_forecast_pressure_change") | float %}
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
  {% set rain = state_attr("sensor.local_weather_forecast_zambretti_detail", "rain_prob")[0] | int %}
  {% if rain > 70 %}⚠️ High rain chance!
  {% elif rain > 40 %}☔ Possible rain
  {% else %}✅ Low rain chance
  {% endif %}
  {{rain}}% in 6h
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

