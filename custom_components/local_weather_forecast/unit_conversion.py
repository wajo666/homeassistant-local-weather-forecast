"""Unit conversion utilities for Local Weather Forecast integration."""
from __future__ import annotations

import logging

from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    PERCENTAGE,
)

_LOGGER = logging.getLogger(__name__)


class UnitConverter:
    """Handle unit conversions for weather sensors."""

    # Required units for calculations (internal format)
    REQUIRED_UNITS = {
        "pressure": UnitOfPressure.HPA,  # hPa for Zambretti/Negretti
        "temperature": UnitOfTemperature.CELSIUS,  # °C for calculations
        "wind_speed": UnitOfSpeed.METERS_PER_SECOND,  # m/s for Zambretti threshold
        "humidity": PERCENTAGE,  # % for calculations
        "precipitation": "mm",  # mm or mm/h for rain detection
    }

    @staticmethod
    def convert_pressure(value: float, from_unit: str) -> float:
        """Convert pressure to hPa.

        Args:
            value: Pressure value
            from_unit: Source unit (hPa, inHg, mbar, mmHg, kPa, Pa, psi)

        Returns:
            Pressure in hPa
        """
        if from_unit in (UnitOfPressure.HPA, UnitOfPressure.MBAR, "hPa", "mbar"):
            _LOGGER.debug(f"Pressure conversion: {value} {from_unit} (no conversion needed)")
            return value

        result = value
        if from_unit in (UnitOfPressure.INHG, "inHg"):
            result = value * 33.8639  # inHg to hPa
        elif from_unit in (UnitOfPressure.MMHG, "mmHg"):
            result = value * 1.33322  # mmHg to hPa
        elif from_unit in (UnitOfPressure.KPA, "kPa"):
            result = value * 10.0  # kPa to hPa
        elif from_unit in (UnitOfPressure.PA, "Pa"):
            result = value / 100.0  # Pa to hPa
        elif from_unit in (UnitOfPressure.PSI, "psi"):
            result = value * 68.9476  # psi to hPa
        else:
            _LOGGER.warning(f"Unknown pressure unit: {from_unit}, assuming hPa")
            return value

        _LOGGER.debug(f"Pressure conversion: {value} {from_unit} → {result:.2f} hPa")
        return result

    @staticmethod
    def convert_temperature(value: float, from_unit: str) -> float:
        """Convert temperature to Celsius.

        Args:
            value: Temperature value
            from_unit: Source unit (°C, °F, K)

        Returns:
            Temperature in °C
        """
        if from_unit in (UnitOfTemperature.CELSIUS, "°C", "C"):
            _LOGGER.debug(f"Temperature conversion: {value} {from_unit} (no conversion needed)")
            return value

        result = value
        if from_unit in (UnitOfTemperature.FAHRENHEIT, "°F", "F"):
            result = (value - 32) * 5 / 9  # °F to °C
        elif from_unit in (UnitOfTemperature.KELVIN, "K"):
            result = value - 273.15  # K to °C
        else:
            _LOGGER.warning(f"Unknown temperature unit: {from_unit}, assuming °C")
            return value

        _LOGGER.debug(f"Temperature conversion: {value} {from_unit} → {result:.2f} °C")
        return result

    @staticmethod
    def convert_wind_speed(value: float, from_unit: str) -> float:
        """Convert wind speed to m/s.

        Args:
            value: Wind speed value
            from_unit: Source unit (m/s, km/h, mph, kn, ft/s)

        Returns:
            Wind speed in m/s
        """
        if from_unit in (UnitOfSpeed.METERS_PER_SECOND, "m/s"):
            _LOGGER.debug(f"Wind speed conversion: {value} {from_unit} (no conversion needed)")
            return value

        result = value
        if from_unit in (UnitOfSpeed.KILOMETERS_PER_HOUR, "km/h", "kmh"):
            result = value / 3.6  # km/h to m/s
        elif from_unit in (UnitOfSpeed.MILES_PER_HOUR, "mph"):
            result = value * 0.44704  # mph to m/s
        elif from_unit in (UnitOfSpeed.KNOTS, "kn", "kt"):
            result = value * 0.514444  # knots to m/s
        elif from_unit in ("ft/s", "fps"):
            result = value * 0.3048  # ft/s to m/s
        else:
            _LOGGER.warning(f"Unknown wind speed unit: {from_unit}, assuming m/s")
            return value

        _LOGGER.debug(f"Wind speed conversion: {value} {from_unit} → {result:.2f} m/s")
        return result

    @staticmethod
    def convert_precipitation(value: float, from_unit: str) -> float:
        """Convert precipitation/rain rate to mm or mm/h.

        Args:
            value: Precipitation value
            from_unit: Source unit (mm, mm/h, in, in/h)

        Returns:
            Precipitation in mm or mm/h (same time unit as input)
        """
        if from_unit in ("mm", "mm/h"):
            _LOGGER.debug(f"Precipitation conversion: {value} {from_unit} (no conversion needed)")
            return value

        result = value
        if from_unit in ("in", "in/h"):
            result = value * 25.4  # inches to mm (1 inch = 25.4 mm)
            _LOGGER.debug(f"Precipitation conversion: {value} {from_unit} → {result:.2f} mm")
        else:
            _LOGGER.warning(f"Unknown precipitation unit: {from_unit}, assuming mm")
            return value

        return result

    @staticmethod
    def get_sensor_unit(hass, entity_id: str) -> str | None:
        """Get unit of measurement from sensor entity.

        Args:
            hass: Home Assistant instance
            entity_id: Entity ID

        Returns:
            Unit of measurement or None
        """
        state = hass.states.get(entity_id)
        if state:
            return state.attributes.get("unit_of_measurement")
        return None

    @classmethod
    def convert_sensor_value(
        cls,
        value: float,
        sensor_type: str,
        from_unit: str | None = None,
    ) -> float:
        """Convert sensor value to required internal unit.

        Args:
            value: Sensor value
            sensor_type: Type of sensor (pressure, temperature, wind_speed, humidity, precipitation)
            from_unit: Source unit (if None, assumes already in correct unit)

        Returns:
            Converted value in required unit
        """
        if from_unit is None:
            _LOGGER.debug(f"Converting {sensor_type}: {value} (no unit specified, assuming correct unit)")
            return value

        _LOGGER.debug(f"Converting {sensor_type}: {value} {from_unit} to {cls.REQUIRED_UNITS.get(sensor_type)}")

        if sensor_type == "pressure":
            return cls.convert_pressure(value, from_unit)
        elif sensor_type == "temperature":
            return cls.convert_temperature(value, from_unit)
        elif sensor_type == "wind_speed":
            return cls.convert_wind_speed(value, from_unit)
        elif sensor_type == "humidity":
            # Humidity is always in %
            _LOGGER.debug(f"Humidity: {value}% (no conversion needed)")
            return value
        elif sensor_type == "precipitation":
            return cls.convert_precipitation(value, from_unit)
        else:
            _LOGGER.warning(f"Unknown sensor type: {sensor_type}")
            return value

    @classmethod
    async def get_converted_value(
        cls,
        hass,
        entity_id: str,
        sensor_type: str,
        default: float = 0.0,
    ) -> tuple[float, str]:
        """Get sensor value and convert to required unit.

        Args:
            hass: Home Assistant instance
            entity_id: Entity ID
            sensor_type: Type of sensor
            default: Default value if sensor unavailable

        Returns:
            Tuple of (converted_value, original_unit)
        """
        state = hass.states.get(entity_id)
        if not state or state.state in ("unknown", "unavailable"):
            return (default, cls.REQUIRED_UNITS.get(sensor_type, ""))

        try:
            value = float(state.state)
            unit = state.attributes.get("unit_of_measurement")

            converted = cls.convert_sensor_value(value, sensor_type, unit)

            _LOGGER.debug(
                f"Converted {entity_id}: {value} {unit} → {converted:.2f} "
                f"{cls.REQUIRED_UNITS.get(sensor_type)}"
            )

            return (converted, unit)

        except (ValueError, TypeError) as e:
            _LOGGER.error(
                f"Failed to convert {entity_id} value '{state.state}': {e}"
            )
            return (default, "")

    @staticmethod
    def format_for_ui(
        value: float,
        sensor_type: str,
        user_unit: str | None = None,
        precision: int = 1,
    ) -> str:
        """Format value for UI display in user's preferred unit.

        Args:
            value: Value in internal unit (SI: hPa, °C, m/s, %)
            sensor_type: Type of sensor
            user_unit: User's preferred unit (from HA settings)
            precision: Decimal places

        Returns:
            Formatted string with value converted to user's unit
        """
        if user_unit is None:
            # Use HA defaults (SI units)
            if sensor_type == "pressure":
                return f"{value:.{precision}f} hPa"
            elif sensor_type == "temperature":
                return f"{value:.{precision}f}°C"
            elif sensor_type == "wind_speed":
                return f"{value:.{precision}f} m/s"
            elif sensor_type == "humidity":
                return f"{value:.0f}%"

        # Reverse conversion: SI units → user's preferred unit
        converted_value = value

        if sensor_type == "pressure":
            # Value is in hPa, convert to user's unit
            if user_unit in (UnitOfPressure.INHG, "inHg"):
                converted_value = value / 33.8639  # hPa to inHg
            elif user_unit in (UnitOfPressure.MMHG, "mmHg"):
                converted_value = value / 1.33322  # hPa to mmHg
            elif user_unit in (UnitOfPressure.KPA, "kPa"):
                converted_value = value / 10.0  # hPa to kPa
            elif user_unit in (UnitOfPressure.PSI, "psi"):
                converted_value = value / 68.9476  # hPa to psi

        elif sensor_type == "temperature":
            # Value is in °C, convert to user's unit
            if user_unit in (UnitOfTemperature.FAHRENHEIT, "°F", "F"):
                converted_value = (value * 9 / 5) + 32  # °C to °F
            elif user_unit in (UnitOfTemperature.KELVIN, "K"):
                converted_value = value + 273.15  # °C to K

        elif sensor_type == "wind_speed":
            # Value is in m/s, convert to user's unit
            if user_unit in (UnitOfSpeed.KILOMETERS_PER_HOUR, "km/h", "kmh"):
                converted_value = value * 3.6  # m/s to km/h
            elif user_unit in (UnitOfSpeed.MILES_PER_HOUR, "mph"):
                converted_value = value / 0.44704  # m/s to mph
            elif user_unit in (UnitOfSpeed.KNOTS, "kn", "kt"):
                converted_value = value / 0.514444  # m/s to knots
            elif user_unit in ("ft/s", "fps"):
                converted_value = value / 0.3048  # m/s to ft/s

        elif sensor_type == "precipitation":
            # Value is in mm, convert to user's unit
            if user_unit in ("in", "in/h"):
                converted_value = value / 25.4  # mm to inches

        return f"{converted_value:.{precision}f} {user_unit}"


# Convenience functions
async def get_pressure_hpa(hass, entity_id: str, default: float = 1013.25) -> float:
    """Get pressure in hPa."""
    value, _ = await UnitConverter.get_converted_value(
        hass, entity_id, "pressure", default
    )
    return value


async def get_temperature_celsius(hass, entity_id: str, default: float = 15.0) -> float:
    """Get temperature in °C."""
    value, _ = await UnitConverter.get_converted_value(
        hass, entity_id, "temperature", default
    )
    return value


async def get_wind_speed_ms(hass, entity_id: str, default: float = 0.0) -> float:
    """Get wind speed in m/s."""
    value, _ = await UnitConverter.get_converted_value(
        hass, entity_id, "wind_speed", default
    )
    return value

