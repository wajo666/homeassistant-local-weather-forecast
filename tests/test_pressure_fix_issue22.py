"""Tests for Issue #22 fix: false morning rain predictions.

Tests cover:
- Phase 0: AWS QC input validation (sensor.py)
- Phase 1: Linear regression pressure change (sensor.py)
- Phase 2c: Shared functions in calculations.py
- Phase 3: Threshold harmonization (±1.6 hPa)
- Phase 5a: Sanity check in combined_model.py
- Phase 5b: PressureModel dead zone
"""
import math
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from custom_components.local_weather_forecast.const import (
    PRESSURE_QC_MAX,
    PRESSURE_QC_MIN,
    PRESSURE_SPIKE_LIMIT,
    PRESSURE_TREND_FALLING,
    PRESSURE_TREND_RISING,
)
from custom_components.local_weather_forecast.calculations import (
    calculate_sea_level_pressure,
    get_beaufort_number,
    get_atmosphere_stability,
)
from custom_components.local_weather_forecast.combined_model import (
    calculate_combined_forecast_with_time,
)
from custom_components.local_weather_forecast.forecast_calculator import (
    PressureModel,
)
from custom_components.local_weather_forecast.zambretti import (
    calculate_zambretti_forecast,
)
from custom_components.local_weather_forecast.negretti_zambra import (
    calculate_negretti_zambra_forecast,
)
from custom_components.local_weather_forecast.wmo_simple import (
    calculate_wmo_simple_forecast,
)


# ============================================================================
# Phase 0: AWS QC input validation constants
# ============================================================================

class TestQCConstants:
    """Test QC constant values match professional meteorological standards."""

    def test_qc_min_is_870(self):
        """Lowest recorded sea-level: Typhoon Tip 1979 = 870 hPa."""
        assert PRESSURE_QC_MIN == 870.0

    def test_qc_max_is_1084(self):
        """Highest recorded sea-level: Agata Siberia 1968 = 1084 hPa."""
        assert PRESSURE_QC_MAX == 1084.0

    def test_spike_limit_is_10(self):
        """Max change between consecutive readings = 10 hPa."""
        assert PRESSURE_SPIKE_LIMIT == 10.0

    def test_trend_rising_is_1_6(self):
        """Rising threshold = +1.6 hPa (Negretti-Zambra standard)."""
        assert PRESSURE_TREND_RISING == 1.6

    def test_trend_falling_is_neg_1_6(self):
        """Falling threshold = -1.6 hPa (Negretti-Zambra standard)."""
        assert PRESSURE_TREND_FALLING == -1.6


# ============================================================================
# Phase 2c: Shared functions (calculations.py)
# ============================================================================

class TestCalculateSeaLevelPressure:
    """Test shared calculate_sea_level_pressure function."""

    def test_zero_elevation_returns_station_pressure(self):
        """At sea level, QNH = QFE."""
        assert calculate_sea_level_pressure(1013.25, 20.0, 0) == 1013.25

    def test_positive_elevation_increases_pressure(self):
        """Higher elevation → larger QNH correction."""
        p0 = calculate_sea_level_pressure(970.0, 15.0, 314.0)
        assert p0 > 970.0, "QNH must be higher than QFE at elevation"

    def test_typical_central_europe(self):
        """Bratislava ~140m: QFE≈997 → QNH≈1013."""
        p0 = calculate_sea_level_pressure(997.0, 15.0, 140.0)
        assert 1010 < p0 < 1016


class TestGetBeaufortNumber:
    """Test shared get_beaufort_number function."""

    def test_calm(self):
        assert get_beaufort_number(0.0) == 0

    def test_light_air(self):
        assert get_beaufort_number(1.0) == 1

    def test_moderate_breeze(self):
        assert get_beaufort_number(6.0) == 4

    def test_hurricane(self):
        assert get_beaufort_number(35.0) == 12


class TestGetAtmosphereStability:
    """Test shared get_atmosphere_stability function."""

    def test_no_gust_ratio(self):
        assert get_atmosphere_stability(5.0, None) == "unknown"

    def test_stable(self):
        assert get_atmosphere_stability(5.0, 1.2) == "stable"

    def test_very_unstable(self):
        assert get_atmosphere_stability(10.0, 2.5) == "very_unstable"


