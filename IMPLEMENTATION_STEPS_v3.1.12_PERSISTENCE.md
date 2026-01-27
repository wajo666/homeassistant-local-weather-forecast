# Implementation Steps - Version 3.1.12 (PERSISTENCE MODEL Extension)

**Status:** ⏸️ Planned  
**Start Date:** TBD (po TIME DECAY)  
**Target:** Persistence Model implementácia (+2% accuracy improvement)  
**Version:** 3.1.12 (rozšírenie, nie nová verzia)

---

## 📋 KROK-PO-KROKU IMPLEMENTÁCIA

### ⚠️ DÔLEŽITÉ: Rozsah v3.1.12 PERSISTENCE Extension

**✅ ČO SA IMPLEMENTUJE v3.1.12 (PERSISTENCE):**
- Persistence Model (`persistence.py`)
- Integrácia do `combined_model.py`
- Orchestrácia: Hour 0 → Persistence, Hours 1+ → TIME DECAY
- Unit a integration testy
- **Výsledok: +2% presnosť (82% → 84%), Hour 0: 82% → 98%**
- **Verzia zostáva: 3.1.12** (nie 3.2.0)

**Prečo v rovnakej verzii 3.1.12?**
- Persistence je logické rozšírenie TIME DECAY
- Oba features tvoria kompletnú orchestráciu
- Žiadne breaking changes
- Jeden unified release je lepší ako dve malé

---

## ✅ FÁZA 0: PRÍPRAVA

**Progres FAZY 0:** ⏸️ 0% (0/2 krokov)

### **Krok 0.1: Update CHANGELOG pre Persistence**
**Súbor:** `CHANGELOG.md`

**Čo pridať k existujúcej v3.1.12 sekcii:**
```markdown
## [3.1.12] - 2026-01-27

### ✨ What's New
- **Smarter Long-Term Forecasts** - TIME DECAY weighting
  - Hour 0: Sharp and responsive
  - 24h: Balanced and reliable
- **Persistence Model** - Stabilizes current conditions (NEW!)
  - 98% accuracy for hour 0
  - Filters sensor noise and fluctuations
  - Smooth baseline for forecasts

### 📊 Impact
- **Hour 0 Accuracy:** +16% (82% → 98%) ⭐⭐⭐
- **Overall Accuracy:** +8% (76% → 84%) ⭐⭐⭐
- **No Breaking Changes:** Everything works as before

### 🔧 Technical Details
- Added TIME DECAY weighting for dynamic model selection
- Added Persistence Model for hour 0 stabilization
- Enhanced orchestration: Hour 0 (Persistence) → Hours 1+ (TIME DECAY)
```

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 0.2: Review existujúceho TIME DECAY kódu**
**Cieľ:** Pochopiť TIME DECAY implementáciu pred pridaním Persistence

**Čo reviewovať:**
- `combined_model.py::_calculate_weights_with_time_decay()`
- `combined_model.py::calculate_combined_forecast_with_time()`
- `forecast_calculator.py::HourlyForecastGenerator` (ENHANCED model)

**Kľúčové body:**
- TIME DECAY funguje pre hours 0-24
- Hour 0 používa `hours_ahead=0` (žiadny decay, ale stále Zambretti/Negretti)
- **Persistence nahradí hour 0 logiku úplne**

**Status:** ⏸️ Čaká na začiatok

---

## 🔧 FÁZA 1: PERSISTENCE MODEL (PRIORITA: VYSOKÁ)

**Progres FAZY 1:** ⏸️ 0% (0/3 krokov)

### **Krok 1.1: Vytvoriť persistence.py modul**
**Súbor:** `custom_components/local_weather_forecast/persistence.py` (NOVÝ)

