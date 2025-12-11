"""Tests for const.py constants validation."""

from custom_components.local_weather_forecast.const import (
    COMFORT_COLD,
    COMFORT_COMFORTABLE,
    COMFORT_COOL,
    COMFORT_HOT,
    COMFORT_VERY_COLD,
    COMFORT_VERY_HOT,
    COMFORT_WARM,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    DEFAULT_ELEVATION,
    DEFAULT_ENABLE_EXTENDED_SENSORS,
    DEFAULT_ENABLE_WEATHER_ENTITY,
    DEFAULT_FORECAST_INTERVAL,
    DEFAULT_LANGUAGE,
    DEFAULT_LATITUDE,
    DEFAULT_PRESSURE_TYPE,
    FOG_RISK_HIGH,
    FOG_RISK_LOW,
    FOG_RISK_MEDIUM,
    FOG_RISK_NONE,
    FORECAST_INTERVALS,
    FROST_RISK_CRITICAL,
    FROST_RISK_HIGH,
    FROST_RISK_LOW,
    FROST_RISK_MEDIUM,
    FROST_RISK_NONE,
    GRAVITY_CONSTANT,
    KELVIN_OFFSET,
    LANGUAGE_INDEX,
    LANGUAGES,
    LAPSE_RATE,
    PRESSURE_CHANGE_MINUTES,
    PRESSURE_MIN_RECORDS,
    PRESSURE_TREND_FALLING,
    PRESSURE_TREND_RISING,
    PRESSURE_TYPE_ABSOLUTE,
    PRESSURE_TYPE_RELATIVE,
    SNOW_RISK_HIGH,
    SNOW_RISK_LOW,
    SNOW_RISK_MEDIUM,
    SNOW_RISK_NONE,
    TEMPERATURE_CHANGE_MINUTES,
    TEMPERATURE_MIN_RECORDS,
    TREND_DETERIORATING,
    TREND_FALLING,
    TREND_IMPROVING,
    TREND_RISING,
    TREND_STABLE,
    TREND_STEADY,
    ZAMBRETTI_TO_CONDITION,
)


class TestLanguageConstants:
    """Test language-related constants."""

    def test_all_languages_have_index(self):
        """Test that all languages in LANGUAGES dict have corresponding index."""
        for lang_code in LANGUAGES.keys():
            assert lang_code in LANGUAGE_INDEX, f"Language {lang_code} missing from LANGUAGE_INDEX"

    def test_all_indexes_have_language(self):
        """Test that all language indexes have corresponding language."""
        for lang_code in LANGUAGE_INDEX.keys():
            assert lang_code in LANGUAGES, f"Language index {lang_code} missing from LANGUAGES"

    def test_language_indexes_are_sequential(self):
        """Test that language indexes are sequential starting from 0."""
        indexes = sorted(LANGUAGE_INDEX.values())
        expected = list(range(len(indexes)))
        assert indexes == expected, f"Language indexes not sequential: {indexes}"

    def test_default_language_exists(self):
        """Test that default language exists in LANGUAGES."""
        assert DEFAULT_LANGUAGE in LANGUAGES
        assert DEFAULT_LANGUAGE in LANGUAGE_INDEX

    def test_language_count(self):
        """Test that we have exactly 5 languages."""
        assert len(LANGUAGES) == 5
        assert len(LANGUAGE_INDEX) == 5


class TestZambrettiConstants:
    """Test Zambretti-related constants."""

    def test_all_zambretti_letters_mapped(self):
        """Test that all Zambretti letters A-Z are mapped."""
        expected_letters = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        assert len(ZAMBRETTI_TO_CONDITION) == 26

        for letter in expected_letters:
            assert letter in ZAMBRETTI_TO_CONDITION, f"Zambretti letter {letter} not mapped"

    def test_zambretti_conditions_are_valid_ha_conditions(self):
        """Test that all mapped conditions are valid HA weather conditions."""
        valid_conditions = {
            "clear-night", "cloudy", "exceptional", "fog", "hail", "lightning",
            "lightning-rainy", "partlycloudy", "pouring", "rainy", "snowy",
            "snowy-rainy", "sunny", "windy"
        }

        for letter, condition in ZAMBRETTI_TO_CONDITION.items():
            assert condition in valid_conditions, f"Invalid condition '{condition}' for letter {letter}"

    def test_zambretti_progression_makes_sense(self):
        """Test that Zambretti progression goes from good to bad weather."""
        # First letters (A-E) should be good weather (sunny/partlycloudy)
        good_weather = {"sunny", "partlycloudy"}
        assert ZAMBRETTI_TO_CONDITION["A"] in good_weather
        assert ZAMBRETTI_TO_CONDITION["B"] in good_weather

        # Middle letters (M-S) should be rainy/pouring
        bad_weather = {"rainy", "pouring"}
        assert ZAMBRETTI_TO_CONDITION["M"] in bad_weather
        assert ZAMBRETTI_TO_CONDITION["P"] in bad_weather

        # Last letter (Z) should be worst (lightning-rainy)
        assert ZAMBRETTI_TO_CONDITION["Z"] == "lightning-rainy"