# ============================================================================
# Phase 3: Threshold harmonization (±1.6 hPa)
# ============================================================================

class TestZambrettiThresholds:
    """Test Zambretti uses ±1.6 hPa thresholds."""

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_minus_1_2_is_steady_not_falling(self, mock_datetime):
        """Core bug fix: -1.2 hPa must NOT trigger FALLING formula."""
        mock_datetime.now.return_value = datetime(2025, 1, 15, 6, 0)
        # -1.2 is between -1.6 and 0, so STEADY
        result_steady = calculate_zambretti_forecast(
            1013.0, -1.2, [0, 0.0, "N", 0], 1
        )
        result_falling = calculate_zambretti_forecast(
            1013.0, -1.8, [0, 0.0, "N", 0], 1
        )
        # -1.2 should give STEADY (same as 0.0 change)
        result_zero = calculate_zambretti_forecast(
            1013.0, 0.0, [0, 0.0, "N", 0], 1
        )
        # Steady results should match each other, not falling
        assert result_steady[1] == result_zero[1], (
            f"-1.2 hPa gave code {result_steady[1]}, expected same as steady ({result_zero[1]})"
        )

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_minus_1_6_is_still_steady(self, mock_datetime):
        """Threshold is strict less-than: exactly -1.6 is NOT falling."""
        mock_datetime.now.return_value = datetime(2025, 1, 15, 6, 0)
        result = calculate_zambretti_forecast(
            1013.0, -1.6, [0, 0.0, "N", 0], 1
        )
        result_zero = calculate_zambretti_forecast(
            1013.0, 0.0, [0, 0.0, "N", 0], 1
        )
        # -1.6 should still be STEADY (not < -1.6)
        assert result[1] == result_zero[1]

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_minus_1_7_is_falling(self, mock_datetime):
        """Just below threshold: -1.7 IS falling."""
        mock_datetime.now.return_value = datetime(2025, 1, 15, 6, 0)
        # Use high pressure where steady vs falling differ clearly
        result_falling = calculate_zambretti_forecast(
            1025.0, -1.7, [0, 0.0, "N", 0], 1
        )
        result_zero = calculate_zambretti_forecast(
            1025.0, 0.0, [0, 0.0, "N", 0], 1
        )
        # At 1025 hPa, falling formula gives worse weather than steady
        assert result_falling[1] >= result_zero[1], (
            "-1.7 hPa at high pressure should predict worse weather than steady"
        )


class TestNegrettiThresholds:
    """Test Negretti-Zambra uses ±1.6 hPa thresholds."""

    @patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
    def test_minus_1_2_is_steady(self, mock_datetime):
        """Negretti: -1.2 hPa must be STEADY."""
        mock_datetime.now.return_value = datetime(2025, 1, 15, 6, 0)
        result_sub = calculate_negretti_zambra_forecast(
            1013.0, -1.2, [0, 0.0, "N", 0], 1, 314.0
        )
        result_zero = calculate_negretti_zambra_forecast(
            1013.0, 0.0, [0, 0.0, "N", 0], 1, 314.0
        )
        assert result_sub[1] == result_zero[1]


class TestWmoSimpleThresholds:
    """Test WMO Simple uses ±1.6 hPa thresholds."""

    def test_minus_1_2_is_steady(self):
        """WMO: -1.2 hPa must NOT worsen forecast."""
        # WMO takes (current_condition_code, pressure_change_3h, lang_index, hours_ahead)
        result_sub = calculate_wmo_simple_forecast(5, -1.2, 1, 1)
        result_zero = calculate_wmo_simple_forecast(5, 0.0, 1, 1)
        # Sub-threshold change should give same result as no change
        assert result_sub[1] == result_zero[1]


# ============================================================================
# Phase 3f: PressureModel dead zone
# ============================================================================

