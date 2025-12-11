"""Tests for forecast_data.py multilingual data validation."""

from custom_components.local_weather_forecast.forecast_data import (
    ADJUSTMENT_TEMPLATES,
    ATMOSPHERE_STABILITY,
    COMFORT_LEVELS,
    CONDITIONS,
    FOG_RISK_LEVELS,
    FORECAST_TEXTS,
    PRESSURE_SYSTEMS,
    VISIBILITY_ESTIMATES,
    WIND_TYPES,
    ZAMBRETTI_LETTERS,
)


class TestMultilingualDataStructure:
    """Test that all multilingual data has correct structure."""

    def test_all_tuples_have_5_languages(self):
        """Test that all multilingual tuples have exactly 5 languages (de, en, gr, it, sk)."""
        # CONDITIONS
        assert len(CONDITIONS) == 5
        for condition in CONDITIONS:
            assert len(condition) == 5, f"Condition {condition[1]} has {len(condition)} languages, expected 5"

        # PRESSURE_SYSTEMS
        assert len(PRESSURE_SYSTEMS) == 3
        for system in PRESSURE_SYSTEMS:
            assert len(system) == 5, f"Pressure system {system[1]} has {len(system)} languages"

        # FORECAST_TEXTS
        assert len(FORECAST_TEXTS) == 26  # A-Z
        for idx, text in enumerate(FORECAST_TEXTS):
            assert len(text) == 5, f"Forecast text {idx} ({text[1]}) has {len(text)} languages"

        # WIND_TYPES
        assert len(WIND_TYPES) == 13  # Beaufort 0-12
        for idx, wind_type in enumerate(WIND_TYPES):
            assert len(wind_type) == 5, f"Wind type {idx} ({wind_type[1]}) has {len(wind_type)} languages"

    def test_all_dicts_have_5_languages(self):
        """Test that all multilingual dictionaries have exactly 5 languages per value."""
        # VISIBILITY_ESTIMATES
        for key, values in VISIBILITY_ESTIMATES.items():
            assert len(values) == 5, f"Visibility estimate '{key}' has {len(values)} languages"

        # COMFORT_LEVELS
        for key, values in COMFORT_LEVELS.items():
            assert len(values) == 5, f"Comfort level '{key}' has {len(values)} languages"

        # FOG_RISK_LEVELS
        for key, values in FOG_RISK_LEVELS.items():
            assert len(values) == 5, f"Fog risk level '{key}' has {len(values)} languages"

        # ATMOSPHERE_STABILITY
        for key, values in ATMOSPHERE_STABILITY.items():
            assert len(values) == 5, f"Atmosphere stability '{key}' has {len(values)} languages"

        # ADJUSTMENT_TEMPLATES
        for key, values in ADJUSTMENT_TEMPLATES.items():
            assert len(values) == 5, f"Adjustment template '{key}' has {len(values)} languages"


class TestZambrettiData:
    """Test Zambretti-related data."""

    def test_zambretti_letters_count(self):
        """Test that we have exactly 26 Zambretti letters."""
        assert len(ZAMBRETTI_LETTERS) == 26

    def test_zambretti_letters_are_a_to_z(self):
        """Test that Zambretti letters are A-Z."""
        expected = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        assert ZAMBRETTI_LETTERS == expected

    def test_forecast_texts_match_zambretti_letters(self):
        """Test that we have one forecast text per Zambretti letter."""
        assert len(FORECAST_TEXTS) == len(ZAMBRETTI_LETTERS)

    def test_forecast_texts_have_no_duplicates(self):
        """Test that forecast texts are unique (English version)."""
        english_texts = [text[1] for text in FORECAST_TEXTS]
        assert len(english_texts) == len(set(english_texts)), "Duplicate forecast texts found"


class TestWindData:
    """Test wind-related data."""

    def test_wind_types_beaufort_scale(self):
        """Test that we have wind types for Beaufort scale 0-12."""
        assert len(WIND_TYPES) == 13  # 0-12 inclusive

    def test_wind_types_no_empty_strings(self):
        """Test that no wind type contains empty strings."""
        for idx, wind_type in enumerate(WIND_TYPES):
            for lang_idx, translation in enumerate(wind_type):
                assert translation, f"Wind type {idx} has empty translation at language index {lang_idx}"

    def test_wind_types_logical_progression(self):
        """Test that wind types progress from calm to hurricane."""
        english_types = [wind[1].lower() for wind in WIND_TYPES]

        # First should be calm
        assert "calm" in english_types[0]

        # Last should be hurricane
        assert "hurricane" in english_types[12]