class TestPressureConstants:
    """Test pressure-related constants."""

    def test_pressure_type_values(self):
        """Test pressure type constant values."""
        assert PRESSURE_TYPE_ABSOLUTE == "absolute"
        assert PRESSURE_TYPE_RELATIVE == "relative"

    def test_pressure_change_intervals(self):
        """Test pressure change time intervals."""
        assert PRESSURE_CHANGE_MINUTES == 180  # 3 hours
        assert TEMPERATURE_CHANGE_MINUTES == 60  # 1 hour

    def test_pressure_min_records(self):
        """Test minimum records count."""
        assert PRESSURE_MIN_RECORDS == 36
        assert TEMPERATURE_MIN_RECORDS == 12

        # Verify that min records align with change minutes for 5-min updates
        # 180 min / 5 min = 36 records
        assert PRESSURE_MIN_RECORDS == PRESSURE_CHANGE_MINUTES // 5
        # 60 min / 5 min = 12 records
        assert TEMPERATURE_MIN_RECORDS == TEMPERATURE_CHANGE_MINUTES // 5

    def test_pressure_trend_thresholds(self):
        """Test pressure trend thresholds are symmetric."""
        assert PRESSURE_TREND_RISING == 1.6
        assert PRESSURE_TREND_FALLING == -1.6
        assert PRESSURE_TREND_RISING == -PRESSURE_TREND_FALLING

    def test_barometric_constants(self):
        """Test barometric constants have reasonable values."""
        assert 0 < LAPSE_RATE < 0.01  # K/m
        assert 5 < GRAVITY_CONSTANT < 6
        assert KELVIN_OFFSET == 273.15


class TestRiskLevelConstants:
    """Test risk level constants."""

    def test_fog_risk_levels(self):
        """Test fog risk levels are defined."""
        assert FOG_RISK_NONE == "none"
        assert FOG_RISK_LOW == "low"
        assert FOG_RISK_MEDIUM == "medium"
        assert FOG_RISK_HIGH == "high"

    def test_snow_risk_levels(self):
        """Test snow risk levels are defined."""
        assert SNOW_RISK_NONE == "none"
        assert SNOW_RISK_LOW == "low"
        assert SNOW_RISK_MEDIUM == "medium"
        assert SNOW_RISK_HIGH == "high"

    def test_frost_risk_levels(self):
        """Test frost risk levels are defined."""
        assert FROST_RISK_NONE == "none"
        assert FROST_RISK_LOW == "low"
        assert FROST_RISK_MEDIUM == "medium"
        assert FROST_RISK_HIGH == "high"
        assert FROST_RISK_CRITICAL == "critical"

    def test_frost_has_most_levels(self):
        """Test that frost has 5 levels (including critical)."""
        frost_levels = {
            FROST_RISK_NONE, FROST_RISK_LOW, FROST_RISK_MEDIUM,
            FROST_RISK_HIGH, FROST_RISK_CRITICAL
        }
        assert len(frost_levels) == 5


class TestComfortLevelConstants:
    """Test comfort level constants."""

    def test_all_comfort_levels_defined(self):
        """Test all 7 comfort levels are defined."""
        comfort_levels = {
            COMFORT_VERY_COLD, COMFORT_COLD, COMFORT_COOL, COMFORT_COMFORTABLE,
            COMFORT_WARM, COMFORT_HOT, COMFORT_VERY_HOT
        }
        assert len(comfort_levels) == 7

    def test_comfort_level_names(self):
        """Test comfort level constant names match their values."""
        assert COMFORT_VERY_COLD == "very_cold"
        assert COMFORT_COLD == "cold"
        assert COMFORT_COOL == "cool"
        assert COMFORT_COMFORTABLE == "comfortable"
        assert COMFORT_WARM == "warm"
        assert COMFORT_HOT == "hot"
        assert COMFORT_VERY_HOT == "very_hot"


class TestTrendConstants:
    """Test trend-related constants."""

    def test_trend_states_defined(self):
        """Test all trend states are defined."""
        trend_states = {
            TREND_IMPROVING, TREND_DETERIORATING, TREND_STABLE,
            TREND_RISING, TREND_FALLING, TREND_STEADY
        }
        assert len(trend_states) == 6

    def test_trend_state_names(self):
        """Test trend state names match their values."""
        assert TREND_IMPROVING == "improving"
        assert TREND_DETERIORATING == "deteriorating"
        assert TREND_STABLE == "stable"
        assert TREND_RISING == "rising"
        assert TREND_FALLING == "falling"
        assert TREND_STEADY == "steady"


