"""Tests for unit_conversion.py module."""
import pytest
from unittest.mock import Mock

from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

from custom_components.local_weather_forecast.unit_conversion import (
    UnitConverter,
)


class TestPressureConversion:
    """Test pressure conversion methods."""

    def test_convert_pressure_hpa_no_conversion(self):
        """Test pressure conversion when already in hPa."""
        result = UnitConverter.convert_pressure(1013.25, UnitOfPressure.HPA)
        assert result == 1013.25

    def test_convert_pressure_mbar_no_conversion(self):
        """Test pressure conversion when in mbar (same as hPa)."""
        result = UnitConverter.convert_pressure(1013.25, UnitOfPressure.MBAR)
        assert result == 1013.25

    def test_convert_pressure_inhg_to_hpa(self):
        """Test pressure conversion from inHg to hPa."""
        result = UnitConverter.convert_pressure(29.92, UnitOfPressure.INHG)
        assert pytest.approx(result, abs=0.1) == 1013.25

    def test_convert_pressure_mmhg_to_hpa(self):
        """Test pressure conversion from mmHg to hPa."""
        result = UnitConverter.convert_pressure(760.0, UnitOfPressure.MMHG)
        assert pytest.approx(result, abs=0.5) == 1013.25

    def test_convert_pressure_kpa_to_hpa(self):
        """Test pressure conversion from kPa to hPa."""
        result = UnitConverter.convert_pressure(101.325, UnitOfPressure.KPA)
        assert pytest.approx(result, abs=0.1) == 1013.25

    def test_convert_pressure_pa_to_hpa(self):
        """Test pressure conversion from Pa to hPa."""
        result = UnitConverter.convert_pressure(101325.0, UnitOfPressure.PA)
        assert pytest.approx(result, abs=0.1) == 1013.25

    def test_convert_pressure_psi_to_hpa(self):
        """Test pressure conversion from psi to hPa."""
        result = UnitConverter.convert_pressure(14.696, UnitOfPressure.PSI)
        assert pytest.approx(result, abs=1.0) == 1013.25

    def test_convert_pressure_unknown_unit(self):
        """Test pressure conversion with unknown unit (should return original)."""
        result = UnitConverter.convert_pressure(1013.25, "unknown")
        assert result == 1013.25


class TestTemperatureConversion:
    """Test temperature conversion methods."""

    def test_convert_temperature_celsius_no_conversion(self):
        """Test temperature conversion when already in Celsius."""
        result = UnitConverter.convert_temperature(20.0, UnitOfTemperature.CELSIUS)
        assert result == 20.0

    def test_convert_temperature_fahrenheit_to_celsius(self):
        """Test temperature conversion from Fahrenheit to Celsius."""
        result = UnitConverter.convert_temperature(68.0, UnitOfTemperature.FAHRENHEIT)
        assert pytest.approx(result, abs=0.1) == 20.0

    def test_convert_temperature_freezing_point(self):
        """Test temperature conversion at freezing point."""
        result = UnitConverter.convert_temperature(32.0, UnitOfTemperature.FAHRENHEIT)
        assert pytest.approx(result, abs=0.1) == 0.0

    def test_convert_temperature_kelvin_to_celsius(self):
        """Test temperature conversion from Kelvin to Celsius."""
        result = UnitConverter.convert_temperature(293.15, UnitOfTemperature.KELVIN)
        assert pytest.approx(result, abs=0.1) == 20.0

    def test_convert_temperature_absolute_zero(self):
        """Test temperature conversion at absolute zero."""
        result = UnitConverter.convert_temperature(0.0, UnitOfTemperature.KELVIN)
        assert pytest.approx(result, abs=0.1) == -273.15

    def test_convert_temperature_unknown_unit(self):
        """Test temperature conversion with unknown unit (should return original)."""
        result = UnitConverter.convert_temperature(20.0, "unknown")
        assert result == 20.0

    def test_convert_temperature_negative_fahrenheit(self):
        """Test temperature conversion with negative Fahrenheit."""
        result = UnitConverter.convert_temperature(-40.0, UnitOfTemperature.FAHRENHEIT)
        assert pytest.approx(result, abs=0.1) == -40.0  # -40°F = -40°C


