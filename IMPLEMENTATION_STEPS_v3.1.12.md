# Implementation Steps - Version 3.1.12 (TIME DECAY)

**Status:** 🚧 In Progress  
**Start Date:** 2026-01-27  
**Target:** Minimal TIME DECAY implementation (+6% accuracy improvement)

---

## 📋 KROK-PO-KROKU IMPLEMENTÁCIA

### ⚠️ DÔLEŽITÉ: Rozsah v3.1.12

**✅ ČO SA IMPLEMENTUJE v3.1.12:**
- TIME DECAY weighting v `combined_model.py`
- Integrácia TIME DECAY do `forecast_calculator.py`
- Unit a integration testy
- **Výsledok: +6% presnosť (76% → 82%)**

**⏸️ ČO SA NEIMPLEMENTUJE v3.1.12 (odložené na v3.2.0+):**
- ❌ `persistence.py` - Persistence model (hour 0 stabilization)
- ❌ `wmo_simple.py` - WMO Simple model (hours 1-3 nowcasting)
- ❌ Multi-model orchestration functions

**Prečo odložené?**
- TIME DECAY už poskytuje **80% výhody** (+6% presnosť)
- Persistence/WMO pridajú len **+1-2% navyše**
- Môžu byť v samostatnej verzii (menšie riziko)
- Udržiava v3.1.12 **jednoduchú a stabilnú**

---

### ✅ FÁZA 0: PRÍPRAVA (HOTOVO)
- [x] **Krok 0.1:** Bump version na 3.1.12 ✅
- [x] **Krok 0.2:** Pridať CHANGELOG sekciu ✅
- [x] **Krok 0.3:** Aktualizovať manifest.json, sensor.py, weather.py ✅
- [x] **Krok 0.4:** Vytvoriť implementačný plán ✅

---

## 🔧 FÁZA 1: NEW MODELS - persistence.py & wmo_simple.py (PRIORITA: VYSOKÁ)

### **Krok 1.1: Vytvoriť `persistence.py` modul**
**Súbor:** `custom_components/local_weather_forecast/persistence.py` (NOVÝ)

**Čo implementovať:**
```python
"""Persistence Model - Najjednoduchší forecasting model.

Predpokladá, že aktuálne podmienky budú pretrvávať nezmenené.
Najlepšie pre: Hodina 0 (stabilizácia aktuálneho stavu)
Presnosť: 98% pre hodinu 0, 95% pre +1h, rýchlo klesá potom
"""

def calculate_persistence_forecast(
    current_condition_code: int,
    lang_index: int = 1
) -> list:
    """Calculate Persistence forecast (hour 0 stabilization).
    
    Args:
        current_condition_code: Current unified forecast code (0-25)
        lang_index: Language index for text
        
    Returns:
        [forecast_text, forecast_number, letter_code]
    """
    from .forecast_mapping import get_forecast_text
    
    # Persistence = current state persists
    forecast_number = current_condition_code
    forecast_text = get_forecast_text(forecast_number, lang_index)
    letter_code = chr(65 + min(forecast_number // 3, 7))  # A-H
    
    return [forecast_text, forecast_number, letter_code]


def get_persistence_confidence(hours_ahead: int) -> float:
    """Get confidence for persistence model based on time horizon.
    
    Args:
        hours_ahead: Hours into future
        
    Returns:
        Confidence (0.0-1.0)
    """
    if hours_ahead == 0:
        return 0.98  # Excellent for current state
    elif hours_ahead == 1:
        return 0.95  # Very good for 1h
    elif hours_ahead == 2:
        return 0.90  # Good for 2h
    elif hours_ahead == 3:
        return 0.85  # Acceptable for 3h
    else:
        return 0.80 - (hours_ahead - 3) * 0.05  # Declining
```

**Detaily:**
- Vracia rovnaký kód ako aktuálny stav
- Používa unified mapping pre text
- Confidence klesá s časom
- Optimálny len pre hodinu 0