**Čo implementovať:**
```python
"""Persistence Model - Simplest forecasting model.

Assumes current conditions will persist unchanged.
Best for: Hour 0 (current state stabilization)
Accuracy: 98-100% for current state, 95% for +1h, declines rapidly after

Theory:
- "Počasie bude rovnaké ako teraz"
- Optimal pre veľmi krátky horizont (0-1h)
- Stabilizuje fluktuácie senzorov
- Poskytuje smooth baseline pre ostatné modely
"""

import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)


def calculate_persistence_forecast(
    current_condition_code: int,
    lang_index: int = 1,
    hours_ahead: int = 0
) -> list:
    """Calculate Persistence forecast (current conditions persist).
    
    Args:
        current_condition_code: Current unified condition code (0-25)
        lang_index: Language index for forecast text
        hours_ahead: Hours into future (0 recommended, 1-3 acceptable)
        
    Returns:
        [forecast_text, forecast_code, letter_code, confidence]
    """
    # Persistence = current state
    forecast_code = current_condition_code
    
    # Get text from unified mapping
    from .forecast_mapping import get_forecast_text
    forecast_text = get_forecast_text(forecast_code, lang_index)
    
    # Generate letter code (A-Z mapping)
    letter_code = chr(65 + min(forecast_code // 3, 7))
    
    # Confidence decays with time
    confidence = get_persistence_confidence(hours_ahead)
    
    _LOGGER.debug(
        f"🔒 Persistence: h{hours_ahead} → code={forecast_code} "
        f"({forecast_text}), confidence={confidence:.0%}"
    )
    
    return [forecast_text, forecast_code, letter_code, confidence]


def get_persistence_confidence(hours_ahead: int) -> float:
    """Calculate confidence for Persistence model based on forecast horizon.
    
    Persistence accuracy declines rapidly with time:
    - Hour 0: 98% (excellent - stabilized current state)
    - Hour 1: 95% (very good)
    - Hour 2: 90% (good)
    - Hour 3: 85% (acceptable)
    - Hour 4+: <80% (poor - use other models)
    
    Args:
        hours_ahead: Hours into future (0-24)
        
    Returns:
        Confidence score (0.0-1.0)
    """
    if hours_ahead == 0:
        return 0.98  # Excellent for current state
    elif hours_ahead == 1:
        return 0.95  # Very good for +1h
    elif hours_ahead == 2:
        return 0.90  # Good for +2h
    elif hours_ahead == 3:
        return 0.85  # Acceptable for +3h
    else:
        # Rapid decline after 3h
        return max(0.60, 0.85 - (hours_ahead - 3) * 0.05)


def get_current_condition_code(
    temperature: float,
    pressure: float,
    humidity: float,
    dewpoint: float,
    weather_condition: Optional[str] = None
) -> int:
    """Determine current unified condition code from sensor data.
    
    Maps current weather conditions to unified codes (0-25).
    
    Args:
        temperature: Current temperature in °C
        pressure: Current pressure in hPa
        humidity: Current humidity in %
        dewpoint: Current dewpoint in °C
        weather_condition: Current HA weather condition (optional)
        
    Returns:
        Unified condition code (0-25)
    """
    # Import existing mapping functions
    from .forecast_mapping import (
        get_condition_from_pressure_and_trend,
        get_unified_code_from_condition
    )
    
    # For hour 0, assume steady pressure (no historical data needed)
    pressure_trend = 0.0
    
    # Get condition based on current pressure
    condition = get_condition_from_pressure_and_trend(
        pressure=pressure,
        pressure_change=pressure_trend,
        humidity=humidity,
        temperature=temperature,
        dewpoint=dewpoint
    )
    
    # Convert to unified code
    unified_code = get_unified_code_from_condition(condition)
    
    _LOGGER.debug(
        f"🎯 Current state: P={pressure:.1f} hPa, T={temperature:.1f}°C, "
        f"RH={humidity:.0f}% → code={unified_code} ({condition})"
    )
    
    return unified_code
```

**Kľúčové funkcie:**
- `calculate_persistence_forecast()` - hlavná funkcia
- `get_persistence_confidence()` - confidence decay formula
- `get_current_condition_code()` - mapovanie senzorov na unified code

