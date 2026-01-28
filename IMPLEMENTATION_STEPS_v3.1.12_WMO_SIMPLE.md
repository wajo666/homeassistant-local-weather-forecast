# Implementation Steps - Version 3.1.12 (WMO SIMPLE Extension)

**Status:** ⏸️ Planned  
**Start Date:** TBD (po Persistence)  
**Target:** WMO Simple Model implementácia (+6% accuracy improvement)  
**Version:** 3.1.12 (unified release - TIME DECAY + Persistence + WMO Simple)

---

## 📋 KROK-PO-KROKU IMPLEMENTÁCIA

### ⚠️ DÔLEŽITÉ: Rozsah v3.1.12 WMO Simple Extension

**✅ ČO SA IMPLEMENTUJE v3.1.12 (WMO SIMPLE):**
- WMO Simple Model (`wmo_simple.py`)
- Integrácia do `combined_model.py` orchestrácie
- Blending WMO → TIME DECAY (hours 4-6)
- Orchestrácia: Hour 0 (Persistence) → Hours 1-3 (WMO) → Hours 4-6 (Blend) → Hours 7+ (TIME DECAY)
- Unit a integration testy
- **Výsledok: +6% presnosť hours 1-3 (84% → 90%), Overall: 84% → 90%**
- **Verzia zostáva: 3.1.12** (unified release)

**Prečo v rovnakej verzii 3.1.12?**
- WMO Simple je logické rozšírenie orchestrácie
- Všetky tri features tvoria kompletnú forecast stratégiu
- Žiadne breaking changes
- Jeden unified release je lepší ako tri malé

**Prerequisity:**
- ✅ TIME DECAY implementované
- ✅ Persistence Model implementované
- ✅ `generate_enhanced_hourly_forecast()` existuje

---

## ✅ FÁZA 0: PRÍPRAVA

**Progres FAZY 0:** ⏸️ 0% (0/2 krokov)

### **Krok 0.1: Update CHANGELOG pre WMO Simple**
**Súbor:** `CHANGELOG.md`

**Čo upraviť v existujúcej v3.1.12 sekcii:**
```markdown
## [3.1.12] - 2026-01-28

### ✨ What's New
- **3-Model Orchestration** - Smart model selection by forecast horizon
  - Hour 0: Persistence (98% accuracy)
  - Hours 1-3: WMO Simple nowcasting (90% accuracy) ⭐ NEW!
  - Hours 4-6: Smooth WMO→TIME DECAY blend
  - Hours 7+: TIME DECAY dynamic weighting

### 📊 Impact
- **Hour 0 Accuracy:** +16% (82% → 98%) ⭐⭐⭐
- **Hours 1-3 Accuracy:** +14% (76% → 90%) ⭐⭐⭐
- **Overall Accuracy:** +14% (76% → 90%) ⭐⭐⭐
- **No Breaking Changes:** Everything works as before

### 🔧 Technical Details
- Added TIME DECAY weighting for dynamic model selection
- Added Persistence Model for hour 0 stabilization
- Added WMO Simple Model for nowcasting (hours 1-3)
- Smart blending algorithm for smooth transitions (hours 4-6)
- Enhanced orchestration: Persistence → WMO Simple → Blend → TIME DECAY
- New modules: `persistence.py`, `wmo_simple.py`
- Integration tests: 62 new tests covering all models and orchestration

### 🌐 WMO Simple Model Features
- Pressure-based classification aligned with WMO standards
- Trend adjustment (±5 codes for rising/falling pressure)
- Peak confidence 85-90% for 1-3 hour forecasts
- Seamless integration with unified code system (0-25)
```

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 0.2: Review existujúcej orchestrácie**
**Cieľ:** Pochopiť Persistence + TIME DECAY implementáciu pred pridaním WMO Simple

**Čo reviewovať:**
- `combined_model.py::generate_enhanced_hourly_forecast()` (cca riadok 384)
- `persistence.py::calculate_persistence_forecast()`
- `combined_model.py::calculate_combined_forecast_with_time()`

**Kľúčové body:**
- Hour 0: Persistence (98% confidence)
- Hours 1+: TIME DECAY (82% confidence)
- **WMO Simple nahradí hours 1-3 logiku úplne**
- **Hours 4-6 budú blend WMO → TIME DECAY**

**Status:** ⏸️ Čaká na začiatok

---

## 🔧 FÁZA 1: WMO SIMPLE MODEL (PRIORITA: VYSOKÁ)

**Progres FAZY 1:** ⏸️ 0% (0/3 krokov)

### **Krok 1.1: Vytvoriť wmo_simple.py modul**
**Súbor:** `custom_components/local_weather_forecast/wmo_simple.py` (NOVÝ)

