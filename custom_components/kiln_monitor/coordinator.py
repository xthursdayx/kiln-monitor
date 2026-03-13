"""Coordinator for Kiln Monitor."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
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

    def _extract_primary_temperature(
        self,
        status: dict[str, Any],
        summary: dict[str, Any],
    ) -> float | None:
        """Extract the primary temperature sample used for rate calculations."""
        raw = status.get("t1")
        if raw is None:
            raw = summary.get("list", {}).get("temperature")

        if raw is None:
            return None

        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _parse_updated_at(self, status: dict[str, Any]) -> datetime | None:
        """Parse the status updatedAt timestamp."""
        raw = status.get("updatedAt")
        if not raw:
            return None

        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _calculate_cooling_rate(
        self,
        previous_data: dict[str, Any] | None,
        current_status: dict[str, Any],
        current_summary: dict[str, Any],
    ) -> float:
        """Calculate cooling rate in degrees per hour.

        Returns a positive number when cooling, otherwise 0.
        """
        if not previous_data:
            return 0.0

        previous_status = previous_data.get("status", {})
        previous_summary = previous_data.get("summary", {})

        current_temp = self._extract_primary_temperature(current_status, current_summary)
        previous_temp = self._extract_primary_temperature(previous_status, previous_summary)

        current_time = self._parse_updated_at(current_status)
        previous_time = self._parse_updated_at(previous_status)

        if (
            current_temp is None
            or previous_temp is None
            or current_time is None
            or previous_time is None
        ):
            return float(previous_data.get("metadata", {}).get("cooling_rate_per_hour", 0.0))

        delta_seconds = (current_time - previous_time).total_seconds()
        if delta_seconds <= 0:
            return float(previous_data.get("metadata", {}).get("cooling_rate_per_hour", 0.0))

        delta_hours = delta_seconds / 3600.0
        # Avoid absurd spikes from extremely small intervals.
        if delta_hours < (1 / 120):  # less than 30 seconds
            return float(previous_data.get("metadata", {}).get("cooling_rate_per_hour", 0.0))

        rate = (current_temp - previous_temp) / delta_hours

        if rate < 0:
            return round(abs(rate), 2)

        return 0.0

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch merged data.

        Important behavior:
        - status is primary
        - summary/view are best-effort and cached
        - if status temporarily fails after initial success, keep last good data
          so entities do not flap unavailable every poll
        """
        previous_data = self.data if isinstance(self.data, dict) else None

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
        cooling_rate_per_hour = self._calculate_cooling_rate(previous_data, status, summary)

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
                "cooling_rate_per_hour": cooling_rate_per_hour,
            },
        }