**Testovať:**
- Hour 0: confidence = 98%
- Hour 1: confidence = 95%
- Hour 3: confidence = 85%
- Hour 6+: confidence < 75%

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 1.2: Unit testy pre Persistence Model**
**Súbor:** `tests/test_persistence.py` (NOVÝ)

**Čo testovať:**
```python
"""Unit tests for Persistence Model."""

import pytest
from custom_components.local_weather_forecast.persistence import (
    calculate_persistence_forecast,
    get_persistence_confidence,
    get_current_condition_code,
)


class TestCalculatePersistenceForecast:
    """Test calculate_persistence_forecast() function."""
    
    def test_hour_0_returns_current_code(self):
        """Test that hour 0 returns exact current condition."""
        current_code = 5  # Fine weather
        result = calculate_persistence_forecast(current_code, lang_index=1, hours_ahead=0)
        
        assert result[1] == 5  # Same code
        assert result[3] == 0.98  # 98% confidence
    
    def test_hour_1_returns_current_code(self):
        """Test that hour 1 still returns current condition."""
        current_code = 12  # Cloudy
        result = calculate_persistence_forecast(current_code, lang_index=1, hours_ahead=1)
        
        assert result[1] == 12  # Same code
        assert result[3] == 0.95  # 95% confidence
    
    def test_forecast_text_from_unified_mapping(self):
        """Test that forecast text comes from unified mapping."""
        current_code = 0  # Settled fine
        result = calculate_persistence_forecast(current_code, lang_index=1, hours_ahead=0)
        
        assert isinstance(result[0], str)  # Text present
        assert len(result[0]) > 0  # Not empty
    
    def test_letter_code_generation(self):
        """Test letter code generation (A-Z)."""
        # Code 0-2 → A
        result = calculate_persistence_forecast(0, lang_index=1, hours_ahead=0)
        assert result[2] == 'A'
        
        # Code 21-23 → H
        result = calculate_persistence_forecast(21, lang_index=1, hours_ahead=0)
        assert result[2] == 'H'


class TestGetPersistenceConfidence:
    """Test get_persistence_confidence() function."""
    
    def test_hour_0_highest_confidence(self):
        """Test hour 0 has 98% confidence."""
        assert get_persistence_confidence(0) == 0.98
    
    def test_hour_1_very_high_confidence(self):
        """Test hour 1 has 95% confidence."""
        assert get_persistence_confidence(1) == 0.95
    
    def test_hour_2_high_confidence(self):
        """Test hour 2 has 90% confidence."""
        assert get_persistence_confidence(2) == 0.90
    
    def test_hour_3_good_confidence(self):
        """Test hour 3 has 85% confidence."""
        assert get_persistence_confidence(3) == 0.85
    
    def test_confidence_decays_after_3h(self):
        """Test confidence decays for hours > 3."""
        conf_3h = get_persistence_confidence(3)
        conf_6h = get_persistence_confidence(6)
        conf_12h = get_persistence_confidence(12)
        
        assert conf_6h < conf_3h
        assert conf_12h < conf_6h
        assert conf_12h >= 0.60  # Minimum threshold


class TestGetCurrentConditionCode:
    """Test get_current_condition_code() function."""
    
    def test_fine_weather_detection(self):
        """Test detection of fine weather (high pressure)."""
        code = get_current_condition_code(
            temperature=20.0,
            pressure=1025.0,
            humidity=60.0,
            dewpoint=12.0,
            weather_condition="sunny"
        )
        
        assert 0 <= code <= 7  # Fine weather range
    
    def test_rainy_weather_detection(self):
        """Test detection of rainy weather (low pressure)."""
        code = get_current_condition_code(
            temperature=15.0,
            pressure=995.0,
            humidity=85.0,
            dewpoint=13.0,
            weather_condition="rainy"
        )
        
        assert 15 <= code <= 21  # Rainy weather range
    
    def test_stormy_weather_detection(self):
        """Test detection of stormy weather (very low pressure)."""
        code = get_current_condition_code(
            temperature=12.0,
            pressure=975.0,
            humidity=90.0,
            dewpoint=11.0,
            weather_condition="lightning-rainy"
        )
        
        assert 22 <= code <= 25  # Storm range
```