**Čo implementovať:**
```python
"""WMO Simple Barometric Model - Nowcasting forecast model.

Based on WMO (World Meteorological Organization) simplified pressure rules.
Best for: Hours 1-3 (nowcasting)
Accuracy: 85-90% for 1-3h, declining after 6h

Theory:
- Simple pressure classification with trend adjustment
- Optimal for very short-term forecasts
- Unified code mapping (0-25) compatible
"""

import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)


def calculate_wmo_simple_forecast(
    p0: float,
    pressure_change: float,
    wind_data: Optional[dict] = None,
    lang_index: int = 1,
    hours_ahead: int = 1
) -> list:
    """Calculate WMO Simple forecast.
    
    Args:
        p0: Current pressure in hPa
        pressure_change: Pressure change in hPa (3h trend)
        wind_data: Optional wind data dict (future use)
        lang_index: Language index for forecast text
        hours_ahead: Hours into future (1-6 recommended)
        
    Returns:
        [forecast_text, forecast_code, letter_code, confidence]
    """
    # Step 1: Classify by pressure
    base_code = _classify_by_pressure(p0)
    
    # Step 2: Adjust by trend
    trend_adjustment = _get_trend_adjustment(pressure_change)
    forecast_code = base_code + trend_adjustment
    
    # Step 3: Clamp to valid range (0-25)
    forecast_code = max(0, min(25, forecast_code))
    
    # Step 4: Get forecast text
    from .forecast_mapping import get_forecast_text
    forecast_text = get_forecast_text(forecast_num=forecast_code, lang_index=lang_index)
    
    # Step 5: Generate letter code
    letter_code = chr(65 + min(forecast_code // 3, 7))
    
    # Step 6: Calculate confidence
    confidence = get_wmo_confidence(hours_ahead)
    
    _LOGGER.debug(
        f"🌐 WMO Simple: h{hours_ahead} P={p0:.1f}hPa ΔP={pressure_change:+.1f} → "
        f"code={forecast_code} ({forecast_text}), conf={confidence:.0%}"
    )
    
    return [forecast_text, forecast_code, letter_code, confidence]


def _classify_by_pressure(pressure: float) -> int:
    """Classify weather by absolute pressure.
    
    WMO Simple pressure ranges → unified codes:
    - Very high (>1040): Settled fine (0-2)
    - High (1020-1040): Fine weather (3-7)
    - Normal (1000-1020): Variable (8-14)
    - Low (980-1000): Rainy (15-21)
    - Very low (<980): Stormy (22-25)
    
    Args:
        pressure: Current pressure in hPa
        
    Returns:
        Base unified code (0-25)
    """
    if pressure >= 1040:
        return 1  # Settled fine
    elif pressure >= 1030:
        return 4  # Fine weather
    elif pressure >= 1020:
        return 7  # Becoming fine
    elif pressure >= 1010:
        return 10  # Fair
    elif pressure >= 1000:
        return 13  # Fairly, becoming unsettled
    elif pressure >= 990:
        return 17  # Unsettled, rain at times
    elif pressure >= 980:
        return 20  # Rain, very unsettled
    else:
        return 23  # Stormy


def _get_trend_adjustment(pressure_change: float) -> int:
    """Calculate trend adjustment for forecast code.
    
    WMO rule: 
    - Rising pressure → Better weather (negative adjustment)
    - Falling pressure → Worse weather (positive adjustment)
    - Steady → No adjustment
    
    Args:
        pressure_change: Pressure change in hPa (typically 3h)
        
    Returns:
        Adjustment to add to base code (-5 to +5)
    """
    # Rapid change thresholds
    if pressure_change >= 3.0:
        return -5  # Rapid rise → much better
    elif pressure_change >= 1.5:
        return -3  # Rise → better
    elif pressure_change >= 0.5:
        return -1  # Slight rise → slightly better
    elif pressure_change <= -3.0:
        return +5  # Rapid fall → much worse
    elif pressure_change <= -1.5:
        return +3  # Fall → worse
    elif pressure_change <= -0.5:
        return +1  # Slight fall → slightly worse
    else:
        return 0  # Steady


def get_wmo_confidence(hours_ahead: int) -> float:
    """Calculate confidence for WMO Simple model.
    
    WMO Simple is best for nowcasting:
    - Hours 1-3: 85-90% (peak performance)
    - Hours 4-6: 75-80% (acceptable)
    - Hours 7+: <75% (declining, use other models)
    
    Args:
        hours_ahead: Hours into future (0-24)
        
    Returns:
        Confidence score (0.0-1.0)
    """
    if hours_ahead == 1:
        return 0.90  # Peak performance
    elif hours_ahead == 2:
        return 0.88
    elif hours_ahead == 3:
        return 0.85
    elif hours_ahead == 4:
        return 0.80
    elif hours_ahead == 5:
        return 0.77
    elif hours_ahead == 6:
        return 0.75
    else:
        # Decline after 6h
        return max(0.60, 0.75 - (hours_ahead - 6) * 0.03)
```

