"""Binary sensor platform for Kiln Monitor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import KilnDataCoordinator
from .entity import KilnEntity
from .entity_descriptions import (
    BINARY_SENSOR_DESCRIPTIONS,
    KilnBinarySensorDescription,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up kiln binary sensors."""
    coordinators: list[KilnDataCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KilnBinarySensor(coordinator, description)
        for coordinator in coordinators
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class KilnBinarySensor(KilnEntity, BinarySensorEntity):
    """Representation of a kiln binary sensor."""

    entity_description: KilnBinarySensorDescription

    def __init__(
        self,
        coordinator: KilnDataCoordinator,
        description: KilnBinarySensorDescription,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}_{description.key}"
        self._attr_device_class = description.device_class
        # _attr_name intentionally omitted — derived from entity_description.name
        # via _attr_has_entity_name=True inherited from KilnEntity.

    @property
    def is_on(self) -> bool:
        """Return binary state."""
        data = self.coordinator.data or {}
        status = data.get("status", {})
        view = data.get("view", {})

        mode = str(
            status.get("mode")
            or status.get("kilnStatus")
            or ""
        ).strip().lower()

        alarm = str(
            status.get("alarmAbbreviation")
            or view.get("status", {}).get("alarm")
            or ""
        ).strip().upper()

        error_text = str(
            status.get("errorText")
            or view.get("status", {}).get("error", {}).get("err_text")
            or ""
        ).strip()

        key = self.entity_description.key

        if key == "firing_active":
            return "firing" in mode

        if key == "cooling_active":
            return "cooling" in mode

        if key == "firing_complete":
            return "complete" in mode

        if key == "alarm_active":
            return alarm not in {"", "OFF"}

        if key == "kiln_fault":
            return error_text not in {"", "No Errors"}

        return False
