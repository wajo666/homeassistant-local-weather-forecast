"""Local Weather Forecast Integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WEATHER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Local Weather Forecast from a config entry."""
    _LOGGER.debug("Setting up Local Weather Forecast integration")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Migrate entities to new unique IDs (remove entry_id prefix)
    await async_migrate_entities(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_migrate_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate entities from old unique_id format to new format."""
    entity_registry = er.async_get(hass)

    # Mapping of old unique_id (with entry_id prefix) to new unique_id (without prefix)
    migrations = {
        f"{entry.entry_id}_main": "local_forecast",
        f"{entry.entry_id}_pressure": "local_forecast_pressure",
        f"{entry.entry_id}_temperature": "local_forecast_temperature",
        f"{entry.entry_id}_pressure_change": "local_forecast_pressurechange",
        f"{entry.entry_id}_temperature_change": "local_forecast_temperaturechange",
        f"{entry.entry_id}_zambretti_detail": "local_forecast_zambretti_detail",
        f"{entry.entry_id}_neg_zam_detail": "local_forecast_neg_zam_detail",
    }

    for old_unique_id, new_unique_id in migrations.items():
        # Find entity with old unique_id
        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, old_unique_id
        )

        if entity_id:
            _LOGGER.info(
                "Migrating entity %s from unique_id '%s' to '%s'",
                entity_id,
                old_unique_id,
                new_unique_id,
            )

            # Update the entity's unique_id
            entity_registry.async_update_entity(
                entity_id,
                new_unique_id=new_unique_id,
            )
        else:
            _LOGGER.debug(
                "No entity found with old unique_id '%s', assuming clean install",
                old_unique_id,
            )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Local Weather Forecast integration")

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    # Only reload if sensor configuration or critical settings changed
    # This prevents infinite reload loop when only options like enable_weather_entity change

    # Get old and new data
    old_data = hass.data[DOMAIN].get(entry.entry_id, {})
    new_data = entry.data

    # Check if sensor configuration changed (these require platform reload)
    sensor_keys = [
        "pressure_sensor",
        "temperature_sensor",
        "wind_direction_sensor",
        "wind_speed_sensor",
        "humidity_sensor",
        "wind_gust_sensor",
        "rain_rate_sensor",
    ]

    # Check if any sensor configuration changed
    sensors_changed = False
    for key in sensor_keys:
        if old_data.get(key) != new_data.get(key):
            sensors_changed = True
            _LOGGER.info(f"Sensor configuration changed: {key}")
            break

    # Check if critical settings changed
    critical_keys = ["elevation", "pressure_type", "language", "enable_weather_entity"]
    critical_changed = False
    for key in critical_keys:
        if old_data.get(key) != new_data.get(key):
            critical_changed = True
            _LOGGER.info(f"Critical setting changed: {key}")
            break

    # Only reload if something actually changed
    if sensors_changed or critical_changed:
        _LOGGER.info("Configuration changed, reloading integration")
        # Schedule reload instead of immediate to avoid double-reload
        hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))
    else:
        # Just update the data in memory without reload
        _LOGGER.debug("Configuration unchanged, skipping reload")
        hass.data[DOMAIN][entry.entry_id] = new_data

