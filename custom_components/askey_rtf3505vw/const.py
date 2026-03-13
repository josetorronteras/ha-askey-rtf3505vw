"""Constants for the Askey RTF3505VW integration."""

DOMAIN = "askey_rtf3505vw"

# Config entry keys
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_HOST = "192.168.1.1"
DEFAULT_SCAN_INTERVAL = 300  # seconds

# Router endpoints
ENDPOINT_LOGIN = "/te_acceso_router.cgi"
ENDPOINT_DHCP = "/dhcpinfo.html"
ENDPOINT_ARP = "/arpview.cmd"
ENDPOINT_WIFI = "/wlstationlist.cmd"
ENDPOINT_WIFI_SWITCH_WL0 = "/wlswitchinterface0.wl"
ENDPOINT_WIFI_SWITCH_WL1 = "/wlswitchinterface1.wl"
ENDPOINT_INFO = "/info.html"

# Session cookie
SESSION_COOKIE = "sessionID"

# WiFi interface names
IFACE_WIFI_24 = "wl0"
IFACE_WIFI_24_GUEST = "wl0.1"
IFACE_WIFI_5 = "wl1"

# Sensor unique IDs
SENSOR_TOTAL = "devices_total"
SENSOR_WIRED = "devices_wired"
SENSOR_WIFI_24 = "devices_wifi_24"
SENSOR_WIFI_5 = "devices_wifi_5"
SENSOR_GUEST = "devices_guest"
SENSOR_UPTIME = "uptime"