class TestWindSpeedConversion:
    """Test wind speed conversion methods."""

    def test_convert_wind_speed_ms_no_conversion(self):
        """Test wind speed conversion when already in m/s."""
        result = UnitConverter.convert_wind_speed(10.0, UnitOfSpeed.METERS_PER_SECOND)
        assert result == 10.0

    def test_convert_wind_speed_kmh_to_ms(self):
        """Test wind speed conversion from km/h to m/s."""
        result = UnitConverter.convert_wind_speed(36.0, UnitOfSpeed.KILOMETERS_PER_HOUR)
        assert pytest.approx(result, abs=0.1) == 10.0

    def test_convert_wind_speed_mph_to_ms(self):
        """Test wind speed conversion from mph to m/s."""
        result = UnitConverter.convert_wind_speed(22.369, UnitOfSpeed.MILES_PER_HOUR)
        assert pytest.approx(result, abs=0.1) == 10.0

    def test_convert_wind_speed_knots_to_ms(self):
        """Test wind speed conversion from knots to m/s."""
        result = UnitConverter.convert_wind_speed(19.438, UnitOfSpeed.KNOTS)
        assert pytest.approx(result, abs=0.1) == 10.0

    def test_convert_wind_speed_fts_to_ms(self):
        """Test wind speed conversion from ft/s to m/s."""
        result = UnitConverter.convert_wind_speed(32.808, "ft/s")
        assert pytest.approx(result, abs=0.1) == 10.0

    def test_convert_wind_speed_unknown_unit(self):
        """Test wind speed conversion with unknown unit (should return original)."""
        result = UnitConverter.convert_wind_speed(10.0, "unknown")
        assert result == 10.0

    def test_convert_wind_speed_calm(self):
        """Test wind speed conversion with calm conditions."""
        result = UnitConverter.convert_wind_speed(0.0, UnitOfSpeed.KILOMETERS_PER_HOUR)
        assert result == 0.0


class TestPrecipitationConversion:
    """Test precipitation conversion methods."""

    def test_convert_precipitation_mm_no_conversion(self):
        """Test precipitation conversion when already in mm."""
        result = UnitConverter.convert_precipitation(10.0, "mm")
        assert result == 10.0

    def test_convert_precipitation_mmh_no_conversion(self):
        """Test precipitation conversion when already in mm/h."""
        result = UnitConverter.convert_precipitation(5.0, "mm/h")
        assert result == 5.0

    def test_convert_precipitation_in_to_mm(self):
        """Test precipitation conversion from inches to mm."""
        result = UnitConverter.convert_precipitation(1.0, "in")
        assert pytest.approx(result, abs=0.1) == 25.4

    def test_convert_precipitation_inh_to_mmh(self):
        """Test precipitation rate conversion from in/h to mm/h."""
        result = UnitConverter.convert_precipitation(2.0, "in/h")
        assert pytest.approx(result, abs=0.1) == 50.8

    def test_convert_precipitation_unknown_unit(self):
        """Test precipitation conversion with unknown unit (should return original)."""
        result = UnitConverter.convert_precipitation(10.0, "unknown")
        assert result == 10.0


class TestConvertSensorValue:
    """Test generic sensor value conversion."""

    def test_convert_sensor_value_pressure(self):
        """Test converting pressure sensor value."""
        result = UnitConverter.convert_sensor_value(29.92, "pressure", UnitOfPressure.INHG)
        assert pytest.approx(result, abs=0.1) == 1013.25

    def test_convert_sensor_value_temperature(self):
        """Test converting temperature sensor value."""
        result = UnitConverter.convert_sensor_value(68.0, "temperature", UnitOfTemperature.FAHRENHEIT)
        assert pytest.approx(result, abs=0.1) == 20.0

    def test_convert_sensor_value_wind_speed(self):
        """Test converting wind speed sensor value."""
        result = UnitConverter.convert_sensor_value(36.0, "wind_speed", UnitOfSpeed.KILOMETERS_PER_HOUR)
        assert pytest.approx(result, abs=0.1) == 10.0

    def test_convert_sensor_value_humidity(self):
        """Test converting humidity sensor value (no conversion)."""
        result = UnitConverter.convert_sensor_value(75.0, "humidity", "%")
        assert result == 75.0

    def test_convert_sensor_value_precipitation(self):
        """Test converting precipitation sensor value."""
        result = UnitConverter.convert_sensor_value(1.0, "precipitation", "in")
        assert pytest.approx(result, abs=0.1) == 25.4

    def test_convert_sensor_value_no_unit(self):
        """Test converting sensor value with no unit specified."""
        result = UnitConverter.convert_sensor_value(100.0, "pressure", None)
        assert result == 100.0

    def test_convert_sensor_value_unknown_type(self):
        """Test converting unknown sensor type."""
        result = UnitConverter.convert_sensor_value(100.0, "unknown", "unit")
        assert result == 100.0


