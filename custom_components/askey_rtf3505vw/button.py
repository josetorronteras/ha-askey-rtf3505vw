"""Button platform for the Askey RTF3505VW integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AskeyCoordinator

_LOGGER = logging.getLogger(__name__)


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
        await self._coordinator.client.async_reboot()
