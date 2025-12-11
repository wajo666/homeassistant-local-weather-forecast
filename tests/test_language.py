"""Tests for language.py module."""
from types import SimpleNamespace

from custom_components.local_weather_forecast.language import (
    get_language_index,
    get_wind_type,
    get_visibility_estimate,
    get_comfort_level_text,
    get_fog_risk_text,
    get_atmosphere_stability_text,
    get_adjustment_text,
    get_snow_risk_text,
    get_frost_risk_text,
    LANGUAGE_MAP,
    DEFAULT_LANGUAGE_INDEX,
)


class MockConfig:
    """Mock Home Assistant config."""

    def __init__(self, language: str = "en", temp_unit: str = "°C"):
        self.language = language
        self.units = SimpleNamespace(temperature_unit=temp_unit)


class MockHass:
    """Mock Home Assistant instance."""

    def __init__(self, language: str = "en", temp_unit: str = "°C"):
        self.config = MockConfig(language, temp_unit)


# Test get_language_index
def test_get_language_index_english():
    """Test language detection for English."""
    hass = MockHass("en")
    assert get_language_index(hass) == 1


def test_get_language_index_german():
    """Test language detection for German."""
    hass = MockHass("de")
    assert get_language_index(hass) == 0


def test_get_language_index_greek():
    """Test language detection for Greek."""
    hass = MockHass("el")
    assert get_language_index(hass) == 2


def test_get_language_index_italian():
    """Test language detection for Italian."""
    hass = MockHass("it")
    assert get_language_index(hass) == 3


def test_get_language_index_slovak():
    """Test language detection for Slovak."""
    hass = MockHass("sk")
    assert get_language_index(hass) == 4


def test_get_language_index_unknown():
    """Test language detection for unknown language falls back to English."""
    hass = MockHass("fr")
    assert get_language_index(hass) == DEFAULT_LANGUAGE_INDEX


def test_get_language_index_no_hass():
    """Test language detection with no hass instance."""
    assert get_language_index(None) == DEFAULT_LANGUAGE_INDEX


# Test get_wind_type
def test_get_wind_type_calm():
    """Test wind type for calm conditions."""
    hass = MockHass("en")
    result = get_wind_type(hass, 0)
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_wind_type_breeze():
    """Test wind type for breeze conditions."""
    hass = MockHass("en")
    result = get_wind_type(hass, 3)
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_wind_type_storm():
    """Test wind type for storm conditions."""
    hass = MockHass("en")
    result = get_wind_type(hass, 10)
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_wind_type_invalid():
    """Test wind type for invalid beaufort number."""
    hass = MockHass("en")
    result = get_wind_type(hass, 99)
    assert result == "Unknown"


def test_get_wind_type_slovak():
    """Test wind type returns Slovak text."""
    hass = MockHass("sk")
    result = get_wind_type(hass, 2)
    assert isinstance(result, str)
    assert len(result) > 0


# Test get_visibility_estimate
def test_get_visibility_estimate_high():
    """Test visibility estimate for high fog risk."""
    hass = MockHass("en")
    result = get_visibility_estimate(hass, "high")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_visibility_estimate_none():
    """Test visibility estimate for no fog."""
    hass = MockHass("en")
    result = get_visibility_estimate(hass, "none")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_visibility_estimate_invalid():
    """Test visibility estimate for invalid fog risk."""
    hass = MockHass("en")
    result = get_visibility_estimate(hass, "invalid")
    assert isinstance(result, str)
    assert len(result) > 0


# Test get_comfort_level_text
def test_get_comfort_level_text_comfortable():
    """Test comfort level for comfortable conditions."""
    hass = MockHass("en")
    result = get_comfort_level_text(hass, "comfortable")
    assert result == "Comfortable"


