"""API client for Kiln Monitor."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import DATA_URL, LOGIN_URL, STATUS_URL, VIEW_URL

_LOGGER = logging.getLogger(__name__)


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

    async def authenticate(self) -> None:
        """Authenticate and cache token."""
        headers = {
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
        payload = {
            "email": self._email,
            "password": self._password,
        }

        try:
            async with self._session.post(
                LOGIN_URL,
                headers=headers,
                json=payload,
                timeout=30,
            ) as resp:
                if resp.status == 401:
                    raise KilnAuthError("Invalid email or password")
                if resp.status != 200:
                    raise KilnConnectionError(
                        f"Login failed with status {resp.status}"
                    )
                data = await resp.json()
        except asyncio.TimeoutError as exc:
            raise KilnConnectionError("Login request timed out") from exc
        except ClientError as exc:
            raise KilnConnectionError(str(exc)) from exc

        token = data.get("authentication_token")
        if not token:
            raise KilnAuthError("Authentication token missing from response")

        self._token = token

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
                    timeout=30,
                ) as resp:
                    if resp.status == 401:
                        self._token = None
                        if attempt == 0:
                            await self.authenticate()
                            continue
                        raise KilnAuthError("Authentication failed")
                    if resp.status != 200:
                        raise KilnConnectionError(
                            f"Request to {url} failed with status {resp.status}"
                        )
                    return await resp.json()

            except asyncio.TimeoutError as exc:
                raise KilnConnectionError(f"Request to {url} timed out") from exc
            except ClientError as exc:
                raise KilnConnectionError(str(exc)) from exc

        raise KilnConnectionError(f"Unable to complete request to {url}")

    async def fetch_kilns(self) -> list[dict[str, Any]]:
        """Fetch and normalize the account's kilns.

        This relies on the same discovery approach the current repo was already
        attempting: POST /kilns/data with an empty externalIds list.
        """
        data = await self._post_json(DATA_URL, {"externalIds": []})

        if not isinstance(data, list):
            raise KilnConnectionError("Unexpected kiln discovery response format")

        kilns: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            external_id = item.get("externalId")
            serial_number = item.get("serialNumber")
            name = (
                item.get("list", {}).get("name")
                or item.get("settings", {}).get("name")
                or "Kiln"
            )

            if not external_id or not serial_number:
                continue

            kilns.append(
                {
                    "external_id": external_id,
                    "serial_number": serial_number,
                    "name": name,
                    "initial_summary": item,
                }
            )

        return kilns

    async def fetch_summary(self, external_id: str) -> dict[str, Any]:
        """Fetch summary data for one kiln."""
        data = await self._post_json(DATA_URL, {"externalIds": [external_id]})
        if not isinstance(data, list) or not data:
            raise KilnConnectionError("Unexpected summary response format")
        return data[0]

    async def fetch_status(self, external_id: str) -> dict[str, Any]:
        """Fetch primary live status for one kiln."""
        data = await self._post_json(STATUS_URL, {"externalIds": external_id})
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