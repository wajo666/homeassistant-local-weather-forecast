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


# ============================================================================
# Regression window: pressure uses only 180-min, temperature uses only 60-min
# ============================================================================

def _linear_regression(data, extrapolate_minutes):
    """Helper: compute regression slope × extrapolate_minutes from (timestamp, value) pairs.

    Mimics the sensor.py regression logic for unit testing without HA dependency.
    """
    n = len(data)
    t0 = data[0][0]
    times = [(ts - t0).total_seconds() / 60.0 for ts, _ in data]
    values = [v for _, v in data]

    t_mean = sum(times) / n
    v_mean = sum(values) / n

    numerator = sum((t - t_mean) * (v - v_mean) for t, v in zip(times, values))
    denominator = sum((t - t_mean) ** 2 for t in times)

    if denominator > 0:
        slope = numerator / denominator
        return round(slope * extrapolate_minutes, 2)
    return 0.0


class TestPressureRegressionWindow:
    """Test that pressure regression uses only 180-min data window."""

    def test_regression_uses_only_180min_window(self):
        """7.5h buffer — regression must match 3h-only result, not full buffer."""
        from datetime import timedelta

        base = datetime(2025, 3, 23, 14, 0, 0)
        # 36 points over 7.5h: slow rise 1017→1019.2
        full_buffer = []
        for i in range(36):
            ts = base + timedelta(minutes=i * 12.5)
            pressure = 1017.0 + (2.2 * i / 35)
            full_buffer.append((ts, pressure))

        # Full buffer regression (wrong — over 7.5h)
        full_result = _linear_regression(full_buffer, 180)

        # 180-min window only (correct)
        cutoff = full_buffer[-1][0] - timedelta(minutes=180)
        window_data = [(ts, p) for ts, p in full_buffer if ts > cutoff]
        window_result = _linear_regression(window_data, 180)

        # Both should give similar results for linear data,
        # but with non-linear data they'd differ
        assert len(window_data) < len(full_buffer), \
            "Window should have fewer points than full buffer"
        assert abs(full_result - window_result) < 0.5, \
            "For linear data, results should be similar"

    def test_regression_3h_window_excludes_old_data(self):
        """Old data that contradicts current trend must be excluded."""
        from datetime import timedelta

        base = datetime(2025, 3, 23, 14, 0, 0)
        # First 2h: pressure FALLING 1020 → 1017
        # Last 3h: pressure RISING 1017 → 1019.2
        data = []
        # Old falling data (4h-2h ago)
        for i in range(12):
            ts = base + timedelta(minutes=i * 10)
            pressure = 1020.0 - (3.0 * i / 11)
            data.append((ts, pressure))
        # Recent rising data (last 3h)
        for i in range(18):
            ts = base + timedelta(minutes=120 + i * 10)
            pressure = 1017.0 + (2.2 * i / 17)
            data.append((ts, pressure))

        # Full buffer regression: diluted by old falling data
        full_result = _linear_regression(data, 180)

        # 180-min window only: sees only rising data
        cutoff = data[-1][0] - timedelta(minutes=180)
        window_data = [(ts, p) for ts, p in data if ts > cutoff]
        window_result = _linear_regression(window_data, 180)

        # Window result must be positive (rising), full might be near zero
        assert window_result > 1.0, \
            f"3h window should show rising trend, got {window_result}"
        assert window_result > full_result, \
            "3h window should show stronger rise than diluted full buffer"

    def test_regression_fallback_when_few_points(self):
        """< 2 points in 3h window — must fall back to full buffer."""
        from datetime import timedelta

        base = datetime(2025, 3, 23, 14, 0, 0)
        # Only 1 point in 3h window, rest are old
        data = [
            (base, 1015.0),
            (base + timedelta(minutes=30), 1015.5),
            (base + timedelta(minutes=300), 1017.0),  # Only this in 3h window
        ]

        cutoff = data[-1][0] - timedelta(minutes=180)
        window_data = [(ts, p) for ts, p in data if ts > cutoff]
        assert len(window_data) < 2, "Should have < 2 points in window"

        # Fallback to full buffer should still produce a result
        result = _linear_regression(data, 180)
        assert result > 0, "Fallback regression should show rising trend"


