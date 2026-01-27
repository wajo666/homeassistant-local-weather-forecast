# Implementation Steps - Complete Forecast Update Roadmap

**Version Range:** 3.1.12 → 4.0.0  
**Status:** 📋 Complete Roadmap  
**Date:** 2026-01-27  
**Purpose:** Celkový plán implementácie forecast vylepšení vo všetkých verziách

---

## 🗺️ ROADMAP OVERVIEW

| Verzia | Feature | Presnosť | Komplexita | Status |
|--------|---------|----------|------------|--------|
| **v3.1.12** | TIME DECAY | 76% → 82% (+6%) | 🟢 Nízka | 🚧 In Progress |
| **v3.2.0** | Persistence Model | 82% → 84% (+2%) | 🟡 Stredná | ⏸️ Planned |
| **v3.3.0** | WMO Simple Model | 84% → 87% (+3%) | 🟡 Stredná | ⏸️ Planned |
| **v4.0.0** | Multi-Model Orchestration | 87% → 92% (+5%) | 🔴 Vysoká | ⏸️ Future |

**Celkový cieľ:** 76% → 92% presnosť (**+16% improvement**)

---

## 📦 VERSION 3.1.12: TIME DECAY (CURRENT)

**Status:** 🚧 In Progress (24% complete - 4/17 krokov)  
**Priority:** 🔥 CRITICAL  
**Target Release:** 2026-01-30  
**Impact:** +6% accuracy (76% → 82%)

### Rozsah v3.1.12:
- ✅ TIME DECAY weighting v `combined_model.py`
- ✅ Integrácia do `forecast_calculator.py`
- ✅ Unit a integration testy
- ⏸️ **NEIMPLEMENTUJE:** persistence.py, wmo_simple.py, orchestration

### Detailný plán:
> Pozri `IMPLEMENTATION_STEPS_v3.1.12.md` pre krok-po-kroku implementáciu

**Hotové kroky:**
- [x] Krok 0.1: Bump version na 3.1.12
- [x] Krok 0.2: Pridať CHANGELOG sekciu
- [x] Krok 0.3: Aktualizovať manifest.json, sensor.py, weather.py
- [x] Krok 0.4: Vytvoriť implementačný plán

**Ostávajúce kroky:**
- [ ] Krok 1.1-1.3: TIME DECAY funkcie v combined_model.py
- [ ] Krok 2.1-2.2: Integrácia do forecast_calculator.py
- [ ] Krok 3.1-3.3: Unit a integration testy
- [ ] Krok 4.1-4.2: Dokumentácia
- [ ] Krok 5.1-5.3: Release

---

## 📦 VERSION 3.2.0: PERSISTENCE MODEL

**Status:** ⏸️ Planned  
**Priority:** 🟡 MEDIUM  
**Target Release:** 2026-02-15  
**Impact:** +2% accuracy (82% → 84%)

### 🎯 Cieľ:
Stabilizovať hodinu 0 (aktuálny stav) pomocou Persistence modelu.

### 📋 Rozsah v3.2.0:

#### **FÁZA 1: Vytvoriť persistence.py modul**

**Krok 1.1: Implementovať Persistence Model**
- **Súbor:** `custom_components/local_weather_forecast/persistence.py` (NOVÝ)
- **Funkcionalita:**
  - `calculate_persistence_forecast()` - predpovedá že aktuálny stav pretrváva
  - `get_persistence_confidence()` - confidence decay s časom
- **Presnosť:**
  - Hour 0: 98% (excellent)
  - Hour 1: 95% (very good)
  - Hour 2: 90% (good)
  - Hour 3+: <85% (declining)

**Krok 1.2: Unit testy pre persistence**
- **Súbor:** `tests/test_persistence.py` (NOVÝ)
- **Testy:**
  - `test_persistence_returns_current_state()`
  - `test_persistence_confidence_decay()`
  - `test_persistence_unified_mapping()`

---

#### **FÁZA 2: Integrácia do combined_model.py**

**Krok 2.1: Pridať persistence do orchestrácie**
- **Súbor:** `custom_components/local_weather_forecast/combined_model.py`
- **Funkcie:**
  - `generate_enhanced_hourly_forecast()` - začať implementáciu
  - Stratégia: Hour 0 → použiť Persistence
  - Hours 1+: Použiť TIME DECAY (existujúce)

