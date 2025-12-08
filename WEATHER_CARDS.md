# Weather Card Examples for Lovelace UI

**📦 Version:** v3.1.0 (2025-12-08)  
**🎨 Purpose:** Lovelace UI card examples for Local Weather Forecast integration

---

## 📋 Quick Start: Available Sensors

Use these entity IDs in your Lovelace cards:

**Main Sensors:**
- `sensor.local_forecast` - Forecast text
- `sensor.local_forecast_enhanced` - Enhanced forecast with fog/stability
- `sensor.local_forecast_rain_probability` - Rain probability
- `weather.local_weather_forecast_weather` - Weather entity

**Supporting Sensors:**
- `sensor.local_forecast_pressure` - Pressure
- `sensor.local_forecast_temperature` - Temperature
- `sensor.local_forecast_pressurechange` - Pressure trend
- `sensor.local_forecast_temperaturechange` - Temperature trend

---

## 💡 Template Tips

**Array attributes** (use `[index]` to access):
```yaml
{{ state_attr("sensor.local_forecast", "forecast_zambretti")[0] }}  # "Fine Weather!"
{{ state_attr("sensor.local_forecast_enhanced", "dew_point") }}  # 5.02
```

---

## 📋 Card 1: Simple Entities Card

**No custom cards needed!**

```yaml
type: entities
title: Local Weather Forecast
entities:
  - entity: sensor.local_forecast
    name: Forecast
  - entity: sensor.local_forecast_enhanced
    name: Enhanced Forecast
  - entity: sensor.local_forecast_pressure
    name: Pressure
  - entity: sensor.local_forecast_temperature
    name: Temperature
  - entity: sensor.local_forecast_rain_probability
    name: Rain Probability
```

---

## 🎨 Card 2: Mushroom Cards (Beautiful UI)

**Requirements:** Install via HACS:
- [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom)
- [Vertical Stack In Card](https://github.com/ofekashery/vertical-stack-in-card)

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
  
  # Current conditions
  - type: horizontal-stack
    cards:
      # Now
      - type: custom:mushroom-template-card
        primary: "Now"
        secondary: |
          {% set st = state_attr("sensor.local_forecast", "forecast_short_term") %}
          {{states("sensor.local_forecast_temperature")}}°C
          {% if st and st is iterable and st is not string %}{{st[0]}}{% endif %}
        icon: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if det and det is iterable and det is not string %}{{det[0]}}{% else %}mdi:weather-partly-cloudy{% endif %}
        icon_color: blue
        layout: vertical
        tap_action:
          action: more-info
          entity: sensor.local_forecast
      
      # Next 6h
      - type: custom:mushroom-template-card
        primary: "6h"
        secondary: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% if det and det is iterable and det is not string %}{{det[0]}}% rain{% else %}N/A{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:help{% endif %}
        icon_color: orange
        layout: vertical
      
      # Next 12h
      - type: custom:mushroom-template-card
        primary: "12h"
        secondary: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% if det and det is iterable and det is not string %}{{det[1]}}% rain{% else %}N/A{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[1]}}{% else %}mdi:help{% endif %}
        icon_color: green
        layout: vertical
  
  # Pressure & Temperature trends
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: sensor.local_forecast_pressure
        name: Pressure
        icon: mdi:gauge
      
      - type: custom:mushroom-entity-card
        entity: sensor.local_forecast_pressurechange
        name: Trend (3h)
        icon: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 0.5 %}mdi:trending-up
          {% elif change < -0.5 %}mdi:trending-down
          {% else %}mdi:trending-neutral{% endif %}
