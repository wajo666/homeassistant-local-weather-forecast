"""Tests for combined_model.py TIME DECAY functionality."""
import pytest
import math
from custom_components.local_weather_forecast.combined_model import (
    _calculate_weights_with_time_decay,
    calculate_combined_forecast_with_time,
    calculate_combined_forecast,
)


class TestTimeDecayFormula:
    """Test TIME DECAY exponential formula."""

    def test_time_decay_at_hour_0(self):
        """Verify decay = 1.0 at hour 0 (no decay)."""
        expected_decay = math.exp(-0 / 12.0)
        assert expected_decay == 1.0, "Hour 0 should have no decay"

    def test_time_decay_at_hour_6(self):
        """Verify decay ≈ 0.61 at hour 6."""
        expected_decay = math.exp(-6 / 12.0)
        assert 0.60 <= expected_decay <= 0.62, f"Hour 6 decay should be ~0.61, got {expected_decay}"

    def test_time_decay_at_hour_12(self):
        """Verify decay ≈ 0.37 at hour 12 (half-life)."""
        expected_decay = math.exp(-12 / 12.0)
        assert 0.36 <= expected_decay <= 0.38, f"Hour 12 decay should be ~0.37, got {expected_decay}"

    def test_time_decay_at_hour_24(self):
        """Verify decay ≈ 0.14 at hour 24."""
        expected_decay = math.exp(-24 / 12.0)
        assert 0.13 <= expected_decay <= 0.15, f"Hour 24 decay should be ~0.14, got {expected_decay}"


class TestTimeDecayAnticyclone:
    """Test TIME DECAY for anticyclone scenario (P=1037 hPa, ΔP=+0.2 hPa)."""

    def test_anticyclone_hour_0(self):
        """Hour 0: Z=10%, N=90% (stable anticyclone)."""
        z_weight, n_weight, reason = _calculate_weights_with_time_decay(
            current_pressure=1037.0,
            pressure_change=0.2,
            hours_ahead=0
        )
        
        # Expected: base_zambretti_weight = 0.10 (stable anticyclone)
        # With decay=1.0: final = 0.10 * 1.0 + 0.5 * 0.0 = 0.10
        assert abs(z_weight - 0.10) < 0.01, f"Hour 0: Expected Z≈10%, got {z_weight:.0%}"
        assert abs(n_weight - 0.90) < 0.01, f"Hour 0: Expected N≈90%, got {n_weight:.0%}"
        assert "stable anticyclone" in reason.lower()

    def test_anticyclone_hour_6(self):
        """Hour 6: Z≈26%, N≈74% (anticyclone weakening)."""
        z_weight, n_weight, reason = _calculate_weights_with_time_decay(
            current_pressure=1037.0,
            pressure_change=0.2,
            hours_ahead=6
        )
        
        # Expected: base=0.10, decay≈0.61
        # final = 0.10 * 0.61 + 0.5 * 0.39 = 0.061 + 0.195 = 0.256 ≈ 26%
        assert 0.24 <= z_weight <= 0.28, f"Hour 6: Expected Z≈26%, got {z_weight:.0%}"
        assert 0.72 <= n_weight <= 0.76, f"Hour 6: Expected N≈74%, got {n_weight:.0%}"

    def test_anticyclone_hour_12(self):
        """Hour 12: Z≈35%, N≈65% (trend developing)."""
        z_weight, n_weight, reason = _calculate_weights_with_time_decay(
            current_pressure=1037.0,
            pressure_change=0.2,
            hours_ahead=12
        )
        
        # Expected: base=0.10, decay≈0.37
        # final = 0.10 * 0.37 + 0.5 * 0.63 = 0.037 + 0.315 = 0.352 ≈ 35%
        assert 0.33 <= z_weight <= 0.37, f"Hour 12: Expected Z≈35%, got {z_weight:.0%}"
        assert 0.63 <= n_weight <= 0.67, f"Hour 12: Expected N≈65%, got {n_weight:.0%}"

    def test_anticyclone_hour_24(self):
        """Hour 24: Z≈46%, N≈54% (nearly balanced)."""
        z_weight, n_weight, reason = _calculate_weights_with_time_decay(
            current_pressure=1037.0,
            pressure_change=0.2,
            hours_ahead=24
        )
        
        # Expected: base=0.10, decay≈0.14
        # final = 0.10 * 0.14 + 0.5 * 0.86 = 0.014 + 0.43 = 0.444 ≈ 46%
        assert 0.44 <= z_weight <= 0.48, f"Hour 24: Expected Z≈46%, got {z_weight:.0%}"
        assert 0.52 <= n_weight <= 0.56, f"Hour 24: Expected N≈54%, got {n_weight:.0%}"