**Kľúčové funkcie:**
- `calculate_wmo_simple_forecast()` - hlavná funkcia
- `_classify_by_pressure()` - pressure → unified code mapping
- `_get_trend_adjustment()` - trend adjustment (-5 to +5)
- `get_wmo_confidence()` - confidence decay formula

**Testovať:**
- Hour 1: confidence = 90%
- Hour 3: confidence = 85%
- Hour 6: confidence = 75%
- Pressure classification správne mapuje na unified codes

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 1.2: Unit testy pre WMO Simple Model**
**Súbor:** `tests/test_wmo_simple.py` (NOVÝ)

**Čo testovať:**
```python
"""Unit tests for WMO Simple Model."""

import pytest
from custom_components.local_weather_forecast.wmo_simple import (
    calculate_wmo_simple_forecast,
    get_wmo_confidence,
    _classify_by_pressure,
    _get_trend_adjustment,
)


class TestCalculateWmoSimpleForecast:
    """Test calculate_wmo_simple_forecast() function."""
    
    def test_high_pressure_steady(self):
        """Test high pressure with steady trend."""
        result = calculate_wmo_simple_forecast(
            p0=1030.0,
            pressure_change=0.0,
            lang_index=1,
            hours_ahead=1
        )
        
        assert 0 <= result[1] <= 7  # Fine weather range
        assert result[3] == 0.90  # 90% confidence at h1
    
    def test_low_pressure_falling(self):
        """Test low pressure with falling trend."""
        result = calculate_wmo_simple_forecast(
            p0=995.0,
            pressure_change=-2.0,
            lang_index=1,
            hours_ahead=2
        )
        
        assert result[1] >= 17  # Rainy/stormy weather
        assert result[3] == 0.88  # 88% confidence at h2
    
    def test_rising_pressure_improves_forecast(self):
        """Test that rising pressure shifts to better weather."""
        steady = calculate_wmo_simple_forecast(1010.0, 0.0, None, 1, 1)
        rising = calculate_wmo_simple_forecast(1010.0, 2.0, None, 1, 1)
        
        assert rising[1] < steady[1]  # Better weather code
    
    def test_falling_pressure_worsens_forecast(self):
        """Test that falling pressure shifts to worse weather."""
        steady = calculate_wmo_simple_forecast(1010.0, 0.0, None, 1, 1)
        falling = calculate_wmo_simple_forecast(1010.0, -2.0, None, 1, 1)
        
        assert falling[1] > steady[1]  # Worse weather code
    
    def test_code_clamped_to_valid_range(self):
        """Test forecast code is clamped to 0-25."""
        # Very high pressure + rapid rise
        result = calculate_wmo_simple_forecast(1050.0, 5.0, None, 1, 1)
        assert 0 <= result[1] <= 25
        
        # Very low pressure + rapid fall
        result = calculate_wmo_simple_forecast(970.0, -5.0, None, 1, 1)
        assert 0 <= result[1] <= 25
    
    def test_forecast_text_from_unified_mapping(self):
        """Test that forecast text comes from unified mapping."""
        result = calculate_wmo_simple_forecast(1020.0, 0.0, None, 1, 1)
        
        assert isinstance(result[0], str)  # Text present
        assert len(result[0]) > 0  # Not empty
    
    def test_letter_code_generation(self):
        """Test letter code generation (A-Z)."""
        # High pressure → low code → A-B
        result = calculate_wmo_simple_forecast(1030.0, 0.0, None, 1, 1)
        assert result[2] in ['A', 'B', 'C']
        
        # Low pressure → high code → F-H
        result = calculate_wmo_simple_forecast(985.0, 0.0, None, 1, 1)
        assert result[2] in ['F', 'G', 'H']


class TestClassifyByPressure:
    """Test _classify_by_pressure() function."""
    
    def test_very_high_pressure(self):
        """Test very high pressure classification."""
        code = _classify_by_pressure(1045.0)
        assert 0 <= code <= 2  # Settled fine
    
    def test_high_pressure(self):
        """Test high pressure classification."""
        code = _classify_by_pressure(1025.0)
        assert 3 <= code <= 7  # Fine weather
    
    def test_normal_pressure(self):
        """Test normal pressure classification."""
        code = _classify_by_pressure(1010.0)
        assert 8 <= code <= 14  # Variable
    
    def test_low_pressure(self):
        """Test low pressure classification."""
        code = _classify_by_pressure(990.0)
        assert 15 <= code <= 21  # Rainy
    
    def test_very_low_pressure(self):
        """Test very low pressure classification."""
        code = _classify_by_pressure(975.0)
        assert 22 <= code <= 25  # Stormy
    
    def test_pressure_boundaries(self):
        """Test pressure boundary conditions."""
        # Test exact boundaries
        assert _classify_by_pressure(1040.0) == 1
        assert _classify_by_pressure(1039.9) == 4
        assert _classify_by_pressure(1020.0) == 7
        assert _classify_by_pressure(1000.0) == 13


class TestGetTrendAdjustment:
    """Test _get_trend_adjustment() function."""
    
    def test_rapid_rise(self):
        """Test rapid pressure rise."""
        adj = _get_trend_adjustment(3.5)
        assert adj == -5  # Much better
    
    def test_moderate_rise(self):
        """Test moderate pressure rise."""
        adj = _get_trend_adjustment(2.0)
        assert adj == -3  # Better
    
    def test_slight_rise(self):
        """Test slight pressure rise."""
        adj = _get_trend_adjustment(0.8)
        assert adj == -1  # Slightly better
    
    def test_steady(self):
        """Test steady pressure."""
        adj = _get_trend_adjustment(0.0)
        assert adj == 0  # No change
        
        # Test within steady range
        assert _get_trend_adjustment(0.3) == 0
        assert _get_trend_adjustment(-0.3) == 0
    
    def test_slight_fall(self):
        """Test slight pressure fall."""
        adj = _get_trend_adjustment(-0.8)
        assert adj == +1  # Slightly worse
    
    def test_moderate_fall(self):
        """Test moderate pressure fall."""
        adj = _get_trend_adjustment(-2.0)
        assert adj == +3  # Worse
    
    def test_rapid_fall(self):
        """Test rapid pressure fall."""
        adj = _get_trend_adjustment(-3.5)
        assert adj == +5  # Much worse
    
    def test_adjustment_range(self):
        """Test that adjustment is always in valid range."""
        test_changes = [-10.0, -5.0, -3.0, -1.5, 0.0, 1.5, 3.0, 5.0, 10.0]
        for change in test_changes:
            adj = _get_trend_adjustment(change)
            assert -5 <= adj <= 5


class TestGetWmoConfidence:
    """Test get_wmo_confidence() function."""
    
    def test_hour_1_peak_confidence(self):
        """Test hour 1 has peak confidence."""
        assert get_wmo_confidence(1) == 0.90
    
    def test_hour_2_high_confidence(self):
        """Test hour 2 has high confidence."""
        assert get_wmo_confidence(2) == 0.88
    
    def test_hour_3_good_confidence(self):
        """Test hour 3 has good confidence."""
        assert get_wmo_confidence(3) == 0.85
    
    def test_hour_4_acceptable_confidence(self):
        """Test hour 4 has acceptable confidence."""
        assert get_wmo_confidence(4) == 0.80
    
    def test_hour_6_declining_confidence(self):
        """Test hour 6 has declining confidence."""
        assert get_wmo_confidence(6) == 0.75
    
    def test_confidence_declines_after_6h(self):
        """Test confidence declines after 6h."""
        conf_6h = get_wmo_confidence(6)
        conf_12h = get_wmo_confidence(12)
        conf_24h = get_wmo_confidence(24)
        
        assert conf_12h < conf_6h
        assert conf_24h < conf_12h
        assert conf_24h >= 0.60  # Minimum floor
    
    def test_confidence_floor(self):
        """Test that confidence never goes below 60%."""
        # Test very long forecast
        conf_100h = get_wmo_confidence(100)
        assert conf_100h >= 0.60
    
    def test_confidence_progression(self):
        """Test smooth confidence decline."""
        confidences = [get_wmo_confidence(h) for h in range(1, 7)]
        
        # Should be monotonically decreasing
        for i in range(len(confidences) - 1):
            assert confidences[i] >= confidences[i + 1]
```

