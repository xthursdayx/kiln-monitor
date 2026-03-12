from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_UPDATE_INTERVAL


class KilnCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, api, kiln):

        super().__init__(
            hass,
            None,
            name="kiln_monitor",
            update_interval=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
        )

        self.api = api
        self.kiln = kiln
        self.view_cache = None

    async def _async_update_data(self):

        status = await self.api.fetch_status(self.kiln["externalId"])

        if status["mode"] == "Firing" or self.view_cache is None:
            self.view_cache = await self.api.fetch_view(self.kiln["serialNumber"])

        return {
            "status": status,
            "view": self.view_cache,
        }