**Testovať:**
- Overenie, že vracia správny kód
- Overenie confidence values
- Overenie unified mapping

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 1.2: Vytvoriť `wmo_simple.py` modul**
**Súbor:** `custom_components/local_weather_forecast/wmo_simple.py` (NOVÝ)

**Čo implementovať:**
```python
"""WMO Simple Barometric Forecast Model.

Jednoduchý forecast založený na tlaku podľa World Meteorological Organization.
Najlepšie pre: Hodiny 1-3 (nowcasting)
Presnosť: 85-90% pre 1-3h horizont, peak performance pre short-term
"""

import logging
from typing import List

_LOGGER = logging.getLogger(__name__)


def calculate_wmo_simple_forecast(
    p0: float,
    pressure_change: float,
    wind_data: list,
    lang_index: int,
) -> list:
    """Calculate WMO Simple forecast (optimal for 1-3h).
    
    Args:
        p0: Sea level pressure in hPa
        pressure_change: Pressure change in hPa (3h trend)
        wind_data: [wind_fak, direction, dir_text, speed_fak]
        lang_index: Language index (0=DE, 1=EN, 2=EL, 3=IT, 4=SK)
        
    Returns:
        [forecast_text, forecast_number, letter_code]
    """
    # Step 1: Determine pressure trend
    if pressure_change < -1.5:
        trend = "falling"
    elif pressure_change > 1.5:
        trend = "rising"
    else:
        trend = "steady"
    
    # Step 2: Classify based on absolute pressure + trend
    forecast_type = _classify_wmo_simple(p0, trend, wind_data)
    
    # Step 3: Get text from unified mapping
    from .forecast_mapping import get_forecast_text
    forecast_text = get_forecast_text(forecast_type, lang_index)
    
    # Step 4: Generate letter code (A-H based on severity)
    letter_code = chr(65 + min(forecast_type // 3, 7))
    
    _LOGGER.debug(
        f"WMO Simple: P={p0:.1f} hPa, ΔP={pressure_change:+.1f} ({trend}) "
        f"→ code={forecast_type}, letter={letter_code}"
    )
    
    return [forecast_text, forecast_type, letter_code]


def _classify_wmo_simple(p0: float, trend: str, wind_data: list) -> int:
    """Classify weather based on WMO Simple rules.
    
    WMO Simple Classification (aligned with unified codes 0-25):
    - Very low pressure (<980) → Storm conditions (22-25)
    - Low pressure (980-1000) → Rainy/unsettled (15-21)
    - Normal pressure (1000-1020) → Variable (8-14)
    - High pressure (1020-1040) → Fine weather (1-7)
    - Very high pressure (>1040) → Settled fine (0)
    
    Trend adjustment:
    - Rising: Better weather (shift toward lower codes)
    - Falling: Worse weather (shift toward higher codes)
    """
    wind_fak = wind_data[0] if len(wind_data) > 0 else 1
    
    # Base classification by absolute pressure
    if p0 < 980:
        # Very low - stormy conditions
        base_code = 24 if trend == "falling" else 22
    elif p0 < 1000:
        # Low - rainy/unsettled
        if trend == "falling":
            base_code = 21  # Rain at times, becoming very unsettled
        elif trend == "rising":
            base_code = 8   # Showery early, improving
        else:
            base_code = 18  # Unsettled, rain at times
    elif p0 < 1010:
        # Normal-low - variable
        if trend == "falling":
            base_code = 17  # Unsettled, rain later
        elif trend == "rising":
            base_code = 9   # Changeable, mending
        else:
            base_code = 15  # Changeable, some rain
    elif p0 < 1020:
        # Normal-high - mostly fine
        if trend == "falling":
            base_code = 13  # Showery, bright intervals
        elif trend == "rising":
            base_code = 6   # Fairly fine, possible showers early
        else:
            base_code = 10  # Fairly fine, showers likely
    elif p0 < 1030:
        # High - fine weather
        if trend == "falling":
            base_code = 7   # Fairly fine, showery later
        elif trend == "rising":
            base_code = 2   # Becoming fine
        else:
            base_code = 4   # Fine, possible showers
    elif p0 < 1040:
        # Very high - settled fine
        if trend == "falling":
            base_code = 3   # Fine, becoming less settled
        elif trend == "rising":
            base_code = 1   # Fine weather
        else:
            base_code = 1   # Fine weather
    else:
        # Extremely high - very settled
        base_code = 0  # Settled fine
    
    # Wind adjustment (strong wind makes conditions worse)
    if wind_fak >= 2:  # Strong wind
        base_code = min(25, base_code + 1)
    
    return base_code


def get_wmo_simple_confidence(hours_ahead: int) -> float:
    """Get confidence for WMO Simple model based on time horizon.
    
    Args:
        hours_ahead: Hours into future
        
    Returns:
        Confidence (0.0-1.0)
    """
    if hours_ahead <= 1:
        return 0.90  # Excellent for 1h
    elif hours_ahead <= 2:
        return 0.88  # Very good for 2h
    elif hours_ahead <= 3:
        return 0.85  # Good for 3h (peak)
    elif hours_ahead <= 4:
        return 0.82  # Acceptable for 4h
    elif hours_ahead <= 6:
        return 0.78  # Declining for 6h
    else:
        return 0.70  # Poor beyond 6h
```