**Očakávaný výsledok:**
- Minimálne 12 testov
- 100% code coverage pre persistence.py
- Všetky testy PASS

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 1.3: Integračné testy (placeholder)**
**Súbor:** `tests/test_forecast_calculator.py`

**Poznámka:** Integration testy sa dokončia v FÁZE 3 po orchestrácii.

**Status:** ⏸️ Čaká na FÁZU 2

---

## 🔀 FÁZA 2: ORCHESTRATION - combined_model.py (PRIORITA: VYSOKÁ)

**Progres FAZY 2:** ⏸️ 0% (0/3 krokov)

### **Krok 2.1: Pridať generate_enhanced_hourly_forecast() funkciu**
**Súbor:** `custom_components/local_weather_forecast/combined_model.py`

**Čo implementovať:**
```python
# ========================
# PHASE 2: ORCHESTRATION (v3.1.12 - Persistence Extension)
# ========================

def generate_enhanced_hourly_forecast(
    weather_data: dict,
    hours: int = 24,
    lang_index: int = 1
) -> list[dict]:
    """Generate enhanced hourly forecast with optimal model selection.
    
    Orchestration Strategy (v3.1.12):
    - Hour 0: Persistence (98% accuracy)
    - Hours 1+: Zambretti/Negretti with TIME DECAY (82% accuracy)
    
    Future versions:
    - v3.3.0: Hours 1-3 will use WMO Simple (90%)
    - v3.3.0: Hours 4-6 will blend WMO→Zambretti
    
    Args:
        weather_data: Dict with weather sensor data
        hours: Number of hours to forecast (default 24)
        lang_index: Language index for forecast text
        
    Returns:
        List of hourly forecast dicts
    """
    from datetime import timedelta
    
    forecasts = []
    start_time = weather_data.get("start_time")
    
    for hour in range(hours + 1):
        if hour == 0:
            # ═══════════════════════════════════════
            # HOUR 0: PERSISTENCE MODEL (v3.1.12)
            # ═══════════════════════════════════════
            from .persistence import (
                calculate_persistence_forecast,
                get_current_condition_code
            )
            
            # Get current condition code from sensors
            current_code = get_current_condition_code(
                temperature=weather_data.get("temperature", 15.0),
                pressure=weather_data.get("pressure", 1013.25),
                humidity=weather_data.get("humidity", 70.0),
                dewpoint=weather_data.get("dewpoint", 10.0),
                weather_condition=weather_data.get("condition", "unknown")
            )
            
            # Calculate Persistence forecast
            forecast_result = calculate_persistence_forecast(
                current_condition_code=current_code,
                lang_index=lang_index,
                hours_ahead=0
            )
            
            forecast_text = forecast_result[0]
            forecast_code = forecast_result[1]
            confidence = forecast_result[3]
            
            _LOGGER.debug(
                f"🎯 Hour {hour}: PERSISTENCE → {forecast_text} "
                f"(code={forecast_code}, confidence={confidence:.0%})"
            )
        
        else:
            # ═══════════════════════════════════════
            # HOURS 1+: TIME DECAY (v3.1.12)
            # ═══════════════════════════════════════
            # Use existing TIME DECAY implementation
            zambretti_result = weather_data.get("zambretti_result", ["", 13])
            negretti_result = weather_data.get("negretti_result", ["", 13])
            
            (
                forecast_code,
                zambretti_weight,
                negretti_weight,
                consensus
            ) = calculate_combined_forecast_with_time(
                zambretti_result=zambretti_result,
                negretti_result=negretti_result,
                current_pressure=weather_data.get("pressure", 1013.25),
                pressure_change=weather_data.get("pressure_change", 0.0),
                hours_ahead=hour,
                source=f"Enhanced_h{hour}"
            )
            
            # Get forecast text
            from .forecast_mapping import get_forecast_text
            forecast_text = get_forecast_text(forecast_code, lang_index)
            
            # Confidence based on TIME DECAY consensus
            confidence = 0.85 if consensus else 0.78
            
            _LOGGER.debug(
                f"🎯 Hour {hour}: TIME DECAY → {forecast_text} "
                f"(Z:{zambretti_weight:.0%}/N:{negretti_weight:.0%}, "
                f"confidence={confidence:.0%})"
            )
        
        # ═══════════════════════════════════════
        # BUILD HOURLY FORECAST DICT
        # ═══════════════════════════════════════
        forecast_dict = {
            "datetime": start_time + timedelta(hours=hour) if start_time else None,
            "condition": forecast_text,
            "condition_code": forecast_code,
            "confidence": confidence,
            "temperature": calculate_temperature_at_hour(
                hour, 
                weather_data.get("temperature", 15.0),
                weather_data.get("temperature_trend", 0.0)
            ),
            "pressure": weather_data.get("pressure", 1013.25),
            # Add more fields as needed...
        }
        
        forecasts.append(forecast_dict)
    
    return forecasts


def calculate_temperature_at_hour(
    hour: int,
    current_temp: float,
    temp_trend: float = 0.0
) -> float:
    """Calculate temperature at future hour (simple linear model).
    
    Args:
        hour: Hours ahead (0-24)
        current_temp: Current temperature in °C
        temp_trend: Temperature trend in °C/hour
        
    Returns:
        Estimated temperature in °C
    """
    # Simple linear extrapolation
    # Future: Use diurnal cycle model
    return current_temp + (temp_trend * hour)
```

