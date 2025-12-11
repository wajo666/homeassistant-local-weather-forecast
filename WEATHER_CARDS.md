# Weather Card Examples for Lovelace UI

**📦 Version:** v3.1.3 (2025-12-10)  
**🎨 Purpose:** Lovelace UI card examples for Local Weather Forecast integration

**🆕 v3.1.3 Features:**
- ❄️ Snow risk detection (temperature, humidity, precipitation)
- 🧊 Ice/frost risk detection (temperature, dew point)
- 🌫️ Enhanced fog detection
- 🌡️ Extended comfort analysis

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
          {{state_attr("sensor.local_forecast_enhanced", "fog_risk") | default("No fog")}}
        icon: mdi:weather-fog
        icon_color: |
          {% set fog = state_attr("sensor.local_forecast_enhanced", "fog_risk") | lower %}
          {% if "critical" in fog or "kritické" in fog %}red
          {% elif "high" in fog or "vysoké" in fog %}orange
          {% elif "medium" in fog or "stredné" in fog %}yellow
          {% elif "low" in fog or "nízke" in fog %}blue
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
          {{state_attr("sensor.local_forecast_enhanced", "atmosphere_stability") | default("Unknown")}}
        icon: mdi:weather-partly-cloudy
        icon_color: |
          {% set stability = state_attr("sensor.local_forecast_enhanced", "atmosphere_stability") | lower %}
          {% if "very_unstable" in stability or "veľmi nestabilná" in stability %}red
          {% elif "unstable" in stability or "nestabilná" in stability %}orange
          {% elif "moderate" in stability or "mierne" in stability %}yellow
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

**🆕 Nové v3.1.3:**
- ❄️ Detekcia rizika snehu (teplota, vlhkosť, zrážky)
- 🧊 Detekcia rizika poľadovice/námrazy (teplota, rosný bod)
- 🌫️ Vylepšená detekcia hmly
- 🌡️ Rozšírená analýza komfortu

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
          {{state_attr("sensor.local_forecast_enhanced", "atmosphere_stability") | default("Neznáma")}}
          
          {% set ratio = state_attr("sensor.local_forecast_enhanced", "gust_ratio") %}
          {% if ratio %}Gust ratio: {{ratio}}{% endif %}
        icon: mdi:weather-tornado
        icon_color: |
          {% set stability = state_attr("sensor.local_forecast_enhanced", "atmosphere_stability") | lower %}
          {% if "veľmi nestabilná" in stability %}red
          {% elif "nestabilná" in stability %}orange
          {% elif "mierne" in stability %}yellow
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
          {{state_attr("sensor.local_forecast_enhanced", "fog_risk") | default("Žiadne riziko")}}
        secondary: |
          Rosný bod: {{state_attr("sensor.local_forecast_enhanced", "dew_point") | default("N/A")}}°C
          Spread: {{state_attr("sensor.local_forecast_enhanced", "dewpoint_spread") | default("N/A")}}°C
          Vlhkosť: {{state_attr("sensor.local_forecast_enhanced", "humidity") | default("N/A")}}%
          
          {% set visibility = state_attr("weather.local_weather_forecast_weather", "visibility_estimate") %}
          {% if visibility %}Viditeľnosť: {{visibility}}{% endif %}
        icon: mdi:weather-fog
        icon_color: |
          {% set fog = state_attr("sensor.local_forecast_enhanced", "fog_risk") | lower %}
          {% if "kritické" in fog %}red
          {% elif "vysoké" in fog %}orange
          {% elif "stredné" in fog %}yellow
          {% elif "nízke" in fog %}blue
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
  # SNEH A POĽADOVICA
  # ========================================================================
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: |
          {% set risk = state_attr("weather.local_weather_forecast_weather", "snow_risk") %}
          {% if risk == "critical" %}⚠️ KRITICKÉ RIZIKO SNEHU
          {% elif risk == "high" %}❄️ Vysoké riziko snehu
          {% elif risk == "medium" %}🌨️ Stredné riziko snehu
          {% elif risk == "low" %}☁️ Nízke riziko snehu
          {% else %}Žiadne riziko snehu{% endif %}
        secondary: |
          Teplota: {{state_attr("weather.local_weather_forecast_weather", "temperature") | default("N/A")}}°C
          Vlhkosť: {{state_attr("sensor.local_forecast_enhanced", "humidity") | default("N/A")}}%
          {% set rain_prob = states("sensor.local_forecast_rain_probability") | int(0) %}
          Zrážky: {{rain_prob}}%
          
          {% set risk = state_attr("weather.local_weather_forecast_weather", "snow_risk") %}
          {% if risk in ["high", "critical"] %}⚠️ Očakávaj sneženie!{% endif %}
        icon: mdi:snowflake
        icon_color: |
          {% set risk = state_attr("weather.local_weather_forecast_weather", "snow_risk") %}
          {% if risk == "critical" %}red
          {% elif risk == "high" %}orange
          {% elif risk == "medium" %}blue
          {% elif risk == "low" %}cyan
          {% else %}grey{% endif %}
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: |
          {% set risk = state_attr("weather.local_weather_forecast_weather", "ice_risk") %}
          {% if risk == "critical" %}🚨 KRITICKÉ RIZIKO NÁMRAZY
          {% elif risk == "high" %}⚠️ Vysoké riziko námrazy
          {% elif risk == "medium" %}❄️ Stredné riziko námrazy
          {% elif risk == "low" %}💧 Nízke riziko námrazy
          {% else %}Žiadne riziko námrazy{% endif %}
        secondary: |
          Teplota: {{state_attr("weather.local_weather_forecast_weather", "temperature") | default("N/A")}}°C
          Rosný bod: {{state_attr("sensor.local_forecast_enhanced", "dew_point") | default("N/A")}}°C
          Spread: {{state_attr("sensor.local_forecast_enhanced", "dewpoint_spread") | default("N/A")}}°C
          
          {% set risk = state_attr("weather.local_weather_forecast_weather", "ice_risk") %}
          {% if risk in ["high", "critical"] %}⚠️ POZOR - klzké cesty!{% endif %}
        icon: mdi:snowflake-alert
        icon_color: |
          {% set risk = state_attr("weather.local_weather_forecast_weather", "ice_risk") %}
          {% if risk == "critical" %}red
          {% elif risk == "high" %}orange
          {% elif risk == "medium" %}yellow
          {% elif risk == "low" %}blue
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
| **Complete Dashboard (SK)** | All data | ⭐⭐⭐⭐ Expert | ALL sensors + snow/ice/fog warnings |