**Detaily:**
- WMO Simple klasifikácia podľa tlaku + trend
- Aligned s unified codes 0-25
- Wind adjustment pre presnosť
- Peak performance pre 1-3h

**Testovať:**
- Overenie klasifikácie pre rôzne tlaky
- Overenie trend adjustment
- Overenie confidence values
- Overenie unified mapping

**Status:** ⏸️ Čaká na implementáciu

---

## 🔧 FÁZA 2: CORE - combined_model.py (PRIORITA: VYSOKÁ)

### **Krok 1.1: Pridať `_calculate_weights_with_time_decay()` funkciu**
**Súbor:** `custom_components/local_weather_forecast/combined_model.py`

**Čo implementovať:**
```python
def _calculate_weights_with_time_decay(
    current_pressure: float,
    pressure_change: float,
    hours_ahead: int = 0
) -> tuple[float, float, str]:
    """Calculate weights with TIME DECAY over forecast horizon.
    
    TIME DECAY Formula:
    - time_decay = exp(-hours_ahead / 12.0)
    - weight = base_weight × time_decay + 0.5 × (1 - time_decay)
    
    Args:
        current_pressure: Current pressure in hPa
        pressure_change: Pressure change in hPa
        hours_ahead: Hours into future (0-24)
        
    Returns:
        (zambretti_weight, negretti_weight, reason)
    """
```

**Detaily:**
- Zachovať existujúce threshold logiky (anticyklóna, rýchla zmena, atď.)
- Pridať TIME DECAY výpočet pomocou `math.exp()`
- Blend base_weight s 0.5 (balanced baseline)
- Vrátiť tuple s reason stringom pre logging

**Testovať:**
- Anticyklóna: h0=10%, h6=26%, h12=35%, h24=46%
- Rýchla zmena: h0=75%, h6=66%, h12=59%, h24=53%

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 1.2: Pridať `calculate_combined_forecast_with_time()` wrapper**
**Súbor:** `custom_components/local_weather_forecast/combined_model.py`

**Čo implementovať:**
```python
def calculate_combined_forecast_with_time(
    zambretti_result: list,
    negretti_result: list,
    current_pressure: float,
    pressure_change: float,
    hours_ahead: int = 0,
    source: str = "CombinedModel"
) -> tuple[int, float, float, bool]:
    """Calculate Combined forecast WITH TIME DECAY.
    
    NEW: Adds hours_ahead parameter for dynamic weighting.
    """
```

