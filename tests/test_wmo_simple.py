"""Unit tests for WMO Simple Model."""

import pytest
from custom_components.local_weather_forecast.wmo_simple import (
    calculate_wmo_simple_forecast,
    get_wmo_confidence,
    _calculate_wmo_trend_adjustment,
    _apply_trend_adjustment,
)


class TestCalculateWMOSimpleForecast:
    """Test calculate_wmo_simple_forecast() function."""
    
    def test_rapid_pressure_rise_improves_conditions(self):
        """Test that rapid pressure rise improves forecast."""
        current_code = 15  # Cloudy/rainy
        pressure_change = 4.0  # Rapid rise
        
        result = calculate_wmo_simple_forecast(
            current_code, pressure_change, lang_index=1, hours_ahead=1
        )
        
        # Should improve (lower code = better weather)
        assert result[1] < current_code
        assert result[3] >= 0.90  # High confidence
    
    def test_rapid_pressure_fall_worsens_conditions(self):
        """Test that rapid pressure fall worsens forecast."""
        current_code = 5  # Fine weather
        pressure_change = -4.0  # Rapid fall
        
        result = calculate_wmo_simple_forecast(
            current_code, pressure_change, lang_index=1, hours_ahead=1
        )
        
        # Should worsen (higher code = worse weather)
        assert result[1] > current_code
        assert result[3] >= 0.90  # High confidence
    
    def test_steady_pressure_maintains_conditions(self):
        """Test that steady pressure maintains current conditions."""
        current_code = 10  # Moderate conditions
        pressure_change = 0.0  # Steady
        
        result = calculate_wmo_simple_forecast(
            current_code, pressure_change, lang_index=1, hours_ahead=1
        )
        
        # Should stay similar (±3 codes due to blending)
        assert abs(result[1] - current_code) <= 3
    
    def test_steady_rise_moderate_improvement(self):
        """Test that steady rise gives moderate improvement."""
        current_code = 15  # Cloudy
        pressure_change = 2.0  # Steady rise
        
        result = calculate_wmo_simple_forecast(
            current_code, pressure_change, lang_index=1, hours_ahead=2
        )
        
        # Should improve moderately
        improvement = current_code - result[1]
        assert 3 <= improvement <= 9  # -2 adjustment * 3 codes
    
    def test_forecast_text_from_unified_mapping(self):
        """Test that forecast text comes from unified mapping."""
        current_code = 5
        result = calculate_wmo_simple_forecast(
            current_code, 1.5, lang_index=1, hours_ahead=1
        )
        
        assert isinstance(result[0], str)  # Text present
        assert len(result[0]) > 0  # Not empty
    
    def test_letter_code_generation(self):
        """Test letter code generation (A-Z)."""
        # Code 0-2 → A
        result = calculate_wmo_simple_forecast(0, 0.0, lang_index=1, hours_ahead=1)
        assert result[2] == 'A'
        
        # Code 21-23 → H
        result = calculate_wmo_simple_forecast(21, 0.0, lang_index=1, hours_ahead=1)
        assert result[2] == 'H'
    
    def test_confidence_decreases_with_time(self):
        """Test that confidence decreases as hours_ahead increases."""
        current_code = 10
        pressure_change = 1.0
        
        result_1h = calculate_wmo_simple_forecast(current_code, pressure_change, 1, 1)
        result_2h = calculate_wmo_simple_forecast(current_code, pressure_change, 1, 2)
        result_3h = calculate_wmo_simple_forecast(current_code, pressure_change, 1, 3)
        
        assert result_1h[3] > result_2h[3]  # Hour 1 > Hour 2
        assert result_2h[3] > result_3h[3]  # Hour 2 > Hour 3


class TestCalculateWMOTrendAdjustment:
    """Test _calculate_wmo_trend_adjustment() function."""
    
    def test_rapid_rise_strong_improvement(self):
        """Test rapid rise (≥3 hPa) gives -3 adjustment."""
        assert _calculate_wmo_trend_adjustment(3.5) == -3
        assert _calculate_wmo_trend_adjustment(5.0) == -3
    
    def test_steady_rise_moderate_improvement(self):
        """Test steady rise (1-3 hPa) gives -2 adjustment."""
        assert _calculate_wmo_trend_adjustment(1.0) == -2
        assert _calculate_wmo_trend_adjustment(2.5) == -2
    
    def test_steady_no_change(self):
        """Test steady (±1 hPa) gives 0 adjustment."""
        assert _calculate_wmo_trend_adjustment(0.5) == 0
        assert _calculate_wmo_trend_adjustment(0.0) == 0
        assert _calculate_wmo_trend_adjustment(-0.5) == 0
    
    def test_steady_fall_moderate_deterioration(self):
        """Test steady fall (-1 to -3 hPa) gives +2 adjustment."""
        assert _calculate_wmo_trend_adjustment(-1.5) == +2
        assert _calculate_wmo_trend_adjustment(-2.5) == +2
    
    def test_rapid_fall_strong_deterioration(self):
        """Test rapid fall (<-3 hPa) gives +3 adjustment."""
        assert _calculate_wmo_trend_adjustment(-3.5) == +3
        assert _calculate_wmo_trend_adjustment(-5.0) == +3