class TestConditionsData:
    """Test weather conditions data."""

    def test_conditions_count(self):
        """Test that we have exactly 5 conditions."""
        assert len(CONDITIONS) == 5

    def test_conditions_are_unique(self):
        """Test that all conditions are unique (English version)."""
        english_conditions = [cond[1] for cond in CONDITIONS]
        assert len(english_conditions) == len(set(english_conditions))

    def test_conditions_no_empty_strings(self):
        """Test that no condition contains empty strings."""
        for idx, condition in enumerate(CONDITIONS):
            for lang_idx, translation in enumerate(condition):
                assert translation, f"Condition {idx} has empty translation at language index {lang_idx}"


class TestPressureSystemsData:
    """Test pressure systems data."""

    def test_pressure_systems_count(self):
        """Test that we have exactly 3 pressure systems."""
        assert len(PRESSURE_SYSTEMS) == 3

    def test_pressure_systems_order(self):
        """Test that pressure systems are in order: Low, Normal, High."""
        english_systems = [system[1].lower() for system in PRESSURE_SYSTEMS]
        assert "low" in english_systems[0]
        assert "normal" in english_systems[1]
        assert "high" in english_systems[2]


class TestComfortLevels:
    """Test comfort levels data."""

    def test_comfort_levels_count(self):
        """Test that we have exactly 7 comfort levels."""
        assert len(COMFORT_LEVELS) == 7

    def test_comfort_levels_keys(self):
        """Test that all expected comfort level keys exist."""
        expected_keys = {"very_cold", "cold", "cool", "comfortable", "warm", "hot", "very_hot"}
        assert set(COMFORT_LEVELS.keys()) == expected_keys

    def test_comfort_levels_progression(self):
        """Test that comfort levels have logical progression."""
        english_levels = {key: COMFORT_LEVELS[key][1].lower() for key in COMFORT_LEVELS}

        assert "very" in english_levels["very_cold"] and "cold" in english_levels["very_cold"]
        assert "cold" in english_levels["cold"]
        assert "comfortable" in english_levels["comfortable"]
        assert "hot" in english_levels["hot"]
        assert "very" in english_levels["very_hot"] and "hot" in english_levels["very_hot"]


class TestFogRiskLevels:
    """Test fog risk levels data."""

    def test_fog_risk_levels_count(self):
        """Test that we have exactly 5 fog risk levels."""
        assert len(FOG_RISK_LEVELS) == 5

    def test_fog_risk_levels_keys(self):
        """Test that all expected fog risk level keys exist."""
        expected_keys = {"none", "low", "medium", "high", "critical"}
        assert set(FOG_RISK_LEVELS.keys()) == expected_keys

    def test_fog_risk_levels_progression(self):
        """Test that fog risk levels have logical progression."""
        english_levels = {key: FOG_RISK_LEVELS[key][1].lower() for key in FOG_RISK_LEVELS}

        assert "no" in english_levels["none"]
        assert "low" in english_levels["low"]
        assert "medium" in english_levels["medium"]
        assert "high" in english_levels["high"]
        assert "critical" in english_levels["critical"]


class TestAtmosphereStability:
    """Test atmosphere stability data."""

    def test_atmosphere_stability_count(self):
        """Test that we have exactly 5 stability levels."""
        assert len(ATMOSPHERE_STABILITY) == 5

    def test_atmosphere_stability_keys(self):
        """Test that all expected stability level keys exist."""
        expected_keys = {"stable", "moderate", "unstable", "very_unstable", "unknown"}
        assert set(ATMOSPHERE_STABILITY.keys()) == expected_keys

    def test_atmosphere_stability_progression(self):
        """Test that stability levels have logical progression."""
        english_levels = {key: ATMOSPHERE_STABILITY[key][1].lower() for key in ATMOSPHERE_STABILITY}

        assert "stable" in english_levels["stable"]
        assert "moderate" in english_levels["moderate"]
        assert "unstable" in english_levels["unstable"]
        assert "very" in english_levels["very_unstable"] and "unstable" in english_levels["very_unstable"]


class TestVisibilityEstimates:
    """Test visibility estimates data."""

    def test_visibility_estimates_count(self):
        """Test that we have exactly 4 visibility levels."""
        assert len(VISIBILITY_ESTIMATES) == 4

    def test_visibility_estimates_keys(self):
        """Test that all expected visibility level keys exist."""
        expected_keys = {"high", "medium", "low", "none"}
        assert set(VISIBILITY_ESTIMATES.keys()) == expected_keys

    def test_visibility_estimates_have_distances(self):
        """Test that visibility estimates include distance indicators."""
        for key, values in VISIBILITY_ESTIMATES.items():
            english_text = values[1]
            # Each should mention a distance range or comparison
            assert "km" in english_text or "visibility" in english_text.lower()


