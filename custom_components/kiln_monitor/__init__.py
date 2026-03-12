"""Kiln Monitor integration."""

from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import KilnAPI
from .coordinator import KilnCoordinator
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Kiln Monitor from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    session = aiohttp.ClientSession()

    api = KilnAPI(
        session,
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )

    await api.authenticate()

    kiln = await api.fetch_summary_list()

    coordinator = KilnCoordinator(hass, api, kiln)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok