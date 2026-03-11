from homeassistant.components.sensor import SensorEntityDescription


SENSORS = [
    SensorEntityDescription(
        key="temperature",
        name="Temperature",
    ),
    SensorEntityDescription(
        key="t1",
        name="Thermocouple 1",
    ),
    SensorEntityDescription(
        key="t2",
        name="Thermocouple 2",
    ),
    SensorEntityDescription(
        key="t3",
        name="Thermocouple 3",
    ),
]