**Príklad kódu:**
```python
def generate_enhanced_hourly_forecast(
    weather_data: dict,
    hours: int = 24,
    lang_index: int = 1
) -> list[dict]:
    """Generate hourly forecast with optimal model selection.
    
    Strategy:
    - Hour 0: Persistence (98% accuracy)
    - Hours 1+: Zambretti/Negretti with TIME DECAY
    """
    forecasts = []
    
    for hour in range(hours + 1):
        if hour == 0:
            # Use Persistence for current state stabilization
            from .persistence import calculate_persistence_forecast
            current_code = weather_data.get("current_condition_code", 0)
            forecast = calculate_persistence_forecast(current_code, lang_index)
        else:
            # Use existing TIME DECAY logic
            forecast = calculate_combined_forecast_with_time(
                zambretti_result=weather_data["zambretti"],
                negretti_result=weather_data["negretti"],
                current_pressure=weather_data["pressure"],
                pressure_change=weather_data["pressure_change"],
                hours_ahead=hour
            )
        
        forecasts.append({
            "datetime": weather_data["start_time"] + timedelta(hours=hour),
            "condition": forecast[0],
            "temperature": calculate_temperature_at_hour(hour, weather_data),
            # ...existing fields...
        })
    
    return forecasts
```

**Krok 2.2: Aktualizovať forecast_calculator.py**
- Pridať volanie `generate_enhanced_hourly_forecast()` pre ENHANCED model
- Zachovať existujúce správanie pre Zambretti/Negretti modely

---

#### **FÁZA 3: Testing & Documentation**

**Krok 3.1: Integration testy**
- Overiť že hour 0 používa Persistence
- Overiť že hours 1+ používajú TIME DECAY
- Overiť backward compatibility

**Krok 3.2: Dokumentácia**
- Aktualizovať CHANGELOG.md
- Aktualizovať README.md (pridať Persistence do model stratégie)
- Aktualizovať WEATHER_CARDS.md (vysvetliť hour 0 stabilizáciu)

**Krok 3.3: Release**
- Bump version na 3.2.0
- GitHub release s release notes
- HACS update

---

### 📊 Očakávané výsledky v3.2.0:

| Horizont | v3.1.12 | v3.2.0 | Zlepšenie |
|----------|---------|--------|-----------|
| **Hour 0** | 82% | **98%** | +16% ⭐⭐⭐ |
| **Hours 1-6** | 82% | **84%** | +2% ⭐ |
| **Hours 7-24** | 82% | 82% | 0% |
| **CELKOM** | **82%** | **84%** | **+2%** |

---

## 📦 VERSION 3.3.0: WMO SIMPLE MODEL

**Status:** ⏸️ Planned  
**Priority:** 🟡 MEDIUM  
**Target Release:** 2026-03-15  
**Impact:** +3% accuracy (84% → 87%)

### 🎯 Cieľ:
Vylepšiť nowcasting (hodiny 1-3) pomocou WMO Simple barometric modelu.

### 📋 Rozsah v3.3.0:

#### **FÁZA 1: Vytvoriť wmo_simple.py modul**

**Krok 1.1: Implementovať WMO Simple Model**
- **Súbor:** `custom_components/local_weather_forecast/wmo_simple.py` (NOVÝ)
- **Funkcionalita:**
  - `calculate_wmo_simple_forecast()` - forecast z tlaku + trend
  - `_classify_wmo_simple()` - klasifikácia podľa WMO pravidiel
  - `get_wmo_confidence()` - confidence pre 1-3h horizont
- **Presnosť:**
  - Hours 1-3: 85-90% (peak performance)
  - Hours 4-6: 78-82% (acceptable)
  - Hours 7+: <75% (declining)

**WMO Simple Rules:**
```python
# Pressure ranges (aligned with unified codes 0-25):
# - Very low (<980 hPa) → Storm (22-25)
# - Low (980-1000 hPa) → Rainy (15-21)
# - Normal (1000-1020 hPa) → Variable (8-14)
# - High (1020-1040 hPa) → Fine (1-7)
# - Very high (>1040 hPa) → Settled (0)

# Trend adjustment:
# - Rising → Better weather (shift -3 codes)
# - Falling → Worse weather (shift +3 codes)
# - Steady → No adjustment
```

**Krok 1.2: Unit testy pre WMO Simple**
- **Súbor:** `tests/test_wmo_simple.py` (NOVÝ)
- **Testy:**
  - `test_wmo_classification_by_pressure()`
  - `test_wmo_trend_adjustment()`
  - `test_wmo_confidence_peak()`
  - `test_wmo_unified_mapping()`

