"""Entity descriptions for Kiln Monitor."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory


@dataclass(frozen=True, kw_only=True)
class KilnSensorDescription(SensorEntityDescription):
    """Description of a kiln sensor."""

    path: tuple[str, ...]
    fallback_paths: tuple[tuple[str, ...], ...] = ()
    value_type: type = str
    dynamic_temperature_unit: bool = False
    dynamic_temperature_rate_unit: bool = False
    scale_divisor: float | None = None


@dataclass(frozen=True, kw_only=True)
class KilnBinarySensorDescription(BinarySensorEntityDescription):
    """Description of a kiln binary sensor."""


SENSOR_DESCRIPTIONS: tuple[KilnSensorDescription, ...] = (
    KilnSensorDescription(
        key="temperature",
        name="Temperature",
        path=("status", "t1"),
        fallback_paths=(("summary", "list", "temperature"),),
        value_type=float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        dynamic_temperature_unit=True,
    ),
    KilnSensorDescription(
        key="cooling_rate",
        name="Cooling Rate",
        path=("metadata", "cooling_rate_per_hour"),
        value_type=float,
        state_class=SensorStateClass.MEASUREMENT,
        dynamic_temperature_rate_unit=True,
    ),
    KilnSensorDescription(
        key="target_firing_curve",
        name="Target Firing Curve",
        path=("metadata", "target_curve_summary"),
        value_type=str,
    ),
    KilnSensorDescription(
        key="thermocouple_1",
        name="Thermocouple 1",
        path=("status", "t1"),
        value_type=float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        dynamic_temperature_unit=True,
    ),
    KilnSensorDescription(
        key="thermocouple_2",
        name="Thermocouple 2",
        path=("status", "t2"),
        value_type=float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        dynamic_temperature_unit=True,
    ),
    KilnSensorDescription(
        key="thermocouple_3",
        name="Thermocouple 3",
        path=("status", "t3"),
        value_type=float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        dynamic_temperature_unit=True,
    ),
    KilnSensorDescription(
        key="set_point",
        name="Set Point",
        path=("status", "setPoint"),
        fallback_paths=(("view", "status", "firing", "set_pt"),),
        value_type=float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        dynamic_temperature_unit=True,
    ),
    KilnSensorDescription(
        key="kiln_status",
        name="Status",
        path=("status", "mode"),
        fallback_paths=(("summary", "list", "kilnStatus"),),
        value_type=str,
    ),
    KilnSensorDescription(
        key="program_name",
        name="Program Name",
        path=("status", "programName"),
        fallback_paths=(("view", "program", "name"),),
        value_type=str,
    ),
    KilnSensorDescription(
        key="current_segment",
        name="Current Segment",
        path=("status", "segment"),
        fallback_paths=(
            ("view", "status", "firing", "step"),
            ("view", "status", "firing", "segment"),
        ),
        value_type=str,
    ),
    KilnSensorDescription(
        key="estimated_time_remaining",
        name="Estimated Time Remaining",
        path=("status", "estimatedTimeRemaining"),
        fallback_paths=(
            ("status", "etr"),
            ("view", "status", "firing", "etr"),
        ),
        value_type=str,
    ),
    KilnSensorDescription(
        key="hold_remaining_time",
        name="Hold Remaining Time",
        path=("status", "holdRemainingTime"),
        fallback_paths=(("view", "status", "firing", "hold_remaining"),),
        value_type=str,
    ),
    KilnSensorDescription(
        key="firing_time",
        name="Firing Time",
        path=("status", "firingTime"),
        fallback_paths=(("view", "status", "firing", "fire_time"),),
        value_type=str,
    ),
    # max_temperature is a running high-water mark for the current firing,
    # not an instantaneous measurement.  Using MEASUREMENT here would cause
    # HA's statistics engine to compute misleading min/mean/max over time.
    # No state_class is set; long-term stats are tracked via the recorder
    # include in configuration.yaml instead.
    KilnSensorDescription(
        key="max_temperature",
        name="Max Temperature",
        path=("view", "status", "firing", "max_temp"),
        fallback_paths=(("status", "maxTemperature"),),
        value_type=float,
        device_class=SensorDeviceClass.TEMPERATURE,
        dynamic_temperature_unit=True,
        # Not DIAGNOSTIC — this is a primary firing outcome metric that
        # is actively used in automations and summary displays.
    ),
    # firing_cost is also a primary firing outcome.  Keeping it visible
    # (not DIAGNOSTIC) so it appears on the device card without expanding.
    KilnSensorDescription(
        key="firing_cost",
        name="Firing Cost",
        path=("view", "status", "firing", "cost"),
        fallback_paths=(("status", "cost"),),
        value_type=float,
        # No entity_registry_enabled_default=False so it is visible by default.
    ),
    KilnSensorDescription(
        key="firmware_version",
        name="Firmware Version",
        path=("view", "status", "fw"),
        fallback_paths=(("summary", "settings", "firmwareVersion"),),
        value_type=str,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KilnSensorDescription(
        key="num_firings",
        name="Number of Firings",
        path=("summary", "settings", "numFirings"),
        fallback_paths=(
            ("view", "status", "num_fire"),
            ("view", "firings_count"),
            ("status", "number_firings"),
        ),
        value_type=int,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KilnSensorDescription(
        key="num_zones",
        name="Zone Count",
        path=("status", "numZones"),
        fallback_paths=(
            ("summary", "settings", "numZones"),
            ("view", "config", "num_zones"),
            ("view", "config", "zones"),
        ),
        value_type=int,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KilnSensorDescription(
        key="error_text",
        name="Error Text",
        path=("status", "errorText"),
        fallback_paths=(("view", "status", "error", "err_text"),),
        value_type=str,
    ),
    KilnSensorDescription(
        key="error_number",
        name="Error Number",
        path=("view", "status", "error", "err_num"),
        value_type=int,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KilnSensorDescription(
        key="board_temperature",
        name="Board Temperature",
        path=("view", "status", "diag", "board_t"),
        fallback_paths=(("view", "status", "board_t"),),
        value_type=float,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        dynamic_temperature_unit=True,
    ),
    KilnSensorDescription(
        key="amperage_1",
        name="Amperage 1",
        path=("view", "status", "diag", "a1"),
        value_type=float,
        native_unit_of_measurement="A",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KilnSensorDescription(
        key="amperage_2",
        name="Amperage 2",
        path=("view", "status", "diag", "a2"),
        value_type=float,
        native_unit_of_measurement="A",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KilnSensorDescription(
        key="amperage_3",
        name="Amperage 3",
        path=("view", "status", "diag", "a3"),
        value_type=float,
        native_unit_of_measurement="A",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KilnSensorDescription(
        key="voltage_1",
        name="Voltage 1",
        path=("view", "status", "diag", "v1"),
        value_type=float,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        scale_divisor=10,
    ),
    KilnSensorDescription(
        key="voltage_2",
        name="Voltage 2",
        path=("view", "status", "diag", "v2"),
        value_type=float,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        scale_divisor=10,
    ),
    KilnSensorDescription(
        key="voltage_3",
        name="Voltage 3",
        path=("view", "status", "diag", "v3"),
        value_type=float,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        scale_divisor=10,
    ),
    KilnSensorDescription(
        key="supply_voltage",
        name="Supply Voltage",
        path=("view", "status", "diag", "vs"),
        value_type=float,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        scale_divisor=10,
    ),
    KilnSensorDescription(
        key="no_load_voltage",
        name="No Load Voltage",
        path=("view", "status", "diag", "nl"),
        value_type=float,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KilnSensorDescription(
        key="full_load_voltage",
        name="Full Load Voltage",
        path=("view", "status", "diag", "fl"),
        value_type=float,
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KilnSensorDescription(
        key="last_error_code",
        name="Last Error Code",
        path=("view", "status", "diag", "last_err"),
        value_type=int,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KilnSensorDescription(
        key="program_type",
        name="Program Type",
        path=("view", "program", "type"),
        value_type=str,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KilnSensorDescription(
        key="program_speed",
        name="Program Speed",
        path=("view", "program", "speed"),
        value_type=str,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KilnSensorDescription(
        key="program_cone",
        name="Program Cone",
        path=("view", "program", "cone"),
        value_type=str,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KilnSensorDescription(
        key="program_steps_count",
        name="Program Step Count",
        path=("view", "program", "num_steps"),
        fallback_paths=(("metadata", "target_curve", "segment_count"),),
        value_type=int,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

BINARY_SENSOR_DESCRIPTIONS: tuple[KilnBinarySensorDescription, ...] = (
    KilnBinarySensorDescription(key="firing_active", name="Firing Active"),
    KilnBinarySensorDescription(key="cooling_active", name="Cooling Active"),
    KilnBinarySensorDescription(key="firing_complete", name="Firing Complete"),
    KilnBinarySensorDescription(key="alarm_active", name="Alarm Active"),
    KilnBinarySensorDescription(key="kiln_fault", name="Kiln Fault"),
)
