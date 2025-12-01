# Roadmap: Extended Sensors & Weather Entity

**Branch:** `feature/extended-sensors`  
**Target Version:** 3.1.0  
**Created:** 2025-12-01

---

## 🎯 Ciele

1. **Rozšírenie vstupných senzorov** - Pridať voliteľné senzory pre presnejšiu predpoveď
2. **Nové vypočítané senzory** - Odvodené hodnoty pre detailnejšiu analýzu
3. **Weather Entity** - Implementácia `weather.local_forecast` entity s forecast atribútom

---

## 📊 Nové Vstupné Senzory (Voliteľné)

### Základné meteorologické parametre:
- ✅ **Humidity** (vlhkosť vzduchu) - %
  - Pomôže určiť pravdepodobnosť zrážok
  - Vylepší predpoveď kondenzácie/hmly
  
- ✅ **Dew Point** (rosný bod) - °C
  - Vypočíta sa z teploty a vlhkosti ak nie je k dispozícii
  - Indikátor pre hmlu a oblačnosť

- ✅ **Cloud Coverage** (oblačnosť) - %
  - Vylepší určenie aktuálnych podmienok
  - Pomôže s krátkodobou predpoveďou (1-3h)

- ✅ **UV Index** (UV index) - 0-11+
  - Doplnková informácia pre weather entity
  
- ✅ **Visibility** (viditeľnosť) - km
  - Indikátor pre hmlu/búrku

### Rozšírené meteorologické parametre:
- ⚡ **Wind Gust** (nárazy vetra) - km/h
  - Dôležité pre predpoveď búrok
  
- ⚡ **Rain Rate** (intenzita dažďa) - mm/h
  - Aktuálne zrážky pre krátkodobú predpoveď
  
- ⚡ **Precipitation Total** (úhrn zrážok) - mm
  - História zrážok za posledných 24h

---

## 🧮 Nové Vypočítané Senzory

### 1. **Humidity-based sensors:**
```yaml
sensor.local_forecast_humidity:
  state: 75  # %
  attributes:
    trend: "rising"  # rising/falling/steady
    change_1h: +5
    change_3h: +12
```

### 2. **Comfort Index:**
```yaml
sensor.local_forecast_comfort_index:
  state: 18.5  # Apparent temperature (°C)
  attributes:
    heat_index: 19.2
    wind_chill: 17.8
    comfort_level: "comfortable"  # cold/cool/comfortable/warm/hot
```

### 3. **Rain Probability (Enhanced):**
```yaml
sensor.local_forecast_rain_probability:
  state: 30  # %
  attributes:
    source: "combined"  # zambretti/negretti/humidity/cloud
    confidence: "medium"  # low/medium/high
    next_1h: 15
    next_3h: 30
    next_6h: 45
    next_12h: 35
```

### 4. **Weather Condition:**
```yaml
sensor.local_forecast_condition:
  state: "cloudy"  # HA standard conditions
  attributes:
    zambretti_condition: "Fine"
    negretti_condition: "Fine"
    confidence: 0.75
    icon: "mdi:weather-cloudy"
```

### 5. **Forecast Trend Analyzer:**
```yaml
sensor.local_forecast_trend:
  state: "improving"  # improving/deteriorating/stable
  attributes:
    pressure_trend: "rising"
    temperature_trend: "falling"
    humidity_trend: "steady"
    confidence: "high"
    time_to_change: "6-12h"
```

### 6. **Dew Point:**
```yaml
sensor.local_forecast_dewpoint:
  state: 2.5  # °C
  device_class: temperature
  attributes:
    spread: 1.5  # Temperature - Dewpoint
    fog_risk: "low"  # low/medium/high (spread < 2°C = high)
```

---

## 🌦️ Weather Entity Implementation

### Phase 1: Basic Weather Entity
```python
weather.local_forecast:
  state: "cloudy"
  temperature: 4.0
  pressure: 1014.0
  humidity: 75
  wind_speed: 5
  wind_bearing: 185
  dew_point: 2.5
  cloud_coverage: 65
```