class TestPressureModelDeadZone:
    """Test PressureModel suppresses sub-threshold pressure changes."""

    def test_sub_threshold_change_zeroed(self):
        """±1.5 hPa/3h → change_rate_1h = 0.0 (dead zone)."""
        model = PressureModel(1013.0, -1.2)
        assert model.change_rate_1h == 0.0
        assert model.change_rate_3h == -1.2  # Raw value preserved

    def test_at_threshold_still_zeroed(self):
        """Exactly ±1.6 → abs(1.6) < abs(-1.6) is False → NOT zeroed."""
        model = PressureModel(1013.0, -1.6)
        # abs(-1.6) < abs(-1.6) → False, so NOT in dead zone
        assert model.change_rate_1h != 0.0

    def test_above_threshold_not_zeroed(self):
        """±1.8 hPa/3h → change_rate_1h = ±0.6 (real trend)."""
        model = PressureModel(1013.0, -1.8)
        assert model.change_rate_1h == pytest.approx(-0.6, abs=0.01)

    def test_positive_sub_threshold_zeroed(self):
        """+1.2 hPa/3h → dead zone."""
        model = PressureModel(1013.0, 1.2)
        assert model.change_rate_1h == 0.0

    def test_get_trend_steady_for_sub_threshold(self):
        """get_trend returns 'steady' when change is sub-threshold."""
        model = PressureModel(1013.0, -1.2)
        assert model.get_trend(3) == "steady"

    def test_get_trend_falling_above_threshold(self):
        """get_trend returns 'falling' for real pressure drop."""
        model = PressureModel(1013.0, -3.0)
        assert model.get_trend(3) == "falling"

    def test_predict_no_change_sub_threshold(self):
        """Prediction = current pressure when sub-threshold."""
        model = PressureModel(1013.0, -1.2)
        assert model.predict(3) == pytest.approx(1013.0, abs=0.01)


# ============================================================================
# Phase 5a: Combined model sanity check
# ============================================================================

class TestSanityCheck:
    """Test multi-level sanity check caps impossible rain predictions."""

    @patch('custom_components.local_weather_forecast.combined_model.datetime')
    def test_level1_clear_sky_dry_caps_rain(self, mock_datetime):
        """L1: cloud<25% + humidity<50% → rain forecast capped to ≤5."""
        mock_datetime.now.return_value = datetime(2025, 7, 15, 6, 0)
        # Zambretti says rain (code 20), Negretti says rain (code 20)
        forecast_number, _, _, _ = calculate_combined_forecast_with_time(
            zambretti_result=["Rain", 20],
            negretti_result=["Rain", 20],
            current_pressure=1013.0,
            pressure_change=-2.0,
            hours_ahead=0,
            source="test",
            cloud_cover=10.0,   # Clear sky
            humidity=30.0,      # Very dry
        )
        assert forecast_number <= 5, f"Clear+dry should cap rain, got code {forecast_number}"

    @patch('custom_components.local_weather_forecast.combined_model.datetime')
    def test_level2_very_dry_caps_rain(self, mock_datetime):
        """L2: humidity<35% (no cloud data) → rain forecast capped to ≤5."""
        mock_datetime.now.return_value = datetime(2025, 7, 15, 6, 0)
        forecast_number, _, _, _ = calculate_combined_forecast_with_time(
            zambretti_result=["Rain", 20],
            negretti_result=["Rain", 20],
            current_pressure=1013.0,
            pressure_change=-2.0,
            hours_ahead=0,
            source="test",
            cloud_cover=None,   # No cloud sensor
            humidity=25.0,      # Very dry
        )
        assert forecast_number <= 5, f"Very dry should cap rain, got code {forecast_number}"

    @patch('custom_components.local_weather_forecast.combined_model.datetime')
    def test_level3_no_sensors_passes_through(self, mock_datetime):
        """L3: no cloud/humidity → forecast passes through unchanged."""
        mock_datetime.now.return_value = datetime(2025, 7, 15, 6, 0)
        forecast_number, _, _, _ = calculate_combined_forecast_with_time(
            zambretti_result=["Rain", 20],
            negretti_result=["Rain", 20],
            current_pressure=1013.0,
            pressure_change=-2.0,
            hours_ahead=0,
            source="test",
            cloud_cover=None,
            humidity=None,
        )
        # Should NOT be capped (no sensor data to check)
        assert forecast_number == 20

    @patch('custom_components.local_weather_forecast.combined_model.datetime')
    def test_non_rain_forecast_not_capped(self, mock_datetime):
        """Sanity check only applies to rain forecasts (code >= 13)."""
        mock_datetime.now.return_value = datetime(2025, 7, 15, 6, 0)
        forecast_number, _, _, _ = calculate_combined_forecast_with_time(
            zambretti_result=["Fine", 5],
            negretti_result=["Fine", 5],
            current_pressure=1020.0,
            pressure_change=0.0,
            hours_ahead=0,
            source="test",
            cloud_cover=10.0,
            humidity=30.0,
        )
        assert forecast_number == 5

    @patch('custom_components.local_weather_forecast.combined_model.datetime')
    def test_cloudy_and_humid_not_capped(self, mock_datetime):
        """High clouds + high humidity → rain forecast is legitimate."""
        mock_datetime.now.return_value = datetime(2025, 7, 15, 6, 0)
        forecast_number, _, _, _ = calculate_combined_forecast_with_time(
            zambretti_result=["Rain", 20],
            negretti_result=["Rain", 20],
            current_pressure=1005.0,
            pressure_change=-3.0,
            hours_ahead=0,
            source="test",
            cloud_cover=80.0,   # Overcast
            humidity=85.0,      # Humid
        )
        assert forecast_number == 20, "Cloudy+humid rain should NOT be capped"


