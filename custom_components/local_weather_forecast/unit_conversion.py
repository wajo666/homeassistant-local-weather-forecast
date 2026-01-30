"""Unit conversion utilities for Local Weather Forecast integration."""
from __future__ import annotations

import logging

from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfLength,
    PERCENTAGE,
)
from homeassistant.util.unit_conversion import (
    PressureConverter,
    TemperatureConverter,
    SpeedConverter,
    DistanceConverter,
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
        "solar_radiation": "W/m²",  # W/m² for solar radiation
    }

    @staticmethod
    def convert_pressure(value: float, from_unit: str) -> float:
        """Convert pressure to hPa using Home Assistant's official converter.

        Args:
            value: Pressure value
            from_unit: Source unit (hPa, inHg, mbar, mmHg, kPa, Pa, psi)

        Returns:
            Pressure in hPa
        """
        try:
            # Normalize unit names for HA converter
            unit_map = {
                "hPa": UnitOfPressure.HPA,
                "mbar": UnitOfPressure.MBAR,
                "inHg": UnitOfPressure.INHG,
                "mmHg": UnitOfPressure.MMHG,
                "kPa": UnitOfPressure.KPA,
                "Pa": UnitOfPressure.PA,
                "psi": UnitOfPressure.PSI,
            }
            normalized_unit = unit_map.get(from_unit, from_unit)
            
            # Use Home Assistant's official PressureConverter for better precision
            result = PressureConverter.convert(value, normalized_unit, UnitOfPressure.HPA)
            _LOGGER.debug(f"Pressure conversion: {value} {from_unit} → {result:.2f} hPa")
            return result
        except Exception as e:
            _LOGGER.warning(f"Pressure conversion error for {value} {from_unit}: {e}, assuming hPa")
            return value

    @staticmethod
    def convert_temperature(value: float, from_unit: str) -> float:
        """Convert temperature to Celsius using Home Assistant's official converter.

        Args:
            value: Temperature value
            from_unit: Source unit (°C, °F, K)

        Returns:
            Temperature in °C
        """
        try:
            # Normalize unit names for HA converter
            unit_map = {
                "C": UnitOfTemperature.CELSIUS,
                "°C": UnitOfTemperature.CELSIUS,
                "F": UnitOfTemperature.FAHRENHEIT,
                "°F": UnitOfTemperature.FAHRENHEIT,
                "K": UnitOfTemperature.KELVIN,
            }
            normalized_unit = unit_map.get(from_unit, from_unit)
            
            # Use Home Assistant's official TemperatureConverter for consistency
            result = TemperatureConverter.convert(value, normalized_unit, UnitOfTemperature.CELSIUS)
            _LOGGER.debug(f"Temperature conversion: {value} {from_unit} → {result:.2f} °C")
            return result
        except Exception as e:
            _LOGGER.warning(f"Temperature conversion error for {value} {from_unit}: {e}, assuming °C")
            return value

    @staticmethod
    def convert_wind_speed(value: float, from_unit: str) -> float:
        """Convert wind speed to m/s using Home Assistant's official converter.

        Args:
            value: Wind speed value
            from_unit: Source unit (m/s, km/h, mph, kn, ft/s)

        Returns:
            Wind speed in m/s
        """
        try:
            # Normalize unit names for HA converter
            unit_map = {
                "m/s": UnitOfSpeed.METERS_PER_SECOND,
                "km/h": UnitOfSpeed.KILOMETERS_PER_HOUR,
                "kmh": UnitOfSpeed.KILOMETERS_PER_HOUR,
                "mph": UnitOfSpeed.MILES_PER_HOUR,
                "kn": UnitOfSpeed.KNOTS,
                "kt": UnitOfSpeed.KNOTS,
                "ft/s": UnitOfSpeed.FEET_PER_SECOND,
                "fps": UnitOfSpeed.FEET_PER_SECOND,
            }
            normalized_unit = unit_map.get(from_unit, from_unit)
            
            # Use Home Assistant's official SpeedConverter for consistency
            result = SpeedConverter.convert(value, normalized_unit, UnitOfSpeed.METERS_PER_SECOND)
            _LOGGER.debug(f"Wind speed conversion: {value} {from_unit} → {result:.2f} m/s")
            return result
        except Exception as e:
            _LOGGER.warning(f"Wind speed conversion error for {value} {from_unit}: {e}, assuming m/s")
            return value

    @staticmethod
    def convert_precipitation(value: float, from_unit: str) -> float:
        """Convert precipitation/rain rate to mm or mm/h using Home Assistant's official converter.

        Args:
            value: Precipitation value
            from_unit: Source unit (mm, mm/h, in, in/h)

        Returns:
            Precipitation in mm or mm/h (same time unit as input)
        """
        try:
            # Normalize unit names for HA DistanceConverter
            # Handle rate units (mm/h, in/h) by converting distance part only
            is_rate = "/h" in from_unit
            base_unit = from_unit.replace("/h", "") if is_rate else from_unit
            
            # Map common aliases to UnitOfLength constants
            unit_map = {
                "mm": UnitOfLength.MILLIMETERS,
                "in": UnitOfLength.INCHES,
            }
            
            normalized_unit = unit_map.get(base_unit, base_unit)
            
            # Use Home Assistant's official DistanceConverter
            result = DistanceConverter.convert(value, normalized_unit, UnitOfLength.MILLIMETERS)
            
            target_unit = "mm/h" if is_rate else "mm"
            _LOGGER.debug(f"Precipitation conversion: {value} {from_unit} → {result:.2f} {target_unit}")
            return result
        except Exception as e:
            _LOGGER.warning(f"Precipitation conversion error for {value} {from_unit}: {e}, assuming mm")
            return value

    @staticmethod
    def convert_solar_radiation(value: float, from_unit: str) -> float:
        """Convert solar radiation to W/m².
        
        Note: Home Assistant core doesn't provide a solar radiation converter
        because the lux→W/m² relationship is highly spectrum-dependent.
        This custom implementation uses a conservative factor suitable for direct sunlight.

        Args:
            value: Solar radiation value
            from_unit: Source unit (W/m², lx, lux)

        Returns:
            Solar radiation in W/m²
        """
        if from_unit in ("W/m²", "W/m2", "watt/m²"):
            _LOGGER.debug(f"Solar radiation conversion: {value} {from_unit} (no conversion needed)")
            return value

        result = value
        if from_unit in ("lx", "lux"):
            # Convert lux to W/m²
            # For direct sunlight: 1 lux ≈ 0.0079 W/m²
            # This is an approximation as the exact conversion depends on light spectrum
            result = value * 0.0079
            _LOGGER.debug(f"Solar radiation conversion: {value} {from_unit} → {result:.2f} W/m²")
        else:
            _LOGGER.warning(f"Unknown solar radiation unit: {from_unit}, assuming W/m²")
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
        elif sensor_type == "solar_radiation":
            return cls.convert_solar_radiation(value, from_unit)
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
        """Format value for UI display in user's preferred unit using HA converters.

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

        # Reverse conversion: SI units → user's preferred unit using HA converters
        # Type guard: user_unit is guaranteed to be str here (not None) due to check above
        assert user_unit is not None
        
        try:
            if sensor_type == "pressure":
                # Value is in hPa, convert to user's unit using PressureConverter
                converted_value = PressureConverter.convert(value, UnitOfPressure.HPA, user_unit)
            elif sensor_type == "temperature":
                # Value is in °C, convert to user's unit using TemperatureConverter
                converted_value = TemperatureConverter.convert(value, UnitOfTemperature.CELSIUS, user_unit)
            elif sensor_type == "wind_speed":
                # Value is in m/s, convert to user's unit using SpeedConverter
                converted_value = SpeedConverter.convert(value, UnitOfSpeed.METERS_PER_SECOND, user_unit)
            elif sensor_type == "precipitation":
                # Value is in mm, convert to user's unit using DistanceConverter
                base_unit = user_unit.replace("/h", "") if "/h" in user_unit else user_unit
                unit_map = {
                    "mm": UnitOfLength.MILLIMETERS,
                    "in": UnitOfLength.INCHES,
                }
                target_unit = unit_map.get(base_unit, base_unit)
                converted_value = DistanceConverter.convert(value, UnitOfLength.MILLIMETERS, target_unit)
            else:
                # Fallback for unknown types
                converted_value = value

            return f"{converted_value:.{precision}f} {user_unit}"
        except Exception as e:
            _LOGGER.warning(f"UI formatting error for {sensor_type} {value} → {user_unit}: {e}")
            return f"{value:.{precision}f} {user_unit}"


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