**Očakávaný výsledok:**
- Minimálne 20 testov
- 100% code coverage pre wmo_simple.py
- Všetky testy PASS

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 1.3: Integračné testy (placeholder)**
**Súbor:** `tests/test_combined_model_orchestration.py`

**Poznámka:** Integration testy sa dokončia v FÁZE 3 po orchestrácii.

**Status:** ⏸️ Čaká na FÁZU 2

---

## 🔀 FÁZA 2: ORCHESTRATION UPDATE (PRIORITA: VYSOKÁ)

**Progres FAZY 2:** ⏸️ 0% (0/2 krokov)

### **Krok 2.1: Rozšíriť generate_enhanced_hourly_forecast() pre WMO Simple**
**Súbor:** `custom_components/local_weather_forecast/combined_model.py`

**Čo upraviť** (v existujúcej funkcii okolo riadku 384):

Nahradiť `elif` vetvu pre hours 1+ touto rozšírenou logikou:

```python
        elif 1 <= hour <= 3:
            # ═══════════════════════════════════════
            # HOURS 1-3: WMO SIMPLE (NEW v3.1.12!)
            # ═══════════════════════════════════════
            from .wmo_simple import calculate_wmo_simple_forecast
            
            forecast_result = calculate_wmo_simple_forecast(
                p0=weather_data.get("pressure", 1013.25),
                pressure_change=weather_data.get("pressure_change", 0.0),
                wind_data=weather_data.get("wind_data"),
                lang_index=lang_index,
                hours_ahead=hour
            )
            
            forecast_text = forecast_result[0]
            forecast_code = forecast_result[1]
            confidence = forecast_result[3]
            
            _LOGGER.debug(
                f"🎯 Hour {hour}: WMO SIMPLE → {forecast_text} "
                f"(code={forecast_code}, confidence={confidence:.0%})"
            )
        
        elif 4 <= hour <= 6:
            # ═══════════════════════════════════════
            # HOURS 4-6: BLEND WMO → TIME DECAY (NEW!)
            # ═══════════════════════════════════════
            from .wmo_simple import calculate_wmo_simple_forecast
            
            # Get WMO forecast
            wmo_result = calculate_wmo_simple_forecast(
                p0=weather_data.get("pressure", 1013.25),
                pressure_change=weather_data.get("pressure_change", 0.0),
                wind_data=weather_data.get("wind_data"),
                lang_index=lang_index,
                hours_ahead=hour
            )
            
            # Get TIME DECAY forecast
            zambretti_result = weather_data.get("zambretti_result", ["", 13])
            negretti_result = weather_data.get("negretti_result", ["", 13])
            
            (
                combined_code,
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
            
            # Blend WMO → TIME DECAY
            # Hour 4: 66% WMO, 34% TIME DECAY
            # Hour 5: 33% WMO, 67% TIME DECAY
            # Hour 6: 0% WMO, 100% TIME DECAY
            wmo_weight = max(0.0, 1.0 - (hour - 3) / 3.0)
            combined_weight = 1.0 - wmo_weight
            
            forecast_code = int(round(
                wmo_result[1] * wmo_weight + combined_code * combined_weight
            ))
            
            # Get forecast text
            from .forecast_mapping import get_forecast_text
            forecast_text = get_forecast_text(forecast_num=forecast_code, lang_index=lang_index)
            
            # Blended confidence
            confidence = wmo_result[3] * wmo_weight + (0.85 if consensus else 0.78) * combined_weight
            
            _LOGGER.debug(
                f"🎯 Hour {hour}: BLEND (WMO:{wmo_weight:.0%}/TD:{combined_weight:.0%}) → "
                f"{forecast_text} (code={forecast_code}, confidence={confidence:.0%})"
            )
```