def test_get_comfort_level_text_cold():
    """Test comfort level for cold conditions."""
    hass = MockHass("en")
    result = get_comfort_level_text(hass, "cold")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_comfort_level_text_hot():
    """Test comfort level for hot conditions."""
    hass = MockHass("en")
    result = get_comfort_level_text(hass, "hot")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_comfort_level_text_invalid():
    """Test comfort level for invalid key."""
    hass = MockHass("en")
    result = get_comfort_level_text(hass, "invalid")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_comfort_level_text_slovak():
    """Test comfort level returns Slovak text."""
    hass = MockHass("sk")
    result = get_comfort_level_text(hass, "comfortable")
    assert result == "Príjemne"


# Test get_fog_risk_text
def test_get_fog_risk_text_critical():
    """Test fog risk text for critical fog."""
    hass = MockHass("en")
    result = get_fog_risk_text(hass, "critical")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_fog_risk_text_none():
    """Test fog risk text for no fog."""
    hass = MockHass("en")
    result = get_fog_risk_text(hass, "none")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_fog_risk_text_invalid():
    """Test fog risk text for invalid risk level."""
    hass = MockHass("en")
    result = get_fog_risk_text(hass, "invalid")
    assert isinstance(result, str)
    assert len(result) > 0


# Test get_atmosphere_stability_text
def test_get_atmosphere_stability_text_stable():
    """Test atmosphere stability text for stable conditions."""
    hass = MockHass("en")
    result = get_atmosphere_stability_text(hass, "stable")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_atmosphere_stability_text_very_unstable():
    """Test atmosphere stability text for very unstable conditions."""
    hass = MockHass("en")
    result = get_atmosphere_stability_text(hass, "very_unstable")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_atmosphere_stability_text_invalid():
    """Test atmosphere stability text for invalid stability level."""
    hass = MockHass("en")
    result = get_atmosphere_stability_text(hass, "invalid")
    assert isinstance(result, str)
    assert len(result) > 0


# Test get_adjustment_text
def test_get_adjustment_text_high_humidity():
    """Test adjustment text for high humidity."""
    hass = MockHass("en")
    result = get_adjustment_text(hass, "high_humidity", "95.5")
    assert isinstance(result, str)
    assert "95.5" in result


def test_get_adjustment_text_critical_fog_celsius():
    """Test adjustment text for critical fog in Celsius."""
    hass = MockHass("en", "°C")
    result = get_adjustment_text(hass, "critical_fog_risk", "0.5")
    assert isinstance(result, str)
    assert "0.5" in result


def test_get_adjustment_text_critical_fog_fahrenheit():
    """Test adjustment text for critical fog in Fahrenheit."""
    hass = MockHass("en", "°F")
    result = get_adjustment_text(hass, "critical_fog_risk", "0.5")
    assert isinstance(result, str)
    # 0.5°C spread = 0.9°F spread
    assert "0.9" in result or "°F" in result


def test_get_adjustment_text_critical_fog_kelvin():
    """Test adjustment text for critical fog in Kelvin."""
    hass = MockHass("en", "K")
    result = get_adjustment_text(hass, "critical_fog_risk", "0.5")
    assert isinstance(result, str)
    assert "0.5" in result


def test_get_adjustment_text_gust_ratio():
    """Test adjustment text for gust ratio (no conversion)."""
    hass = MockHass("en")
    result = get_adjustment_text(hass, "high_gust_ratio", "2.5")
    assert isinstance(result, str)
    assert "2.5" in result


def test_get_adjustment_text_invalid_key():
    """Test adjustment text for invalid key."""
    hass = MockHass("en")
    result = get_adjustment_text(hass, "invalid_key", "100")
    assert isinstance(result, str)
    assert "invalid_key" in result


def test_get_adjustment_text_non_numeric():
    """Test adjustment text for non-numeric value."""
    hass = MockHass("en")
    result = get_adjustment_text(hass, "high_humidity", "N/A")
    assert isinstance(result, str)
    assert "N/A" in result