### Phase 2: Forecast Attribute (3h intervals)
```python
  forecast:
    - datetime: "2025-12-01T15:00:00+00:00"
      condition: "rainy"
      temperature: 3.5
      templow: 2.0
      precipitation_probability: 30
      pressure: 1013.5
      wind_speed: 8
      wind_bearing: 190
      
    - datetime: "2025-12-01T18:00:00+00:00"
      condition: "cloudy"
      temperature: 3.0
      templow: 1.5
      precipitation_probability: 20
      pressure: 1013.8
      wind_speed: 6
      wind_bearing: 185
```

### Phase 3: Hourly Forecasts (1h intervals)
- Implementácia `get_forecasts()` service call
- Support pre `hourly` a `daily` forecast types

---

## 🔄 Spätná Kompatibilita

- ✅ Všetky existujúce sensory zostanú funkčné
- ✅ Config flow umožní povoliť/zakázať nové funkcie
- ✅ Weather entity je voliteľná (opt-in v config)
- ✅ Bez nových senzorov funguje ako doteraz (graceful degradation)

---

## 📝 Config Flow Updates

### Nová sekcia: "Advanced Sensors" (optional step)
```yaml
Humidity Sensor: sensor.outdoor_humidity (optional)
Dew Point Sensor: sensor.outdoor_dewpoint (optional)
Cloud Coverage: sensor.cloud_coverage (optional)
UV Index: sensor.uv_index (optional)
Visibility: sensor.visibility (optional)
Wind Gust: sensor.wind_gust (optional)
Rain Rate: sensor.rain_rate (optional)
```

### Nová sekcia: "Features"
```yaml
☑ Enable Weather Entity
☑ Enable Extended Sensors
☑ Enable Hourly Forecasts
  Forecast Interval: [1h / 3h / 6h]
```

---

## 📋 Implementation Plan

### Step 1: Rozšírenie const.py (✅ READY)
- Pridať nové konštanty pre senzory
- Definovať weather conditions mapping

### Step 2: Config Flow Update (⏳ TODO)
- Pridať optional sensor inputs
- Pridať feature toggles

### Step 3: Extended Sensors (⏳ TODO)
- Implementovať humidity sensor
- Implementovať dew point calculation
- Implementovať comfort index
- Implementovať rain probability

### Step 4: Weather Entity (⏳ TODO)
- Vytvoriť `weather.py` platform
- Implementovať base weather entity
- Pridať forecast generation logic

### Step 5: Testing & Documentation (⏳ TODO)
- Unit tests pre nové výpočty
- Update README.md
- Update WEATHER_CARDS.md
- Example configurations

### Step 6: Release (⏳ TODO)
- Version bump to 3.1.0
- CHANGELOG update
- Release notes

---

## 🧪 Testovanie

### Bez nových senzorov:
- Musí fungovať rovnako ako 3.0.x
- Žiadne errors v logoch

### S novými senzormi:
- Presnejšia predpoveď
- Rozšírené atribúty
- Weather entity dostupná

### Edge cases:
- Senzory sa stanú unavailable
- Neplatné hodnoty (string namiesto čísla)
- Historické dáta chýbajú

---

## 📚 Resources

### Home Assistant Weather Entity:
- [Weather Entity Documentation](https://developers.home-assistant.io/docs/core/entity/weather/)
- [Weather Integration](https://www.home-assistant.io/integrations/weather/)

### Meteorológia:
- Dew Point calculation
- Heat Index / Wind Chill formulas
- Comfort index calculations
- Rain probability algorithms

---

## 🎯 Success Criteria

- ✅ Všetky nové senzory sú voliteľné
- ✅ Spätná kompatibilita 100%
- ✅ Weather entity funguje s 3rd party cards
- ✅ Žiadne breaking changes
- ✅ Dokumentácia aktualizovaná
- ✅ Performance impact < 5%
- ✅ Unit tests coverage > 80%

---

**Next Steps:**
1. Update `const.py` s novými konštantami
2. Navrhnúť API pre extended sensors
3. Implementovať prvý sensor (humidity)
4. Testovať a iterovať


