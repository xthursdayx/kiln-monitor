"""Binary sensor platform for Kiln Monitor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KilnDataCoordinator
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
    entities: list[KilnBinarySensor] = []

    for coordinator in coordinators:
        for description in BINARY_SENSOR_DESCRIPTIONS:
            entities.append(KilnBinarySensor(coordinator, description))

    async_add_entities(entities)


class KilnBinarySensor(CoordinatorEntity[KilnDataCoordinator], BinarySensorEntity):
    """Representation of a kiln binary sensor."""

    entity_description: KilnBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KilnDataCoordinator,
        description: KilnBinarySensorDescription,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}_{description.key}"
        self._attr_name = description.name
        self._attr_device_class = description.device_class

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.serial_number)},
            name=self.coordinator.kiln_name,
            manufacturer="Bartlett Instruments",
            model="KilnAid Kiln",
            serial_number=self.coordinator.serial_number,
        )

    @property
    def is_on(self) -> bool:
        """Return binary state."""
        status = self.coordinator.data.get("status", {})
        view = self.coordinator.data.get("view", {})

        mode = str(
            status.get("mode")
            or status.get("kilnStatus")
            or ""
        ).lower()

        alarm = str(
            status.get("alarmAbbreviation")
            or view.get("status", {}).get("alarm")
            or ""
        ).upper()

        error_text = str(
            status.get("errorText")
            or view.get("status", {}).get("error", {}).get("err_text")
            or ""
        )

        error_num = view.get("status", {}).get("error", {}).get("err_num")
        last_err = view.get("status", {}).get("diag", {}).get("last_err")

        if self.entity_description.key == "firing_active":
            return "firing" in mode
        if self.entity_description.key == "cooling_active":
            return "cooling" in mode
        if self.entity_description.key == "firing_complete":
            return "complete" in mode
        if self.entity_description.key == "alarm_active":
            return alarm not in {"", "OFF"}
        if self.entity_description.key == "kiln_fault":
            if error_text and error_text != "No Errors":
                return True
            if error_num not in (None, 255):
                return True
            if last_err not in (None, 255):
                return True
            return False

        return False