class TestGetSensorUnit:
    """Test getting sensor unit from entity."""

    def test_get_sensor_unit_exists(self):
        """Test getting unit from existing sensor."""
        mock_hass = Mock()
        mock_state = Mock()
        mock_state.attributes = {"unit_of_measurement": "hPa"}
        mock_hass.states.get.return_value = mock_state

        result = UnitConverter.get_sensor_unit(mock_hass, "sensor.test_pressure")

        assert result == "hPa"
        mock_hass.states.get.assert_called_once_with("sensor.test_pressure")

    def test_get_sensor_unit_not_exists(self):
        """Test getting unit from non-existing sensor."""
        mock_hass = Mock()
        mock_hass.states.get.return_value = None

        result = UnitConverter.get_sensor_unit(mock_hass, "sensor.nonexistent")

        assert result is None


class TestFormatForUI:
    """Test formatting values for UI display."""

    def test_format_for_ui_pressure_default(self):
        """Test formatting pressure with default (SI) units."""
        result = UnitConverter.format_for_ui(1013.25, "pressure", None, 1)
        assert result == "1013.2 hPa"

    def test_format_for_ui_pressure_inhg(self):
        """Test formatting pressure in inHg."""
        result = UnitConverter.format_for_ui(1013.25, "pressure", UnitOfPressure.INHG, 2)
        expected = 1013.25 / 33.8639
        assert result == f"{expected:.2f} {UnitOfPressure.INHG}"

    def test_format_for_ui_temperature_default(self):
        """Test formatting temperature with default (SI) units."""
        result = UnitConverter.format_for_ui(20.0, "temperature", None, 1)
        assert result == "20.0°C"

    def test_format_for_ui_temperature_fahrenheit(self):
        """Test formatting temperature in Fahrenheit."""
        result = UnitConverter.format_for_ui(20.0, "temperature", UnitOfTemperature.FAHRENHEIT, 1)
        expected = (20.0 * 9 / 5) + 32
        assert result == f"{expected:.1f} {UnitOfTemperature.FAHRENHEIT}"

    def test_format_for_ui_wind_speed_default(self):
        """Test formatting wind speed with default (SI) units."""
        result = UnitConverter.format_for_ui(10.0, "wind_speed", None, 1)
        assert result == "10.0 m/s"

    def test_format_for_ui_wind_speed_kmh(self):
        """Test formatting wind speed in km/h."""
        result = UnitConverter.format_for_ui(10.0, "wind_speed", UnitOfSpeed.KILOMETERS_PER_HOUR, 1)
        expected = 10.0 * 3.6
        assert result == f"{expected:.1f} {UnitOfSpeed.KILOMETERS_PER_HOUR}"

    def test_format_for_ui_humidity(self):
        """Test formatting humidity."""
        result = UnitConverter.format_for_ui(75.5, "humidity", None, 0)
        assert result == "76%"

    def test_format_for_ui_precipitation_inches(self):
        """Test formatting precipitation in inches."""
        result = UnitConverter.format_for_ui(25.4, "precipitation", "in", 2)
        expected = 25.4 / 25.4
        assert result == f"{expected:.2f} in"


class TestRequiredUnits:
    """Test REQUIRED_UNITS constants."""

    def test_required_units_pressure(self):
        """Test that required pressure unit is hPa."""
        assert UnitConverter.REQUIRED_UNITS["pressure"] == UnitOfPressure.HPA

    def test_required_units_temperature(self):
        """Test that required temperature unit is Celsius."""
        assert UnitConverter.REQUIRED_UNITS["temperature"] == UnitOfTemperature.CELSIUS

    def test_required_units_wind_speed(self):
        """Test that required wind speed unit is m/s."""
        assert UnitConverter.REQUIRED_UNITS["wind_speed"] == UnitOfSpeed.METERS_PER_SECOND

    def test_required_units_humidity(self):
        """Test that required humidity unit is %."""
        from homeassistant.const import PERCENTAGE
        assert UnitConverter.REQUIRED_UNITS["humidity"] == PERCENTAGE

    def test_required_units_precipitation(self):
        """Test that required precipitation unit is mm."""
        assert UnitConverter.REQUIRED_UNITS["precipitation"] == "mm"


