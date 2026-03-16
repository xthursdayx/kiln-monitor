"""API client for Kiln Monitor."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import DATA_URL, LOGIN_URL, LOGIN_HEADERS, SETTINGS_URL, STATUS_URL, VIEW_URL

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = ClientTimeout(total=30)


class KilnApiError(Exception):
    """Base Kiln API error."""


class KilnAuthError(KilnApiError):
    """Authentication failure."""


class KilnConnectionError(KilnApiError):
    """Transport or remote API failure."""


class KilnAPI:
    """Async API client for Bartlett / KilnAid."""

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None
        self._login_data: dict[str, Any] | None = None

    async def authenticate(self) -> None:
        """Authenticate and cache token."""
        payload = {
            "email": self._email,
            "password": self._password,
        }

        try:
            async with self._session.post(
                LOGIN_URL,
                headers=LOGIN_HEADERS,
                json=payload,
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    raise KilnAuthError("Invalid email or password")
                if resp.status != 200:
                    raise KilnConnectionError(
                        f"Login failed with status {resp.status}"
                    )
                data = await resp.json()
        except KilnApiError:
            raise
        except ClientError as exc:
            raise KilnConnectionError(str(exc)) from exc

        token = data.get("authentication_token")
        if not token:
            raise KilnAuthError("Authentication token missing from response")

        self._token = token
        self._login_data = data
        _LOGGER.debug("Kiln API authentication succeeded for %s", self._email)

    async def _ensure_authenticated(self) -> None:
        """Authenticate if not already authenticated."""
        if not self._token:
            await self.authenticate()

    def _headers(self) -> dict[str, str]:
        """Common authenticated headers."""
        if not self._token:
            raise KilnAuthError("Client is not authenticated")

        return {
            "auth-token": f"binst-cookie={self._token}",
            "email": self._email,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "kaid-version": "kaid-plus",
            "x-app-name-token": "kiln-aid",
        }

    async def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        include_query_auth: bool = False,
    ) -> Any:
        """POST JSON with one re-auth retry on 401."""
        await self._ensure_authenticated()

        for attempt in range(2):
            try:
                params = None
                if include_query_auth:
                    params = {
                        "token": self._token,
                        "user_email": self._email,
                    }

                async with self._session.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                    params=params,
                    timeout=_TIMEOUT,
                ) as resp:
                    if resp.status == 401:
                        self._token = None
                        if attempt == 0:
                            _LOGGER.debug("401 from %s, re-authenticating once", url)
                            await self.authenticate()
                            continue
                        raise KilnAuthError("Authentication failed")
                    if resp.status != 200:
                        raise KilnConnectionError(
                            f"Request to {url} failed with status {resp.status}"
                        )
                    return await resp.json()

            except KilnApiError:
                raise
            except ClientError as exc:
                raise KilnConnectionError(str(exc)) from exc

        raise KilnConnectionError(f"Unable to complete request to {url}")

    def _normalize_kiln(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Normalize kiln data from various endpoint shapes."""
        external_id = (
            item.get("external_id")
            or item.get("externalId")
            or item.get("kiln_id")
        )
        serial_number = (
            item.get("serial_number")
            or item.get("serialNumber")
        )
        name = (
            item.get("name")
            or item.get("list", {}).get("name")
            or item.get("settings", {}).get("name")
            or "Kiln"
        )

        if not external_id or not serial_number:
            return None

        return {
            "external_id": external_id,
            "serial_number": serial_number,
            "name": name,
            "initial_summary": item if "list" in item or "settings" in item else {},
        }

    def _extract_kilns_recursive(self, obj: Any) -> list[dict[str, Any]]:
        """Recursively search nested responses for kiln-like dicts.

        Returns early after matching a dict so that nested sub-keys within an
        already-matched kiln object are not also evaluated as potential kilns.
        """
        found: list[dict[str, Any]] = []

        if isinstance(obj, dict):
            normalized = self._normalize_kiln(obj)
            if normalized:
                # Stop recursing into this dict — its children belong to
                # this kiln, not to separate kiln objects.
                found.append(normalized)
                return found

            for value in obj.values():
                found.extend(self._extract_kilns_recursive(value))

        elif isinstance(obj, list):
            for item in obj:
                found.extend(self._extract_kilns_recursive(item))

        return found

    def _dedupe_kilns(self, kilns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate by external_id + serial_number."""
        deduped: dict[tuple[str, str], dict[str, Any]] = {}
        for kiln in kilns:
            key = (kiln["external_id"], kiln["serial_number"])
            deduped[key] = kiln
        return list(deduped.values())

    async def fetch_kilns(self) -> list[dict[str, Any]]:
        """Discover kilns for the authenticated account."""
        await self._ensure_authenticated()

        discovered: list[dict[str, Any]] = []

        if self._login_data:
            discovered.extend(self._extract_kilns_recursive(self._login_data))

        discovery_attempts: list[tuple[str, dict[str, Any]]] = [
            (DATA_URL, {"externalIds": []}),
            (SETTINGS_URL, {}),
            (SETTINGS_URL, {"kiln_ids": []}),
        ]

        for url, payload in discovery_attempts:
            try:
                data = await self._post_json(url, payload)
                discovered.extend(self._extract_kilns_recursive(data))
            except Exception as exc:
                _LOGGER.debug(
                    "Kiln discovery attempt failed for %s %s: %s",
                    url,
                    payload,
                    exc,
                )

        kilns = self._dedupe_kilns(discovered)
        _LOGGER.debug("Discovered %d kilns", len(kilns))
        return kilns

    async def fetch_summary(self, external_id: str) -> dict[str, Any]:
        """Fetch summary data for one kiln."""
        data = await self._post_json(DATA_URL, {"externalIds": [external_id]})
        if not isinstance(data, list) or not data:
            raise KilnConnectionError("Unexpected summary response format")
        return data[0]

    async def fetch_status(self, external_id: str) -> dict[str, Any]:
        """Fetch primary live status for one kiln."""
        # externalIds must be a list, consistent with all other endpoints.
        data = await self._post_json(STATUS_URL, {"externalIds": [external_id]})
        if not isinstance(data, list) or not data:
            raise KilnConnectionError("Unexpected status response format")
        return data[0]

    async def fetch_view(self, serial_number: str) -> dict[str, Any]:
        """Fetch detailed kiln view data for one kiln."""
        data = await self._post_json(
            VIEW_URL,
            {"ids": [serial_number]},
            include_query_auth=True,
        )
        kilns = data.get("kilns", [])
        if not isinstance(kilns, list) or not kilns:
            raise KilnConnectionError("Unexpected view response format")
        return kilns[0]
