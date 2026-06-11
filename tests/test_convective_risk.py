"""Tests for convective storm risk detection (get_convective_risk).

Convective (local) thunderstorms form from thermal instability and surface moisture.
They are NOT detected by barometric models — they often occur with RISING pressure
(mesohigh outflow). This risk function provides a complementary warning signal.

Meteorological basis:
- Dewpoint >= 10°C: minimum moisture for convective initiation (WMO)
- Temperature >= 18°C: minimum CAPE proxy (Brooks et al. 2003)
- Pressure 1005-1022 hPa: excludes anticyclone (>1022) and synoptic low (<1005)
- Hours 10-23: solar heating required for convective available potential energy
"""
import pytest

from custom_components.local_weather_forecast.calculations import get_convective_risk
from custom_components.local_weather_forecast.const import (
    CONVECTIVE_RISK_NONE,
    CONVECTIVE_RISK_LOW,
    CONVECTIVE_RISK_HIGH,
)


class TestConvectiveRiskHigh:
    """Test HIGH convective risk detection."""

    def test_high_risk_warm_moist_afternoon(self):
        """T=24°C, RH=68%, P=1013, h=15 → HIGH risk."""
        assert get_convective_risk(
            temperature=24.0, humidity=68.0, pressure=1013.0, hour=15, dewpoint=16.5
        ) == CONVECTIVE_RISK_HIGH

    def test_high_risk_evening_storm(self):
        """T=22°C, RH=68%, P=1013, h=21 → HIGH risk (last HIGH hour)."""
        assert get_convective_risk(
            temperature=22.0, humidity=68.0, pressure=1013.0, hour=21, dewpoint=14.5
        ) == CONVECTIVE_RISK_HIGH

    def test_low_risk_late_evening(self):
        """T=22°C, RH=68%, P=1013, h=22 → LOW risk (after HIGH hours 12-21)."""
        assert get_convective_risk(
            temperature=22.0, humidity=68.0, pressure=1013.0, hour=22, dewpoint=14.5
        ) == CONVECTIVE_RISK_LOW

    def test_high_risk_peak_hour(self):
        """T=26°C, RH=70%, P=1010, h=14 → HIGH risk (peak convective hour)."""
        assert get_convective_risk(
            temperature=26.0, humidity=70.0, pressure=1010.0, hour=14, dewpoint=19.0
        ) == CONVECTIVE_RISK_HIGH

    def test_high_risk_boundary_conditions(self):
        """T=22°C, RH=65%, P=1015, h=12 → HIGH risk (exact HIGH thresholds)."""
        result = get_convective_risk(
            temperature=22.0, humidity=65.0, pressure=1015.0, hour=12, dewpoint=14.0
        )
        assert result == CONVECTIVE_RISK_HIGH


class TestConvectiveRiskLow:
    """Test LOW convective risk detection."""

    def test_low_risk_moderate_conditions(self):
        """T=20°C, RH=58%, P=1015, h=19 → LOW risk."""
        assert get_convective_risk(
            temperature=20.0, humidity=58.0, pressure=1015.0, hour=19, dewpoint=11.0
        ) == CONVECTIVE_RISK_LOW

    def test_low_risk_early_afternoon(self):
        """T=18°C, RH=60%, P=1015, h=11 → LOW risk (minimum temp threshold met)."""
        assert get_convective_risk(
            temperature=18.0, humidity=60.0, pressure=1015.0, hour=11, dewpoint=10.0
        ) == CONVECTIVE_RISK_LOW

    def test_low_risk_not_enough_for_high(self):
        """T=21°C, RH=57%, P=1013, h=13 → LOW risk (humidity below HIGH threshold)."""
        assert get_convective_risk(
            temperature=21.0, humidity=57.0, pressure=1013.0, hour=13, dewpoint=11.5
        ) == CONVECTIVE_RISK_LOW