---

#### **FÁZA 2: Integrácia do combined_model.py**

**Krok 2.1: Rozšíriť orchestráciu pre WMO Simple**
- **Súbor:** `custom_components/local_weather_forecast/combined_model.py`
- **Funkcie:**
  - Rozšíriť `generate_enhanced_hourly_forecast()`
  - Stratégia: Hours 1-3 → WMO Simple
  - Hours 4-6: Blend WMO → Zambretti
  - Hours 7+: Zambretti/Negretti TIME DECAY

**Príklad kódu:**
```python
def generate_enhanced_hourly_forecast(
    weather_data: dict,
    hours: int = 24,
    lang_index: int = 1
) -> list[dict]:
    """Generate hourly forecast with optimal model selection.
    
    Strategy:
    - Hour 0: Persistence (98%)
    - Hours 1-3: WMO Simple (85-90%) ⭐ NEW!
    - Hours 4-6: Blend WMO → Zambretti (80-85%)
    - Hours 7+: Zambretti/Negretti TIME DECAY (78-82%)
    """
    forecasts = []
    
    for hour in range(hours + 1):
        if hour == 0:
            # Persistence
            forecast = calculate_persistence_forecast(...)
        
        elif 1 <= hour <= 3:
            # WMO Simple (peak nowcasting) ⭐ NEW!
            from .wmo_simple import calculate_wmo_simple_forecast
            forecast = calculate_wmo_simple_forecast(
                p0=weather_data["pressure"],
                pressure_change=weather_data["pressure_change"],
                wind_data=weather_data["wind_data"],
                lang_index=lang_index
            )
        
        elif 4 <= hour <= 6:
            # Blend WMO → Zambretti ⭐ NEW!
            wmo_forecast = calculate_wmo_simple_forecast(...)
            combined_forecast = calculate_combined_forecast_with_time(...)
            
            # Blend based on hour
            blend_factor = (hour - 3) / 3.0  # 0.33 at h4, 0.66 at h5, 1.0 at h6
            forecast = blend_forecasts(wmo_forecast, combined_forecast, blend_factor)
        
        else:
            # Zambretti/Negretti TIME DECAY (existing)
            forecast = calculate_combined_forecast_with_time(
                hours_ahead=hour,
                ...
            )
        
        forecasts.append(...)
    
    return forecasts
```

**Krok 2.2: Implementovať blending logiku**
```python
def blend_forecasts(
    forecast_a: list,
    forecast_b: list,
    factor: float
) -> list:
    """Blend two forecasts smoothly.
    
    Args:
        forecast_a: First forecast [text, code, letter]
        forecast_b: Second forecast [text, code, letter]
        factor: Blend factor (0.0 = 100% A, 1.0 = 100% B)
        
    Returns:
        Blended forecast [text, code, letter]
    """
    code_a = forecast_a[1]
    code_b = forecast_b[1]
    
    # Weighted average of codes
    blended_code = int(round(code_a * (1 - factor) + code_b * factor))
    
    # Get text from unified mapping
    from .forecast_mapping import get_forecast_text
    blended_text = get_forecast_text(blended_code, lang_index)
    
    # Generate letter code
    letter_code = chr(65 + min(blended_code // 3, 7))
    
    return [blended_text, blended_code, letter_code]
```

---

#### **FÁZA 3: Testing & Documentation**

**Krok 3.1: Integration testy**
- Overiť že hours 1-3 používajú WMO Simple
- Overiť blending hours 4-6
- Overiť že hours 7+ stále používajú TIME DECAY

**Krok 3.2: Dokumentácia**
- Aktualizovať CHANGELOG.md
- Aktualizovať README.md (pridať WMO Simple do stratégie)
- Vytvoriť comparison chart (Persistence vs WMO vs TIME DECAY)

**Krok 3.3: Release**
- Bump version na 3.3.0
- GitHub release
- HACS update

---

### 📊 Očakávané výsledky v3.3.0:

| Horizont | v3.2.0 | v3.3.0 | Zlepšenie |
|----------|---------|--------|-----------|
| **Hour 0** | 98% | 98% | 0% |
| **Hours 1-3** | 84% | **90%** | +6% ⭐⭐⭐ |
| **Hours 4-6** | 82% | **85%** | +3% ⭐⭐ |
| **Hours 7-12** | 82% | **84%** | +2% ⭐ |
| **Hours 13-24** | 80% | 82% | +2% ⭐ |
| **CELKOM** | **84%** | **87%** | **+3%** |

