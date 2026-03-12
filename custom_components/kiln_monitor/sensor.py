"""Sensor platform for Kiln Monitor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KilnDataCoordinator
from .entity_descriptions import KilnSensorDescription, SENSOR_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up kiln sensors."""
    coordinators: list[KilnDataCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities: list[KilnSensor] = []

    for coordinator in coordinators:
        for description in SENSOR_DESCRIPTIONS:
            entities.append(KilnSensor(coordinator, description))

    async_add_entities(entities)


class KilnSensor(CoordinatorEntity[KilnDataCoordinator], SensorEntity):
    """Representation of a kiln sensor."""

    entity_description: KilnSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KilnDataCoordinator,
        description: KilnSensorDescription,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}_{description.key}"
        self._attr_name = description.name
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = description.entity_registry_enabled_default

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.serial_number)},
            name=self.coordinator.kiln_name,
            manufacturer="Bartlett Instruments",
            model="KilnAid Kiln",
            serial_number=self.coordinator.serial_number,
            sw_version=(
                self._get_nested(self.coordinator.data, ("view", "status", "fw"))
                or self._get_nested(self.coordinator.data, ("summary", "settings", "firmwareVersion"))
            ),
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return native unit."""
        if self.entity_description.dynamic_temperature_unit:
            scale = self._get_nested(
                self.coordinator.data,
                ("metadata", "temperature_scale"),
            )
            return UnitOfTemperature.CELSIUS if scale == "C" else UnitOfTemperature.FAHRENHEIT

        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self) -> Any:
        """Return current value."""
        value = self._resolve_value()
        if value is None:
            return None

        if self.entity_description.scale_divisor:
            value = float(value) / self.entity_description.scale_divisor

        if self.entity_description.value_type is float:
            return float(value)
        if self.entity_description.value_type is int:
            return int(value)
        return str(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.key == "program_name":
            return {
                "unformatted_program_segments": self._get_nested(
                    self.coordinator.data,
                    ("status", "unformattedProgramSegments"),
                ),
                "program_segments": self._get_nested(
                    self.coordinator.data,
                    ("status", "programSegments"),
                ),
                "program_steps": self._get_nested(
                    self.coordinator.data,
                    ("view", "program", "steps"),
                ),
            }

        if self.entity_description.key == "kiln_status":
            return {
                "external_id": self._get_nested(
                    self.coordinator.data,
                    ("metadata", "external_id"),
                ),
                "serial_number": self._get_nested(
                    self.coordinator.data,
                    ("metadata", "serial_number"),
                ),
                "temperature_scale": self._get_nested(
                    self.coordinator.data,
                    ("metadata", "temperature_scale"),
                ),
            }

        return None

    def _resolve_value(self) -> Any:
        """Resolve primary or fallback path."""
        value = self._get_nested(self.coordinator.data, self.entity_description.path)
        if value is not None:
            return value

        for path in self.entity_description.fallback_paths:
            value = self._get_nested(self.coordinator.data, path)
            if value is not None:
                return value

        return None

    def _get_nested(self, data: Any, path: tuple[str, ...]) -> Any:
        """Safely resolve nested path."""
        current = data
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current