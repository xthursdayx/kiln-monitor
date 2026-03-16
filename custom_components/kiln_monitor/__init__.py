"""The Kiln Monitor integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KilnAPI
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import KilnDataCoordinator

# Pre-import platform modules so they are already in sys.modules by the time
# async_forward_entry_setups runs inside the event loop.  Without this,
# Python 3.14 / HA 2025.x detects importlib.import_module as a blocking call
# and logs a "Detected blocking call to import_module" warning.  Importing at
# module level is safe because HA's loader imports __init__.py off the event
# loop during integration setup.
from . import binary_sensor, sensor  # noqa: E402, F401

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kiln Monitor from a config entry."""
    session = async_get_clientsession(hass)
    api = KilnAPI(
        session=session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        kilns = await api.fetch_kilns()
    except Exception as exc:
        raise ConfigEntryNotReady(f"Could not fetch kiln list: {exc}") from exc

    if not kilns:
        raise ConfigEntryNotReady("No kilns found for this account")

    update_interval = entry.options.get(
        CONF_UPDATE_INTERVAL,
        DEFAULT_UPDATE_INTERVAL,
    )

    coordinators: list[KilnDataCoordinator] = []
    for kiln_info in kilns:
        coordinator = KilnDataCoordinator(
            hass=hass,
            api=api,
            kiln_info=kiln_info,
            update_interval_minutes=update_interval,
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators.append(coordinator)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinators

    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates."""
    coordinators: list[KilnDataCoordinator] = hass.data[DOMAIN][entry.entry_id]
    update_interval = entry.options.get(
        CONF_UPDATE_INTERVAL,
        DEFAULT_UPDATE_INTERVAL,
    )

    for coordinator in coordinators:
        coordinator.update_interval_minutes(update_interval)
