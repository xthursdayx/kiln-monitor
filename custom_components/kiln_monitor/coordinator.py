from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class KilnCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, api, kiln):
        super().__init__(
            hass,
            _LOGGER,
            name="kiln_monitor",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        self.api = api
        self.kiln = kiln
        self.view_cache = None
        self.view_refresh_counter = 0

    async def _async_update_data(self):

        status = await self.api.fetch_status(self.kiln["external_id"])
        summary = await self.api.fetch_summary(self.kiln["external_id"])

        if status["mode"] == "Firing" or self.view_cache is None:
            self.view_cache = await self.api.fetch_view(self.kiln["serial_number"])

        data = {
            "status": status,
            "summary": summary,
            "view": self.view_cache,
        }

        return data