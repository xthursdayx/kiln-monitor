"""Shared base entity for Kiln Monitor platforms."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KilnDataCoordinator


class KilnEntity(CoordinatorEntity[KilnDataCoordinator]):
    """Base entity for all Kiln Monitor platforms.

    Provides a single shared device_info implementation so that the
    sensor and binary_sensor platforms always expose identical device
    metadata — including sw_version — to the device registry.
    """

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        data = self.coordinator.data or {}
        view = data.get("view", {})
        summary = data.get("summary", {})

        firmware = (
            self._get_nested(data, ("view", "status", "fw"))
            or self._get_nested(data, ("summary", "settings", "firmwareVersion"))
        )

        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.serial_number)},
            name=self.coordinator.kiln_name,
            manufacturer="Bartlett Instruments",
            model=(
                data.get("metadata", {}).get("product")
                or "KilnAid Kiln"
            ),
            serial_number=self.coordinator.serial_number,
            sw_version=firmware,
        )

    def _get_nested(self, data: object, path: tuple[str, ...]) -> object:
        """Safely resolve a nested dict path, returning None on any miss."""
        current = data
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current
