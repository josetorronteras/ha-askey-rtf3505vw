"""Device tracker platform for the Askey RTF3505VW integration."""
from __future__ import annotations

import logging

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AskeyCoordinator
from .router import RouterDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AskeyCoordinator = hass.data[DOMAIN][entry.entry_id]
    tracked: set[str] = set()

    @callback
    def _add_new_devices() -> None:
        """Create a tracker entity for every MAC not yet tracked."""
        new_entities = [
            AskeyDeviceTracker(coordinator, mac)
            for mac in coordinator.data
            if mac not in tracked
        ]
        if new_entities:
            tracked.update(t._mac for t in new_entities)
            async_add_entities(new_entities)

    _add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_devices))


class AskeyDeviceTracker(CoordinatorEntity[AskeyCoordinator], ScannerEntity):
    """Represents one network client detected by the router."""

    _attr_source_type = SourceType.ROUTER

    def __init__(self, coordinator: AskeyCoordinator, mac: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{mac}"

    @property
    def name(self) -> str:
        dev = self._device
        if dev and dev.hostname and dev.hostname != self._mac:
            return dev.hostname
        return self._mac.replace(":", "")[-6:]

    @property
    def is_connected(self) -> bool:
        return self._mac in self.coordinator.data

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def hostname(self) -> str | None:
        dev = self._device
        return dev.hostname if dev else None

    @property
    def ip_address(self) -> str | None:
        dev = self._device
        return dev.ip if dev else None

    @property
    def extra_state_attributes(self) -> dict:
        dev = self._device
        if not dev:
            return {}
        attrs: dict = {}
        if dev.band:
            attrs["band"] = dev.band
        if dev.interface:
            attrs["interface"] = dev.interface
        if dev.dhcp_expires:
            attrs["dhcp_expires"] = dev.dhcp_expires
        if dev.ssid:
            attrs["ssid"] = dev.ssid
        if dev.rssi != 0:
            attrs["rssi"] = dev.rssi
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="Askey RTF3505VW",
            manufacturer="Askey",
            model="RTF3505VW",
        )

    @property
    def _device(self) -> RouterDevice | None:
        return self.coordinator.data.get(self._mac)
