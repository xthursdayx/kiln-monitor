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
        if delta_hours < (1 / 120):
            return float(previous_data.get("metadata", {}).get("cooling_rate_per_hour", 0.0))

        rate = (current_temp - previous_temp) / delta_hours

        if rate < 0:
            return round(abs(rate), 2)

        return 0.0

    def _extract_program_steps(
        self,
        status: dict[str, Any],
        view: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str]:
        """Extract the target firing program steps and source."""
        status_steps = status.get("unformattedProgramSegments")
        if isinstance(status_steps, list) and status_steps:
            return status_steps, "status.unformattedProgramSegments"

        view_steps = view.get("program", {}).get("steps")
        if isinstance(view_steps, list) and view_steps:
            return view_steps, "view.program.steps"

        return [], "none"

    def _extract_start_temperature(
        self,
        status: dict[str, Any],
        summary: dict[str, Any],
        view: dict[str, Any],
    ) -> float | None:
        """Find the best available starting temperature for target-curve math."""
        start_temp = view.get("latest_firing", {}).get("starting_temp", {}).get("z1")
        if start_temp is not None:
            try:
                return float(start_temp)
            except (TypeError, ValueError):
                pass

        current_temp = self._extract_primary_temperature(status, summary)
        if current_temp is not None:
            return current_temp

        return None

    def _build_target_curve(
        self,
        status: dict[str, Any],
        summary: dict[str, Any],
        view: dict[str, Any],
        temperature_scale: str,
    ) -> dict[str, Any]:
        """Build a compact chart-friendly target curve."""
        steps, source = self._extract_program_steps(status, view)
        if not steps:
            return {
                "summary": "No target curve",
                "source": source,
                "program_name": status.get("programName") or view.get("program", {}).get("name"),
                "temperature_scale": temperature_scale,
                "start_temperature": None,
                "segment_count": 0,
                "segments": [],
                "target_points": [],
            }

        start_temp = self._extract_start_temperature(status, summary, view)

        program_name = status.get("programName") or view.get("program", {}).get("name")
        segments: list[dict[str, Any]] = []
        target_points: list[dict[str, Any]] = []

        current_minute = 0.0
        previous_target = start_temp

        if start_temp is not None:
            target_points.append(
                {
                    "minute": 0.0,
                    "temp": round(float(start_temp), 2),
                    "label": "Start",
                }
            )

        for raw_step in steps:
            try:
                segment_num = int(raw_step.get("num"))
            except (TypeError, ValueError):
                segment_num = len(segments) + 1

            target_temp_raw = raw_step.get("t")
            ramp_rate_raw = raw_step.get("rt")
            hold_hours_raw = raw_step.get("hr", 0)
            hold_minutes_raw = raw_step.get("mn", 0)

            try:
                target_temp = float(target_temp_raw)
            except (TypeError, ValueError):
                continue

            try:
                ramp_rate = float(ramp_rate_raw)
            except (TypeError, ValueError):
                ramp_rate = 0.0

            try:
                hold_minutes = (int(hold_hours_raw) * 60) + int(hold_minutes_raw)
            except (TypeError, ValueError):
                hold_minutes = 0

            if previous_target is None:
                previous_target = target_temp

            if ramp_rate <= 0:
                ramp_minutes = 0.0
                segment_kind = "hold"
            elif ramp_rate >= 9999:
                ramp_minutes = 0.0
                segment_kind = "fast"
            else:
                ramp_minutes = abs(target_temp - previous_target) / ramp_rate * 60.0
                if hold_minutes > 0:
                    segment_kind = "ramp_hold"
                elif target_temp > previous_target:
                    segment_kind = "ramp_up"
                elif target_temp < previous_target:
                    segment_kind = "ramp_down"
                else:
                    segment_kind = "hold"

            start_minute = round(current_minute, 2)
            ramp_end_minute = round(current_minute + ramp_minutes, 2)
            end_minute = round(ramp_end_minute + hold_minutes, 2)

            segments.append(
                {
                    "segment": segment_num,
                    "target_temp": round(target_temp, 2),
                    "ramp_rate": round(ramp_rate, 2),
                    "hold_minutes": hold_minutes,
                    "start_minute": start_minute,
                    "ramp_end_minute": ramp_end_minute,
                    "end_minute": end_minute,
                    "kind": segment_kind,
                }
            )

            target_points.append(
                {
                    "minute": ramp_end_minute,
                    "temp": round(target_temp, 2),
                    "label": f"Segment {segment_num} target",
                }
            )

            if hold_minutes > 0:
                target_points.append(
                    {
                        "minute": end_minute,
                        "temp": round(target_temp, 2),
                        "label": f"Segment {segment_num} hold end",
                    }
                )

            current_minute = end_minute
            previous_target = target_temp

        summary_text = f"{len(segments)} segments"

        return {
            "summary": summary_text,
            "source": source,
            "program_name": program_name,
            "temperature_scale": temperature_scale,
            "start_temperature": round(start_temp, 2) if start_temp is not None else None,
            "segment_count": len(segments),
            "segments": segments,
            "target_points": target_points,
        }

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
        target_curve = self._build_target_curve(status, summary, view, temperature_scale)

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
                "target_curve_summary": target_curve["summary"],
                "target_curve": target_curve,
            },
        }