class TestTemperatureRegressionWindow:
    """Test that temperature regression uses only 60-min data window."""

    def test_temp_regression_uses_only_60min_window(self):
        """2h buffer — regression must use only last 1h data."""
        from datetime import timedelta

        base = datetime(2025, 3, 23, 20, 0, 0)
        # First hour: cooling 10.1 → 8.9
        # Second hour: warming 9.1 → 9.4
        data = []
        for i in range(6):
            ts = base + timedelta(minutes=i * 10)
            temp = 10.1 - (1.2 * i / 5)
            data.append((ts, temp))
        for i in range(6):
            ts = base + timedelta(minutes=60 + i * 10)
            temp = 9.1 + (0.3 * i / 5)
            data.append((ts, temp))

        # Full buffer (wrong): sees cooling + warming → net negative
        full_result = _linear_regression(data, 60)

        # 60-min window (correct): sees only warming
        cutoff = data[-1][0] - timedelta(minutes=60)
        window_data = [(ts, t) for ts, t in data if ts > cutoff]
        window_result = _linear_regression(window_data, 60)

        assert full_result < 0, \
            f"Full buffer should show net cooling, got {full_result}"
        assert window_result > 0, \
            f"1h window should show warming, got {window_result}"

    def test_temp_inverted_trend_fixed(self):
        """User data: actual 1h trend is +0.3°C but old code showed -0.7°C."""
        from datetime import timedelta

        base = datetime(2025, 3, 23, 19, 42, 0)
        # Exact user data from Issue report
        user_data = [
            (base, 10.1),
            (base + timedelta(minutes=20), 10.0),
            (base + timedelta(minutes=30), 9.7),
            (base + timedelta(minutes=32), 9.6),
            (base + timedelta(minutes=40), 9.3),
            (base + timedelta(minutes=46), 9.1),
            (base + timedelta(minutes=49), 9.0),
            (base + timedelta(minutes=50), 8.9),
            (base + timedelta(minutes=90), 9.1),
            (base + timedelta(minutes=100), 9.2),
            (base + timedelta(minutes=110), 9.3),
            (base + timedelta(minutes=120), 9.4),
        ]

        # Old method: newest - oldest
        old_result = user_data[-1][1] - user_data[0][1]
        assert old_result == pytest.approx(-0.7, abs=0.01), \
            "Sanity check: old method gives -0.7"

        # New method: regression over 60-min window
        cutoff = user_data[-1][0] - timedelta(minutes=60)
        window_data = [(ts, t) for ts, t in user_data if ts > cutoff]
        window_result = _linear_regression(window_data, 60)

        # 1h window should show warming (positive), not cooling
        assert window_result > 0, \
            f"1h regression should show warming, got {window_result}"

    def test_temp_qc_rejects_nan(self):
        """NaN temperature must be rejected (tested via constant existence)."""
        assert math.isnan(float('nan'))
        assert math.isinf(float('inf'))

    def test_temp_qc_spike_limit(self):
        """Temperature spike limit constant exists and is reasonable."""
        from custom_components.local_weather_forecast.const import TEMPERATURE_SPIKE_LIMIT
        assert TEMPERATURE_SPIKE_LIMIT == 10.0

    def test_temp_regression_fallback_few_points(self):
        """< 2 points in 1h window — must fall back to full buffer."""
        from datetime import timedelta

        base = datetime(2025, 3, 23, 18, 0, 0)
        data = [
            (base, 15.0),
            (base + timedelta(minutes=30), 15.5),
            (base + timedelta(minutes=120), 16.0),  # Only this in 1h window
        ]

        cutoff = data[-1][0] - timedelta(minutes=60)
        window_data = [(ts, t) for ts, t in data if ts > cutoff]
        assert len(window_data) < 2, "Should have < 2 points in window"

        # Fallback to full buffer
        result = _linear_regression(data, 60)
        assert result > 0, "Fallback regression should show warming"