---

## 📦 VERSION 4.0.0: MULTI-MODEL ORCHESTRATION

**Status:** ⏸️ Future (Major Update)  
**Priority:** 🔵 LOW  
**Target Release:** 2026-06-01  
**Impact:** +5% accuracy (87% → 92%)

### 🎯 Cieľ:
Komplexná orchestrácia všetkých modelov s pokročilými technikami.

### 📋 Rozsah v4.0.0:

#### **FÁZA 1: Advanced Model Selection**

**Krok 1.1: Dynamická detekcia počasia**
- Rozpoznať typy situácií:
  - Anticyklóna (stable high)
  - Cyklóna (deep low)
  - Frontal passage (rapid change)
  - Ridge/trough patterns
- Pre každý typ použiť optimálny model

**Krok 1.2: Confidence-based weighting**
- Každý model vracia confidence score
- Vážiť modely podľa confidence
- Adaptívne sa učiť z accuracy

**Príklad:**
```python
def calculate_multi_model_forecast(
    weather_data: dict,
    hours_ahead: int,
    lang_index: int
) -> dict:
    """Calculate forecast using ALL models with confidence weighting."""
    
    # Get forecasts from all models
    persistence = calculate_persistence_forecast(...)
    wmo = calculate_wmo_simple_forecast(...)
    zambretti = calculate_zambretti_forecast(...)
    negretti = calculate_negretti_zambra_forecast(...)
    
    # Get confidence for each model at this horizon
    confidences = {
        "persistence": get_persistence_confidence(hours_ahead),
        "wmo": get_wmo_confidence(hours_ahead),
        "zambretti": get_zambretti_confidence(hours_ahead, weather_data),
        "negretti": get_negretti_confidence(hours_ahead, weather_data),
    }
    
    # Weighted blend based on confidence
    forecast = weighted_ensemble([
        (persistence, confidences["persistence"]),
        (wmo, confidences["wmo"]),
        (zambretti, confidences["zambretti"]),
        (negretti, confidences["negretti"]),
    ])
    
    return forecast
```

---

#### **FÁZA 2: Advanced Features**

**Krok 2.1: Probabilistic forecasts**
- Každý model vracia distribution, nie single value
- Ensemble všetkých modelov
- Výstup: Most likely + uncertainty range

**Krok 2.2: Learning & Adaptation**
- Track accuracy každého modelu
- Adaptívne upraviť váhy
- Store performance metrics

**Krok 2.3: Weather pattern recognition**
- Rozpoznať synoptické patterns
- Použiť historické analógie
- Improve long-term accuracy

---

#### **FÁZA 3: API Enhancements**

**Krok 3.1: Nové atribúty sensora**
```python
sensor.local_forecast_enhanced:
  attributes:
    # Existujúce
    base_forecast: "Pekné počasie"
    forecast_model: "enhanced"
    confidence: "high"
    
    # NOVÉ v4.0.0
    model_contributions:  # Ktorý model koľko prispieval
      persistence: 0.20
      wmo_simple: 0.35
      zambretti: 0.25
      negretti: 0.20
    
    uncertainty_range:  # Rozsah neistoty
      lower_bound: 0  # Settled fine
      upper_bound: 3  # Fine, becoming less settled
    
    pattern_detected: "anticyclone"  # Rozpoznaný pattern
    
    next_change_time: "2026-01-28T15:00:00"  # Kedy očakávať zmenu
    next_change_confidence: 0.75
```

**Krok 3.2: Nové služby**
```yaml
# Service: local_weather_forecast.get_detailed_forecast
service: local_weather_forecast.get_detailed_forecast
data:
  entity_id: sensor.local_forecast_enhanced
  hours_ahead: 12
response:
  forecast: "Pekné, stáva sa premenlivé"
  confidence: 0.82
  model_used: "zambretti"
  uncertainty: "±2 codes"
  contributing_models:
    - persistence: 0.15
    - wmo_simple: 0.25
    - zambretti: 0.35
    - negretti: 0.25
```

---

#### **FÁZA 4: Testing & Performance**

**Krok 4.1: Extensive testing**
- Historical data validation
- Cross-validation na rôznych lokáciách
- Edge case testing

**Krok 4.2: Performance optimization**
- Cache model calculations
- Optimize blending algorithms
- Reduce update frequency kde nie je potrebná

**Krok 4.3: Documentation**
- Kompletný migration guide
- API documentation
- Best practices guide

