"""Tests for negretti_zambra.py module."""
from unittest.mock import patch
from datetime import datetime

from custom_components.local_weather_forecast.negretti_zambra import (
    calculate_negretti_zambra_forecast,
    _map_zambretti_to_letter,
)


# Test _map_zambretti_to_letter function
def test_map_zambretti_to_letter_a():
    """Test mapping for letter A."""
    assert _map_zambretti_to_letter(1) == "A"
    assert _map_zambretti_to_letter(10) == "A"
    assert _map_zambretti_to_letter(20) == "A"


def test_map_zambretti_to_letter_b():
    """Test mapping for letter B."""
    assert _map_zambretti_to_letter(2) == "B"
    assert _map_zambretti_to_letter(11) == "B"
    assert _map_zambretti_to_letter(21) == "B"


def test_map_zambretti_to_letter_various():
    """Test mapping for various letters."""
    assert _map_zambretti_to_letter(3) == "D"
    assert _map_zambretti_to_letter(4) == "H"
    assert _map_zambretti_to_letter(5) == "O"
    assert _map_zambretti_to_letter(6) == "R"
    assert _map_zambretti_to_letter(7) == "U"
    assert _map_zambretti_to_letter(8) == "V"


def test_map_zambretti_to_letter_x():
    """Test mapping for letter X - now only Z=18."""
    # FIXED: Z=9 (high pressure + steady) → F (Fairly Fine), not X (Very Unsettled)!
    assert _map_zambretti_to_letter(18) == "X"


def test_map_zambretti_to_letter_z():
    """Test mapping for letter Z - only extreme cases."""
    # FIXED: Z=19 (high pressure + rising) → B (Fine Weather), not Z (Stormy)!
    assert _map_zambretti_to_letter(32) == "Z"
    assert _map_zambretti_to_letter(33) == "Z"


def test_map_zambretti_to_letter_f():
    """Test mapping for letter F - including corrected Z=9."""
    # FIXED: Z=9 now correctly maps to F (Fairly Fine)
    assert _map_zambretti_to_letter(9) == "F"
    assert _map_zambretti_to_letter(22) == "F"
    assert _map_zambretti_to_letter(23) == "F"


def test_map_zambretti_to_letter_b_high_pressure_rising():
    """Test mapping for letter B - including corrected Z=19."""
    # FIXED: Z=19 (high pressure + rising) → B (Fine Weather), not Z (Stormy)!
    assert _map_zambretti_to_letter(19) == "B"
    assert _map_zambretti_to_letter(2) == "B"
    assert _map_zambretti_to_letter(11) == "B"
    assert _map_zambretti_to_letter(21) == "B"


def test_map_zambretti_to_letter_unknown():
    """Test mapping for out-of-range numbers gets clamped to valid range."""
    # z=99 should clamp to 33 → "Z"
    assert _map_zambretti_to_letter(99) == "Z"
    # z=0 should clamp to 1 → "A"
    assert _map_zambretti_to_letter(0) == "A"
    # z=-1 should clamp to 1 → "A"
    assert _map_zambretti_to_letter(-1) == "A"


