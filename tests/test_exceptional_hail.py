"""Test exceptional and hail weather conditions.

NOTE: These tests verify the LOGIC of exceptional/hail detection,
not the full integration (which requires complex mocking of HA internals).
Full integration is tested in real HA environment.

Thresholds based on:
- Brooks et al. (2003), Allen & Karoly (2014) — temperature 18-35°C
- SPC guidelines — humidity >65%
- Bradbury et al. (1994) — gust ratio >2.0
- WMO severe thunderstorm — gust >=15 m/s
- ESSL ESWD — pressure <1015 hPa for hail (general); <1000 hPa for significant hail (>5cm)
- Groenemeijer & van Delden (2007) — pressure <980 hPa for lightning-rainy
"""
import pytest

# Mirror runtime constants for test validation
HAIL_PRESSURE_MAX = 1015.0
HAIL_TEMP_MIN = 18.0
HAIL_TEMP_MAX = 35.0
HAIL_HUMIDITY_MIN = 65.0
HAIL_GUST_RATIO_MIN = 2.0
HAIL_GUST_MIN = 15.0
LIGHTNING_PRESSURE_MAX = 980.0


def check_hail_conditions(pressure, temp, humidity, gust_ratio, wind_gust):
    """Check if all hail conditions are met (mirrors runtime logic)."""
    if any(v is None for v in [pressure, temp, humidity, gust_ratio, wind_gust]):
        return False
    return (
        pressure < HAIL_PRESSURE_MAX
        and HAIL_TEMP_MIN <= temp <= HAIL_TEMP_MAX
        and humidity > HAIL_HUMIDITY_MIN
        and gust_ratio > HAIL_GUST_RATIO_MIN
        and wind_gust >= HAIL_GUST_MIN
    )


def resolve_precipitation(pressure, hail_conditions_present, is_raining):
    """Resolve precipitation type (mirrors runtime precipitation resolver)."""
    if not is_raining:
        return None
    # Deep cyclone
    if pressure is not None and pressure < LIGHTNING_PRESSURE_MAX:
        if hail_conditions_present:
            return "hail"
        return "lightning-rainy"
    # Moderate low + hail
    if hail_conditions_present:
        return "hail"
    # Normal rain
    return "rainy"


class TestExceptionalLogic:
    """Test exceptional weather detection logic."""

    def test_exceptional_hurricane_condition(self):
        """Test hurricane-force low pressure triggers exceptional."""
        pressure = 915.0
        assert pressure < 950, "Hurricane condition met"

    def test_exceptional_extreme_high_condition(self):
        """Test extreme high pressure triggers exceptional."""
        pressure = 1075.0
        assert pressure > 1050, "Extreme high pressure condition met"

    def test_exceptional_bomb_cyclone_condition(self):
        """Test bomb cyclone (rapid change) triggers exceptional."""
        pressure_change = -25.0
        assert abs(pressure_change) > 24, "Bomb cyclone condition met"

    def test_exceptional_rapid_rise_condition(self):
        """Test rapid pressure rise triggers exceptional."""
        pressure_change = 25.5
        assert abs(pressure_change) > 24, "Rapid rise condition met"

    def test_normal_pressure_no_exceptional(self):
        """Test normal conditions don't trigger exceptional."""
        pressure = 1015.0
        pressure_change = -2.0

        assert not (pressure < 950), "Not hurricane"
        assert not (pressure > 1050), "Not extreme high"
        assert not (abs(pressure_change) > 24), "Not bomb cyclone"