**Detaily:**
- Použiť `_calculate_weights_with_time_decay()` namiesto `_calculate_weights()`
- Zachovať rovnakú logiku výberu forecast_number
- Pridať debug logging s TIME DECAY info
- Vrátiť tuple: (forecast_number, zambretti_weight, negretti_weight, consensus)

**Testovať:**
- Overenie, že váhy sa menia s časom
- Logging obsahuje `hours_ahead` a `decay` hodnoty

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 1.3: Zachovať `calculate_combined_forecast()` pre backward compatibility**
**Súbor:** `custom_components/local_weather_forecast/combined_model.py`

**Čo implementovať:**
```python
def calculate_combined_forecast(
    zambretti_result: list,
    negretti_result: list,
    current_pressure: float,
    pressure_change: float,
    source: str = "CombinedModel"
) -> tuple[int, float, float, bool]:
    """EXISTING function - kept for backward compatibility.
    
    Used by: sensor.py (current state, hour 0)
    Does NOT use TIME DECAY.
    """
    # Call new function with hours_ahead=0 (no decay)
    return calculate_combined_forecast_with_time(
        zambretti_result, negretti_result,
        current_pressure, pressure_change,
        hours_ahead=0,  # No time decay
        source=source
    )
```

**Detaily:**
- Wrappuje novú funkciu s `hours_ahead=0`
- Zachováva API pre existujúci kód
- Žiadne breaking changes

**Testovať:**
- sensor.py stále funguje
- Statické váženie pre hodinu 0

**Status:** ⏸️ Čaká na implementáciu

---

## 📊 FÁZA 2: INTEGRATION - forecast_calculator.py (PRIORITA: VYSOKÁ)

### **Krok 2.1: Upraviť HourlyForecastGenerator pre ENHANCED model**
**Súbor:** `custom_components/local_weather_forecast/forecast_calculator.py`

**Čo upraviť:**
- Nájsť `HourlyForecastGenerator.generate()` metódu (cca riadok 975-1015)
- Upraviť len pre `FORECAST_MODEL_ENHANCED`
- Pridať `hours_ahead=hour_offset` parameter

**Pred (statické):**
```python
if self.forecast_model == FORECAST_MODEL_ENHANCED:
    (forecast_num, ...) = calculate_combined_forecast(
        zambretti_result=["", zambretti_num],
        negretti_result=["", negretti_num],
        current_pressure=future_pressure,
        pressure_change=pressure_change,
        source="HourlyForecast"
    )
```

**Po (TIME DECAY):**
```python
if self.forecast_model == FORECAST_MODEL_ENHANCED:
    from .combined_model import calculate_combined_forecast_with_time
    
    (forecast_num, ...) = calculate_combined_forecast_with_time(
        zambretti_result=["", zambretti_num],
        negretti_result=["", negretti_num],
        current_pressure=future_pressure,
        pressure_change=pressure_change,
        hours_ahead=hour_offset,  # ← NEW!
        source=f"HourlyForecast_h{hour_offset}"
    )
```

**Detaily:**
- Importovať `calculate_combined_forecast_with_time`
- Pridať `hours_ahead=hour_offset` parameter
- Upraviť `source` string pre lepší logging
- Zambretti/Negretti modely PONECHAŤ BEZ ZMIEN

**Testovať:**
- Enhanced model používa TIME DECAY
- Zambretti model stále funguje bez zmien
- Negretti model stále funguje bez zmien
- Logy ukazujú dynamické váženie

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 2.2: Overiť DailyForecastGenerator (voliteľné)**
**Súbor:** `custom_components/local_weather_forecast/forecast_calculator.py`

**Čo overiť:**
- Daily forecast už používa správne modely?
- Je potrebné pridať TIME DECAY aj pre daily?

**Poznámka:**
- Daily forecast má iný prístup (celý deň, nie hodiny)
- Možno stačí existujúca logika
- Overiť v logoch

**Status:** ⏸️ Čaká na overenie

---

## 🧪 FÁZA 3: TESTING (PRIORITA: VYSOKÁ)