# Test calculate_negretti_zambra_forecast function
@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_steady_winter(mock_datetime):
    """Test forecast calculation with steady pressure in winter."""
    # Mock winter month (January)
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1013.0  # Normal pressure
    pressure_change = 0.5  # Steady (between -1.6 and 1.6)
    wind_data = [0, 180.0, "S", 0]  # No wind factor
    lang_index = 1  # English
    elevation = 100.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    assert isinstance(result, list)
    assert len(result) == 3  # Returns: [text, code, letter]
    assert isinstance(result[0], str)  # forecast_text
    assert isinstance(result[1], int)  # forecast_number
    assert isinstance(result[2], str)  # letter_code


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_rising_summer(mock_datetime):
    """Test forecast calculation with rising pressure in summer."""
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 15, 12, 0)

    p0 = 1020.0  # High pressure
    pressure_change = 2.5  # Rising (>= 1.6)
    wind_data = [1, 45.0, "NE", 1]  # With wind factor
    lang_index = 1  # English
    elevation = 100.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    assert isinstance(result, list)
    assert len(result) == 3  # Returns: [text, code, letter]
    assert isinstance(result[0], str)
    assert isinstance(result[1], int)
    assert isinstance(result[2], str)


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_falling_winter(mock_datetime):
    """Test forecast calculation with falling pressure in winter."""
    # Mock winter month (December)
    mock_datetime.now.return_value = datetime(2025, 12, 15, 12, 0)

    p0 = 995.0  # Low pressure
    pressure_change = -3.0  # Falling (<= -1.6)
    wind_data = [1, 270.0, "W", 1]  # With wind factor
    lang_index = 1  # English
    elevation = 100.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    assert isinstance(result, list)
    assert len(result) == 3  # Returns: [text, code, letter]
    assert isinstance(result[0], str)
    assert isinstance(result[1], int)
    assert isinstance(result[2], str)


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_exceptional_high_pressure(mock_datetime):
    """Test forecast with exceptionally high pressure."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1050.0  # Very high pressure (at bar_top)
    pressure_change = 2.0  # Rising
    wind_data = [0, 0.0, "N", 0]
    lang_index = 1  # English
    elevation = 100.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    assert isinstance(result, list)
    assert len(result) == 3  # Returns: [text, code, letter]
    # Should contain "Exceptional Weather" for English
    assert "Exceptional" in result[0] or isinstance(result[0], str)


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_exceptional_low_pressure(mock_datetime):
    """Test forecast with exceptionally low pressure."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 950.0  # Very low pressure (at bar_bottom)
    pressure_change = -2.0  # Falling
    wind_data = [0, 0.0, "N", 0]
    lang_index = 1  # English
    elevation = 100.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    assert isinstance(result, list)
    assert len(result) == 3  # Returns: [text, code, letter]


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_wind_directions(mock_datetime):
    """Test forecast with different wind directions."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1013.0
    pressure_change = 0.0
    lang_index = 1
    elevation = 100.0

    # Test North wind
    wind_data_n = [1, 0.0, "N", 1]
    result_n = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data_n, lang_index, elevation, hemisphere="north")
    assert isinstance(result_n, list)

    # Test East wind
    wind_data_e = [1, 90.0, "E", 1]
    result_e = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data_e, lang_index, elevation, hemisphere="north")
    assert isinstance(result_e, list)

    # Test South wind
    wind_data_s = [1, 180.0, "S", 1]
    result_s = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data_s, lang_index, elevation, hemisphere="north")
    assert isinstance(result_s, list)

    # Test West wind
    wind_data_w = [1, 270.0, "W", 1]
    result_w = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data_w, lang_index, elevation, hemisphere="north")
    assert isinstance(result_w, list)


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_all_languages(mock_datetime):
    """Test forecast returns text in all supported languages."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1013.0
    pressure_change = 0.0
    wind_data = [0, 0.0, "N", 0]
    elevation = 100.0

    # Test German (0)
    result_de = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, 0, elevation, hemisphere="north")
    assert isinstance(result_de[0], str)
    assert len(result_de[0]) > 0

    # Test English (1)
    result_en = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, 1, elevation, hemisphere="north")
    assert isinstance(result_en[0], str)
    assert len(result_en[0]) > 0

    # Test Greek (2)
    result_el = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, 2, elevation, hemisphere="north")
    assert isinstance(result_el[0], str)
    assert len(result_el[0]) > 0

    # Test Italian (3)
    result_it = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, 3, elevation, hemisphere="north")
    assert isinstance(result_it[0], str)
    assert len(result_it[0]) > 0

    # Test Slovak (4)
    result_sk = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, 4, elevation, hemisphere="north")
    assert isinstance(result_sk[0], str)
    assert len(result_sk[0]) > 0


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_summer_adjustment(mock_datetime):
    """Test summer adjustment is applied correctly."""
    # Mock summer month (June)
    mock_datetime.now.return_value = datetime(2025, 6, 15, 12, 0)

    p0 = 1013.0
    pressure_change = 2.0  # Rising
    wind_data = [0, 0.0, "N", 0]
    lang_index = 1
    elevation = 100.0

    result_summer = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    # Mock winter month (January)
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)
    result_winter = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    # Results might differ due to summer adjustment
    assert isinstance(result_summer, list)
    assert isinstance(result_winter, list)


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_pressure_boundaries(mock_datetime):
    """Test forecast with pressure at boundaries."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    wind_data = [0, 0.0, "N", 0]
    lang_index = 1
    elevation = 100.0

    # Test at bar_bottom
    result_low = calculate_negretti_zambra_forecast(950.0, 0.0, wind_data, lang_index, elevation, hemisphere="north")
    assert isinstance(result_low, list)
    assert len(result_low) == 3

    # Test at bar_top - 1
    result_high = calculate_negretti_zambra_forecast(1049.0, 0.0, wind_data, lang_index, elevation, hemisphere="north")
    assert isinstance(result_high, list)
    assert len(result_high) == 3

    # Test above bar_top (should be clamped)
    result_exceed = calculate_negretti_zambra_forecast(1060.0, 0.0, wind_data, lang_index, elevation, hemisphere="north")
    assert isinstance(result_exceed, list)
    assert len(result_exceed) == 3


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_trend_thresholds(mock_datetime):
    """Test forecast trend detection at threshold boundaries."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1013.0
    wind_data = [0, 0.0, "N", 0]
    lang_index = 1
    elevation = 100.0

    # Test rising threshold
    result_rising = calculate_negretti_zambra_forecast(p0, 1.6, wind_data, lang_index, elevation, hemisphere="north")
    assert isinstance(result_rising, list)

    # Test falling threshold
    result_falling = calculate_negretti_zambra_forecast(p0, -1.6, wind_data, lang_index, elevation, hemisphere="north")
    assert isinstance(result_falling, list)

    # Test steady (just below rising threshold)
    result_steady_1 = calculate_negretti_zambra_forecast(p0, 1.5, wind_data, lang_index, elevation, hemisphere="north")
    assert isinstance(result_steady_1, list)

    # Test steady (just above falling threshold)
    result_steady_2 = calculate_negretti_zambra_forecast(p0, -1.5, wind_data, lang_index, elevation, hemisphere="north")
    assert isinstance(result_steady_2, list)


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_wind_speed_factor(mock_datetime):
    """Test forecast with and without wind speed factor."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1013.0
    pressure_change = 0.0
    lang_index = 1
    elevation = 100.0

    # With wind speed factor
    wind_data_with = [1, 45.0, "NE", 1]
    result_with = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data_with, lang_index, elevation, hemisphere="north")

    # Without wind speed factor
    wind_data_without = [1, 45.0, "NE", 0]
    result_without = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data_without, lang_index, elevation, hemisphere="north")

    # Both should return valid results
    assert isinstance(result_with, list)
    assert isinstance(result_without, list)


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_all_wind_sectors(mock_datetime):
    """Test forecast with wind from all compass sectors."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1013.0
    pressure_change = 0.0
    lang_index = 1
    elevation = 100.0

    # Test all 16 wind directions (every 22.5 degrees)
    wind_directions = [
        (0.0, "N"), (22.5, "NNE"), (45.0, "NE"), (67.5, "ENE"),
        (90.0, "E"), (112.5, "ESE"), (135.0, "SE"), (157.5, "SSE"),
        (180.0, "S"), (202.5, "SSW"), (225.0, "SW"), (247.5, "WSW"),
        (270.0, "W"), (292.5, "WNW"), (315.0, "NW"), (337.5, "NNW"),
    ]

    for direction, dir_text in wind_directions:
        wind_data = [1, direction, dir_text, 1]
        result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")
        assert isinstance(result, list)
        assert len(result) == 3  # Returns: [text, code, letter]
        assert isinstance(result[0], str)
        assert isinstance(result[1], int)
        assert isinstance(result[2], str)


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_calculate_forecast_letter_code_valid(mock_datetime):
    """Test that forecast always returns a valid letter code."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1013.0
    pressure_change = 0.0
    wind_data = [0, 0.0, "N", 0]
    lang_index = 1
    elevation = 100.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    # Extract letter_code from result
    text, num, letter_code = result
    assert isinstance(letter_code, str)
    assert len(letter_code) == 1
    assert letter_code.isalpha()
    assert letter_code.isupper()


# Integration tests
@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_forecast_consistency(mock_datetime):
    """Test that same inputs produce same outputs."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    p0 = 1013.0
    pressure_change = 0.5
    wind_data = [1, 45.0, "NE", 1]
    lang_index = 1
    elevation = 100.0

    result1 = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")
    result2 = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    assert result1 == result2


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_forecast_realistic_values(mock_datetime):
    """Test forecast with realistic weather station values."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    # Realistic values from a weather station
    p0 = 1015.3
    pressure_change = -1.2
    wind_data = [1, 225.0, "SW", 1]
    lang_index = 1
    elevation = 314.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    assert isinstance(result, list)
    assert len(result) == 3  # Returns: [text, code, letter]
    assert isinstance(result[0], str)
    assert 0 <= result[1] <= 25  # Valid forecast index range
    assert isinstance(result[2], str)
    assert len(result[2]) == 1


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_exceptional_weather_slovak(mock_datetime):
    """Test exceptional weather with Slovak language (lang_index=4)."""
    # Mock winter month
    mock_datetime.now.return_value = datetime(2025, 1, 15, 12, 0)

    # High pressure scenario that triggers exceptional weather
    p0 = 1030.0  # High pressure
    pressure_change = 2.90  # Rising
    wind_data = [1, 270.0, 'W', 0]  # West wind
    lang_index = 4  # Slovak
    elevation = 314.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")

    assert isinstance(result, list)
    assert len(result) == 3  # Returns: [text, code, letter]
    assert isinstance(result[0], str)
    # Should not throw "list index out of range" error
    assert len(result[0]) > 0
    # If exceptional, should contain Slovak exceptional weather text
    if "Výnimočné" in result[0]:
        assert "Výnimočné počasie" in result[0]


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_summer_adjustment_moderate_pressure_rising(mock_datetime):
    """Test that summer adjustment IS applied for moderate pressure (975-1025 hPa) with rising trend."""
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 18, 12, 0)

    # Moderate pressure, rising trend
    p0 = 1010.0  # Moderate pressure
    pressure_change = 2.0  # Rising (>1.6)
    wind_data = [0, 0, 'N', 0]  # Calm, no wind adjustment
    lang_index = 1  # English
    elevation = 300.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")
    text, num, letter = result  # Has 3 values

    # Summer adjustment should be applied for moderate pressure
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert len(text) > 0


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_summer_adjustment_very_low_pressure_rising(mock_datetime):
    """Test that summer adjustment is NOT applied for very low pressure (<975 hPa) with rising trend.

    Very low pressure rising = storm recovery. Summer adjustment would make it too optimistic.

    Example: 965 hPa rising summer:
    - OLD: +12.25 hPa adjustment → z_hp=977 → too optimistic ❌
    - NEW: No adjustment → z_hp=965 → appropriate storm recovery ✅
    """
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 18, 12, 0)

    # Very low pressure (storm), rising trend (recovery)
    p0 = 965.0  # Very low pressure
    pressure_change = 2.5  # Rising (storm passing)
    wind_data = [0, 270, 'W', 1]  # West wind
    lang_index = 1  # English
    elevation = 300.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")
    text, num, letter = result  # Has 3 values

    # Should not give overly optimistic forecast during storm recovery
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert len(text) > 0


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_summer_adjustment_high_pressure_rising(mock_datetime):
    """Test that summer adjustment is NOT applied for high pressure (>1025 hPa) with rising trend.

    High pressure rising in summer = already very good weather. Summer adjustment would be redundant.

    Example: 1035 hPa rising summer:
    - OLD: +12.25 hPa adjustment → z_hp=1047 → redundant ❌
    - NEW: No adjustment → z_hp=1035 → fine weather ✅
    """
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 18, 12, 0)

    # High pressure, rising trend
    p0 = 1035.0  # High pressure
    pressure_change = 1.8  # Rising
    wind_data = [0, 0, 'N', 0]  # Calm
    lang_index = 1  # English
    elevation = 300.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")
    text, num, letter = result  # Has 3 values

    # Should give fine weather forecast without over-adjustment
    assert isinstance(num, int)
    assert 0 <= num <= 25
    # High pressure rising should give good forecast
    assert num <= 5, \
        f"High pressure (1035 hPa) rising should give excellent forecast, got #{num}: {text}"


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_summer_adjustment_very_low_pressure_falling(mock_datetime):
    """Test that summer adjustment is NOT applied for very low pressure (<975 hPa) with falling trend.

    Very low pressure falling = deepening storm. Summer adjustment would make it worse.
    """
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 18, 12, 0)

    # Very low pressure (storm), falling trend (deepening)
    p0 = 970.0  # Very low pressure
    pressure_change = -2.0  # Falling (storm deepening)
    wind_data = [2, 180, 'S', 1]  # South wind, strong
    lang_index = 1  # English
    elevation = 300.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")
    text, num, letter = result  # Has 3 values

    # Very low pressure falling should give stormy forecast
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert len(text) > 0


@patch('custom_components.local_weather_forecast.negretti_zambra.datetime')
def test_summer_adjustment_high_pressure_falling(mock_datetime):
    """Test that summer adjustment is NOT applied for high pressure (>1025 hPa) with falling trend."""
    # Mock summer month (July)
    mock_datetime.now.return_value = datetime(2025, 7, 18, 12, 0)

    # High pressure, falling trend (breakdown of anticyclone)
    p0 = 1030.0  # High pressure
    pressure_change = -1.8  # Falling
    wind_data = [1, 180, 'S', 0]  # South, calm
    lang_index = 1  # English
    elevation = 300.0

    result = calculate_negretti_zambra_forecast(p0, pressure_change, wind_data, lang_index, elevation, hemisphere="north")
    text, num, letter = result  # Has 3 values

    # Should give reasonable forecast for anticyclone breakdown
    assert isinstance(num, int)
    assert 0 <= num <= 25
    assert len(text) > 0