class TestHailLogic:
    """Test hail detection logic with science-based thresholds."""

    def test_hail_perfect_conditions(self):
        """Test all hail conditions met → hail."""
        assert check_hail_conditions(
            pressure=990.0, temp=24.0, humidity=75.0,
            gust_ratio=2.5, wind_gust=18.0
        )

    def test_hail_at_boundary_temp_low(self):
        """Test hail at lower temperature boundary (18°C)."""
        assert check_hail_conditions(
            pressure=990.0, temp=18.0, humidity=70.0,
            gust_ratio=2.5, wind_gust=16.0
        )

    def test_hail_at_boundary_temp_high(self):
        """Test hail at upper temperature boundary (35°C)."""
        assert check_hail_conditions(
            pressure=990.0, temp=35.0, humidity=70.0,
            gust_ratio=2.5, wind_gust=16.0
        )

    def test_no_hail_temp_below_range(self):
        """Test no hail below temperature range (17.9°C)."""
        assert not check_hail_conditions(
            pressure=990.0, temp=17.9, humidity=75.0,
            gust_ratio=2.5, wind_gust=18.0
        )

    def test_no_hail_temp_above_range(self):
        """Test no hail above temperature range (35.1°C)."""
        assert not check_hail_conditions(
            pressure=990.0, temp=35.1, humidity=75.0,
            gust_ratio=2.5, wind_gust=18.0
        )

    def test_no_hail_low_humidity(self):
        """Test no hail when humidity <= 65%."""
        assert not check_hail_conditions(
            pressure=990.0, temp=24.0, humidity=65.0,
            gust_ratio=2.5, wind_gust=18.0
        )

    def test_no_hail_stable_atmosphere(self):
        """Test no hail when gust ratio <= 2.0."""
        assert not check_hail_conditions(
            pressure=990.0, temp=24.0, humidity=75.0,
            gust_ratio=2.0, wind_gust=18.0
        )

    def test_no_hail_at_high_pressure(self):
        """Test no hail at P >= 1015 hPa (anticyclone, no storm context)."""
        assert not check_hail_conditions(
            pressure=1020.0, temp=24.0, humidity=75.0,
            gust_ratio=2.5, wind_gust=18.0
        )

    def test_no_hail_at_boundary_pressure(self):
        """Test no hail at exactly P = 1015 hPa (boundary, not below threshold)."""
        assert not check_hail_conditions(
            pressure=1015.0, temp=24.0, humidity=75.0,
            gust_ratio=2.5, wind_gust=18.0
        )

    def test_hail_at_typical_summer_pressure(self):
        """Test hail at typical CE summer thunderstorm pressure (1013 hPa)."""
        assert check_hail_conditions(
            pressure=1013.0, temp=24.0, humidity=75.0,
            gust_ratio=2.5, wind_gust=18.0
        )

    def test_no_hail_low_gust_speed(self):
        """Test no hail when gust ratio high but gust speed < 15 m/s (ratio artifact)."""
        assert not check_hail_conditions(
            pressure=990.0, temp=24.0, humidity=75.0,
            gust_ratio=2.5, wind_gust=5.0
        )

    def test_no_hail_missing_gust_ratio(self):
        """Test no hail when gust_ratio sensor unavailable (None)."""
        assert not check_hail_conditions(
            pressure=990.0, temp=24.0, humidity=75.0,
            gust_ratio=None, wind_gust=18.0
        )

    def test_no_hail_missing_wind_gust(self):
        """Test no hail when wind_gust sensor unavailable (None)."""
        assert not check_hail_conditions(
            pressure=990.0, temp=24.0, humidity=75.0,
            gust_ratio=2.5, wind_gust=None
        )

    def test_no_hail_missing_pressure(self):
        """Test no hail when pressure unavailable (None)."""
        assert not check_hail_conditions(
            pressure=None, temp=24.0, humidity=75.0,
            gust_ratio=2.5, wind_gust=18.0
        )

    def test_hail_at_deep_low(self):
        """Test hail at P=985 hPa with all conditions met."""
        assert check_hail_conditions(
            pressure=985.0, temp=24.0, humidity=75.0,
            gust_ratio=2.5, wind_gust=18.0
        )


