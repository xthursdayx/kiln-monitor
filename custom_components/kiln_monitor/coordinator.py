"""Coordinator for Kiln Monitor."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KilnAPI
from .const import (
    DEFAULT_UPDATE_INTERVAL,
    IDLE_SUMMARY_REFRESH_EVERY,
    IDLE_VIEW_REFRESH_EVERY,
)

_LOGGER = logging.getLogger(__name__)


class KilnDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for one kiln."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: KilnAPI,
        kiln_info: dict[str, Any],
        update_interval_minutes: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize coordinator."""
        self.api = api
        self.kiln_id: str = kiln_info["external_id"]
        self.serial_number: str = kiln_info["serial_number"]
        self.kiln_name: str = kiln_info.get("name", "Kiln")
        self._summary_cache: dict[str, Any] = kiln_info.get("initial_summary", {})
        self._view_cache: dict[str, Any] = {}
        self._summary_idle_counter = 0
        self._view_idle_counter = 0

        super().__init__(
            hass,
            _LOGGER,
            name=f"kiln_monitor_{self.kiln_name}",
            update_interval=timedelta(minutes=update_interval_minutes),
        )

    def update_interval_minutes(self, minutes: int) -> None:
        """Update polling interval."""
        self.update_interval = timedelta(minutes=minutes)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch merged data."""
        try:
            status = await self.api.fetch_status(self.kiln_id)

            mode = str(status.get("mode", "")).lower()
            active = "firing" in mode or "cooling" in mode

            need_summary = not self._summary_cache or self._summary_idle_counter >= IDLE_SUMMARY_REFRESH_EVERY
            if need_summary:
                self._summary_cache = await self.api.fetch_summary(self.kiln_id)
                self._summary_idle_counter = 0
            else:
                self._summary_idle_counter += 1

            need_view = not self._view_cache or active or self._view_idle_counter >= IDLE_VIEW_REFRESH_EVERY
            if need_view:
                try:
                    self._view_cache = await self.api.fetch_view(self.serial_number)
                    self._view_idle_counter = 0
                except Exception as exc:
                    _LOGGER.debug(
                        "View fetch failed for %s this cycle: %s",
                        self.kiln_name,
                        exc,
                    )
                    if active and not self._view_cache:
                        raise
            else:
                self._view_idle_counter += 1

            summary = self._summary_cache
            view = self._view_cache

            self.kiln_name = (
                status.get("name")
                or summary.get("list", {}).get("name")
                or summary.get("settings", {}).get("name")
                or view.get("name")
                or self.kiln_name
            )

            temperature_scale = (
                status.get("temperatureScale")
                or summary.get("list", {}).get("temperatureScale")
                or summary.get("settings", {}).get("temperatureScale")
                or view.get("config", {}).get("t_scale")
                or "F"
            )

            return {
                "summary": summary,
                "status": status,
                "view": view,
                "metadata": {
                    "external_id": self.kiln_id,
                    "serial_number": self.serial_number,
                    "name": self.kiln_name,
                    "temperature_scale": temperature_scale,
                },
            }

        except Exception as exc:
            raise UpdateFailed(f"Failed to update {self.kiln_name}: {exc}") from exc