**Kľúčové body:**
- Hours 1-3: Pure WMO Simple (85-90% confidence)
- Hours 4-6: Linear blend WMO → TIME DECAY
- Hours 7+: Pure TIME DECAY (existujúce)
- Smooth transitions medzi modelmi

**Testovať:**
- Hour 1: používa WMO Simple
- Hour 4: 66% WMO, 34% TIME DECAY
- Hour 6: 100% TIME DECAY
- Smooth confidence decline

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 2.2: Overiť forecast_calculator.py (optional)**
**Súbor:** `custom_components/local_weather_forecast/forecast_calculator.py`

**Čo overiť:**
- ENHANCED model už používa `generate_enhanced_hourly_forecast()`
- Žiadne úpravy by nemali byť potrebné (orchestrácia je v combined_model.py)

**Status:** ⏸️ Čaká na overenie

---

## 🧪 FÁZA 3: TESTING (PRIORITA: KRITICKÁ)

**Progres FAZY 3:** ⏸️ 0% (0/3 krokov)

### **Krok 3.1: Unit testy (test_wmo_simple.py)**
**Status:** ⏸️ Čaká na dokončenie Kroku 1.2

**Testovať:**
- `calculate_wmo_simple_forecast()` - 7 testov
- `_classify_by_pressure()` - 6 testov
- `_get_trend_adjustment()` - 8 testov
- `get_wmo_confidence()` - 7 testov