class TestApplyTrendAdjustment:
    """Test _apply_trend_adjustment() function."""
    
    def test_improvement_decreases_code(self):
        """Test negative adjustment improves conditions."""
        # Code 15, -3 adjustment → code 6 (improvement)
        result = _apply_trend_adjustment(15, -3)
        assert result == 6
    
    def test_deterioration_increases_code(self):
        """Test positive adjustment worsens conditions."""
        # Code 5, +3 adjustment → code 14 (deterioration)
        result = _apply_trend_adjustment(5, +3)
        assert result == 14
    
    def test_no_change_maintains_code(self):
        """Test zero adjustment maintains code."""
        result = _apply_trend_adjustment(10, 0)
        assert result == 10
    
    def test_clamps_to_minimum_zero(self):
        """Test adjustment clamped to 0."""
        # Code 3, -3 adjustment → should clamp to 0
        result = _apply_trend_adjustment(3, -3)
        assert result == 0
    
    def test_clamps_to_maximum_25(self):
        """Test adjustment clamped to 25."""
        # Code 20, +3 adjustment → should clamp to 25
        result = _apply_trend_adjustment(20, +3)
        assert result == 25


class TestGetWMOConfidence:
    """Test get_wmo_confidence() function."""
    
    def test_hour_1_highest_confidence(self):
        """Test hour 1 has 95% base confidence."""
        assert get_wmo_confidence(1, 1.0) == 0.95
    
    def test_hour_2_high_confidence(self):
        """Test hour 2 has 92% base confidence."""
        assert get_wmo_confidence(2, 1.0) == 0.92
    
    def test_hour_3_good_confidence(self):
        """Test hour 3 has 90% base confidence."""
        assert get_wmo_confidence(3, 1.0) == 0.90
    
    def test_confidence_decays_after_3h(self):
        """Test confidence decays for hours > 3."""
        conf_3h = get_wmo_confidence(3, 1.0)
        conf_6h = get_wmo_confidence(6, 1.0)
        
        assert conf_6h < conf_3h
    
    def test_strong_trend_boosts_confidence(self):
        """Test strong pressure trend increases confidence."""
        # Strong trend (≥3 hPa)
        conf_strong = get_wmo_confidence(1, 4.0)
        conf_normal = get_wmo_confidence(1, 1.0)
        
        assert conf_strong > conf_normal
        assert conf_strong == 0.98  # 0.95 + 0.03 boost
    
    def test_moderate_trend_small_boost(self):
        """Test moderate pressure trend gives small boost."""
        conf_moderate = get_wmo_confidence(2, 2.0)
        conf_normal = get_wmo_confidence(2, 1.0)
        
        assert conf_moderate > conf_normal
        assert abs(conf_moderate - 0.94) < 0.001  # 0.92 + 0.02 boost (with floating point tolerance)
    
    def test_weak_trend_no_boost(self):
        """Test weak pressure trend gives no boost."""
        conf_weak = get_wmo_confidence(1, 0.5)
        assert conf_weak == 0.95  # No boost


class TestWMOSimpleIntegration:
    """Integration tests for WMO Simple Model."""
    
    def test_storm_approaching_scenario(self):
        """Test storm approaching (rapid pressure fall)."""
        current_code = 3  # Fine weather
        pressure_change = -5.0  # Rapid fall - storm approaching
        
        result = calculate_wmo_simple_forecast(current_code, pressure_change, 1, 1)
        
        # Should predict worsening conditions
        assert result[1] > current_code
        assert result[3] >= 0.95  # High confidence in strong trend
    
    def test_clearing_weather_scenario(self):
        """Test clearing weather (rapid pressure rise)."""
        current_code = 18  # Rainy
        pressure_change = 4.5  # Rapid rise - clearing
        
        result = calculate_wmo_simple_forecast(current_code, pressure_change, 1, 1)
        
        # Should predict improving conditions
        assert result[1] < current_code
        assert result[3] >= 0.95  # High confidence in strong trend
    
    def test_stable_conditions_scenario(self):
        """Test stable conditions (steady pressure)."""
        current_code = 10  # Moderate
        pressure_change = 0.3  # Very steady
        
        result = calculate_wmo_simple_forecast(current_code, pressure_change, 1, 2)
        
        # Should maintain similar conditions
        assert abs(result[1] - current_code) <= 3
        assert result[3] >= 0.90  # Good confidence