```

---

## 🌟 Card 3: Advanced Mushroom Card (v3.1.0 Enhanced Features)

```yaml
type: custom:vertical-stack-in-card
cards:
  # Title
  - type: custom:mushroom-title-card
    title: Weather Forecast v3.1.0
    subtitle: 'Enhanced with Fog Risk & Stability'
  
  # Main forecast card
  - type: custom:mushroom-template-card
    primary: |
      {{states("sensor.local_forecast_enhanced")}}
    secondary: |
      Confidence: {{state_attr("sensor.local_forecast_enhanced", "confidence") | capitalize}}
      Rain: {{states("sensor.local_forecast_rain_probability")}}%
    icon: |
      {% set condition = states("weather.local_weather_forecast_weather") %}
      {% if condition == "sunny" %}mdi:weather-sunny
      {% elif condition == "cloudy" %}mdi:weather-cloudy
      {% elif condition == "rainy" %}mdi:weather-rainy
      {% elif condition == "fog" %}mdi:weather-fog
      {% else %}mdi:weather-partly-cloudy{% endif %}
    icon_color: |
      {% set rain = states("sensor.local_forecast_rain_probability") | int(0) %}
      {% if rain > 70 %}red
      {% elif rain > 40 %}orange
      {% elif rain > 20 %}yellow
      {% else %}blue{% endif %}
    multiline_secondary: true
    tap_action:
      action: more-info
      entity: weather.local_weather_forecast_weather
  
  # Fog Risk & Dew Point
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Fog Risk
        secondary: |
          {{state_attr("sensor.local_forecast_enhanced", "fog_risk") | capitalize}}
        icon: mdi:weather-fog
        icon_color: |
          {% set fog = state_attr("sensor.local_forecast_enhanced", "fog_risk") %}
          {% if fog == "critical" %}red
          {% elif fog == "high" %}orange
          {% elif fog == "medium" %}yellow
          {% elif fog == "low" %}blue
          {% else %}green{% endif %}
        layout: vertical
      
      - type: custom:mushroom-template-card
        primary: Dew Point
        secondary: |
          {{state_attr("sensor.local_forecast_enhanced", "dew_point")}}°C
          Spread: {{state_attr("sensor.local_forecast_enhanced", "dewpoint_spread")}}°C
        icon: mdi:water-thermometer
        icon_color: cyan
        layout: vertical
  
  # Wind Classification
  - type: custom:mushroom-template-card
    primary: |
      🌬️ {{state_attr("sensor.local_forecast_enhanced", "wind_type") | default("Unknown")}}
    secondary: |
      Beaufort: {{state_attr("sensor.local_forecast_enhanced", "wind_beaufort_scale")}}/12
      Speed: {{state_attr("sensor.local_forecast_enhanced", "wind_speed")}} m/s
      {% set gust = state_attr("sensor.local_forecast_enhanced", "wind_gust") %}
      {% if gust %}Gusts: {{gust}} m/s{% endif %}
    icon: mdi:weather-windy-variant
    icon_color: |
      {% set beaufort = state_attr("sensor.local_forecast_enhanced", "wind_beaufort_scale") | int(0) %}
      {% if beaufort >= 8 %}red
      {% elif beaufort >= 6 %}orange
      {% elif beaufort >= 3 %}yellow
      {% else %}green{% endif %}
    multiline_secondary: true
  
  # Atmospheric Stability
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Stability
        secondary: |
          {% set stability = state_attr("sensor.local_forecast_enhanced", "atmosphere_stability") %}
          {% if stability == "stable" %}Stable
          {% elif stability == "moderate" %}Moderate
          {% elif stability == "unstable" %}Unstable
          {% elif stability == "very_unstable" %}Very Unstable
          {% else %}Unknown{% endif %}
        icon: mdi:weather-partly-cloudy
        icon_color: |
          {% set stability = state_attr("sensor.local_forecast_enhanced", "atmosphere_stability") %}
          {% if stability == "very_unstable" %}red
          {% elif stability == "unstable" %}orange
          {% elif stability == "moderate" %}yellow
          {% else %}green{% endif %}
        layout: vertical
      
      - type: custom:mushroom-template-card
        primary: Gust Ratio
        secondary: |
          {{state_attr("sensor.local_forecast_enhanced", "gust_ratio") | default("N/A")}}
        icon: mdi:chart-line
        icon_color: purple
        layout: vertical
```

---

## 📱 Card 4: Compact Mobile Card

```yaml
type: vertical-stack
cards:
  # Header
  - type: markdown
    content: |
      ## 🌤️ Weather Forecast
      **{{states("sensor.local_forecast")}}**
  
  # Quick Stats
  - type: glance
    entities:
      - entity: sensor.local_forecast_temperature
        name: Temp
      - entity: sensor.local_forecast_pressure
        name: Pressure
      - entity: sensor.local_forecast_rain_probability
        name: Rain %
      - entity: sensor.local_forecast_enhanced
        name: Forecast
    show_state: true
  
  # Trends
  - type: entities
    entities:
      - entity: sensor.local_forecast_pressurechange
        name: Pressure Trend (3h)
        icon: mdi:trending-up
      - entity: sensor.local_forecast_temperaturechange
        name: Temperature Trend (1h)
        icon: mdi:thermometer
```

---

## 📊 Card 5: Comparison Card (Zambretti vs Negretti)

```yaml
type: entities
title: Forecast Comparison
entities:
  - type: section
    label: Zambretti Method
  - entity: sensor.local_forecast_zambretti_detail
    name: Zambretti Forecast
  - type: attribute
    entity: sensor.local_forecast_zambretti_detail
    attribute: rain_prob
    name: Rain Probability (6h / 12h)
  
  - type: section
    label: Negretti-Zambra Method
  - entity: sensor.local_forecast_neg_zam_detail
    name: Negretti Forecast
  - type: attribute
    entity: sensor.local_forecast_neg_zam_detail
    attribute: rain_prob
    name: Rain Probability (6h / 12h)
  
  - type: section
    label: Consensus
  - entity: sensor.local_forecast_enhanced
    name: Enhanced Forecast
  - type: attribute
    entity: sensor.local_forecast_enhanced
    attribute: confidence
    name: Confidence Level
  - type: attribute
    entity: sensor.local_forecast_enhanced
    attribute: consensus
    name: Methods Agree
```

---

## 🌐 Card 6: Weather Entity Card

```yaml
type: weather-forecast
entity: weather.local_weather_forecast_weather
forecast_type: daily
```

**With hourly forecast:**
```yaml
type: weather-forecast
entity: weather.local_weather_forecast_weather
forecast_type: hourly
```

---

## 🎯 Card Selection Guide

| Card Type | Use Case | Complexity | Features |
|-----------|----------|------------|----------|
| **Simple Entities** | Basic info | ⭐ Easy | No custom cards needed |
| **Basic Mushroom** | Nice looking | ⭐⭐ Medium | Current + 6h + 12h forecast |
| **Advanced Mushroom** | Full features | ⭐⭐⭐ Advanced | Fog risk, wind type, stability |
| **Compact Mobile** | Mobile view | ⭐ Easy | Quick stats, small screen |
| **Comparison** | Method details | ⭐⭐ Medium | Compare Zambretti vs Negretti |
| **Weather Entity** | Standard HA | ⭐ Easy | Daily/hourly forecast |

---

## 📚 Additional Resources

- **[README.md](README.md)** - Installation and configuration
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

**Last updated:** 2025-12-08  
**Version:** v3.1.0

