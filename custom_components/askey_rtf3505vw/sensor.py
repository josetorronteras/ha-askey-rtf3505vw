"""Sensor platform for the Askey RTF3505VW integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_GUEST,
    SENSOR_TOTAL,
    SENSOR_UPTIME,
    SENSOR_WIFI_24,
    SENSOR_WIFI_5,
    SENSOR_WIRED,
)
from .coordinator import AskeyCoordinator
from .router import IFACE_WIFI_24, IFACE_WIFI_5, RouterDevice


@dataclass(frozen=True, kw_only=True)
class AskeySensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with a device filter function."""

    filter_fn: Callable[[RouterDevice], bool] = lambda _: True


SENSOR_DESCRIPTIONS: tuple[AskeySensorDescription, ...] = (
    AskeySensorDescription(
        key=SENSOR_TOTAL,
        name="Dispositivos conectados",
        icon="mdi:devices",
        state_class=SensorStateClass.MEASUREMENT,
        filter_fn=lambda d: True,
    ),
    AskeySensorDescription(
        key=SENSOR_WIRED,
        name="Dispositivos por cable",
        icon="mdi:ethernet",
        state_class=SensorStateClass.MEASUREMENT,
        filter_fn=lambda d: d.is_wired,
    ),
    AskeySensorDescription(
        key=SENSOR_WIFI_24,
        name="WiFi 2.4 GHz",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        filter_fn=lambda d: d.interface == IFACE_WIFI_24,
    ),
    AskeySensorDescription(
        key=SENSOR_WIFI_5,
        name="WiFi 5 GHz",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        filter_fn=lambda d: d.interface == IFACE_WIFI_5,
    ),
    AskeySensorDescription(
        key=SENSOR_GUEST,
        name="Red de invitados",
        icon="mdi:wifi-star",
        state_class=SensorStateClass.MEASUREMENT,
        filter_fn=lambda d: d.is_guest,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AskeyCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        AskeyDeviceCountSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(AskeyUptimeSensor(coordinator))
    async_add_entities(entities)


def _device_info(coordinator: AskeyCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name="Askey RTF3505VW",
        manufacturer="Askey",
        model="RTF3505VW",
        sw_version=coordinator.info.software_version or None,
    )


class AskeyDeviceCountSensor(CoordinatorEntity[AskeyCoordinator], SensorEntity):
    """Counts network devices matching a filter (total, wired, WiFi band, guest)."""

    _attr_has_entity_name = True
    entity_description: AskeySensorDescription

    def __init__(
        self, coordinator: AskeyCoordinator, description: AskeySensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> int:
        return sum(
            1
            for dev in self.coordinator.data.values()
            if self.entity_description.filter_fn(dev)
        )

    @property
    def extra_state_attributes(self) -> dict:
        devices = [
            {
                "hostname": dev.hostname,
                "mac": dev.mac,
                "ip": dev.ip,
                **({"rssi": dev.rssi} if dev.rssi != 0 else {}),
                **({"ssid": dev.ssid} if dev.ssid else {}),
            }
            for dev in sorted(
                (
                    d
                    for d in self.coordinator.data.values()
                    if self.entity_description.filter_fn(d)
                ),
                key=lambda d: d.hostname.lower(),
            )
        ]
        return {"devices": devices}

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self.coordinator)


class AskeyUptimeSensor(CoordinatorEntity[AskeyCoordinator], SensorEntity):
    """Reports router uptime in seconds."""

    _attr_has_entity_name = True
    _attr_name = "Uptime"
    _attr_icon = "mdi:timer-outline"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator: AskeyCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{SENSOR_UPTIME}"

    @property
    def native_value(self) -> int:
        return self.coordinator.info.uptime_seconds

    @property
    def extra_state_attributes(self) -> dict:
        return {"uptime_raw": self.coordinator.info.uptime_raw}

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self.coordinator)