---

## 📚 Additional Resources

- **[README.md](README.md)** - Installation and configuration
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

## 📋 Card 8: Complete Weather Entity Details (All Attributes)

**🎯 Purpose:** Display ALL attributes from weather.local_weather_forecast_weather entity  
**📦 Cards needed:** None for simple version, `custom:mushroom-*` for advanced version

**💡 Why this card?**
- Home Assistant weather UI shows only 5 basic attributes (temperature, pressure, humidity, wind speed, wind bearing)
- Weather entity has **25+ additional attributes** with valuable data!
- This card exposes everything: feels like, dew point, fog risk, wind gust, rain probability, forecasts, etc.

### Option A: Simple Entities Card (No Custom Cards Needed)

```yaml
type: entities
title: Complete Weather Details
show_header_toggle: false
entities:
  # Current Conditions
  - type: section
    label: 🌡️ Current Conditions
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: temperature
    name: Temperature
    suffix: °C
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: feels_like
    name: Feels Like
    suffix: °C
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: comfort_level
    name: Comfort Level
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: humidity
    name: Humidity
    suffix: '%'
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: pressure
    name: Pressure
    suffix: hPa
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: pressure_trend
    name: Pressure Trend
  
  # Wind & Atmospheric
  - type: section
    label: 💨 Wind & Atmospheric
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: wind_speed
    name: Wind Speed
    suffix: m/s
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: wind_gust
    name: Wind Gust
    suffix: m/s
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: gust_ratio
    name: Gust Ratio
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: wind_type
    name: Wind Type
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: wind_beaufort_scale
    name: Beaufort Scale
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: atmosphere_stability
    name: Atmospheric Stability
  
  # Fog & Visibility
  - type: section
    label: 🌫️ Fog & Visibility
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: dew_point
    name: Dew Point
    suffix: °C
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: dewpoint_spread
    name: Dewpoint Spread
    suffix: °C
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: fog_risk
    name: Fog Risk
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: visibility_estimate
    name: Visibility Estimate
  
  # Snow & Ice (v3.1.3+)
  - type: section
    label: ❄️ Snow & Ice Risk
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: snow_risk
    name: Snow Risk
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: ice_risk
    name: Ice/Frost Risk
  
  # Rain Forecast
  - type: section
    label: 🌧️ Rain Forecast
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: rain_probability
    name: Rain Probability
    suffix: '%'
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: rain_confidence
    name: Rain Confidence
  
  # Forecasts
  - type: section
    label: 📊 Forecast Models
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: forecast_zambretti
    name: Zambretti Forecast
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: forecast_negretti_zambra
    name: Negretti-Zambra Forecast
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: forecast_short_term
    name: Short Term Forecast
  - entity: weather.local_weather_forecast_weather
    type: attribute
    attribute: forecast_confidence
    name: Forecast Confidence
```

