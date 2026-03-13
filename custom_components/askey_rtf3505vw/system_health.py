"""System health support for the Askey RTF3505VW integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.system_health import SystemHealthRegistration
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(hass: HomeAssistant, register: SystemHealthRegistration) -> None:
    """Register system health checks."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return system health info for all configured entries."""
    info: dict[str, Any] = {}

    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        host = coordinator.config_entry.data[CONF_HOST]
        info[host] = {
            "reachable": coordinator.last_update_success,
            "software_version": coordinator.info.software_version or "unknown",
            "uptime": coordinator.info.uptime_raw or "unknown",
        }

    return info
