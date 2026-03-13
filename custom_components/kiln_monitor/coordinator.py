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
        self._consecutive_view_failures = 0

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
        """Fetch merged data.

        Important behavior:
        - status is primary
        - summary/view are best-effort and cached
        - if status temporarily fails after initial success, keep last good data
          so entities do not flap unavailable every poll
        """
        previous_data = self.data if isinstance(self.data, dict) else None

        # Status is primary live data, but if we already have previous data,
        # keep serving it instead of going unavailable on a transient failure.
        try:
            status = await self.api.fetch_status(self.kiln_id)
        except Exception as exc:
            if previous_data:
                _LOGGER.warning(
                    "Status update failed for %s; keeping previous data: %s",
                    self.kiln_name,
                    exc,
                )
                return previous_data
            raise UpdateFailed(f"Failed to update {self.kiln_name}: {exc}") from exc

        mode = str(status.get("mode", "")).lower()
        active = "firing" in mode or "cooling" in mode

        # Summary: refresh occasionally, otherwise reuse cache.
        need_summary = (
            not self._summary_cache
            or self._summary_idle_counter >= IDLE_SUMMARY_REFRESH_EVERY
        )
        if need_summary:
            try:
                self._summary_cache = await self.api.fetch_summary(self.kiln_id)
                self._summary_idle_counter = 0
                _LOGGER.debug("Refreshed summary for %s", self.kiln_name)
            except Exception as exc:
                _LOGGER.debug(
                    "Summary refresh failed for %s, using cache: %s",
                    self.kiln_name,
                    exc,
                )
                self._summary_idle_counter += 1
        else:
            self._summary_idle_counter += 1

        # View: refresh while active, on first load, or occasionally while idle.
        need_view = (
            not self._view_cache
            or active
            or self._view_idle_counter >= IDLE_VIEW_REFRESH_EVERY
        )
        if need_view:
            try:
                self._view_cache = await self.api.fetch_view(self.serial_number)
                self._view_idle_counter = 0
                self._consecutive_view_failures = 0
                _LOGGER.debug("Refreshed view for %s", self.kiln_name)
            except Exception as exc:
                self._consecutive_view_failures += 1
                self._view_idle_counter += 1
                _LOGGER.debug(
                    "View refresh failed for %s, using cache: %s",
                    self.kiln_name,
                    exc,
                )
                if active and self._consecutive_view_failures >= 3:
                    _LOGGER.warning(
                        "View data has failed %d consecutive times for %s while active",
                        self._consecutive_view_failures,
                        self.kiln_name,
                    )
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

        product = view.get("product") or "KilnAid Kiln"

        return {
            "summary": summary,
            "status": status,
            "view": view,
            "metadata": {
                "external_id": self.kiln_id,
                "serial_number": self.serial_number,
                "name": self.kiln_name,
                "temperature_scale": temperature_scale,
                "product": product,
            },
        }