"""Sensor platform for Kiln Monitor."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KilnDataCoordinator
from .entity_descriptions import KilnSensorDescription, SENSOR_DESCRIPTIONS


def _safe_float(value: Any) -> float | None:
    """Convert a value to float if possible."""
    try:
        if value in (None, "", "None", "null"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    """Convert a value to int if possible."""
    try:
        if value in (None, "", "None", "null"):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _clean_string(value: Any) -> str | None:
    """Return a cleaned string or None."""
    if value in (None, "", "None", "null"):
        return None
    text = str(value).strip()
    return text or None


def _get_nested(data: dict[str, Any], *path: str) -> Any:
    """Safely walk nested dictionaries."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first(*values: Any) -> Any:
    """Return the first non-empty-ish value."""
    for value in values:
        if value not in (None, "", "None", "null"):
            return value
    return None


def _parse_duration_to_timedelta(value: Any) -> timedelta | None:
    """Parse a Bartlett-style duration string to timedelta.

    Supports:
    - HH:MM
    - H:MM
    - HH:MM:SS
    - numeric minutes/hours strings are not assumed
    """
    text = _clean_string(value)
    if not text:
        return None

    parts = text.split(":")
    try:
        if len(parts) == 2:
            hours = int(parts[0])
            minutes = int(parts[1])
            return timedelta(hours=hours, minutes=minutes)

        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except ValueError:
        return None

    return None