# Test get_snow_risk_text
def test_get_snow_risk_text_none():
    """Test snow risk text for no snow."""
    hass = MockHass("en")
    result = get_snow_risk_text(hass, "none")
    assert result == "No snow"


def test_get_snow_risk_text_high():
    """Test snow risk text for high snow risk."""
    hass = MockHass("en")
    result = get_snow_risk_text(hass, "high")
    assert result == "High snow risk"


def test_get_snow_risk_text_invalid():
    """Test snow risk text for invalid risk level."""
    hass = MockHass("en")
    result = get_snow_risk_text(hass, "invalid")
    assert result == "No snow"


def test_get_snow_risk_text_slovak():
    """Test snow risk text returns Slovak text."""
    hass = MockHass("sk")
    result = get_snow_risk_text(hass, "high")
    assert result == "Vysoké riziko snehu"


# Test get_frost_risk_text
def test_get_frost_risk_text_none():
    """Test frost risk text for no frost."""
    hass = MockHass("en")
    result = get_frost_risk_text(hass, "none")
    assert result == "No frost"


def test_get_frost_risk_text_critical():
    """Test frost risk text for critical frost (black ice)."""
    hass = MockHass("en")
    result = get_frost_risk_text(hass, "critical")
    assert result == "CRITICAL: Black ice!"


def test_get_frost_risk_text_high():
    """Test frost risk text for high frost risk."""
    hass = MockHass("en")
    result = get_frost_risk_text(hass, "high")
    assert result == "High frost risk"


def test_get_frost_risk_text_invalid():
    """Test frost risk text for invalid risk level."""
    hass = MockHass("en")
    result = get_frost_risk_text(hass, "invalid")
    assert result == "No frost"


def test_get_frost_risk_text_slovak():
    """Test frost risk text returns Slovak text."""
    hass = MockHass("sk")
    result = get_frost_risk_text(hass, "critical")
    assert result == "KRITICKÉ: Poľadovica!"


# Integration tests
def test_all_languages_work():
    """Test that all supported languages return valid strings."""
    languages = ["de", "en", "el", "it", "sk"]

    for lang in languages:
        hass = MockHass(lang)

        # Test each function
        assert len(get_wind_type(hass, 5)) > 0
        assert len(get_visibility_estimate(hass, "high")) > 0
        assert len(get_comfort_level_text(hass, "comfortable")) > 0
        assert len(get_fog_risk_text(hass, "critical")) > 0
        assert len(get_atmosphere_stability_text(hass, "stable")) > 0
        assert len(get_adjustment_text(hass, "high_humidity", "95")) > 0
        assert len(get_snow_risk_text(hass, "high")) > 0
        assert len(get_frost_risk_text(hass, "critical")) > 0


def test_temperature_unit_conversion():
    """Test temperature unit conversions work correctly."""
    # Celsius (no conversion)
    hass_c = MockHass("en", "°C")
    result_c = get_adjustment_text(hass_c, "critical_fog_risk", "1.0")
    assert "1.0" in result_c

    # Fahrenheit (scale by 1.8)
    hass_f = MockHass("en", "°F")
    result_f = get_adjustment_text(hass_f, "critical_fog_risk", "1.0")
    assert "1.8" in result_f or "°F" in result_f

    # Kelvin (same as Celsius)
    hass_k = MockHass("en", "K")
    result_k = get_adjustment_text(hass_k, "critical_fog_risk", "1.0")
    assert "1.0" in result_k


def test_language_map_complete():
    """Test that LANGUAGE_MAP contains all expected languages."""
    assert "de" in LANGUAGE_MAP
    assert "en" in LANGUAGE_MAP
    assert "el" in LANGUAGE_MAP
    assert "gr" in LANGUAGE_MAP  # Alternative for Greek
    assert "it" in LANGUAGE_MAP
    assert "sk" in LANGUAGE_MAP

    # Test that all values are valid indices
    for lang_code, index in LANGUAGE_MAP.items():
        assert 0 <= index <= 4