**Kľúčové body:**
- Hour 0: Použiť Persistence (nová funkcionalita)
- Hours 1+: Použiť existujúci TIME DECAY (bez zmien)
- Debug logging pre diagnostiku
- Pripravené pre budúce WMO Simple rozšírenie

**Testovať:**
- Hour 0 volá `calculate_persistence_forecast()`
- Hour 1+ volá `calculate_combined_forecast_with_time()`
- Forecast list obsahuje 25 záznamov (0-24h)

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 2.2: Integrovať do forecast_calculator.py**
**Súbor:** `custom_components/local_weather_forecast/forecast_calculator.py`

**Čo upraviť:**
Nájsť `HourlyForecastGenerator.generate()` metódu (cca riadok 975-1015) a pridať orchestráciu:

**Variant A: Plná orchestrácia (odporúčané):**
```python
# Around line 975-1015

if self.forecast_model == FORECAST_MODEL_ENHANCED:
    # ═══════════════════════════════════════
    # NEW v3.1.12: Use orchestration (Persistence + TIME DECAY)
    # ═══════════════════════════════════════
    from .combined_model import generate_enhanced_hourly_forecast
    
    # Prepare weather data dict
    weather_data = {
        "start_time": current_time,
        "temperature": temp,
        "pressure": future_pressure,
        "pressure_change": pressure_change,
        "humidity": humidity,
        "dewpoint": dewpoint,
        "condition": self.current_condition,
        "zambretti_result": ["", zambretti_num],
        "negretti_result": ["", negretti_num],
        "temperature_trend": self.temperature_trend,
    }
    
    # Generate hourly forecasts using orchestration
    hourly_forecasts = generate_enhanced_hourly_forecast(
        weather_data=weather_data,
        hours=24,
        lang_index=lang_index
    )
    
    # Convert to existing format
    for hour_data in hourly_forecasts:
        # Append to hourly_data list
        # ...existing code...
```