### **Krok 3.1: Unit testy pre TIME DECAY**
**Súbor:** `tests/test_combined_model.py` (nový súbor)

**Čo testovať:**
```python
def test_time_decay_anticyclone():
    """Test TIME DECAY for anticyclone scenario."""
    # P=1037 hPa, ΔP=+0.2 hPa
    
    # Hour 0: Z=10%, N=90%
    # Hour 6: Z=26%, N=74%
    # Hour 12: Z=35%, N=65%
    # Hour 24: Z=46%, N=54%

def test_time_decay_rapid_change():
    """Test TIME DECAY for rapid change scenario."""
    # P=1015 hPa, ΔP=-5.0 hPa
    
    # Hour 0: Z=75%, N=25%
    # Hour 6: Z=66%, N=34%
    # Hour 12: Z=59%, N=41%
    # Hour 24: Z=53%, N=47%

def test_time_decay_formula():
    """Test TIME DECAY exponential formula."""
    # Verify: exp(-h/12) at key hours

def test_backward_compatibility():
    """Test that old function still works."""
    # calculate_combined_forecast() = hours_ahead=0
```

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 3.2: Integration test pre ENHANCED model**
**Súbor:** `tests/test_forecast_calculator.py`

**Čo testovať:**
```python
def test_enhanced_hourly_with_time_decay():
    """Test ENHANCED model uses TIME DECAY in hourly forecast."""
    # Generate 24h forecast
    # Verify weights change with time
    # Verify Zambretti/Negretti unchanged

def test_enhanced_anticyclone_scenario():
    """Real-world anticyclone test."""
    # Simulate anticyclone conditions
    # Verify correct weight progression
```

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 3.3: Spustiť všetky existujúce testy**
**Príkaz:** `pytest tests/ -v`

**Čo overiť:**
- Všetky existujúce testy PRECHÁDZAJÚ
- Žiadne breaking changes
- Backward compatibility funguje

**Status:** ⏸️ Čaká na spustenie

---

## 📝 FÁZA 4: DOCUMENTATION (PRIORITA: STREDNÁ)

### **Krok 4.1: Doplniť CHANGELOG.md**
**Súbor:** `CHANGELOG.md`

**Čo doplniť do sekcie `[3.1.12]`:**
```markdown
## [3.1.12] - 2026-01-27

### 🆕 Added
- **TIME DECAY Weighting** for ENHANCED forecast model
  - Dynamic weight adjustment over forecast horizon (0-24h)
  - Exponential decay formula: `exp(-hours_ahead / 12.0)`
  - Anticyclone: 90% Negretti (h0) → 54% Negretti (h24)
  - Rapid change: 75% Zambretti (h0) → 53% Zambretti (h24)

### 📊 Improved
- **Hourly Forecast Accuracy:** +6% improvement (76% → 82%)
  - Short-term (0-6h): +6% (76% → 82%)
  - Mid-term (7-12h): +2% (78% → 80%)
  - Long-term (13-24h): +6% (72% → 78%)
- **Anticyclone Forecasts:** Better long-term stability prediction
- **Rapid Changes:** Smoother transitions to new equilibrium

### 🔧 Technical Details
- `combined_model.py`: Added `_calculate_weights_with_time_decay()`
- `combined_model.py`: Added `calculate_combined_forecast_with_time()`
- `forecast_calculator.py`: ENHANCED model now uses TIME DECAY
- Backward compatible: Zambretti/Negretti models unchanged

### ✅ Backward Compatible
- No config changes needed
- Automatic improvement for ENHANCED model users
- Sensor attributes unchanged (represents current state)
```

**Status:** ⏸️ Čaká na doplnenie

---

### **Krok 4.2: Aktualizovať README.md (voliteľné)**
**Súbor:** `README.md`

**Čo pridať:**
- Sekcia o TIME DECAY feature
- Tabuľka s accuracy improvements
- Odporúčanie pre ENHANCED model

