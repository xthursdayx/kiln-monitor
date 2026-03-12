from homeassistant.components.sensor import SensorEntity


async def async_setup_entry(hass, entry, async_add_entities):

    coordinator = hass.data["kiln_monitor"][entry.entry_id]

    sensors = [
        KilnTemperatureSensor(coordinator),
    ]

    async_add_entities(sensors)


class KilnTemperatureSensor(SensorEntity):

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "Kiln Temperature"

    @property
    def native_value(self):
        return self.coordinator.data["status"]["t1"]