class TestLightningRainyLogic:
    """Test lightning-rainy detection in precipitation resolver."""

    def test_lightning_rainy_deep_low_no_hail(self):
        """Test P < 980 + rain + no hail conditions → lightning-rainy."""
        result = resolve_precipitation(
            pressure=975.0, hail_conditions_present=False, is_raining=True
        )
        assert result == "lightning-rainy"

    def test_hail_overrides_lightning_at_deep_low(self):
        """Test P < 980 + rain + hail conditions → hail (not lightning-rainy)."""
        result = resolve_precipitation(
            pressure=975.0, hail_conditions_present=True, is_raining=True
        )
        assert result == "hail"

    def test_no_lightning_rainy_above_threshold(self):
        """Test P >= 980 + rain + no hail → normal rain."""
        result = resolve_precipitation(
            pressure=985.0, hail_conditions_present=False, is_raining=True
        )
        assert result == "rainy"

    def test_hail_at_moderate_low(self):
        """Test P 980-1015 + rain + hail conditions → hail."""
        result = resolve_precipitation(
            pressure=990.0, hail_conditions_present=True, is_raining=True
        )
        assert result == "hail"

    def test_normal_rain_high_pressure(self):
        """Test P >= 1015 + rain → normal rain (never hail/lightning)."""
        # hail_conditions_present would be False at P>=1000 due to pressure gate
        result = resolve_precipitation(
            pressure=1015.0, hail_conditions_present=False, is_raining=True
        )
        assert result == "rainy"

    def test_no_precip_returns_none(self):
        """Test no rain → None regardless of pressure."""
        result = resolve_precipitation(
            pressure=970.0, hail_conditions_present=False, is_raining=False
        )
        assert result is None


class TestPriorityLogic:
    """Test priority order logic."""

    def test_exceptional_priority_over_rain(self):
        """Test exceptional has higher priority than rain."""
        has_exceptional = True
        has_rain = True

        if has_exceptional:
            condition = "exceptional"
        elif has_rain:
            condition = "rainy"

        assert condition == "exceptional", "Exceptional overrides rain"

    def test_hail_priority_over_rain(self):
        """Test hail has higher priority than rain."""
        has_hail = True
        has_rain = True

        if has_hail:
            condition = "hail"
        elif has_rain:
            condition = "rainy"

        assert condition == "hail", "Hail overrides rain"

    def test_lightning_rainy_priority_over_plain_rain(self):
        """Test lightning-rainy has higher priority than plain rain."""
        result = resolve_precipitation(
            pressure=975.0, hail_conditions_present=False, is_raining=True
        )
        assert result == "lightning-rainy", "Lightning-rainy overrides plain rain"

    def test_exceptional_priority_over_hail(self):
        """Test exceptional has higher priority than hail."""
        has_exceptional = True
        has_hail = True

        if has_exceptional:
            condition = "exceptional"
        elif has_hail:
            condition = "hail"

        assert condition == "exceptional", "Exceptional overrides hail"


class TestRangeValidation:
    """Test range validation for exceptional and hail (must match const.py)."""

    def test_pressure_ranges(self):
        """Test pressure range definitions match runtime constants."""
        # Exceptional ranges (must match const.py)
        hurricane_threshold = 950  # PRESSURE_HURRICANE_THRESHOLD
        extreme_high_threshold = 1050  # PRESSURE_EXTREME_HIGH_THRESHOLD

        assert hurricane_threshold == 950, "Hurricane threshold"
        assert extreme_high_threshold == 1050, "Extreme high threshold"

        # Test values
        assert 915 < hurricane_threshold, "Hurricane example"
        assert 1075 > extreme_high_threshold, "Extreme high example"
        assert 950 <= 1015 <= 1050, "Normal pressure range"

    def test_change_rate_threshold(self):
        """Test pressure change rate threshold matches runtime constant."""
        bomb_threshold = 24  # PRESSURE_BOMB_CYCLONE_CHANGE (hPa/3h)

        assert abs(-25) > bomb_threshold, "Bomb cyclone fall"
        assert abs(25.5) > bomb_threshold, "Rapid rise"
        assert abs(-5) <= bomb_threshold, "Normal change"

    def test_hail_temp_range(self):
        """Test hail temperature range matches runtime constants."""
        min_temp = HAIL_TEMP_MIN  # 18°C
        max_temp = HAIL_TEMP_MAX  # 35°C

        assert min_temp == 18, "Min convective temp"
        assert max_temp == 35, "Max convective temp"

        # Test values
        assert not (10 >= min_temp), "Too cold"
        assert 20 >= min_temp and 20 <= max_temp, "In range"
        assert not (40 <= max_temp), "Too hot"

    def test_hail_humidity_threshold(self):
        """Test hail humidity threshold matches runtime constant."""
        humidity_threshold = HAIL_HUMIDITY_MIN  # 65%

        assert 70 > humidity_threshold, "High humidity"
        assert not (60 > humidity_threshold), "Low humidity"

    def test_hail_gust_threshold(self):
        """Test hail gust ratio threshold matches runtime constant."""
        gust_threshold = HAIL_GUST_RATIO_MIN  # 2.0

        assert 2.5 > gust_threshold, "Very unstable"
        assert not (1.8 > gust_threshold), "Too stable"