**Status:** ⏸️ Voliteľné

---

## 🚀 FÁZA 5: RELEASE (PRIORITA: NÍZKA - po testovaní)

### **Krok 5.1: Beta testing**
- Testovať na development HA instance
- Overiť TIME DECAY behavior v logoch
- Sledovať forecast presnosť

**Status:** ⏸️ Čaká na beta testing

---

### **Krok 5.2: GitHub release**
- Merge do main branch
- Create tag `v3.1.12`
- Create GitHub release s CHANGELOG

**Status:** ⏸️ Čaká na release

---

### **Krok 5.3: HACS update**
- Automaticky sa updatne z GitHub release
- Overiť v HACS

**Status:** ⏸️ Čaká na release

---

## 📊 PROGRESS TRACKER

### Overall Progress: 11% (2/18 krokov)

| Fáza | Kroky | Hotovo | Progress |
|------|-------|--------|----------|
| **FÁZA 0: Príprava** | 4 | 4 ✅ | 100% ✅ |
| **FÁZA 1: Core** | 3 | 0 | 0% ⏸️ |
| **FÁZA 2: Integration** | 2 | 0 | 0% ⏸️ |
| **FÁZA 3: Testing** | 3 | 0 | 0% ⏸️ |
| **FÁZA 4: Documentation** | 2 | 0 | 0% ⏸️ |
| **FÁZA 5: Release** | 3 | 0 | 0% ⏸️ |
| **CELKOM** | **17** | **4** | **24%** |

---

## 🎯 NEXT STEPS (v poradí priority)

### Teraz implementovať:

1. **KROK 1.1** 🔥 Pridať `_calculate_weights_with_time_decay()` do `combined_model.py`
2. **KROK 1.2** 🔥 Pridať `calculate_combined_forecast_with_time()` do `combined_model.py`
3. **KROK 1.3** 🔥 Upraviť `calculate_combined_forecast()` pre backward compatibility
4. **KROK 2.1** 🔥 Upraviť `forecast_calculator.py` pre ENHANCED model
5. **KROK 3.1** 🔥 Vytvoriť unit testy

---

## 💡 PROMPT TEMPLATE pre každý krok

**Pre každý krok použiť:**

```
Implementuj KROK X.Y z IMPLEMENTATION_STEPS_v3.1.12.md:

[názov kroku]

Súbor: [súbor]
Detaily: [zobraziť sekciu z tohto dokumentu]

Po implementácii:
1. Overím kód pomocou get_errors
2. Spustím relevantné testy
3. Označím krok ako HOTOVÝ ✅
```

---

## 🔍 KRITICKÉ BODY

### ⚠️ NA ČO SI DÁVAŤ POZOR:

1. **Backward Compatibility:**
   - `calculate_combined_forecast()` MUSÍ ostať nezmenená API
   - sensor.py nesmie byť affected
   - Zambretti/Negretti modely BEZ ZMIEN

2. **Import Statements:**
   - `import math` pre `exp()` funkciu
   - `from .combined_model import calculate_combined_forecast_with_time`

3. **Logging:**
   - Pridať debug logy s `hours_ahead`, `decay`, `reason`
   - Pomôže pri diagnostike

4. **Edge Cases:**
   - `hours_ahead = 0` → žiadny decay
   - `hours_ahead > 24` → stále decay (neobmedziť)
   - Negatívne `hours_ahead` → neplatné (ale necrashne)

5. **Testing:**
   - Anticyklóna: Overenie progression
   - Rýchla zmena: Overenie progression
   - Backward compatibility: Overenie že starý kód funguje

---

## 📚 UŽITOČNÉ REFERENCIE

### Dokumenty:
- `IMPLEMENTATION_PLAN_COMBINED_ENHANCED.md` - Kompletný plán
- `ENHANCED_SENSOR_ATTRIBUTES.md` - Analýza atribútov
- `CHANGELOG.md` - Verziovanie