class TestConversionAccuracy:
    """Test conversion accuracy and edge cases."""

    def test_pressure_conversion_roundtrip(self):
        """Test pressure conversion roundtrip accuracy."""
        original = 1013.25
        # Convert to inHg and back
        inhg = original / 33.8639
        back_to_hpa = UnitConverter.convert_pressure(inhg, UnitOfPressure.INHG)
        assert pytest.approx(back_to_hpa, abs=0.01) == original

    def test_temperature_conversion_roundtrip(self):
        """Test temperature conversion roundtrip accuracy."""
        original = 20.0
        # Convert to °F and back
        fahrenheit = (original * 9 / 5) + 32
        back_to_celsius = UnitConverter.convert_temperature(fahrenheit, UnitOfTemperature.FAHRENHEIT)
        assert pytest.approx(back_to_celsius, abs=0.01) == original

    def test_wind_speed_conversion_roundtrip(self):
        """Test wind speed conversion roundtrip accuracy."""
        original = 10.0
        # Convert to km/h and back
        kmh = original * 3.6
        back_to_ms = UnitConverter.convert_wind_speed(kmh, UnitOfSpeed.KILOMETERS_PER_HOUR)
        assert pytest.approx(back_to_ms, abs=0.01) == original

    def test_extreme_pressure_values(self):
        """Test conversion with extreme pressure values."""
        # Very low pressure (tropical cyclone)
        low = UnitConverter.convert_pressure(27.0, UnitOfPressure.INHG)
        assert 900 < low < 950

        # Very high pressure (winter anticyclone)
        high = UnitConverter.convert_pressure(31.5, UnitOfPressure.INHG)
        assert 1050 < high < 1100

    def test_extreme_temperature_values(self):
        """Test conversion with extreme temperature values."""
        # Very cold
        cold_f = -40.0
        cold_c = UnitConverter.convert_temperature(cold_f, UnitOfTemperature.FAHRENHEIT)
        assert cold_c == pytest.approx(-40.0, abs=0.1)

        # Very hot
        hot_f = 120.0
        hot_c = UnitConverter.convert_temperature(hot_f, UnitOfTemperature.FAHRENHEIT)
        assert hot_c == pytest.approx(48.89, abs=0.1)

    def test_extreme_wind_speed_values(self):
        """Test conversion with extreme wind speed values."""
        # Hurricane force wind
        hurricane_mph = 100.0
        hurricane_ms = UnitConverter.convert_wind_speed(hurricane_mph, UnitOfSpeed.MILES_PER_HOUR)
        assert hurricane_ms > 40.0

        # Calm conditions
        calm = UnitConverter.convert_wind_speed(0.0, UnitOfSpeed.KILOMETERS_PER_HOUR)
        assert calm == 0.0


# Integration test
class TestUnitConversionIntegration:
    """Integration tests for unit conversion."""

    def test_realistic_weather_scenario(self):
        """Test conversion with realistic weather station data."""
        # Typical weather station readings in US units
        pressure_inhg = 29.92
        temp_f = 68.0
        wind_mph = 10.0
        rain_in = 0.5

        # Convert to SI units
        pressure_hpa = UnitConverter.convert_pressure(pressure_inhg, UnitOfPressure.INHG)
        temp_c = UnitConverter.convert_temperature(temp_f, UnitOfTemperature.FAHRENHEIT)
        wind_ms = UnitConverter.convert_wind_speed(wind_mph, UnitOfSpeed.MILES_PER_HOUR)
        rain_mm = UnitConverter.convert_precipitation(rain_in, "in")

        # Verify conversions
        assert pytest.approx(pressure_hpa, abs=0.1) == 1013.25
        assert pytest.approx(temp_c, abs=0.1) == 20.0
        assert pytest.approx(wind_ms, abs=0.1) == 4.47
        assert pytest.approx(rain_mm, abs=0.1) == 12.7

    def test_multiple_conversions_consistency(self):
        """Test that multiple conversions remain consistent."""
        original_pressure = 1013.25

        # Convert through multiple units
        inhg = original_pressure / 33.8639
        mmhg = inhg * 25.4  # inHg to mmHg
        back_to_hpa = UnitConverter.convert_pressure(mmhg, UnitOfPressure.MMHG)

        # Should be close to original (within rounding errors)
        assert pytest.approx(back_to_hpa, abs=1.0) == original_pressure