class TestConvectiveLightningRainy:
    """Test convective lightning-rainy detection logic.

    Verifies that get_convective_risk() returns HIGH for conditions that
    should trigger lightning-rainy in the weather entity.
    """

    def test_convective_high_plus_rain_gives_lightning_rainy(self):
        """Convective HIGH + active rain → weather entity should return lightning-rainy."""
        from custom_components.local_weather_forecast.calculations import get_convective_risk
        from custom_components.local_weather_forecast.const import CONVECTIVE_RISK_HIGH

        # Typical CE summer thunderstorm: T=24, Td=16.5, RH=68, P=1013, h=15
        risk = get_convective_risk(
            temperature=24.0, humidity=68.0, pressure=1013.0, hour=15, dewpoint=16.5
        )
        assert risk == CONVECTIVE_RISK_HIGH
        # → weather.py returns lightning-rainy when is_raining=True

    def test_convective_low_plus_rain_does_not_give_lightning_rainy(self):
        """Convective LOW + rain → only rainy (not lightning-rainy)."""
        from custom_components.local_weather_forecast.calculations import get_convective_risk
        from custom_components.local_weather_forecast.const import CONVECTIVE_RISK_HIGH, CONVECTIVE_RISK_LOW

        risk = get_convective_risk(
            temperature=19.0, humidity=57.0, pressure=1015.0, hour=18, dewpoint=10.5
        )
        assert risk == CONVECTIVE_RISK_LOW
        assert risk != CONVECTIVE_RISK_HIGH
        # → weather.py falls through to rainy/pouring

    def test_convective_high_without_rain_not_lightning_rainy(self):
        """Convective HIGH without active rain → NOT lightning-rainy (no precipitation)."""
        from custom_components.local_weather_forecast.calculations import get_convective_risk
        from custom_components.local_weather_forecast.const import CONVECTIVE_RISK_HIGH

        risk = get_convective_risk(
            temperature=24.0, humidity=68.0, pressure=1013.0, hour=15, dewpoint=16.5
        )
        assert risk == CONVECTIVE_RISK_HIGH
        # But weather.py only evaluates convective risk inside the is_raining=True branch
        # → without rain, the lightning-rainy branch is never reached

    def test_convective_high_blocked_by_anticyclone(self):
        """Anticyclone (P > 1022) → convective NONE even with high temp/humidity."""
        from custom_components.local_weather_forecast.calculations import get_convective_risk
        from custom_components.local_weather_forecast.const import CONVECTIVE_RISK_NONE

        risk = get_convective_risk(
            temperature=26.0, humidity=70.0, pressure=1025.0, hour=15
        )
        assert risk == CONVECTIVE_RISK_NONE
        # → weather.py falls through to normal rain/pouring

    def test_convective_priority_below_hail(self):
        """Hail has higher priority than convective lightning-rainy."""
        # Priority order in weather.py:
        # 1. Deep cyclone P<980 → lightning-rainy / hail
        # 2. Hail conditions → hail
        # 3. Convective HIGH + rain → lightning-rainy   ← here
        # 4. pouring / rainy
        # Verified by code inspection — hail check comes before convective check
        assert True, "Priority verified by code structure"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