def _normalize_program_steps(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized program steps from whichever payload is available."""
    program_steps = _first(
        _get_nested(data, "program", "steps"),
        _get_nested(data, "view", "program", "steps"),
        _get_nested(data, "status", "unformattedProgramSegments"),
        _get_nested(data, "view", "status", "unformattedProgramSegments"),
        _get_nested(data, "unformattedProgramSegments"),
    )

    if not isinstance(program_steps, list):
        return []

    normalized: list[dict[str, Any]] = []

    for raw_step in program_steps:
        if not isinstance(raw_step, dict):
            continue

        target = _safe_float(raw_step.get("t"))
        ramp = _safe_float(raw_step.get("rt"))

        hold_hr = _safe_int(raw_step.get("hr")) or 0
        hold_mn = _safe_int(raw_step.get("mn")) or 0

        normalized.append(
            {
                "num": _safe_int(raw_step.get("num")),
                "t": target,
                "rt": ramp,
                "hold_hours": hold_hr,
                "hold_minutes": hold_mn,
            }
        )

    return normalized


def _firing_started_at(data: dict[str, Any]) -> datetime:
    """Estimate absolute firing start time using elapsed firing time."""
    firing_time_raw = _first(
        _get_nested(data, "status", "firing_time"),
        _get_nested(data, "status", "fire_time"),
        _get_nested(data, "view", "status", "firing_time"),
        _get_nested(data, "view", "status", "fire_time"),
        _get_nested(data, "view", "status", "diag", "fire_time"),
        data.get("firing_time"),
    )

    elapsed = _parse_duration_to_timedelta(firing_time_raw)
    now = datetime.now(UTC)

    if elapsed is None:
        return now

    return now - elapsed


def _build_target_curve(data: dict[str, Any]) -> str | None:
    """Build absolute timestamped target firing curve JSON."""
    steps = _normalize_program_steps(data)
    if not steps:
        return None

    start_time = _firing_started_at(data)

    # Best available starting temperature.
    start_temp = _safe_float(
        _first(
            _get_nested(data, "status", "temperature"),
            _get_nested(data, "view", "status", "temperature"),
            data.get("temperature"),
            _get_nested(data, "view", "status", "t1"),
        )
    )
    if start_temp is None:
        start_temp = 70.0

    points: list[dict[str, Any]] = []
    current_time = start_time
    current_temp = start_temp

    points.append(
        {
            "time": current_time.isoformat(),
            "temp": round(current_temp, 2),
        }
    )

    for step in steps:
        target_temp = step.get("t")
        ramp_rate = step.get("rt")
        hold_hours = step.get("hold_hours", 0)
        hold_minutes = step.get("hold_minutes", 0)

        if target_temp is None:
            continue

        # Ramp segment
        if ramp_rate and ramp_rate > 0 and target_temp != current_temp:
            delta = abs(target_temp - current_temp)
            ramp_hours = delta / ramp_rate
            current_time += timedelta(hours=ramp_hours)
            current_temp = target_temp

            points.append(
                {
                    "time": current_time.isoformat(),
                    "temp": round(current_temp, 2),
                }
            )
        else:
            # If no usable ramp rate, snap directly to target at current time.
            current_temp = target_temp
            points.append(
                {
                    "time": current_time.isoformat(),
                    "temp": round(current_temp, 2),
                }
            )

        # Hold segment — this is the subtle accuracy fix:
        # honor BOTH hr and mn.
        hold_delta = timedelta(hours=hold_hours, minutes=hold_minutes)
        if hold_delta.total_seconds() > 0:
            current_time += hold_delta
            points.append(
                {
                    "time": current_time.isoformat(),
                    "temp": round(current_temp, 2),
                }
            )

    return json.dumps(points, separators=(",", ":"))


def _extract_state(data: dict[str, Any], key: str) -> Any:
    """Extract sensor state from coordinator data."""

    status = data.get("status", {})
    view = data.get("view", {})
    view_status = view.get("status", {}) if isinstance(view, dict) else {}
    view_diag = view_status.get("diag", {}) if isinstance(view_status, dict) else {}
    view_error = view_status.get("error", {}) if isinstance(view_status, dict) else {}

    if key == "status":
        return _first(
            status.get("mode"),
            status.get("kilnStatus"),
            view_status.get("mode"),
            view_status.get("status"),
        )

    if key == "temperature":
        return _safe_float(
            _first(
                status.get("temperature"),
                view_status.get("temperature"),
                view_status.get("t1"),
            )
        )

    if key == "thermocouple_1":
        return _safe_float(_first(status.get("t1"), view_status.get("t1")))

    if key == "thermocouple_2":
        return _safe_float(_first(status.get("t2"), view_status.get("t2")))

    if key == "thermocouple_3":
        return _safe_float(_first(status.get("t3"), view_status.get("t3")))

    if key == "set_point":
        return _safe_float(
            _first(
                status.get("setPoint"),
                status.get("set_point"),
                view_status.get("set_point"),
                view_status.get("setPoint"),
            )
        )

    if key == "current_segment":
        return _first(
            status.get("segmentName"),
            status.get("currentSegment"),
            view_status.get("segment_name"),
            view_status.get("segment"),
        )

    if key == "estimated_time_remaining":
        raw = _first(
            status.get("estimated_time_remaining"),
            status.get("etr"),
            view_status.get("etr"),
            view_status.get("estimated_time_remaining"),
        )
        return raw if raw not in (None, "") else "0"

    if key == "firing_time":
        return _first(
            status.get("firing_time"),
            status.get("fire_time"),
            view_diag.get("fire_time"),
            "0:00",
        )

    if key == "hold_remaining_time":
        raw = _first(
            status.get("hold_remaining_time"),
            status.get("holdRemaining"),
            view_status.get("hold_remaining"),
            "0:00",
        )
        return raw if raw not in (None, "") else "0:00"

    if key == "program_name":
        return _first(
            status.get("programName"),
            data.get("programName"),
            view.get("program_name"),
        )

    if key == "program_type":
        return _first(
            status.get("programType"),
            view_diag.get("program_type"),
            _get_nested(data, "program", "type"),
        )

    if key == "program_speed":
        return _first(
            status.get("programSpeed"),
            view_diag.get("program_speed"),
            _get_nested(data, "program", "speed"),
        )

    if key == "program_cone":
        return _first(
            status.get("programCone"),
            view_diag.get("program_cone"),
            _get_nested(data, "program", "cone"),
        )

    if key == "program_step_count":
        steps = _normalize_program_steps(data)
        return len(steps) if steps else 0

    if key == "board_temperature":
        return _safe_float(
            _first(
                status.get("board_temperature"),
                view_diag.get("board_temp"),
                view_diag.get("board_temperature"),
            )
        )

    if key == "amperage_1":
        return _safe_float(_first(status.get("a1"), view_diag.get("a1"), view_diag.get("amp_1")))

    if key == "amperage_2":
        return _safe_float(_first(status.get("a2"), view_diag.get("a2"), view_diag.get("amp_2")))

    if key == "amperage_3":
        return _safe_float(_first(status.get("a3"), view_diag.get("a3"), view_diag.get("amp_3")))

    if key == "voltage_1":
        return _safe_float(_first(status.get("v1"), view_diag.get("v1"), view_diag.get("voltage_1")))

    if key == "voltage_2":
        return _safe_float(_first(status.get("v2"), view_diag.get("v2"), view_diag.get("voltage_2")))

    if key == "voltage_3":
        return _safe_float(_first(status.get("v3"), view_diag.get("v3"), view_diag.get("voltage_3")))

    if key == "supply_voltage":
        return _safe_float(
            _first(
                status.get("supplyVoltage"),
                view_diag.get("supply_v"),
                view_diag.get("supply_voltage"),
            )
        )

    if key == "no_load_voltage":
        return _safe_float(
            _first(
                status.get("noLoadVoltage"),
                view_diag.get("nlv"),
                view_diag.get("no_load_voltage"),
            )
        )

    if key == "full_load_voltage":
        return _safe_float(
            _first(
                status.get("fullLoadVoltage"),
                view_diag.get("flv"),
                view_diag.get("full_load_voltage"),
            )
        )

    if key == "error_text":
        return _first(
            status.get("errorText"),
            view_error.get("err_text"),
            "No Errors",
        )

    if key == "last_error_code":
        return _first(
            status.get("lastErrorCode"),
            view_diag.get("last_err"),
            view_error.get("err_num"),
        )

    if key == "firmware_version":
        return _first(
            status.get("firmwareVersion"),
            view_diag.get("fw"),
            view_diag.get("firmware"),
        )

    if key == "number_of_firings":
        return _safe_int(
            _first(
                data.get("number_firings"),
                status.get("number_firings"),
                view_diag.get("num_fires"),
            )
        )

    if key == "zone_count":
        return _safe_int(
            _first(
                status.get("zoneCount"),
                view_diag.get("zones"),
                view_diag.get("zone_count"),
            )
        )

    if key == "firing_cost":
        return _safe_float(
            _first(
                status.get("firingCost"),
                view_diag.get("firing_cost"),
            )
        )

    if key == "max_temperature":
        return _safe_float(
            _first(
                status.get("maxTemperature"),
                view_diag.get("max_temp"),
            )
        )

    if key == "cooling_rate":
        # Keep this if your coordinator already stores/derives it;
        # otherwise leave unavailable until your current cooling-rate implementation supplies it.
        return _safe_float(
            _first(
                data.get("cooling_rate"),
                status.get("cooling_rate"),
                view_status.get("cooling_rate"),
            )
        )

    if key == "target_firing_curve":
        return _build_target_curve(data)

    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up kiln sensors from a config entry."""
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

    @property
    def available(self) -> bool:
        """Return availability."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def native_value(self) -> Any:
        """Return sensor state."""
        if not self.coordinator.data:
            return None
        return _extract_state(self.coordinator.data, self.entity_description.key)

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
    def entity_registry_visible_default(self) -> bool:
        """Hide JSON curve sensor by default."""
        if self.entity_description.key == "target_firing_curve":
            return False
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes for complex sensors."""
        if not self.coordinator.data:
            return None

        if self.entity_description.key == "target_firing_curve":
            raw = self.native_value
            if not raw:
                return None

            try:
                points = json.loads(raw)
            except (TypeError, ValueError):
                return None

            return {
                "point_count": len(points),
                "program_step_count": len(_normalize_program_steps(self.coordinator.data)),
                "firing_started_at": _firing_started_at(self.coordinator.data).isoformat(),
            }

        return None