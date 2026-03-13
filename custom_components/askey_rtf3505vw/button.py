"""Button platform for the Askey RTF3505VW integration."""
from __future__ import annotations

import logging
import re

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AskeyCoordinator

_LOGGER = logging.getLogger(__name__)
_SESSION_KEY_RE = re.compile(r"var sessionKey='(\d+)'")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AskeyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AskeyRebootButton(coordinator)])


class AskeyRebootButton(ButtonEntity):
    """Button that reboots the router."""

    _attr_name = "Reiniciar router"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator: AskeyCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_reboot"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._coordinator.config_entry.entry_id)},
            name="Askey RTF3505VW",
            manufacturer="Askey",
            model="RTF3505VW",
            sw_version=self._coordinator.info.software_version or None,
        )

    async def async_press(self) -> None:
        """Extract the CSRF sessionKey from /resetrouter.html then trigger reboot."""
        client = self._coordinator.client

        html = await client._fetch("/resetrouter.html")
        if not html:
            _LOGGER.error("Reboot: could not fetch /resetrouter.html")
            return

        match = _SESSION_KEY_RE.search(html)
        if not match:
            _LOGGER.error("Reboot: sessionKey not found in /resetrouter.html")
            return

        session_key = match.group(1)
        _LOGGER.debug("Reboot: sessionKey=%s", session_key)
        await client._fetch(f"/rebootinfo.cgi?sessionKey={session_key}")
        _LOGGER.info("Reboot command sent to router")
