"""Askey RTF3505VW Home Assistant integration."""
from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CONSIDER_HOME,
    CONF_SCAN_INTERVAL,
    DEFAULT_CONSIDER_HOME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import AskeyCoordinator
from .router import AskeyRouterClient

PLATFORMS = [Platform.BUTTON, Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Askey RTF3505VW from a config entry."""

    # The router rejects keep-alive connections, so we need our own
    # aiohttp session with force_close=True instead of HA's shared one.
    connector = aiohttp.TCPConnector(force_close=True)
    session = aiohttp.ClientSession(connector=connector)

    client = AskeyRouterClient(
        session,
        host=entry.data[CONF_HOST],
        password=entry.data[CONF_PASSWORD],
    )

    # Read tunable parameters from options first, fall back to data (migration).
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    consider_home = entry.options.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME)

    coordinator = AskeyCoordinator(
        hass,
        client,
        scan_interval=scan_interval,
        consider_home=consider_home,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.async_close()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry whenever options are changed.
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and close the custom aiohttp session."""
    coordinator: AskeyCoordinator = hass.data[DOMAIN][entry.entry_id]

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await coordinator.client.async_close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded
