"""DataUpdateCoordinator for the Askey RTF3505VW integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .router import AskeyRouterClient, RouterDevice, RouterInfo, SessionExpiredError

_LOGGER = logging.getLogger(__name__)


class AskeyCoordinator(DataUpdateCoordinator[dict[str, RouterDevice]]):
    """Coordinator that polls the router and distributes data to all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: AskeyRouterClient,
        scan_interval: int,
        consider_home: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.info: RouterInfo = RouterInfo()
        self.consider_home: int = max(consider_home, scan_interval)
        self.last_seen: dict[str, datetime] = {}
        self._consecutive_failures: int = 0

    async def _async_setup(self) -> None:
        """Run once during async_config_entry_first_refresh.

        Performs the initial login. Raises ConfigEntryNotReady if the router
        is unreachable, or ConfigEntryAuthFailed if credentials are wrong
        (which triggers the reauth flow automatically).
        """
        try:
            success = await self.client.async_login()
        except Exception as err:
            _LOGGER.warning("Cannot connect to router during setup: %s", err)
            raise ConfigEntryNotReady(f"Cannot connect to router: {err}") from err
        if not success:
            _LOGGER.warning("Login returned False — invalid credentials or missing session cookie")
            raise ConfigEntryAuthFailed("Invalid credentials")

    async def _async_update_data(self) -> dict[str, RouterDevice]:
        """Fetch the latest device list and router info.

        If the router returns the login page (session expired) or any other
        error occurs, attempts a single re-login before giving up.

        A single transient failure returns cached data silently to avoid brief
        "unavailable" flicker in the UI. Only after two consecutive failures is
        UpdateFailed raised (which marks entities unavailable).
        """
        try:
            return await self._fetch_data()
        except (SessionExpiredError, Exception) as err:
            _LOGGER.warning(
                "%s, attempting re-login",
                "Session expired" if isinstance(err, SessionExpiredError) else f"Fetch failed ({err})",
            )
            return await self._relogin_and_fetch()

    async def _fetch_data(self) -> dict[str, RouterDevice]:
        """Fetch devices and info, update state, and return the device dict."""
        devices = await self.client.async_get_devices()
        self.info = await self.client.async_get_info() or self.info

        self._consecutive_failures = 0
        now = dt_util.utcnow()
        for mac in devices:
            self.last_seen[mac] = now

        return devices

    async def _relogin_and_fetch(self) -> dict[str, RouterDevice]:
        """Re-login and retry fetching data, with graceful degradation.

        On the first failure returns cached data; on the second raises
        UpdateFailed so entities are marked unavailable.
        """
        try:
            if not await self.client.async_login():
                return self._handle_failure("Re-login failed")
            return await self._fetch_data()
        except UpdateFailed:
            raise
        except Exception as err:
            return self._handle_failure(f"Fetch failed after re-login: {err}", err)

    def _handle_failure(
        self, message: str, cause: Exception | None = None,
    ) -> dict[str, RouterDevice]:
        """Increment failure counter; return cached data or raise UpdateFailed."""
        self._consecutive_failures += 1
        if self._consecutive_failures < 2:
            _LOGGER.warning("%s (attempt %d), keeping cached data", message, self._consecutive_failures)
            return self.data or {}
        if cause:
            raise UpdateFailed(message) from cause
        raise UpdateFailed(message)