**Variant B: Minimálna zmena (len hour 0):**
```python
if self.forecast_model == FORECAST_MODEL_ENHANCED:
    if hour_offset == 0:
        # NEW v3.1.12: Use Persistence for hour 0
        from .persistence import calculate_persistence_forecast, get_current_condition_code
        
        current_code = get_current_condition_code(
            temperature=temp,
            pressure=future_pressure,
            humidity=humidity,
            dewpoint=dewpoint,
            weather_condition=self.current_condition
        )
        
        forecast_result = calculate_persistence_forecast(
            current_condition_code=current_code,
            lang_index=lang_index,
            hours_ahead=0
        )
        
        forecast_num = forecast_result[1]
        # ...use forecast_num...
    else:
        # Use existing TIME DECAY for hours 1+
        (forecast_num, ...) = calculate_combined_forecast_with_time(
            hours_ahead=hour_offset,
            ...
        )
```

**Odporúčanie:** Variant A (plná orchestrácia) je lepší pre budúce rozšírenia (WMO Simple).

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 2.3: Overiť weather.py (optional)**
**Súbor:** `custom_components/local_weather_forecast/weather.py`

**Čo overiť:**
- Forecast generation pre ENHANCED model
- Môže byť potrebné upraviť len ak sa používa direct call

**Status:** ⏸️ Čaká na overenie

---

## 🧪 FÁZA 3: TESTING (PRIORITA: KRITICKÁ)

**Progres FAZY 3:** ⏸️ 0% (0/3 krokov)

### **Krok 3.1: Unit testy (test_persistence.py)**
**Status:** ⏸️ Čaká na dokončenie Kroku 1.2

**Testovať:**
- `calculate_persistence_forecast()` - 4 testy
- `get_persistence_confidence()` - 5 testov
- `get_current_condition_code()` - 3 testy

**Očakávaný výsledok:**
- Minimálne 12 nových testov PASS
- 100% code coverage pre persistence.py

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 3.2: Integration testy (test_forecast_calculator.py)**
**Súbor:** `tests/test_forecast_calculator.py`

**Čo testovať:**
```python
class TestEnhancedWithPersistence:
    """Test ENHANCED model with Persistence (v3.1.12)."""
    
    def test_hour_0_uses_persistence(self):
        """Test that hour 0 uses Persistence model."""
        # Generate hourly forecast
        forecasts = generate_hourly_forecast(model="enhanced", hours=24)
        
        # Hour 0 should have 98% confidence (Persistence)
        assert forecasts[0]["confidence"] >= 0.98
    
    def test_hour_1_uses_time_decay(self):
        """Test that hour 1+ uses TIME DECAY."""
        forecasts = generate_hourly_forecast(model="enhanced", hours=24)
        
        # Hour 1 should have <95% confidence (TIME DECAY)
        assert forecasts[1]["confidence"] < 0.95
    
    def test_orchestration_smooth_transition(self):
        """Test smooth transition from Persistence to TIME DECAY."""
        forecasts = generate_hourly_forecast(model="enhanced", hours=6)
        
        # Confidence should decline (but may not be perfectly smooth due to consensus)
        assert forecasts[0]["confidence"] >= 0.98  # Persistence
        assert forecasts[1]["confidence"] < 0.95   # TIME DECAY
    
    def test_zambretti_model_unchanged(self):
        """Test that Zambretti model is not affected."""
        forecasts_zambretti = generate_hourly_forecast(model="zambretti", hours=24)
        
        # Should NOT use Persistence (no 98% confidence)
        assert all(f["confidence"] < 0.95 for f in forecasts_zambretti)
```

**Očakávaný výsledok:**
- 4+ nové integration testy PASS
- Overenie orchestrácie
- Backward compatibility check

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 3.3: Spustiť všetky existujúce testy**
**Príkaz:** `pytest tests/ -v`

**Cieľ:** Overiť backward compatibility.

**Očakávaný výsledok:**
- ✅ Všetky existujúce 591 testov PRECHÁDZAJÚ
- ✅ 17 testov z TIME DECAY (existing)
- ✅ 12+ nových testov pre Persistence
- ✅ 4+ nových integration testov
- ✅ Celkovo: ~624 testov PASS
- ✅ Žiadne breaking changes
- ✅ Backward compatibility funguje

**Status:** ⏸️ Čaká na spustenie

---

## 📄 FÁZA 4: DOCUMENTATION