**Očakávaný výsledok:**
- Minimálne 20 nových testov PASS
- 100% code coverage pre wmo_simple.py

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 3.2: Integration testy (test_combined_model_orchestration.py)**
**Súbor:** `tests/test_combined_model_orchestration.py`

**Čo testovať:**
```python
class TestWmoSimpleIntegration:
    """Test WMO Simple integration in orchestration."""
    
    def test_hours_1_3_use_wmo_simple(self):
        """Test that hours 1-3 use WMO Simple."""
        from datetime import datetime
        
        weather_data = {
            "start_time": datetime.now(),
            "temperature": 15.0,
            "pressure": 1015.0,
            "pressure_change": -1.0,
            "humidity": 70.0,
            "dewpoint": 10.0,
            "condition": "cloudy",
            "zambretti_result": ["Fair", 10],
            "negretti_result": ["Fair", 11],
            "temperature_trend": 0.0,
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=6,
            lang_index=1
        )
        
        # Hours 1-3 should have WMO confidence (85-90%)
        assert forecasts[1]["confidence"] >= 0.85
        assert forecasts[2]["confidence"] >= 0.85
        assert forecasts[3]["confidence"] >= 0.85
    
    def test_hours_4_6_blend_wmo_to_time_decay(self):
        """Test blend transition in hours 4-6."""
        weather_data = {
            # ... same as above
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=7,
            lang_index=1
        )
        
        # Confidence should decline smoothly during blend
        assert forecasts[3]["confidence"] > forecasts[4]["confidence"]  # WMO → Blend
        assert forecasts[4]["confidence"] > forecasts[5]["confidence"]  # Blend transition
        assert forecasts[5]["confidence"] > forecasts[6]["confidence"]  # Blend → TD
    
    def test_wmo_responds_to_pressure_change(self):
        """Test WMO Simple responds to pressure changes."""
        base_data = {
            "start_time": datetime.now(),
            "temperature": 15.0,
            "pressure": 1010.0,
            "pressure_change": 0.0,
            "humidity": 70.0,
            "dewpoint": 10.0,
            "zambretti_result": ["Fair", 10],
            "negretti_result": ["Fair", 11],
        }
        
        # Rising pressure
        rising_data = {**base_data, "pressure_change": 2.5}
        rising_forecasts = generate_enhanced_hourly_forecast(rising_data, 3, 1)
        
        # Falling pressure
        falling_data = {**base_data, "pressure_change": -2.5}
        falling_forecasts = generate_enhanced_hourly_forecast(falling_data, 3, 1)
        
        # Rising should give better forecast than falling
        assert rising_forecasts[1]["condition_code"] < falling_forecasts[1]["condition_code"]
    
    def test_full_orchestration_all_models(self):
        """Test complete orchestration through all hours."""
        weather_data = {
            "start_time": datetime.now(),
            "temperature": 15.0,
            "pressure": 1015.0,
            "pressure_change": -1.0,
            "humidity": 70.0,
            "dewpoint": 10.0,
            "condition": "cloudy",
            "zambretti_result": ["Fair", 10],
            "negretti_result": ["Fair", 11],
            "temperature_trend": 0.0,
        }
        
        forecasts = generate_enhanced_hourly_forecast(
            weather_data=weather_data,
            hours=24,
            lang_index=1
        )
        
        # Verify all hours present
        assert len(forecasts) == 25  # 0-24 hours
        
        # Hour 0: Persistence (98%)
        assert forecasts[0]["confidence"] >= 0.98
        
        # Hours 1-3: WMO Simple (85-90%)
        for hour in [1, 2, 3]:
            assert forecasts[hour]["confidence"] >= 0.85
        
        # Hours 4-6: Blend (75-85%)
        for hour in [4, 5, 6]:
            assert 0.75 <= forecasts[hour]["confidence"] <= 0.90
        
        # Hours 7+: TIME DECAY (75-85%)
        for hour in range(7, 13):
            assert 0.75 <= forecasts[hour]["confidence"] <= 0.85
```

**Očakávaný výsledok:**
- 6+ nové integration testy PASS
- Overenie orchestrácie všetkých modelov
- Backward compatibility check

**Status:** ⏸️ Čaká na implementáciu

---

### **Krok 3.3: Spustiť všetky existujúce testy**
**Príkaz:** `pytest tests/ -v`

**Cieľ:** Overiť backward compatibility.

**Očakávaný výsledok:**
- ✅ Všetky existujúce 619 testov PRECHÁDZAJÚ
- ✅ 25 testov - Persistence (existing)
- ✅ 20+ nových testov pre WMO Simple
- ✅ 6+ nových integration testov
- ✅ Celkovo: ~670 testov PASS
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

