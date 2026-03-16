"""Sensor platform for Kiln Monitor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import KilnDataCoordinator
from .entity import KilnEntity
from .entity_descriptions import KilnSensorDescription, SENSOR_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up kiln sensors."""
    coordinators: list[KilnDataCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KilnSensor(coordinator, description)
        for coordinator in coordinators
        for description in SENSOR_DESCRIPTIONS
    )


class KilnSensor(KilnEntity, SensorEntity):
    """Representation of a kiln sensor."""

    entity_description: KilnSensorDescription

    def __init__(
        self,
        coordinator: KilnDataCoordinator,
        description: KilnSensorDescription,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        # unique_id uses the serial number so it survives kiln renames.
        self._attr_unique_id = f"{coordinator.serial_number}_{description.key}"
        # _attr_name is intentionally not set here.  With _attr_has_entity_name=True
        # (inherited from KilnEntity), HA derives the entity name automatically
        # from entity_description.name — setting it again would be redundant.

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return native unit."""
        if self.entity_description.dynamic_temperature_unit:
            scale = self._get_nested(
                self.coordinator.data,
                ("metadata", "temperature_scale"),
            )
            return (
                UnitOfTemperature.CELSIUS
                if scale == "C"
                else UnitOfTemperature.FAHRENHEIT
            )

        if self.entity_description.dynamic_temperature_rate_unit:
            scale = self._get_nested(
                self.coordinator.data,
                ("metadata", "temperature_scale"),
            )
            return "°C/h" if scale == "C" else "°F/h"

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

        text_value = str(value).strip()
        return self._normalize_text_value(text_value)

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

        if self.entity_description.key == "target_firing_curve":
            target_curve = self._get_nested(
                self.coordinator.data,
                ("metadata", "target_curve"),
            )
            if not isinstance(target_curve, dict):
                return None

            return {
                "program_name": target_curve.get("program_name"),
                "temperature_scale": target_curve.get("temperature_scale"),
                "source": target_curve.get("source"),
                "start_temperature": target_curve.get("start_temperature"),
                "segment_count": target_curve.get("segment_count"),
                "segments": target_curve.get("segments"),
                "target_points": target_curve.get("target_points"),
            }

        return None

    def _normalize_text_value(self, value: str) -> str:
        """Normalize string-like sensor values to a canonical zero form."""
        zero_like_map = {
            "estimated_time_remaining": "0h 0m",
            "hold_remaining_time": "0:00",
            "firing_time": "0:00",
        }

        if self.entity_description.key in zero_like_map:
            if value in {"0", "0:00", "0h 0m", "00:00"}:
                return zero_like_map[self.entity_description.key]

        return value

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