class TestTimeDecayRapidChange:
    """Test TIME DECAY for rapid change scenario (P=1015 hPa, ΔP=-5.0 hPa)."""

    def test_rapid_change_hour_0(self):
        """Hour 0: Z=75%, N=25% (rapid response)."""
        z_weight, n_weight, reason = _calculate_weights_with_time_decay(
            current_pressure=1015.0,
            pressure_change=-5.0,
            hours_ahead=0
        )
        
        # Expected: base_zambretti_weight = 0.75 (rapid change ≥3.0 hPa)
        # With decay=1.0: final = 0.75 * 1.0 + 0.5 * 0.0 = 0.75
        assert abs(z_weight - 0.75) < 0.01, f"Hour 0: Expected Z≈75%, got {z_weight:.0%}"
        assert abs(n_weight - 0.25) < 0.01, f"Hour 0: Expected N≈25%, got {n_weight:.0%}"
        assert "rapid change" in reason.lower()

    def test_rapid_change_hour_6(self):
        """Hour 6: Z≈66%, N≈34% (change continuing)."""
        z_weight, n_weight, reason = _calculate_weights_with_time_decay(
            current_pressure=1015.0,
            pressure_change=-5.0,
            hours_ahead=6
        )
        
        # Expected: base=0.75, decay≈0.61
        # final = 0.75 * 0.61 + 0.5 * 0.39 = 0.4575 + 0.195 = 0.6525 ≈ 66%
        assert 0.64 <= z_weight <= 0.68, f"Hour 6: Expected Z≈66%, got {z_weight:.0%}"
        assert 0.32 <= n_weight <= 0.36, f"Hour 6: Expected N≈34%, got {n_weight:.0%}"

    def test_rapid_change_hour_12(self):
        """Hour 12: Z≈59%, N≈41% (new equilibrium forming)."""
        z_weight, n_weight, reason = _calculate_weights_with_time_decay(
            current_pressure=1015.0,
            pressure_change=-5.0,
            hours_ahead=12
        )
        
        # Expected: base=0.75, decay≈0.37
        # final = 0.75 * 0.37 + 0.5 * 0.63 = 0.2775 + 0.315 = 0.5925 ≈ 59%
        assert 0.57 <= z_weight <= 0.61, f"Hour 12: Expected Z≈59%, got {z_weight:.0%}"
        assert 0.39 <= n_weight <= 0.43, f"Hour 12: Expected N≈41%, got {n_weight:.0%}"

    def test_rapid_change_hour_24(self):
        """Hour 24: Z≈53%, N≈47% (nearly balanced)."""
        z_weight, n_weight, reason = _calculate_weights_with_time_decay(
            current_pressure=1015.0,
            pressure_change=-5.0,
            hours_ahead=24
        )
        
        # Expected: base=0.75, decay≈0.14
        # final = 0.75 * 0.14 + 0.5 * 0.86 = 0.105 + 0.43 = 0.535 ≈ 53%
        assert 0.51 <= z_weight <= 0.55, f"Hour 24: Expected Z≈53%, got {z_weight:.0%}"
        assert 0.45 <= n_weight <= 0.49, f"Hour 24: Expected N≈47%, got {n_weight:.0%}"


