"""Pytest configuration and fixtures for Local Weather Forecast tests."""
import pytest
from unittest.mock import Mock
import asyncio


def pytest_configure(config):
    """Configure pytest with asyncio support."""
    config.addinivalue_line("markers", "asyncio: mark test as asyncio")


class MockConfigEntry:
    """Mock ConfigEntry for testing."""

    def __init__(
        self,
        domain="local_weather_forecast",
        data=None,
        options=None,
        entry_id="test_entry",
        title="Test",
        unique_id=None,
        source="user",
    ):
        """Initialize mock config entry."""
        self.domain = domain
        self.data = data or {}
        self.options = options or {}
        self.entry_id = entry_id
        self.title = title
        self.unique_id = unique_id
        self.source = source
        self.state = "loaded"

    async def async_setup(self, hass):
        """Mock setup."""
        return True

    async def async_unload(self, hass):
        """Mock unload."""
        return True


class MockState:
    """Mock State object."""

    def __init__(self, entity_id, state, attributes=None):
        """Initialize mock state."""
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}


class MockStates:
    """Mock states registry."""

    def __init__(self):
        """Initialize mock states."""
        self._states = {}

    def get(self, entity_id):
        """Get state by entity_id."""
        return self._states.get(entity_id)

    def async_set(self, entity_id, state, attributes=None):
        """Set state for entity."""
        self._states[entity_id] = MockState(entity_id, state, attributes)

    def async_remove(self, entity_id):
        """Remove state."""
        self._states.pop(entity_id, None)


class MockFlowHandler:
    """Mock flow handler."""

    def __init__(self, hass, flow_type="config"):
        """Initialize mock flow handler."""
        self.hass = hass
        self._flows = {}
        self._flow_counter = 0
        self._flow_type = flow_type  # "config" or "options"
        self._flow_to_entry_id = {}  # Map flow_id to entry_id for options flow

    async def async_init(self, domain_or_entry_id, context=None, data=None):
        """Initialize a flow."""
        from homeassistant.data_entry_flow import FlowResultType

        self._flow_counter += 1
        flow_id = f"test_flow_{self._flow_counter}"

        # For options flow, domain_or_entry_id is the entry_id
        if self._flow_type == "options":
            self._flow_to_entry_id[flow_id] = domain_or_entry_id

        # Options flow uses "init" step, config flow uses "user" step
        step_id = "init" if self._flow_type == "options" else "user"

        return {
            "type": FlowResultType.FORM,
            "flow_id": flow_id,
            "step_id": step_id,
            "data_schema": None,
            "errors": {},
        }

    async def async_configure(self, flow_id, user_input=None):
        """Configure a flow."""
        from homeassistant.data_entry_flow import FlowResultType

        # Mock validation - check if sensors exist
        errors = {}

        if user_input:
            # Check elevation
            elevation = user_input.get("elevation")
            if elevation is not None:
                if not (0 <= elevation <= 9000):
                    errors["elevation"] = "invalid_elevation"

            # Check all sensor fields - both required and optional
            sensor_fields = [
                "pressure_sensor",
                "temperature_sensor",
                "humidity_sensor",
                "wind_speed_sensor",
                "wind_direction_sensor",
                "wind_gust_sensor",
                "rain_rate_sensor",
            ]

            for field in sensor_fields:
                if field in user_input:
                    sensor_id = user_input.get(field)
                    # Only validate if sensor_id is not empty/None
                    if sensor_id and not self.hass.states.get(sensor_id):
                        errors[field] = "sensor_not_found"

            # Convert empty strings to None
            for key in list(user_input.keys()):
                if user_input[key] == "":
                    user_input[key] = None

        if errors:
            step_id = "init" if self._flow_type == "options" else "user"
            return {
                "type": FlowResultType.FORM,
                "flow_id": flow_id,
                "step_id": step_id,
                "errors": errors,
            }

        # Options flow - update existing entry
        if self._flow_type == "options":
            # Get the entry_id from the flow_id mapping
            entry_id = self._flow_to_entry_id.get(flow_id)
            existing_entry = self.hass.config_entries._entries.get(entry_id)
            if existing_entry and user_input:
                # Update entry data with new values
                existing_entry.data.update(user_input)
                return {
                    "type": FlowResultType.CREATE_ENTRY,
                    "flow_id": flow_id,
                    "title": existing_entry.title,
                    "data": existing_entry.data,
                }

        # Config flow - check for duplicates (already configured)
        if user_input and "pressure_sensor" in user_input:
            for entry in self.hass.config_entries.async_entries("local_weather_forecast"):
                if entry.data.get("pressure_sensor") == user_input.get("pressure_sensor"):
                    return {
                        "type": FlowResultType.ABORT,
                        "reason": "already_configured",
                    }

        # Prepare data with None values for missing optional sensors
        data = user_input.copy() if user_input else {}

        # Add None for optional sensors if not provided
        optional_sensors = [
            "temperature_sensor",
            "wind_speed_sensor",
            "wind_direction_sensor",
            "humidity_sensor",
            "wind_gust_sensor",
            "rain_rate_sensor",
        ]

        for sensor in optional_sensors:
            if sensor not in data:
                data[sensor] = None

        # Create and store the entry (config flow only)
        entry = MockConfigEntry(
            domain="local_weather_forecast",
            data=data,
            entry_id=flow_id,
            title="Local Weather Forecast",
        )
        self.hass.config_entries._entries[flow_id] = entry

        return {
            "type": FlowResultType.CREATE_ENTRY,
            "flow_id": flow_id,
            "title": "Local Weather Forecast",
            "data": data,
        }