class TestAdjustmentTemplates:
    """Test adjustment templates data."""

    def test_adjustment_templates_count(self):
        """Test that we have adjustment templates."""
        assert len(ADJUSTMENT_TEMPLATES) >= 7  # At least the documented ones

    def test_adjustment_templates_have_placeholders(self):
        """Test that adjustment templates use {value} placeholder."""
        for key, values in ADJUSTMENT_TEMPLATES.items():
            for lang_idx, translation in enumerate(values):
                assert "{value}" in translation, \
                    f"Adjustment template '{key}' language {lang_idx} missing {{value}} placeholder"

    def test_adjustment_templates_keys(self):
        """Test that expected adjustment template keys exist."""
        expected_keys = {
            "high_humidity",
            "low_humidity",
            "critical_fog_risk",
            "high_fog_risk",
            "medium_fog_risk",
            "very_unstable",
            "unstable",
        }
        assert expected_keys.issubset(set(ADJUSTMENT_TEMPLATES.keys()))


class TestLanguageConsistency:
    """Test consistency across all language data."""

    def test_no_mixed_language_contamination(self):
        """Test that each language index doesn't contain text from other languages."""
        # This is a heuristic test - check for common words in wrong positions

        # German (index 0) should not have English words in German position
        for text in FORECAST_TEXTS:
            german_text = text[0].lower()
            # German shouldn't contain obvious English-only words
            # (This is simplified - in reality German can have some English loanwords)
            assert not (german_text.startswith("settled") or german_text.startswith("fine"))

        # English (index 1) should be in English
        for text in FORECAST_TEXTS:
            english_text = text[1]
            # Should have Latin characters
            assert english_text.isascii()

    def test_all_languages_non_empty(self):
        """Test that no translation is an empty string."""
        all_data = [
            *CONDITIONS,
            *PRESSURE_SYSTEMS,
            *FORECAST_TEXTS,
            *WIND_TYPES,
            *[v for v in VISIBILITY_ESTIMATES.values()],
            *[v for v in COMFORT_LEVELS.values()],
            *[v for v in FOG_RISK_LEVELS.values()],
            *[v for v in ATMOSPHERE_STABILITY.values()],
            *[v for v in ADJUSTMENT_TEMPLATES.values()],
        ]

        for item in all_data:
            for lang_idx, translation in enumerate(item):
                assert translation.strip(), f"Empty translation found at language index {lang_idx}"

    def test_language_order_documented(self):
        """Test that language order is: German, English, Greek, Italian, Slovak."""
        # This is documented in comments, verify with a sample
        sample_text = FORECAST_TEXTS[0]  # "Settled Fine"

        # Index 0: German (contains umlaut or German-specific words)
        # Index 1: English (should be "Settled Fine" or similar)
        assert "Settled" in sample_text[1] or "Fine" in sample_text[1]

        # Index 2: Greek (should contain Greek characters)
        assert any(ord(char) >= 0x0370 and ord(char) <= 0x03FF for char in sample_text[2])

        # Index 3: Italian
        # Index 4: Slovak


class TestDataIntegrity:
    """Test overall data integrity."""

    def test_forecast_texts_cover_all_weather_scenarios(self):
        """Test that forecast texts cover a range of weather scenarios."""
        english_forecasts = [text[1].lower() for text in FORECAST_TEXTS]
        combined = " ".join(english_forecasts)

        # Should mention various conditions
        assert any(word in combined for word in ["fine", "sunny", "clear"])
        assert any(word in combined for word in ["rain", "rainy", "showery"])
        assert any(word in combined for word in ["unsettled", "changeable"])
        assert any(word in combined for word in ["storm", "stormy"])

    def test_no_obvious_typos_in_english(self):
        """Test that English translations don't have obvious typos."""
        english_forecasts = [text[1] for text in FORECAST_TEXTS]

        # All should start with capital letter
        for forecast in english_forecasts:
            assert forecast[0].isupper(), f"Forecast '{forecast}' doesn't start with capital"

        # Check for double spaces
        for forecast in english_forecasts:
            assert "  " not in forecast, f"Forecast '{forecast}' contains double space"

    def test_special_characters_escaped_properly(self):
        """Test that special characters in templates are handled correctly."""
        for key, values in ADJUSTMENT_TEMPLATES.items():
            for translation in values:
                # {value} should not be escaped
                assert "{value}" in translation
                # Should not have broken placeholders
                assert "{ value }" not in translation
                assert "{value }" not in translation
                assert "{ value}" not in translation