---

### 📊 Očakávané výsledky v4.0.0:

| Horizont | v3.3.0 | v4.0.0 | Zlepšenie |
|----------|---------|--------|-----------|
| **Hour 0** | 98% | **99%** | +1% ⭐ |
| **Hours 1-3** | 90% | **94%** | +4% ⭐⭐ |
| **Hours 4-6** | 85% | **90%** | +5% ⭐⭐⭐ |
| **Hours 7-12** | 84% | **90%** | +6% ⭐⭐⭐ |
| **Hours 13-24** | 82% | **88%** | +6% ⭐⭐⭐ |
| **CELKOM** | **87%** | **92%** | **+5%** |

---

## 📊 CELKOVÝ PROGRESS TRACKER

### Version Milestones:

```
v3.1.11 (baseline)    ████████████████░░░░░░░░ 76%
                      │
v3.1.12 (TIME DECAY)  ██████████████████░░░░░░ 82% (+6%)
                      │ 🚧 In Progress
                      │
v3.2.0 (Persistence)  ███████████████████░░░░░ 84% (+2%)
                      │ ⏸️ Planned
                      │
v3.3.0 (WMO Simple)   ████████████████████░░░░ 87% (+3%)
                      │ ⏸️ Planned
                      │
v4.0.0 (Multi-Model)  ██████████████████████░░ 92% (+5%)
                      │ ⏸️ Future
                      ▼
                    100%
```

### Effort Distribution:

| Verzia | Kroky | Effort | Risk | Value |
|--------|-------|--------|------|-------|
| v3.1.12 | 17 | 3 dni | 🟢 LOW | ⭐⭐⭐ HIGH |
| v3.2.0 | 12 | 5 dni | 🟡 MEDIUM | ⭐⭐ MEDIUM |
| v3.3.0 | 15 | 7 dni | 🟡 MEDIUM | ⭐⭐⭐ HIGH |
| v4.0.0 | 25+ | 15+ dni | 🔴 HIGH | ⭐⭐ MEDIUM |

---

## 🎯 PRIORITY RECOMMENDATIONS

### **Teraz (v3.1.12):**
✅ **Implementovať TIME DECAY** - najväčší ROI (+6% za 3 dni práce)

### **Ďalší krok (v3.2.0):**
🟡 **Pridať Persistence** - stabilizuje hour 0 (+2% za 5 dní práce)

### **Potom (v3.3.0):**
🟡 **Pridať WMO Simple** - vylepší nowcasting (+3% za 7 dní práce)

### **Budúcnosť (v4.0.0):**
🔵 **Major refactor** - komplexná orchestrácia (+5% za 15+ dní práce)
- Zvážiť až po stabilizácii v3.3.0
- Môže byť rozdelené na menšie verzie (v4.1, v4.2, atď.)

---

## 📚 RELATED DOCUMENTS

### Implementation Plans:
- ✅ **`IMPLEMENTATION_PLAN_COMBINED_ENHANCED.md`** - Celkový plán (všetky verzie)
- ✅ **`IMPLEMENTATION_STEPS_v3.1.12.md`** - Detailný plán pre v3.1.12 (TIME DECAY)
- ✅ **`IMPLEMENTATION_STEPS_COMPLETE.md`** - Tento dokument (roadmap)

### Technical Docs:
- `ENHANCED_SENSOR_ATTRIBUTES.md` - Analýza sensor atribútov
- `CHANGELOG.md` - Version history
- `README.md` - User documentation

### Reference:
- `combined_model.py` - Core model implementation
- `forecast_calculator.py` - Forecast generation
- `forecast_mapping.py` - Unified mapping system

---

## 🚀 GETTING STARTED

### Pre v3.1.12 (aktuálna verzia):
```bash
# Začni tu:
Implementuj KROK 1.1 z IMPLEMENTATION_STEPS_v3.1.12.md
```

### Pre v3.2.0 (budúca verzia):
```bash
# Po dokončení v3.1.12:
1. Release v3.1.12
2. Bump version na v3.2.0
3. Začni s KROK 1.1 (Persistence Model)
```

### Pre v3.3.0 a vyššie:
```bash
# Postupne po stabilizácii predchádzajúcich verzií
```

---

**End of Complete Implementation Steps**

**Status:** ✅ Roadmap Ready  
**Next Action:** Continue with v3.1.12 TIME DECAY implementation  
**Long-term Goal:** 92% forecast accuracy by v4.0.0

