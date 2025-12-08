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

## 🌟 Card 7: Complete Weather Analysis Dashboard (Slovak)

**Kompletná karta so VŠETKÝMI dostupnými informáciami zorganizovanými do logických celkov**

```yaml
type: custom:vertical-stack-in-card
cards:
  # ========================================================================
  # HLAVIČKA
  # ========================================================================
  - type: custom:mushroom-title-card
    title: Predpoveď počasia v3.1.0
    subtitle: Kompletná atmosférická analýza
  
  # ========================================================================
  # AKTUÁLNE POČASIE A PREDPOVEĎ
  # ========================================================================
  - type: custom:mushroom-template-card
    primary: Aktuálne počasie
    secondary: |
      {{states("weather.local_weather_forecast_weather") | replace('_', ' ') | title}}
      {{state_attr("weather.local_weather_forecast_weather", "temperature")}}°C
      Pocitovo: {{state_attr("weather.local_weather_forecast_weather", "feels_like")}}°C
    icon: |
      {% set condition = states("weather.local_weather_forecast_weather") %}
      {% if condition == "fog" %}mdi:weather-fog
      {% elif condition == "rainy" %}mdi:weather-rainy
      {% elif condition == "pouring" %}mdi:weather-pouring
      {% elif condition == "cloudy" %}mdi:weather-cloudy
      {% elif condition == "partlycloudy" %}mdi:weather-partly-cloudy
      {% elif condition == "sunny" %}mdi:weather-sunny
      {% elif condition == "clear-night" %}mdi:weather-night
      {% else %}mdi:help-circle{% endif %}
    icon_color: |
      {% set condition = states("weather.local_weather_forecast_weather") %}
      {% if condition == "fog" %}grey
      {% elif condition in ["rainy", "pouring"] %}blue
      {% elif condition == "cloudy" %}grey
      {% else %}orange{% endif %}
    multiline_secondary: true
    tap_action:
      action: more-info
      entity: weather.local_weather_forecast_weather
  
  # ========================================================================
  # PREDPOVEĎ ZAMBRETTI A NEGRETTI-ZAMBRA
  # ========================================================================
  - type: custom:mushroom-template-card
    primary: 📊 Predpoveď
    secondary: |
      {{states("sensor.local_forecast_enhanced")}}
      
      Zambretti: {{state_attr("sensor.local_forecast", "forecast_zambretti")[0] if state_attr("sensor.local_forecast", "forecast_zambretti") else "N/A"}}
      Negretti: {{state_attr("sensor.local_forecast", "forecast_neg_zam")[0] if state_attr("sensor.local_forecast", "forecast_neg_zam") else "N/A"}}
    icon: mdi:weather-partly-cloudy
    icon_color: blue
    multiline_secondary: true
    tap_action:
      action: more-info
      entity: sensor.local_forecast_enhanced
  
  # Confidence & Adjustments
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Presnosť
        secondary: |
          Confidence: {{state_attr("sensor.local_forecast_enhanced", "confidence") | capitalize}}
          Accuracy: {{state_attr("sensor.local_forecast_enhanced", "accuracy_estimate")}}
          Consensus: {{state_attr("sensor.local_forecast_enhanced", "consensus")}}
        icon: mdi:check-circle
        icon_color: |
          {% set conf = state_attr("sensor.local_forecast_enhanced", "confidence") %}
          {% if conf == "very_high" %}green
          {% elif conf == "high" %}blue
          {% elif conf == "medium" %}orange
          {% else %}red{% endif %}
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: Úpravy
        secondary: |
          {{state_attr("sensor.local_forecast_enhanced", "adjustment_details") | default("Žiadne úpravy")}}
        icon: mdi:tune
        icon_color: purple
        layout: vertical
        multiline_secondary: true
  
  # ========================================================================
  # DÁŽĎ A ZRÁŽKY
  # ========================================================================
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Pravdepodobnosť dažďa
        secondary: |
          {{states("sensor.local_forecast_rain_probability")}}%
          Confidence: {{state_attr("sensor.local_forecast_rain_probability", "confidence") | capitalize}}
          
          Zambretti: {{state_attr("sensor.local_forecast_rain_probability", "zambretti_probability")}}%
          Negretti: {{state_attr("sensor.local_forecast_rain_probability", "negretti_probability")}}%
        icon: mdi:weather-rainy
        icon_color: |
          {% set prob = states("sensor.local_forecast_rain_probability") | int(0) %}
          {% if prob >= 70 %}red
          {% elif prob >= 40 %}orange
          {% elif prob >= 20 %}yellow
          {% else %}blue{% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_rain_probability
      
      - type: custom:mushroom-template-card
        primary: Aktuálny dážď
        secondary: |
          {% set rain = state_attr("sensor.local_forecast_rain_probability", "current_rain_rate") %}
          {% if rain and rain > 0 %}
            {{rain}} mm/h - Prší!
          {% else %}
            Bez zrážok
          {% endif %}
        icon: mdi:weather-pouring
        icon_color: |
          {% set rain = state_attr("sensor.local_forecast_rain_probability", "current_rain_rate") %}
          {% if rain and rain > 10 %}red
          {% elif rain and rain > 2.5 %}orange
          {% elif rain and rain > 0.1 %}yellow
          {% else %}blue{% endif %}
        layout: vertical
        multiline_secondary: true
  
  # ========================================================================
  # TEPLOTA A TLAK
  # ========================================================================
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Teplota
        secondary: |
          Aktuálna: {{states("sensor.local_forecast_temperature")}}°C
          Trend: {{states("sensor.local_forecast_temperaturechange")}}°C/h
          
          {% set temp_forecast = state_attr("sensor.local_forecast", "forecast_temp_short") %}
          {% if temp_forecast and temp_forecast[0] != "unavailable" %}
          Predpoveď: {{temp_forecast[0]}}°C
          {% endif %}
        icon: mdi:thermometer
        icon_color: |
          {% set temp = states("sensor.local_forecast_temperature") | float(0) %}
          {% if temp > 30 %}red
          {% elif temp > 20 %}orange
          {% elif temp > 10 %}green
          {% elif temp > 0 %}blue
          {% else %}purple{% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_temperature
      
      - type: custom:mushroom-template-card
        primary: Tlak
        secondary: |
          Aktuálny: {{states("sensor.local_forecast_pressure")}} hPa
          Trend: {{states("sensor.local_forecast_pressurechange")}} hPa/3h
          
          {% set trend = state_attr("sensor.local_forecast", "pressure_trend") %}
          {% if trend %}{{trend[0]}}{% endif %}
        icon: mdi:gauge
        icon_color: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 3 %}red
          {% elif change > 1 %}orange
          {% elif change < -3 %}purple
          {% elif change < -1 %}blue
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_pressure
  
  # Badges pre zmenu tlaku a teploty (s trendovými šípkami)
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Zmena teploty
        secondary: |
          {{states("sensor.local_forecast_temperaturechange")}} °C/1h
        icon: |
          {% set change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% if change > 0.5 %}mdi:thermometer-chevron-up
          {% elif change < -0.5 %}mdi:thermometer-chevron-down
          {% else %}mdi:thermometer{% endif %}
        icon_color: |
          {% set change = states("sensor.local_forecast_temperaturechange") | float(0) %}
          {% if change > 2 %}red
          {% elif change > 0.5 %}orange
          {% elif change < -2 %}blue
          {% elif change < -0.5 %}cyan
          {% else %}green{% endif %}
        layout: vertical
        tap_action:
          action: more-info
          entity: sensor.local_forecast_temperaturechange
      
      - type: custom:mushroom-template-card
        primary: Zmena tlaku
        secondary: |
          {{states("sensor.local_forecast_pressurechange")}} hPa/3h
        icon: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 0.5 %}mdi:trending-up
          {% elif change < -0.5 %}mdi:trending-down
          {% else %}mdi:trending-neutral{% endif %}
        icon_color: |
          {% set change = states("sensor.local_forecast_pressurechange") | float(0) %}
          {% if change > 3 %}red
          {% elif change > 1 %}orange
          {% elif change < -3 %}purple
          {% elif change < -1 %}blue
          {% else %}green{% endif %}
        layout: vertical
        tap_action:
          action: more-info
          entity: sensor.local_forecast_pressurechange
  
  # ========================================================================
  # VIETOR A ATMOSFÉRICKÁ STABILITA
  # ========================================================================
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: |
          🌬️ {{state_attr("sensor.local_forecast_enhanced", "wind_type") | default("Vietor")}}
        secondary: |
          Beaufort: {{state_attr("sensor.local_forecast_enhanced", "wind_beaufort_scale") | default(0)}}/12
          Rýchlosť: {{state_attr("sensor.local_forecast_enhanced", "wind_speed") | default(0)}} m/s
          {% set gust = state_attr("sensor.local_forecast_enhanced", "wind_gust") %}
          {% if gust %}Nárazy: {{gust}} m/s{% endif %}
          
          {% set bearing = state_attr("weather.local_weather_forecast_weather", "wind_bearing") %}
          {% if bearing %}Smer: {{bearing}}°{% endif %}
        icon: mdi:weather-windy
        icon_color: |
          {% set beaufort = state_attr("sensor.local_forecast_enhanced", "wind_beaufort_scale") | int(0) %}
          {% if beaufort >= 8 %}red
          {% elif beaufort >= 6 %}orange
          {% elif beaufort >= 4 %}yellow
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: Stabilita atmosféry
        secondary: |
          {% set stability = state_attr("sensor.local_forecast_enhanced", "atmosphere_stability") %}
          {% if stability == "stable" %}✅ Stabilná
          {% elif stability == "moderate" %}⚠️ Mierne nestabilná
          {% elif stability == "unstable" %}⚠️ Nestabilná
          {% elif stability == "very_unstable" %}🌪️ Veľmi nestabilná
          {% else %}Neznáma{% endif %}
          
          {% set ratio = state_attr("sensor.local_forecast_enhanced", "gust_ratio") %}
          {% if ratio %}Gust ratio: {{ratio}}{% endif %}
        icon: mdi:weather-tornado
        icon_color: |
          {% set stability = state_attr("sensor.local_forecast_enhanced", "atmosphere_stability") %}
          {% if stability == "very_unstable" %}red
          {% elif stability == "unstable" %}orange
          {% elif stability == "moderate" %}yellow
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
  
  # ========================================================================
  # HMLA A VIDITEĽNOSŤ
  # ========================================================================
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: |
          {% set fog = state_attr("sensor.local_forecast_enhanced", "fog_risk") %}
          {% if fog == "critical" %}🚨 KRITICKÁ HMLA
          {% elif fog == "high" %}⚠️ Vysoké riziko
          {% elif fog == "medium" %}⚡ Stredné riziko
          {% elif fog == "low" %}💡 Nízke riziko
          {% else %}✅ Žiadne riziko{% endif %}
        secondary: |
          Rosný bod: {{state_attr("sensor.local_forecast_enhanced", "dew_point") | default("N/A")}}°C
          Spread: {{state_attr("sensor.local_forecast_enhanced", "dewpoint_spread") | default("N/A")}}°C
          Vlhkosť: {{state_attr("sensor.local_forecast_enhanced", "humidity") | default("N/A")}}%
          
          {% set visibility = state_attr("weather.local_weather_forecast_weather", "visibility_estimate") %}
          {% if visibility %}Viditeľnosť: {{visibility}}{% endif %}
        icon: mdi:weather-fog
        icon_color: |
          {% set fog = state_attr("sensor.local_forecast_enhanced", "fog_risk") %}
          {% if fog == "critical" %}red
          {% elif fog == "high" %}orange
          {% elif fog == "medium" %}yellow
          {% elif fog == "low" %}blue
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: Komfort
        secondary: |
          Pocitovo: {{state_attr("weather.local_weather_forecast_weather", "feels_like") | default("N/A")}}°C
          
          {% set comfort = state_attr("weather.local_weather_forecast_weather", "comfort_level") %}
          {% if comfort == "very_hot" %}🔥 Veľmi horúco
          {% elif comfort == "hot" %}🌡️ Horúco
          {% elif comfort == "warm" %}☀️ Teplo
          {% elif comfort == "comfortable" %}✅ Príjemne
          {% elif comfort == "cool" %}🌤️ Chladno
          {% elif comfort == "cold" %}❄️ Zima
          {% elif comfort == "very_cold" %}🥶 Veľmi zima
          {% else %}{{comfort}}{% endif %}
        icon: mdi:account-circle
        icon_color: |
          {% set comfort = state_attr("weather.local_weather_forecast_weather", "comfort_level") %}
          {% if comfort in ["hot", "very_hot"] %}red
          {% elif comfort == "warm" %}orange
          {% elif comfort == "comfortable" %}green
          {% elif comfort == "cool" %}blue
          {% elif comfort in ["cold", "very_cold"] %}purple
          {% else %}grey{% endif %}
        layout: vertical
        multiline_secondary: true
  
  # ========================================================================
  # PREDPOVEĎ NA 6H A 12H (ZAMBRETTI DETAIL)
  # ========================================================================
  - type: markdown
    content: |
      ### 📅 Časová predpoveď (Zambretti)
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: 6 hodín
        secondary: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% set first_time = state_attr("sensor.local_forecast_zambretti_detail", "first_time") %}
          
          {% if det and det is iterable %}Dážď: {{det[0]}}%{% endif %}
          {% if first_time and first_time is iterable %}Čas: {{first_time[0]}}{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-partly-cloudy{% endif %}
        icon_color: orange
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_zambretti_detail
      
      - type: custom:mushroom-template-card
        primary: 12 hodín
        secondary: |
          {% set det = state_attr("sensor.local_forecast_zambretti_detail", "rain_prob") %}
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% set second_time = state_attr("sensor.local_forecast_zambretti_detail", "second_time") %}
          
          {% if det and det is iterable %}Dážď: {{det[1]}}%{% endif %}
          {% if second_time and second_time is iterable %}Čas: {{second_time[0]}}{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_zambretti_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[1]}}{% else %}mdi:weather-partly-cloudy{% endif %}
        icon_color: green
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_zambretti_detail
  
  # ========================================================================
  # PREDPOVEĎ NA 6H A 12H (NEGRETTI DETAIL)
  # ========================================================================
  - type: markdown
    content: |
      ### 📅 Časová predpoveď (Negretti-Zambra)
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: 6 hodín
        secondary: |
          {% set det = state_attr("sensor.local_forecast_neg_zam_detail", "rain_prob") %}
          {% set first_time = state_attr("sensor.local_forecast_neg_zam_detail", "first_time") %}
          
          {% if det and det is iterable %}Dážď: {{det[0]}}%{% endif %}
          {% if first_time and first_time is iterable %}Čas: {{first_time[0]}}{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_neg_zam_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[0]}}{% else %}mdi:weather-partly-cloudy{% endif %}
        icon_color: orange
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_neg_zam_detail
      
      - type: custom:mushroom-template-card
        primary: 12 hodín
        secondary: |
          {% set det = state_attr("sensor.local_forecast_neg_zam_detail", "rain_prob") %}
          {% set second_time = state_attr("sensor.local_forecast_neg_zam_detail", "second_time") %}
          
          {% if det and det is iterable %}Dážď: {{det[1]}}%{% endif %}
          {% if second_time and second_time is iterable %}Čas: {{second_time[0]}}{% endif %}
        icon: |
          {% set icons = state_attr("sensor.local_forecast_neg_zam_detail", "icons") %}
          {% if icons and icons is iterable and icons is not string %}{{icons[1]}}{% else %}mdi:weather-partly-cloudy{% endif %}
        icon_color: green
        layout: vertical
        multiline_secondary: true
        tap_action:
          action: more-info
          entity: sensor.local_forecast_neg_zam_detail
  
  # ========================================================================
  # DENNÁ PREDPOVEĎ (WEATHER ENTITY)
  # ========================================================================
  - type: weather-forecast
    entity: weather.local_weather_forecast_weather
    forecast_type: daily
    show_current: false
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
| **Complete Dashboard (SK)** | All data | ⭐⭐⭐⭐ Expert | ALL sensors organized by category |

---

## 📚 Additional Resources

- **[README.md](README.md)** - Installation and configuration
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

**Last updated:** 2025-12-08  
**Version:** v3.1.0

