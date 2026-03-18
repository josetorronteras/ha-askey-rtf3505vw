# Askey RTF3505VW — Home Assistant Integration

Custom integration for Home Assistant that exposes data from the **Askey RTF3505VW** router (distributed by Movistar Spain) as native entities.

## Requirements

- Home Assistant 2024.1 or later
- Askey RTF3505VW router reachable on the local network

## Installation

### Via HACS (recommended)

1. In HACS, click the three-dot menu (⋮) in the top right and select **Custom repositories**.
2. Paste `https://github.com/josetorronteras/ha-askey-rtf3505vw` and select **Integration** as the category. Click **Add**.
3. Search for **Askey RTF3505VW** in HACS and install it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** and search for "Askey RTF3505VW".

### Manual

1. Copy the `custom_components/askey_rtf3505vw/` folder into the `custom_components/` directory of your Home Assistant installation.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for "Askey RTF3505VW".

## Entities

### Sensors

| Entity | Description |
|---|---|
| Connected devices | Total devices on the network |
| Wired devices | Wired (ethernet) devices |
| WiFi 2.4 GHz | Devices connected to the 2.4 GHz band |
| WiFi 5 GHz | Devices connected to the 5 GHz band |
| Guest network | Devices on the guest network |
| Uptime | Router uptime in seconds |

Entity names are translatable. Spanish translations are included out of the box.

Each device count sensor includes a `devices` attribute listing the hostname, MAC, IP, and (for Wi-Fi devices) SSID and RSSI of each matched device.

### Device trackers

One `device_tracker` entity per detected device. Entities are created dynamically on first detection and persist even after a device disconnects. The last known hostname is preserved while the device is away.

### Button

| Entity | Description |
|---|---|
| Reboot router | Sends the reboot command to the router |

## Configuration

Set during initial setup and adjustable afterwards via **Settings → Devices & Services → Configure**.

| Field | Default | Description |
|---|---|---|
| Router IP | `192.168.1.1` | IP address of the router (set at creation, not editable afterwards) |
| Password | — | Password printed on the router label |
| Scan interval | `300 s` | How often to poll the router (minimum 10 s) |
| Home grace period | `180 s` | Seconds before marking a device as away after it loses connection. Automatically raised to at least the scan interval to ensure the grace period spans a full polling cycle. Set to 0 to disable. |

## Technical notes

- Uses a dedicated `aiohttp` session with `force_close=True` because the router rejects keep-alive connections.
- Device data is merged from three sources: DHCP table, ARP table, and Wi-Fi station lists.
- Session expiry is detected automatically and triggers a re-login. A single transient failure returns cached data; only two consecutive failures mark entities as unavailable.
- Fires a `askey_rtf3505vw_device_connected` event when a new device appears on the network (after initial scan), useful for automations.
