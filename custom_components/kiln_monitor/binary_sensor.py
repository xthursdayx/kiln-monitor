from homeassistant.components.binary_sensor import BinarySensorEntity


async def async_setup_entry(hass, entry, async_add_entities):

    coordinator = hass.data["kiln_monitor"][entry.entry_id]

    async_add_entities([
        KilnFiringSensor(coordinator),
        KilnFaultSensor(coordinator)
    ])


class KilnFiringSensor(BinarySensorEntity):

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "Kiln Firing"

    @property
    def is_on(self):
        return self.coordinator.data["status"]["mode"] == "Firing"


class KilnFaultSensor(BinarySensorEntity):

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "Kiln Fault"

    @property
    def is_on(self):
        return self.coordinator.data["status"]["errorText"] != "No Errors"