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
        self.consider_home: int = consider_home
        self.last_seen: dict[str, datetime] = {}

    async def _async_setup(self) -> None:
        """Run once during async_config_entry_first_refresh.

        Performs the initial login. Raises ConfigEntryNotReady if the router
        is unreachable, or ConfigEntryAuthFailed if credentials are wrong
        (which triggers the reauth flow automatically).
        """
        try:
            success = await self.client.async_login()
        except Exception as err:
            raise ConfigEntryNotReady(f"Cannot connect to router: {err}") from err
        if not success:
            raise ConfigEntryAuthFailed("Invalid credentials")

    async def _async_update_data(self) -> dict[str, RouterDevice]:
        """Fetch the latest device list and router info.

        If the router returns the login page (session expired) or any other
        error occurs, attempts a single re-login before giving up.
        Raises UpdateFailed so HA marks entities as unavailable.
        """
        try:
            devices = await self.client.async_get_devices()
            self.info = await self.client.async_get_info()
        except SessionExpiredError:
            _LOGGER.debug("Session expired, re-logging in")
            try:
                if not await self.client.async_login():
                    raise UpdateFailed("Session expired and re-login failed")
                devices = await self.client.async_get_devices()
                self.info = await self.client.async_get_info()
            except UpdateFailed:
                raise
            except Exception as retry_err:
                raise UpdateFailed(
                    f"Could not fetch data after re-login: {retry_err}"
                ) from retry_err
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Fetch failed (%s), attempting re-login", err)
            try:
                if not await self.client.async_login():
                    raise UpdateFailed("Session expired and re-login failed")
                devices = await self.client.async_get_devices()
                self.info = await self.client.async_get_info()
            except UpdateFailed:
                raise
            except Exception as retry_err:
                raise UpdateFailed(
                    f"Could not fetch data from router: {retry_err}"
                ) from retry_err

        now = dt_util.utcnow()
        for mac in devices:
            self.last_seen[mac] = now

        return devices