class TestBackwardCompatibility:
    """Test that old function still works without TIME DECAY."""

    def test_calculate_combined_forecast_no_time_decay(self):
        """Verify calculate_combined_forecast() uses hours_ahead=0 (no decay)."""
        # Anticyclone scenario
        zambretti_result = ["Settled fine", 2]
        negretti_result = ["Fine weather", 1]
        
        # Call old function (should have no TIME DECAY)
        forecast_num_old, z_weight_old, n_weight_old, consensus_old = calculate_combined_forecast(
            zambretti_result=zambretti_result,
            negretti_result=negretti_result,
            current_pressure=1037.0,
            pressure_change=0.2,
            source="BackwardCompatTest"
        )
        
        # Call new function with hours_ahead=0 (should be identical)
        forecast_num_new, z_weight_new, n_weight_new, consensus_new = calculate_combined_forecast_with_time(
            zambretti_result=zambretti_result,
            negretti_result=negretti_result,
            current_pressure=1037.0,
            pressure_change=0.2,
            hours_ahead=0,
            source="BackwardCompatTest"
        )
        
        # Should be identical
        assert forecast_num_old == forecast_num_new, "Forecast numbers should match"
        assert abs(z_weight_old - z_weight_new) < 0.001, "Zambretti weights should match"
        assert abs(n_weight_old - n_weight_new) < 0.001, "Negretti weights should match"
        assert consensus_old == consensus_new, "Consensus should match"
        
        # Verify anticyclone behavior (90% Negretti)
        assert abs(z_weight_old - 0.10) < 0.01, "Should be 10% Zambretti"
        assert abs(n_weight_old - 0.90) < 0.01, "Should be 90% Negretti"

    def test_consensus_behavior(self):
        """Test consensus detection (models agree within ±1)."""
        # Models agree (codes 1 and 2, diff=1)
        zambretti_result = ["Settled fine", 2]
        negretti_result = ["Fine weather", 1]
        
        _, _, _, consensus = calculate_combined_forecast(
            zambretti_result=zambretti_result,
            negretti_result=negretti_result,
            current_pressure=1020.0,
            pressure_change=0.0,
            source="ConsensusTest"
        )
        
        assert consensus is True, "Models should be in consensus (diff ≤ 1)"

    def test_no_consensus_behavior(self):
        """Test no consensus (models disagree by >1)."""
        # Models disagree (codes 2 and 15, diff=13)
        zambretti_result = ["Settled fine", 2]
        negretti_result = ["Changeable, some rain", 15]
        
        _, _, _, consensus = calculate_combined_forecast(
            zambretti_result=zambretti_result,
            negretti_result=negretti_result,
            current_pressure=1020.0,
            pressure_change=0.0,
            source="NoConsensusTest"
        )
        
        assert consensus is False, "Models should NOT be in consensus (diff > 1)"


class TestTimeDecayProgression:
    """Test that TIME DECAY weights progress smoothly over time."""

    def test_weight_progression_is_monotonic(self):
        """Verify Zambretti weight increases monotonically for anticyclone."""
        current_pressure = 1037.0
        pressure_change = 0.2
        
        weights = []
        for hour in [0, 6, 12, 18, 24]:
            z_weight, _, _ = _calculate_weights_with_time_decay(
                current_pressure=current_pressure,
                pressure_change=pressure_change,
                hours_ahead=hour
            )
            weights.append(z_weight)
        
        # Should be strictly increasing (anticyclone moves toward balance)
        for i in range(len(weights) - 1):
            assert weights[i] < weights[i + 1], (
                f"Weight should increase: hour {i*6} ({weights[i]:.2f}) "
                f"< hour {(i+1)*6} ({weights[i+1]:.2f})"
            )

    def test_converges_to_balanced(self):
        """Verify weights converge to 50/50 for very long horizons."""
        # Test at 48 hours (very long forecast)
        z_weight, n_weight, _ = _calculate_weights_with_time_decay(
            current_pressure=1037.0,
            pressure_change=0.2,
            hours_ahead=48
        )
        
        # Should be very close to balanced (50/50)
        assert 0.48 <= z_weight <= 0.52, f"Hour 48 should be ~50%, got {z_weight:.0%}"
        assert 0.48 <= n_weight <= 0.52, f"Hour 48 should be ~50%, got {n_weight:.0%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