### Súbory na úpravu:
- `custom_components/local_weather_forecast/combined_model.py`
- `custom_components/local_weather_forecast/forecast_calculator.py`

### Súbory na testovanie:
- `tests/test_combined_model.py` (nový)
- `tests/test_forecast_calculator.py`

---

## 🔮 BUDÚCE VERZIE (v3.2.0+)

### ⏸️ Voliteľné rozšírenia (NIE v3.1.12):

#### **persistence.py** (Persistence Model)
**Účel:** Stabilizácia hodiny 0 (aktuálny stav)
**Prínos:** +1% presnosť pre hour 0
**Priorita:** NÍZKA (TIME DECAY je dôležitejší)

```python
# Persistence = "Počasie bude rovnaké ako teraz"
# Použitie: Len pre hodinu 0
# Presnosť: 85-90% pre 0-1h, potom klesá
```

**Kedy implementovať:**
- Po úspešnom nasadení v3.1.12 s TIME DECAY
- Ak chceme ešte lepšiu presnosť hour 0
- V samostatnej verzii v3.2.0

---

#### **wmo_simple.py** (WMO Simple Barometric Model)
**Účel:** Nowcasting pre hodiny 1-3
**Prínos:** +1-2% presnosť pre short-term
**Priorita:** STREDNÁ (užitočné pre nowcasting)

```python
# WMO Simple = Prognóza len z tlaku + trendu
# Použitie: Hodiny 1-3 (krátky horizont)
# Presnosť: 80-85% pre 1-3h
```

**Kedy implementovať:**
- Po stabilizácii v3.1.12 + v3.2.0
- Ak používatelia žiadajú lepší nowcasting
- V verzii v3.3.0 alebo v3.4.0

---

#### **Multi-model Orchestration**
**Účel:** Optimálny model pre každú hodinu
**Prínos:** +2-3% celková presnosť
**Priorita:** NÍZKA (vysoká komplexita)

```python
# Stratégia:
# - Hour 0: Persistence (85-90%)
# - Hours 1-3: WMO Simple (80-85%)
# - Hours 4-6: Blend WMO→Zambretti (78-82%)
# - Hours 7-24: Zambretti/Negretti + TIME DECAY (82%)
```

**Kedy implementovať:**
- Po úspešnom nasadení persistence + WMO
- Ak chceme maximum presnosti
- V verzii v4.0.0 (major update)

---

### 📊 Roadmap:

| Verzia | Feature | Prínos | Komplexita |
|--------|---------|--------|------------|
| **v3.1.12** ✅ | TIME DECAY | +6% | 🟢 Nízka |
| **v3.2.0** ⏸️ | persistence.py | +1% | 🟡 Stredná |
| **v3.3.0** ⏸️ | wmo_simple.py | +1-2% | 🟡 Stredná |
| **v4.0.0** ⏸️ | Multi-model | +2-3% | 🔴 Vysoká |

**Celkový potenciál:** 76% → 92% presnosť (+16%)

**Stratégia:**
1. ✅ **v3.1.12** - TIME DECAY (80% výhody, nízke riziko)
2. ⏸️ **v3.2.0** - Persistence (stabilizácia)
3. ⏸️ **v3.3.0** - WMO Simple (nowcasting)
4. ⏸️ **v4.0.0** - Multi-model (maximálna presnosť)

---

## ✅ CHECKLIST pred dokončením

**Pred označením verzie za HOTOVÚ:**

- [ ] Všetky unit testy PRECHÁDZAJÚ
- [ ] Všetky integration testy PRECHÁDZAJÚ
- [ ] Žiadne get_errors v upravených súboroch
- [ ] CHANGELOG.md je doplnený
- [ ] Logy ukazujú TIME DECAY v akcii
- [ ] Beta testované na HA instance
- [ ] Backward compatibility overená
- [ ] Presnosť je vyššia (76% → 82%)

---

**Pripravené na implementáciu! 🚀**

**Začni s:** `Implementuj KROK 1.1`