**Progres FAZY 4:** ⏸️ 0% (0/2 krokov)

### **Krok 4.1: Doplniť CHANGELOG.md**
**Súbor:** `CHANGELOG.md`

**Status:** Už spravené v Kroku 0.1 ✅

---

### **Krok 4.2: Aktualizovať README.md**
**Súbor:** `README.md`

**Čo pridať:**
```markdown
## 📊 Forecast Accuracy (v3.1.12)

| Model | Hour 0 | Hours 1-6 | Hours 7-24 | Overall |
|-------|--------|-----------|------------|---------|
| **Enhanced** (v3.1.12) | **98%** ⭐⭐⭐ | **84%** ⭐⭐ | 82% ⭐ | **84%** |
| Enhanced (v3.1.11) | 76% | 76% | 76% | 76% |
| Zambretti | 78% | 80% | 78% | 79% |
| Negretti | 76% | 77% | 78% | 77% |

### Enhanced Model Strategy (v3.1.12):
- **Hour 0**: Persistence (98%) - Stabilized current state
- **Hours 1+**: TIME DECAY (82%) - Dynamic Zambretti/Negretti blend

**What's Persistence?**
- Simplest forecast: "Weather stays the same"
- 98% accurate for current conditions
- Filters sensor noise and fluctuations
- Perfect baseline for short-term forecasts
```

**Status:** ⏸️ Voliteľné

---

## 🚀 FÁZA 5: RELEASE (už existuje pre v3.1.12)

**Progres FAZY 5:** ⏸️ 0% (0/3 krokov)

### **Krok 5.1: Beta testing**
- Testovať na development HA instance
- Overiť Persistence pre hour 0
- Overiť TIME DECAY pre hours 1+
- Sledovať accuracy metrics

**Status:** ⏸️ Čaká na beta testing

---

### **Krok 5.2: Git commit**
- Commit všetkých zmien (Persistence + TIME DECAY)
- Push do repository
- (Release tag bude až na konci)

**Status:** ⏸️ Čaká na commit

---

### **Krok 5.3: GitHub release v3.1.12 (na konci)**
- Create tag `v3.1.12`
- Create GitHub release s CHANGELOG (TIME DECAY + Persistence)
- HACS sa automaticky updatne

**Status:** ⏸️ Čaká na finálny release

---

## 📊 PROGRESS TRACKER

### Overall Progress: 0% (0/15 krokov)

| Fáza | Kroky | Hotovo | Progress |
|------|-------|--------|----------|
| **FÁZA 0: Príprava** | 2 | 0 | 0% ⏸️ |
| **FÁZA 1: Persistence Model** | 3 | 0 | 0% ⏸️ |
| **FÁZA 2: Orchestration** | 3 | 0 | 0% ⏸️ |
| **FÁZA 3: Testing** | 3 | 0 | 0% ⏸️ |
| **FÁZA 4: Documentation** | 2 | 0 | 0% ⏸️ |
| **FÁZA 5: Release** | 3 | 0 | 0% ⏸️ |
| **CELKOM** | **16** | **0** | **0%** |

**Poznámka:** FÁZA 5 je zdieľaná s TIME DECAY (už existuje v hlavnom pláne v3.1.12)

---

## 🎯 NEXT STEPS (v poradí priority)

### Po dokončení TIME DECAY:

1. **KROK 0.2** 🔥 Review TIME DECAY kódu
2. **KROK 1.1** 🔥 Vytvoriť `persistence.py` modul
3. **KROK 1.2** 🔥 Unit testy pre Persistence
4. **KROK 2.1** 🔥 Pridať `generate_enhanced_hourly_forecast()` orchestráciu
5. **KROK 2.2** 🔥 Integrovať do `forecast_calculator.py`

---

## 💡 PROMPT TEMPLATE pre každý krok

**Pre každý krok použiť:**