class TestConvectiveRiskNone:
    """Test NONE convective risk scenarios."""

    def test_none_night_hour(self):
        """T=24°C, RH=70%, P=1013, h=9 → NONE (hour < 10, no solar heating)."""
        assert get_convective_risk(
            temperature=24.0, humidity=70.0, pressure=1013.0, hour=9
        ) == CONVECTIVE_RISK_NONE

    def test_none_cold_temperature(self):
        """T=17°C → NONE (below 18°C minimum for CAPE)."""
        assert get_convective_risk(
            temperature=17.0, humidity=70.0, pressure=1013.0, hour=14
        ) == CONVECTIVE_RISK_NONE

    def test_none_anticyclone(self):
        """T=26°C, P=1025 → NONE (anticyclone suppresses convection)."""
        assert get_convective_risk(
            temperature=26.0, humidity=65.0, pressure=1025.0, hour=14
        ) == CONVECTIVE_RISK_NONE

    def test_none_anticyclone_boundary(self):
        """T=26°C, P=1023 → NONE (just above 1022 boundary)."""
        assert get_convective_risk(
            temperature=26.0, humidity=65.0, pressure=1023.0, hour=14
        ) == CONVECTIVE_RISK_NONE

    def test_none_synoptic_low(self):
        """T=26°C, P=1003 → NONE (synoptic low < 1005, different mechanism)."""
        assert get_convective_risk(
            temperature=26.0, humidity=65.0, pressure=1003.0, hour=14
        ) == CONVECTIVE_RISK_NONE

    def test_none_dry_air(self):
        """T=30°C, RH=35%, Td=12°C → NONE (dewpoint < 10°C)."""
        # Td = 30 - (100-35)/5 = 30 - 13 = 17, but explicit dewpoint=8 overrides
        assert get_convective_risk(
            temperature=30.0, humidity=35.0, pressure=1013.0, hour=14, dewpoint=8.0
        ) == CONVECTIVE_RISK_NONE

    def test_none_low_dewpoint_auto_calculated(self):
        """RH=25% → auto-calculated Td = T - (100-RH)/5 < 10°C → NONE."""
        # T=25, RH=25: Td = 25 - 75/5 = 25 - 15 = 10.0 (boundary)
        # T=24, RH=22: Td = 24 - 78/5 = 24 - 15.6 = 8.4 → NONE
        assert get_convective_risk(
            temperature=24.0, humidity=22.0, pressure=1013.0, hour=14
        ) == CONVECTIVE_RISK_NONE

    def test_none_midnight_hour(self):
        """h=0 (midnight) → NONE."""
        assert get_convective_risk(
            temperature=22.0, humidity=70.0, pressure=1013.0, hour=0
        ) == CONVECTIVE_RISK_NONE


class TestDewpointAutoCalculation:
    """Test that dewpoint is correctly auto-calculated when not provided."""

    def test_auto_dewpoint_gives_same_result(self):
        """Explicit dewpoint should give same result as auto-calculated."""
        # T=24, RH=68: Td = 24 - (100-68)/5 = 24 - 6.4 = 17.6 → HIGH
        result_auto = get_convective_risk(
            temperature=24.0, humidity=68.0, pressure=1013.0, hour=15
        )
        result_explicit = get_convective_risk(
            temperature=24.0, humidity=68.0, pressure=1013.0, hour=15, dewpoint=17.6
        )
        assert result_auto == result_explicit == CONVECTIVE_RISK_HIGH

    def test_auto_dewpoint_dry_air_none(self):
        """Low RH → auto-calculated Td too low → NONE."""
        # T=25, RH=30: Td = 25 - 70/5 = 25 - 14 = 11.0 → still >= 10
        # T=25, RH=25: Td = 25 - 75/5 = 25 - 15 = 10.0 → boundary (>=10, could be LOW)
        # T=25, RH=20: Td = 25 - 80/5 = 25 - 16 = 9.0 → NONE
        result = get_convective_risk(
            temperature=25.0, humidity=20.0, pressure=1013.0, hour=14
        )
        assert result == CONVECTIVE_RISK_NONE
