"""Constants for the Kiln Monitor integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "kiln_monitor"

LOGIN_URL = "https://bartinst-user-service-prod.herokuapp.com/login"
DATA_URL = "https://kiln.bartinst.com/kilns/data"
STATUS_URL = "https://kiln.bartinst.com/kilnaid-data/status"
VIEW_URL = "https://kiln.bartinst.com/kilns/view"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 5  # minutes
SCAN_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)

# Refresh tuning
IDLE_VIEW_REFRESH_EVERY = 6
IDLE_SUMMARY_REFRESH_EVERY = 12