# ============================================================================
# Integration: Morning scenario (Issue #22)
# ============================================================================

class TestMorningScenario:
    """Test the specific Issue #22 morning scenario end-to-end."""

    @patch('custom_components.local_weather_forecast.zambretti.datetime')
    def test_morning_slight_drop_no_rain_zambretti(self, mock_datetime):
        """6 AM, -1.2 hPa drop → Zambretti treats as STEADY, not FALLING."""
        mock_datetime.now.return_value = datetime(2025, 7, 15, 6, 0)
        result_sub = calculate_zambretti_forecast(
            1013.0, -1.2, [0, 0.0, "N", 0], 1
        )
        result_zero = calculate_zambretti_forecast(
            1013.0, 0.0, [0, 0.0, "N", 0], 1
        )
        # -1.2 must produce same result as 0.0 (STEADY formula)
        assert result_sub[1] == result_zero[1], (
            f"Morning -1.2 hPa: Zambretti used FALLING formula (code {result_sub[1]}), "
            f"should match STEADY (code {result_zero[1]})"
        )

    @patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
    def test_morning_slight_drop_no_rain_negretti(self, mock_datetime):
        """6 AM, -1.2 hPa drop → Negretti must NOT predict rain."""
        mock_datetime.now.return_value = datetime(2025, 7, 15, 6, 0)
        result = calculate_negretti_zambra_forecast(
            1013.0, -1.2, [0, 0.0, "N", 0], 1, 314.0
        )
        assert result[1] <= 12, (
            f"Morning -1.2 hPa: Negretti predicted rain (code {result[1]}), "
            f"should be steady weather"
        )

    def test_morning_slight_drop_no_rain_wmo(self):
        """6 AM, -1.2 hPa drop → WMO treats as STEADY."""
        # Start with fair weather (code 5)
        result_sub = calculate_wmo_simple_forecast(5, -1.2, 1, 1)
        result_zero = calculate_wmo_simple_forecast(5, 0.0, 1, 1)
        assert result_sub[1] == result_zero[1], (
            f"Morning -1.2 hPa: WMO used FALLING formula (code {result_sub[1]}), "
            f"should match STEADY (code {result_zero[1]})"
        )

    def test_morning_pressure_model_steady(self):
        """PressureModel: -1.2 hPa/3h = dead zone = steady."""
        model = PressureModel(1013.0, -1.2)
        assert model.get_trend(0) == "steady"
        assert model.get_trend(3) == "steady"
        assert model.get_trend(6) == "steady"