class MockConfigEntries:
    """Mock config entries registry."""

    def __init__(self, hass):
        """Initialize mock config entries."""
        self.hass = hass
        self._entries = {}
        self.flow = MockFlowHandler(hass, flow_type="config")
        self.options = MockFlowHandler(hass, flow_type="options")

    def async_entries(self, domain=None):
        """Get all entries."""
        if domain:
            return [e for e in self._entries.values() if e.domain == domain]
        return list(self._entries.values())

    def async_get_entry(self, entry_id):
        """Get entry by ID."""
        return self._entries.get(entry_id)


class MockEventBus:
    """Mock event bus."""

    def __init__(self):
        """Initialize mock event bus."""
        self._listeners = {}

    def async_listen(self, event_type, listener):
        """Listen for events."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    async def async_fire(self, event_type, event_data=None):
        """Fire an event."""
        if event_type in self._listeners:
            for listener in self._listeners[event_type]:
                await listener(event_data)


class MockHomeAssistant:
    """Mock Home Assistant instance."""

    def __init__(self):
        """Initialize mock hass."""
        self.states = MockStates()
        self.config_entries = MockConfigEntries(self)
        self.bus = MockEventBus()
        self.data = {}
        self.config = Mock()
        self.config.language = "en"
        self.loop = asyncio.get_event_loop()

    def async_create_task(self, coro):
        """Create a task."""
        return asyncio.create_task(coro)

    def async_add_executor_job(self, func, *args):
        """Add executor job."""
        return asyncio.get_event_loop().run_in_executor(None, func, *args)

    async def async_block_till_done(self):
        """Block until all pending work is done."""
        # Wait for all pending tasks
        await asyncio.sleep(0)


@pytest.fixture
async def hass():
    """Return a mock Home Assistant instance."""
    return MockHomeAssistant()


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""

    return MockConfigEntry(
        domain="local_weather_forecast",
        data={
            "pressure_sensor": "sensor.test_pressure",
            "temperature_sensor": "sensor.test_temperature",
            "elevation": 314.0,
        },
        options={},
        entry_id="test_entry_id",
        title="Local Weather Forecast",
    )

