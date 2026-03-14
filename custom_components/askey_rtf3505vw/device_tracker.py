"""Device tracker platform for the Askey RTF3505VW integration."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import AskeyCoordinator
from .router import RouterDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AskeyCoordinator = hass.data[DOMAIN][entry.entry_id]
    tracked: set[str] = set()
    initialized = False

    @callback
    def _add_new_devices() -> None:
        nonlocal initialized
        new_macs = [mac for mac in coordinator.data if mac not in tracked]
        if new_macs:
            tracked.update(new_macs)
            async_add_entities([AskeyDeviceTracker(coordinator, mac) for mac in new_macs])
            if initialized:
                for mac in new_macs:
                    dev = coordinator.data[mac]
                    hass.bus.async_fire(
                        f"{DOMAIN}_device_connected",
                        {"mac": mac, "hostname": dev.hostname, "ip": dev.ip},
                    )
        initialized = True

    _add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_devices))


class AskeyDeviceTracker(CoordinatorEntity[AskeyCoordinator], ScannerEntity):
    """Represents one network client detected by the router."""

    _attr_source_type = SourceType.ROUTER

    def __init__(self, coordinator: AskeyCoordinator, mac: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{mac}"
        # Initialise hostname cache from current coordinator data if available.
        dev = coordinator.data.get(mac)
        self._cached_hostname: str | None = (
            dev.hostname if dev and dev.hostname and dev.hostname != mac else None
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update hostname cache whenever new data arrives."""
        dev = self._device
        if dev and dev.hostname and dev.hostname != self._mac:
            self._cached_hostname = dev.hostname
        super()._handle_coordinator_update()

    @property
    def name(self) -> str:
        if self._cached_hostname:
            return self._cached_hostname
        dev = self._device
        if dev and dev.hostname and dev.hostname != self._mac:
            return dev.hostname
        return self._mac.replace(":", "")[-6:]

    @property
    def is_connected(self) -> bool:
        if self._mac in self.coordinator.data:
            return True
        last_seen = self.coordinator.last_seen.get(self._mac)
        if last_seen is None or self.coordinator.consider_home == 0:
            return False
        elapsed = (dt_util.utcnow() - last_seen).total_seconds()
        return elapsed < self.coordinator.consider_home

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def hostname(self) -> str | None:
        dev = self._device
        return dev.hostname if dev else self._cached_hostname

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
            connections={(CONNECTION_NETWORK_MAC, self._mac)},
            via_device=(DOMAIN, self.coordinator.config_entry.entry_id),
        )

    @property
    def _device(self) -> RouterDevice | None:
        return self.coordinator.data.get(self._mac)
