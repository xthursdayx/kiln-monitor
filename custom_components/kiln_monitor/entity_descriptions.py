"""Entity descriptions for Kiln Monitor."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import EntityCategory, UnitOfElectricCurrent, UnitOfTemperature, UnitOfElectricPotential


@dataclass(frozen=True, kw_only=True)
class KilnSensorDescription(SensorEntityDescription):
    """Describes Kiln Monitor sensor entity."""


@dataclass(frozen=True, kw_only=True)
class KilnBinarySensorDescription(BinarySensorEntityDescription):
    """Describes Kiln Monitor binary sensor entity."""


SENSOR_DESCRIPTIONS: tuple[KilnSensorDescription, ...] = (
    KilnSensorDescription(
        key="status",
        name="Status",
        icon="mdi:information-outline",
    ),
    KilnSensorDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        icon="mdi:thermometer",
    ),
    KilnSensorDescription(
        key="thermocouple_1",
        name="Thermocouple 1",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-lines",
    ),
    KilnSensorDescription(
        key="thermocouple_2",
        name="Thermocouple 2",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-lines",
    ),
    KilnSensorDescription(
        key="thermocouple_3",
        name="Thermocouple 3",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-lines",
    ),
    KilnSensorDescription(
        key="set_point",
        name="Set Point",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        icon="mdi:target",
    ),
    KilnSensorDescription(
        key="current_segment",
        name="Current Segment",
        icon="mdi:stairs",
    ),
    KilnSensorDescription(
        key="estimated_time_remaining",
        name="Estimated Time Remaining",
        icon="mdi:timer-sand",
    ),
    KilnSensorDescription(
        key="firing_time",
        name="Firing Time",
        icon="mdi:clock-outline",
    ),
    KilnSensorDescription(
        key="hold_remaining_time",
        name="Hold Remaining Time",
        icon="mdi:timer-outline",
    ),
    KilnSensorDescription(
        key="program_name",
        name="Program Name",
        icon="mdi:playlist-play",
    ),
    KilnSensorDescription(
        key="program_type",
        name="Program Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shape-outline",
    ),
    KilnSensorDescription(
        key="program_speed",
        name="Program Speed",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:speedometer",
    ),
    KilnSensorDescription(
        key="program_cone",
        name="Program Cone",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:triangle-outline",
    ),
    KilnSensorDescription(
        key="program_step_count",
        name="Program Step Count",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:format-list-numbered",
    ),
    KilnSensorDescription(
        key="board_temperature",
        name="Board Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-alert",
    ),
    KilnSensorDescription(
        key="amperage_1",
        name="Amperage 1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:current-ac",
    ),
    KilnSensorDescription(
        key="amperage_2",
        name="Amperage 2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:current-ac",
    ),
    KilnSensorDescription(
        key="amperage_3",
        name="Amperage 3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:current-ac",
    ),
    KilnSensorDescription(
        key="voltage_1",
        name="Voltage 1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sine-wave",
    ),
    KilnSensorDescription(
        key="voltage_2",
        name="Voltage 2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sine-wave",
    ),
    KilnSensorDescription(
        key="voltage_3",
        name="Voltage 3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sine-wave",
    ),
    KilnSensorDescription(
        key="supply_voltage",
        name="Supply Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:flash",
    ),
    KilnSensorDescription(
        key="no_load_voltage",
        name="No Load Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:flash-outline",
    ),
    KilnSensorDescription(
        key="full_load_voltage",
        name="Full Load Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:flash-alert",
    ),
    KilnSensorDescription(
        key="error_text",
        name="Error Text",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
    ),
    KilnSensorDescription(
        key="last_error_code",
        name="Last Error Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:numeric",
    ),
    KilnSensorDescription(
        key="firmware_version",
        name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    KilnSensorDescription(
        key="number_of_firings",
        name="Number of Firings",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
    ),
    KilnSensorDescription(
        key="zone_count",
        name="Zone Count",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:grid",
    ),
    KilnSensorDescription(
        key="firing_cost",
        name="Firing Cost",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:currency-usd",
    ),
    KilnSensorDescription(
        key="max_temperature",
        name="Max Temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-high",
    ),
    KilnSensorDescription(
        key="cooling_rate",
        name="Cooling Rate",
        icon="mdi:coolant-temperature",
    ),
    KilnSensorDescription(
        key="target_firing_curve",
        name="Target Firing Curve",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
    ),
)

BINARY_SENSOR_DESCRIPTIONS: tuple[KilnBinarySensorDescription, ...] = (
    KilnBinarySensorDescription(
        key="alarm_active",
        name="Alarm Active",
        icon="mdi:alarm-light",
    ),
    KilnBinarySensorDescription(
        key="cooling_active",
        name="Cooling Active",
        icon="mdi:snowflake-thermometer",
    ),
    KilnBinarySensorDescription(
        key="firing_active",
        name="Firing Active",
        icon="mdi:fire",
    ),
    KilnBinarySensorDescription(
        key="firing_complete",
        name="Firing Complete",
        icon="mdi:check-circle-outline",
    ),
    KilnBinarySensorDescription(
        key="kiln_fault",
        name="Kiln Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-octagon",
    ),
)