### Option B: Advanced Mushroom Card (Prettier, More Compact)

```yaml
type: custom:vertical-stack-in-card
cards:
  - type: custom:mushroom-title-card
    title: Complete Weather Details
    subtitle: All attributes from weather.local_weather_forecast_weather
  
  # ========== SECTION 1: CURRENT WEATHER ==========
  - type: custom:mushroom-title-card
    title: 🌡️ Current Conditions
    subtitle: ''
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Temperature
        secondary: |
          {{state_attr("weather.local_weather_forecast_weather", "temperature")}}°C
          Feels: {{state_attr("weather.local_weather_forecast_weather", "feels_like")}}°C
        icon: mdi:thermometer
        icon_color: red
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: Humidity
        secondary: |
          {{state_attr("weather.local_weather_forecast_weather", "humidity")}}%
          Comfort: {{state_attr("weather.local_weather_forecast_weather", "comfort_level")}}
        icon: mdi:water-percent
        icon_color: blue
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: Pressure
        secondary: |
          {{state_attr("weather.local_weather_forecast_weather", "pressure")}} hPa
          {{state_attr("weather.local_weather_forecast_weather", "pressure_trend")}}
        icon: mdi:gauge
        icon_color: purple
        layout: vertical
        multiline_secondary: true
  
  # ========== SECTION 2: WIND & ATMOSPHERIC ==========
  - type: custom:mushroom-title-card
    title: 💨 Wind & Atmospheric Stability
    subtitle: ''
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Wind Speed
        secondary: |
          {{state_attr("weather.local_weather_forecast_weather", "wind_speed")}} m/s
          Gust: {{state_attr("weather.local_weather_forecast_weather", "wind_gust")}} m/s
          Ratio: {{state_attr("weather.local_weather_forecast_weather", "gust_ratio")}}
        icon: mdi:weather-windy
        icon_color: cyan
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: |
          {{state_attr("weather.local_weather_forecast_weather", "wind_type")}}
        secondary: |
          Beaufort: {{state_attr("weather.local_weather_forecast_weather", "wind_beaufort_scale")}}/12
          {{state_attr("weather.local_weather_forecast_weather", "atmosphere_stability")}}
        icon: mdi:weather-tornado
        icon_color: |
          {% set stability = state_attr("weather.local_weather_forecast_weather", "atmosphere_stability") | lower %}
          {% if "veľmi nestabilná" in stability or "very unstable" in stability %}red
          {% elif "nestabilná" in stability or "unstable" in stability %}orange
          {% elif "mierne" in stability or "moderate" in stability %}yellow
          {% else %}green{% endif %}
        layout: vertical
        multiline_secondary: true
  
  # ========== SECTION 3: FOG & VISIBILITY ==========
  - type: custom:mushroom-title-card
    title: 🌫️ Fog Risk & Visibility
    subtitle: ''
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: |
          {{state_attr("weather.local_weather_forecast_weather", "fog_risk")}}
        secondary: |
          Dew Point: {{state_attr("weather.local_weather_forecast_weather", "dew_point")}}°C
          Spread: {{state_attr("weather.local_weather_forecast_weather", "dewpoint_spread")}}°C
        icon: mdi:weather-fog
        icon_color: |
          {% set fog = state_attr("weather.local_weather_forecast_weather", "fog_risk") | lower %}
          {% if "kritické" in fog or "critical" in fog %}red
          {% elif "vysoké" in fog or "high" in fog %}orange
          {% elif "stredné" in fog or "medium" in fog %}yellow
          {% else %}blue{% endif %}
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: Visibility
        secondary: |
          {{state_attr("weather.local_weather_forecast_weather", "visibility_estimate")}}
        icon: mdi:eye
        icon_color: grey
        layout: vertical
        multiline_secondary: true
  
  # ========== SECTION 4: RAIN PROBABILITY ==========
  - type: custom:mushroom-title-card
    title: 🌧️ Rain Forecast
    subtitle: ''
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Rain Probability
        secondary: |
          {{state_attr("weather.local_weather_forecast_weather", "rain_probability")}}%
          Confidence: {{state_attr("weather.local_weather_forecast_weather", "rain_confidence")}}
        icon: mdi:weather-rainy
        icon_color: |
          {% set prob = state_attr("weather.local_weather_forecast_weather", "rain_probability") | int(0) %}
          {% if prob >= 70 %}red
          {% elif prob >= 40 %}orange
          {% else %}blue{% endif %}
        layout: vertical
        multiline_secondary: true
  
  # ========== SECTION 5: FORECASTS ==========
  - type: custom:mushroom-title-card
    title: 📊 Forecast Models
    subtitle: ''
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Zambretti
        secondary: |
          {{state_attr("weather.local_weather_forecast_weather", "forecast_zambretti")}}
          Number: {{state_attr("weather.local_weather_forecast_weather", "zambretti_number")}}
        icon: mdi:weather-partly-cloudy
        icon_color: blue
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: Negretti-Zambra
        secondary: |
          {{state_attr("weather.local_weather_forecast_weather", "forecast_negretti_zambra")}}
          Number: {{state_attr("weather.local_weather_forecast_weather", "neg_zam_number")}}
        icon: mdi:weather-partly-rainy
        icon_color: orange
        layout: vertical
        multiline_secondary: true
  
  # ========== SECTION 6: FORECAST CONFIDENCE ==========
  - type: custom:mushroom-title-card
    title: 🎯 Forecast Quality
    subtitle: ''
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Confidence
        secondary: |
          Level: {{state_attr("weather.local_weather_forecast_weather", "forecast_confidence")}}
          
          {% set adj = state_attr("weather.local_weather_forecast_weather", "forecast_adjustments") %}
          {% if adj and adj is iterable and adj is not string %}
            Adjustments: {{adj | length}}
          {% endif %}
        icon: mdi:check-circle
        icon_color: |
          {% set conf = state_attr("weather.local_weather_forecast_weather", "forecast_confidence") %}
          {% if conf == "high" %}green
          {% elif conf == "medium" %}yellow
          {% else %}orange{% endif %}
        layout: vertical
        multiline_secondary: true
      
      - type: custom:mushroom-template-card
        primary: Adjustments
        secondary: |
          {% set details = state_attr("weather.local_weather_forecast_weather", "forecast_adjustment_details") %}
          {% if details and details is iterable and details is not string %}
            {% for detail in details[:3] %}
              • {{detail}}
            {% endfor %}
          {% else %}
            No adjustments
          {% endif %}
        icon: mdi:information
        icon_color: blue
        layout: vertical
        multiline_secondary: true
```

**📋 Available Attributes:**
- `temperature`, `feels_like`, `comfort_level`
- `humidity`, `pressure`, `pressure_trend`
- `wind_speed`, `wind_gust`, `wind_bearing`, `gust_ratio`
- `wind_type`, `wind_beaufort_scale`, `atmosphere_stability`
- `dew_point`, `dewpoint_spread`, `fog_risk`, `visibility_estimate`
- `rain_probability`, `rain_confidence`
- `forecast_zambretti`, `zambretti_number`
- `forecast_negretti_zambra`, `neg_zam_number`
- `forecast_short_term`, `forecast_confidence`
- `forecast_adjustments`, `forecast_adjustment_details`

---

**Last updated:** 2025-12-09  
**Version:** v3.1.1

