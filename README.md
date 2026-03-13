# Askey RTF3505VW — Home Assistant Integration

Custom integration for Home Assistant that exposes data from the **Askey RTF3505VW** router (distributed by Movistar) as native entities.

## Requirements

- Home Assistant 2024.1 or later
- Askey RTF3505VW router reachable on the local network

## Installation

1. Copy the `custom_components/askey_rtf3505vw/` folder into the `custom_components/` directory of your Home Assistant installation.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for "Askey RTF3505VW".
4. Enter the router IP (default `192.168.1.1`), the password, and the scan interval.

## Entities

### Sensors

| Entity | Description |
|---|---|
| Dispositivos conectados | Total devices on the network |
| Dispositivos por cable | Wired (ethernet) devices |
| WiFi 2.4 GHz | Devices connected to the 2.4 GHz band |
| WiFi 5 GHz | Devices connected to the 5 GHz band |
| Red de invitados | Devices on the guest network |
| Uptime | Router uptime in seconds |

### Device trackers

One `device_tracker` entity per detected device. Created dynamically and persist even after a device disconnects.

### Button

| Entity | Description |
|---|---|
| Reiniciar router | Sends the reboot command to the router |

## Configuration

| Field | Default | Description |
|---|---|---|
| Router IP | `192.168.1.1` | IP address of the router on the local network |
| Password | — | Password printed on the router label |
| Scan interval | `300 s` | How often to poll the router (minimum 10 s) |

## Branding

The integration logo (`images/logo.png`) must be submitted to the [Home Assistant brands repository](https://github.com/home-assistant/brands) under `custom_integrations/askey_rtf3505vw/` for it to appear in the HA UI. Until then, HA will show a generic icon.

## Technical notes

- The integration uses its own `aiohttp` session with `force_close=True` because the router rejects keep-alive connections.
- Device data is built by merging three sources: DHCP table, ARP table, and WiFi station lists.
- If the session expires, the coordinator attempts an automatic re-login before marking entities as unavailable.
