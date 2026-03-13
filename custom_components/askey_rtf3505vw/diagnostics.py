"""Diagnostics support for the Askey RTF3505VW integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import AskeyCoordinator
from .router import IFACE_WIFI_24, IFACE_WIFI_5

TO_REDACT = {CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: AskeyCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "router_info": {
            "software_version": coordinator.info.software_version,
            "wireless_driver": coordinator.info.wireless_driver,
            "uptime_raw": coordinator.info.uptime_raw,
            "uptime_seconds": coordinator.info.uptime_seconds,
        },
        "devices": {
            "total": len(coordinator.data),
            "wired": sum(1 for d in coordinator.data.values() if d.is_wired),
            "wifi_24": sum(1 for d in coordinator.data.values() if d.interface == IFACE_WIFI_24),
            "wifi_5": sum(1 for d in coordinator.data.values() if d.interface == IFACE_WIFI_5),
            "guest": sum(1 for d in coordinator.data.values() if d.is_guest),
        },
    }
