from homeassistant.components.sensor import SensorEntity

from .entity_descriptions import SENSORS


async def async_setup_entry(hass, entry, async_add_entities):

    coordinator = hass.data["kiln_monitor"][entry.entry_id]

    sensors = []

    for description in SENSORS:
        sensors.append(KilnSensor(coordinator, description))

    async_add_entities(sensors)


class KilnSensor(SensorEntity):

    def __init__(self, coordinator, description):

        self.coordinator = coordinator
        self.entity_description = description

    @property
    def native_value(self):

        key = self.entity_description.key

        if key in self.coordinator.data["status"]:
            return self.coordinator.data["status"][key]

        return None