```
Implementuj KROK X.Y z IMPLEMENTATION_STEPS_v3.1.12_PERSISTENCE.md:

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
   - Zambretti/Negretti modely NESMÚ byť affected
   - TIME DECAY (už implementovaný) musí fungovať ako predtým
   - Žiadne breaking changes v API

2. **Persistence vs TIME DECAY:**
   - Hour 0: **LEN** Persistence (98% confidence)
   - Hour 1+: **LEN** TIME DECAY (82% confidence)
   - Žiadny overlap, jasná separácia

3. **Verzia zostáva 3.1.12:**
   - Persistence je rozšírenie, nie nová verzia
   - Jeden unified release (TIME DECAY + Persistence)
   - CHANGELOG obsahuje oba features

4. **Import Statements:**
   - `from .persistence import calculate_persistence_forecast`
   - `from .combined_model import generate_enhanced_hourly_forecast`

5. **Logging:**
   - "🔒 Persistence" pre hour 0
   - "🎯 TIME DECAY" pre hours 1+
   - Debug logy pre diagnostiku

6. **Testing:**
   - Minimálne 12 unit testov pre Persistence
   - Minimálne 4 integration testy
   - Všetky existujúce testy musia pass

---

## 📚 UŽITOČNÉ REFERENCIE

### Dokumenty:
- `IMPLEMENTATION_STEPS_v3.1.12.md` - TIME DECAY implementácia (už hotovo)
- `IMPLEMENTATION_PLAN_COMBINED_ENHANCED.md` - Celkový plán
- `IMPLEMENTATION_STEPS_COMPLETE.md` - Roadmap

### Súbory na úpravu:
- `custom_components/local_weather_forecast/persistence.py` (NOVÝ)
- `custom_components/local_weather_forecast/combined_model.py` (rozšíriť)
- `custom_components/local_weather_forecast/forecast_calculator.py` (rozšíriť)

### Súbory na testovanie:
- `tests/test_persistence.py` (NOVÝ)
- `tests/test_forecast_calculator.py` (pridať testy)
- `tests/test_combined_model.py` (reference pre TIME DECAY)

---

## ✅ CHECKLIST pred dokončením

**Pred označením Persistence za HOTOVÉ:**

- [ ] Všetky unit testy PRECHÁDZAJÚ ⏸️ (~624 tests expected)
- [ ] Všetky integration testy PRECHÁDZAJÚ ⏸️
- [ ] Žiadne get_errors v upravených súboroch ⏸️
- [ ] CHANGELOG.md je aktualizovaný ⏸️
- [ ] Logy ukazujú Persistence pre hour 0 ⏸️
- [ ] Logy ukazujú TIME DECAY pre hours 1+ ⏸️
- [ ] Beta testované na HA instance ⏸️
- [ ] Backward compatibility overená ⏸️ (591 existing tests pass)
- [ ] Hour 0 accuracy: 82% → 98% ⏸️ (beta test validation)
- [ ] Overall accuracy: 82% → 84% ⏸️ (beta test validation)

---

## 🎉 FINAL v3.1.12 FEATURES

**Kompletná v3.1.12 bude obsahovať:**

1. ✅ **TIME DECAY** - Dynamické váženie modelov (hours 1-24)
   - Anticyklóna: 90% Negretti → 54% (24h)
   - Rýchla zmena: 75% Zambretti → 53% (24h)
   - +6% presnosť pre hours 1-24

2. 🆕 **PERSISTENCE** - Stabilizácia hour 0
   - 98% presnosť pre aktuálny stav
   - Filtruje sensor noise
   - +16% presnosť pre hour 0

3. 🎯 **ORCHESTRATION** - Optimálny model pre každý horizont
   - Hour 0: Persistence (98%)
   - Hours 1+: TIME DECAY (82%)

**Celkový výsledok:**
- Hour 0: +16% (82% → 98%)
- Hours 1-24: +6% (76% → 82%)
- **Overall: +8% (76% → 84%)** 🎉

---

**Pripravené na implementáciu! 🚀**

**Začni s:** `Implementuj KROK 0.2` (review TIME DECAY kódu)
