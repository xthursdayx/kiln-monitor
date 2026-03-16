"""Constants for the Kiln Monitor integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "kiln_monitor"

LOGIN_URL = "https://bartinst-user-service-prod.herokuapp.com/login"
SETTINGS_URL = "https://kiln.bartinst.com/kilns/settings"
DATA_URL = "https://kiln.bartinst.com/kilns/data"
STATUS_URL = "https://kiln.bartinst.com/kilnaid-data/status"
VIEW_URL = "https://kiln.bartinst.com/kilns/view"

# Login headers shared between KilnAPI.authenticate() and config_flow
# validate_input() so there is a single source of truth.
LOGIN_HEADERS: dict[str, str] = {
    "Accept": "application/json",
    "kaid-version": "kaid-plus",
    "Sec-Fetch-Site": "cross-site",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Mode": "cors",
    "Content-Type": "application/json",
    "Origin": "ionic://localhost",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    ),
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
}

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 5  # minutes
SCAN_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)

# Refresh tuning: how many idle polling cycles before re-fetching
# summary and view data respectively.
IDLE_VIEW_REFRESH_EVERY = 6
IDLE_SUMMARY_REFRESH_EVERY = 12