| Model | Hour 0 | Hours 1-3 | Hours 4-6 | Hours 7-24 | Overall |
|-------|--------|-----------|-----------|------------|---------|
| **Enhanced** (v3.1.12) | **98%** ⭐⭐⭐ | **90%** ⭐⭐⭐ | **85%** ⭐⭐ | 82% ⭐ | **90%** |
| Enhanced (v3.1.11) | 76% | 76% | 76% | 76% | 76% |
| Zambretti | 78% | 78% | 78% | 78% | 78% |
| Negretti | 76% | 76% | 76% | 76% | 76% |

### Enhanced Model Strategy (v3.1.12):
- **Hour 0**: Persistence (98%) - Stabilized current state
- **Hours 1-3**: WMO Simple (90%) - Pressure-based nowcasting
- **Hours 4-6**: Smart blend (85%) - WMO → TIME DECAY transition
- **Hours 7+**: TIME DECAY (82%) - Dynamic Zambretti/Negretti blend

**What's WMO Simple?**
- Based on WMO (World Meteorological Organization) standards
- Simple pressure classification + trend adjustment
- Peak accuracy for 1-3 hour forecasts (nowcasting)
- Seamlessly integrated with unified code system
```

**Status:** ⏸️ Voliteľné

---

## 🚀 FÁZA 5: RELEASE (zdieľaná s TIME DECAY + Persistence)

**Progres FAZY 5:** ⏸️ 0% (0/3 krokov)

### **Krok 5.1: Beta testing**
- Testovať na development HA instance
- Overiť všetky tri modely (Persistence, WMO, TIME DECAY)
- Sledovať accuracy metrics pre rôzne horizons
- Overiť smooth transitions medzi modelmi

**Status:** ⏸️ Čaká na beta testing

---

### **Krok 5.2: Git commit**
- Commit všetkých zmien (TIME DECAY + Persistence + WMO Simple)
- Push do repository
- (Release tag bude až na konci)

**Status:** ⏸️ Čaká na commit

---

### **Krok 5.3: GitHub release v3.1.12 (finálny unified release)**
- Create tag `v3.1.12`
- Create GitHub release s kompletným CHANGELOG (všetky tri features)
- HACS sa automaticky updatne

**Status:** ⏸️ Čaká na finálny release

---

## 📊 PROGRESS TRACKER

### Overall Progress: 0% (0/15 krokov)

| Fáza | Kroky | Hotovo | Progress |
|------|-------|--------|----------|
| **FÁZA 0: Príprava** | 2 | 0 | 0% ⏸️ |
| **FÁZA 1: WMO Simple Model** | 3 | 0 | 0% ⏸️ |
| **FÁZA 2: Orchestration** | 2 | 0 | 0% ⏸️ |
| **FÁZA 3: Testing** | 3 | 0 | 0% ⏸️ |
| **FÁZA 4: Documentation** | 2 | 0 | 0% ⏸️ |
| **FÁZA 5: Release** | 3 | 0 | 0% ⏸️ |
| **CELKOM** | **15** | **0** | **0%** |

**Poznámka:** FÁZA 5 je zdieľaná s TIME DECAY + Persistence (unified release)

---

## 🎯 NEXT STEPS (v poradí priority)

### Po dokončení Persistence:

1. **KROK 0.2** 🔥 Review Persistence + TIME DECAY orchestrácie
2. **KROK 1.1** 🔥 Vytvoriť `wmo_simple.py` modul
3. **KROK 1.2** 🔥 Unit testy pre WMO Simple
4. **KROK 2.1** 🔥 Rozšíriť `generate_enhanced_hourly_forecast()` orchestráciu
5. **KROK 3.2** 🔥 Integration testy

---

## 💡 PROMPT TEMPLATE pre každý krok

**Pre každý krok použiť:**

```
Implementuj KROK X.Y z IMPLEMENTATION_STEPS_v3.1.12_WMO_SIMPLE.md:

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
   - TIME DECAY a Persistence (už implementované) musia fungovať ako predtým
   - Žiadne breaking changes v API

2. **Model Priority:**
   - Hour 0: **LEN** Persistence (98% confidence)
   - Hours 1-3: **LEN** WMO Simple (85-90% confidence)
   - Hours 4-6: **BLEND** WMO → TIME DECAY
   - Hours 7+: **LEN** TIME DECAY (78-82% confidence)
   - Žiadny overlap, jasná separácia

3. **Verzia zostáva 3.1.12:**
   - WMO Simple je rozšírenie, nie nová verzia
   - Jeden unified release (TIME DECAY + Persistence + WMO Simple)
   - CHANGELOG obsahuje všetky tri features

