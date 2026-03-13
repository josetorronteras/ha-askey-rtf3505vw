"""Askey RTF3505VW Home Assistant integration."""
from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
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
    coordinator = AskeyCoordinator(
        hass,
        client,
        scan_interval=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.async_close()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and close the custom aiohttp session."""
    coordinator: AskeyCoordinator = hass.data[DOMAIN][entry.entry_id]

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await coordinator.client.async_close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded
