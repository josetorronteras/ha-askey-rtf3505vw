"""Constants for the Askey RTF3505VW integration."""

DOMAIN = "askey_rtf3505vw"

# Config entry keys
CONF_SCAN_INTERVAL = "scan_interval"
CONF_CONSIDER_HOME = "consider_home"

# Defaults
DEFAULT_HOST = "192.168.1.1"
DEFAULT_SCAN_INTERVAL = 300  # seconds
DEFAULT_CONSIDER_HOME = 180  # seconds

# Sensor unique IDs
SENSOR_TOTAL = "devices_total"
SENSOR_WIRED = "devices_wired"
SENSOR_WIFI_24 = "devices_wifi_24"
SENSOR_WIFI_5 = "devices_wifi_5"
SENSOR_GUEST = "devices_guest"
SENSOR_UPTIME = "uptime"