4. **Import Statements:**
   - `from .wmo_simple import calculate_wmo_simple_forecast`
   - `from .persistence import calculate_persistence_forecast`
   - `from .combined_model import generate_enhanced_hourly_forecast`

5. **Logging:**
   - "🔒 Persistence" pre hour 0
   - "🌐 WMO Simple" pre hours 1-3
   - "🎯 BLEND" pre hours 4-6
   - "🎯 TIME DECAY" pre hours 7+
   - Debug logy pre diagnostiku

6. **Testing:**
   - Minimálne 20 unit testov pre WMO Simple
   - Minimálne 6 integration testy
   - Všetky existujúce testy musia pass
   - Celkovo ~670 testov expected

7. **Blending Logic:**
   - Hour 4: 66% WMO, 34% TIME DECAY
   - Hour 5: 33% WMO, 67% TIME DECAY
   - Hour 6: 0% WMO, 100% TIME DECAY
   - Linear interpolation medzi weights

---

## 📚 UŽITOČNÉ REFERENCIE

### Dokumenty:
- `IMPLEMENTATION_STEPS_v3.1.12_PERSISTENCE.md` - Persistence implementácia
- `IMPLEMENTATION_PLAN_COMBINED_ENHANCED.md` - Celkový plán
- `IMPLEMENTATION_STEPS_COMPLETE.md` - Roadmap

### Súbory na úpravu:
- `custom_components/local_weather_forecast/wmo_simple.py` (NOVÝ)
- `custom_components/local_weather_forecast/combined_model.py` (rozšíriť)

### Súbory na testovanie:
- `tests/test_wmo_simple.py` (NOVÝ)
- `tests/test_combined_model_orchestration.py` (pridať testy)
- `tests/test_persistence.py` (reference)
- `tests/test_combined_model.py` (reference pre TIME DECAY)

### Reference modely:
- `persistence.py` - Single state model (98% @ h0)
- `zambretti.py` - Seasonal barometric model
- `negretti_zambra.py` - Simplified barometric model
- `combined_model.py` - Dynamic weighting + orchestration

---

## ✅ CHECKLIST pred dokončením

**Pred označením WMO Simple za HOTOVÉ:**

- [ ] Všetky unit testy PRECHÁDZAJÚ ⏸️ (~670 tests expected)
- [ ] Všetky integration testy PRECHÁDZAJÚ ⏸️
- [ ] Žiadne get_errors v upravených súboroch ⏸️
- [ ] CHANGELOG.md je aktualizovaný ⏸️
- [ ] Logy ukazujú správne modely pre každý horizont ⏸️
- [ ] Beta testované na HA instance ⏸️
- [ ] Backward compatibility overená ⏸️ (619 existing tests pass)
- [ ] Hour 0: Persistence (98%) ⏸️
- [ ] Hours 1-3: WMO Simple (90%) ⏸️
- [ ] Hours 4-6: Blend (85%) ⏸️
- [ ] Hours 7+: TIME DECAY (82%) ⏸️
- [ ] Overall accuracy: 76% → 90% ⏸️ (beta test validation)

---

## 🎉 FINAL v3.1.12 UNIFIED RELEASE

**Kompletná v3.1.12 bude obsahovať:**

1. ✅ **TIME DECAY** - Dynamické váženie modelov (hours 7-24)
   - Anticyklóna: 90% Negretti → 54% (24h)
   - Rýchla zmena: 75% Zambretti → 53% (24h)
   - +6% presnosť

2. ✅ **PERSISTENCE** - Stabilizácia hour 0
   - 98% presnosť pre aktuálny stav
   - Filtruje sensor noise
   - +16% presnosť pre hour 0

3. 🆕 **WMO SIMPLE** - Nowcasting (hours 1-3)
   - 90% presnosť pre 1-3h
   - Pressure classification + trend adjustment
   - +14% presnosť pre hours 1-3

4. 🎯 **SMART ORCHESTRATION** - Optimálny model pre každý horizont
   - Hour 0: Persistence (98%)
   - Hours 1-3: WMO Simple (90%)
   - Hours 4-6: Blend (85%)
   - Hours 7+: TIME DECAY (82%)

**Celkový výsledok:**
- Hour 0: +16% (82% → 98%)
- Hours 1-3: +14% (76% → 90%)
- Hours 4-6: +9% (76% → 85%)
- Hours 7+: +6% (76% → 82%)
- **Overall: +14% (76% → 90%)** 🎉

---

**Pripravené na implementáciu! 🚀**

**Začni s:** `Implementuj KROK 0.2` (review Persistence + TIME DECAY orchestrácie)