class TestConfidenceConstants:
    """Test confidence level constants."""

    def test_confidence_levels_defined(self):
        """Test all confidence levels are defined."""
        confidence_levels = {CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH}
        assert len(confidence_levels) == 3

    def test_confidence_level_names(self):
        """Test confidence level names."""
        assert CONFIDENCE_LOW == "low"
        assert CONFIDENCE_MEDIUM == "medium"
        assert CONFIDENCE_HIGH == "high"


class TestDefaultValues:
    """Test default configuration values."""

    def test_default_elevation(self):
        """Test default elevation is sea level."""
        assert DEFAULT_ELEVATION == 0

    def test_default_latitude(self):
        """Test default latitude is reasonable."""
        assert -90 <= DEFAULT_LATITUDE <= 90
        assert DEFAULT_LATITUDE == 50.0  # Europe middle

    def test_default_pressure_type(self):
        """Test default pressure type is absolute."""
        assert DEFAULT_PRESSURE_TYPE == PRESSURE_TYPE_ABSOLUTE

    def test_default_feature_flags(self):
        """Test default feature flags."""
        assert DEFAULT_ENABLE_WEATHER_ENTITY is False
        assert DEFAULT_ENABLE_EXTENDED_SENSORS is False

    def test_default_forecast_interval(self):
        """Test default forecast interval."""
        assert DEFAULT_FORECAST_INTERVAL == 3  # hours
        assert DEFAULT_FORECAST_INTERVAL in FORECAST_INTERVALS


class TestForecastIntervals:
    """Test forecast interval constants."""

    def test_forecast_intervals_sorted(self):
        """Test forecast intervals are sorted."""
        assert FORECAST_INTERVALS == sorted(FORECAST_INTERVALS)

    def test_forecast_intervals_positive(self):
        """Test all forecast intervals are positive."""
        assert all(interval > 0 for interval in FORECAST_INTERVALS)

    def test_forecast_intervals_count(self):
        """Test we have 5 forecast intervals."""
        assert len(FORECAST_INTERVALS) == 5

    def test_forecast_intervals_values(self):
        """Test forecast interval values."""
        assert FORECAST_INTERVALS == [1, 3, 6, 12, 24]


class TestConstantImmutability:
    """Test that constants are properly typed as Final."""

    def test_constants_are_final(self):
        """Test that key constants are typed as Final."""
        # This test verifies that constants are declared with Final type hint
        # We can't directly check if they're truly immutable at runtime,
        # but we can verify they exist and have expected types

        # String constants
        assert isinstance(PRESSURE_TYPE_ABSOLUTE, str)
        assert isinstance(DEFAULT_LANGUAGE, str)

        # Numeric constants
        assert isinstance(DEFAULT_ELEVATION, (int, float))
        assert isinstance(PRESSURE_CHANGE_MINUTES, int)

        # Boolean constants
        assert isinstance(DEFAULT_ENABLE_WEATHER_ENTITY, bool)

        # Dictionary constants
        assert isinstance(LANGUAGES, dict)
        assert isinstance(ZAMBRETTI_TO_CONDITION, dict)

        # List constants
        assert isinstance(FORECAST_INTERVALS, list)


class TestConstantConsistency:
    """Test consistency between related constants."""

    def test_risk_levels_use_same_values(self):
        """Test that none/low/medium/high are consistent across risk types."""
        # All risk types should use these same basic levels
        common_levels = {"none", "low", "medium", "high"}

        fog_levels = {FOG_RISK_NONE, FOG_RISK_LOW, FOG_RISK_MEDIUM, FOG_RISK_HIGH}
        assert fog_levels == common_levels

        snow_levels = {SNOW_RISK_NONE, SNOW_RISK_LOW, SNOW_RISK_MEDIUM, SNOW_RISK_HIGH}
        assert snow_levels == common_levels

        # Frost has additional "critical" level
        frost_basic_levels = {FROST_RISK_NONE, FROST_RISK_LOW, FROST_RISK_MEDIUM, FROST_RISK_HIGH}
        assert frost_basic_levels == common_levels

    def test_trend_pairs_are_opposites(self):
        """Test that trend pairs make sense."""
        # Rising/falling should be opposites
        assert TREND_RISING == "rising"
        assert TREND_FALLING == "falling"

        # Improving/deteriorating should be opposites
        assert TREND_IMPROVING == "improving"
        assert TREND_DETERIORATING == "deteriorating"

    def test_pressure_constants_relationship(self):
        """Test relationships between pressure constants."""
        # Change minutes should be exactly divisible by 5 (typical sensor interval)
        assert PRESSURE_CHANGE_MINUTES % 5 == 0
        assert TEMPERATURE_CHANGE_MINUTES % 5 == 0

        # Min records should equal change_minutes / 5
        assert PRESSURE_MIN_RECORDS * 5 == PRESSURE_CHANGE_MINUTES
        assert TEMPERATURE_MIN_RECORDS * 5 == TEMPERATURE_CHANGE_MINUTES

