"""Tests for the HTML parser functions in router.py."""
import pytest

from router import (
    _is_login_page,
    _parse_arp,
    _parse_dhcp,
    _parse_info,
    _parse_uptime,
    _parse_wifi,
)


# ---------------------------------------------------------------------------
# _parse_dhcp
# ---------------------------------------------------------------------------


class TestParseDhcp:
    def test_device_count(self, dhcp_html):
        assert len(_parse_dhcp(dhcp_html)) == 26

    def test_device_with_hostname(self, dhcp_html):
        devices = {d.mac: d for d in _parse_dhcp(dhcp_html)}
        d = devices["AA:BB:CC:DD:EE:01"]
        assert d.hostname == "Device 101"
        assert d.ip == "192.168.1.101"
        assert d.dhcp_expires == "6 hours, 9 minutes, 45 seconds"

    def test_empty_hostname_falls_back_to_mac(self, dhcp_html):
        devices = {d.mac: d for d in _parse_dhcp(dhcp_html)}
        d = devices["AA:BB:CC:DD:EE:02"]
        assert d.hostname == "AA:BB:CC:DD:EE:02"

    def test_mac_normalised_to_uppercase(self, dhcp_html):
        devices = _parse_dhcp(dhcp_html)
        assert all(d.mac == d.mac.upper() for d in devices)

    def test_returns_empty_on_no_table(self):
        assert _parse_dhcp("<html><body>no table here</body></html>") == []

    def test_returns_empty_on_empty_string(self):
        assert _parse_dhcp("") == []

    def test_no_band_set(self, dhcp_html):
        # DHCP parser does not know about WiFi bands.
        devices = _parse_dhcp(dhcp_html)
        assert all(d.band == "" for d in devices)


# ---------------------------------------------------------------------------
# _parse_arp
# ---------------------------------------------------------------------------


class TestParseArp:
    def test_device_count(self, arp_html):
        assert len(_parse_arp(arp_html)) == 21

    def test_standard_br0_interface(self, arp_html):
        devices = {d.mac: d for d in _parse_arp(arp_html)}
        d = devices["AA:BB:CC:DD:EE:06"]
        assert d.ip == "192.168.1.106"
        assert d.interface == "br0"

    def test_non_br0_interface_stored(self, arp_html):
        # AA:BB:CC:DD:EE:1B appears only in ARP (veip0.2), not in DHCP.
        devices = {d.mac: d for d in _parse_arp(arp_html)}
        d = devices["AA:BB:CC:DD:EE:1B"]
        assert d.ip == "192.168.1.127"
        assert d.interface == "veip0.2"

    def test_device_not_in_dhcp_is_included(self, arp_html):
        macs = {d.mac for d in _parse_arp(arp_html)}
        assert "AA:BB:CC:DD:EE:1C" in macs  # 1.1.1.2 — not a 192.168 address

    def test_returns_empty_on_empty_string(self):
        assert _parse_arp("") == []


# ---------------------------------------------------------------------------
# _parse_wifi
# ---------------------------------------------------------------------------


class TestParseWifi24:
    def test_device_count(self, wifi_24_html):
        assert len(_parse_wifi(wifi_24_html, band_hint="2.4GHz")) == 11

    def test_main_network_device(self, wifi_24_html):
        devices = {d.mac: d for d in _parse_wifi(wifi_24_html, band_hint="2.4GHz")}
        d = devices["AA:BB:CC:DD:EE:0C"]
        assert d.band == "2.4GHz"
        assert d.interface == "wl0"
        assert d.ssid == "WIFI"

    def test_rssi_is_negative_integer(self, wifi_24_html):
        devices = {d.mac: d for d in _parse_wifi(wifi_24_html, band_hint="2.4GHz")}
        assert devices["AA:BB:CC:DD:EE:0C"].rssi == -61
        assert devices["AA:BB:CC:DD:EE:12"].rssi == -41
        assert devices["AA:BB:CC:DD:EE:10"].rssi == -75

    def test_all_rssi_are_negative(self, wifi_24_html):
        devices = _parse_wifi(wifi_24_html, band_hint="2.4GHz")
        assert all(d.rssi < 0 for d in devices)

    def test_guest_device_interface(self, wifi_24_html):
        devices = {d.mac: d for d in _parse_wifi(wifi_24_html, band_hint="2.4GHz")}
        d = devices["AA:BB:CC:DD:EE:04"]
        assert d.interface == "wl0.1"
        assert d.ssid == "WIFI_D"
        assert d.band == "2.4GHz"
        assert d.is_guest is True

    def test_main_network_device_is_not_guest(self, wifi_24_html):
        devices = {d.mac: d for d in _parse_wifi(wifi_24_html, band_hint="2.4GHz")}
        assert devices["AA:BB:CC:DD:EE:0C"].is_guest is False

    def test_three_guest_devices(self, wifi_24_html):
        devices = _parse_wifi(wifi_24_html, band_hint="2.4GHz")
        assert sum(1 for d in devices if d.is_guest) == 3


class TestParseWifi5:
    def test_device_count(self, wifi_5_html):
        assert len(_parse_wifi(wifi_5_html, band_hint="5GHz")) == 1

    def test_5ghz_device_attributes(self, wifi_5_html):
        devices = _parse_wifi(wifi_5_html, band_hint="5GHz")
        d = devices[0]
        assert d.mac == "AA:BB:CC:DD:EE:20"
        assert d.band == "5GHz"
        assert d.interface == "wl1"
        assert d.ssid == "WIFI5"
        assert d.rssi == -55

    def test_returns_empty_on_header_only_table(self):
        html = """
        <html><body>
        <table>
          <tr><td>MAC</td><td>SSID</td><td>Interface</td><td>RSSI</td></tr>
        </table>
        </body></html>
        """
        assert _parse_wifi(html, band_hint="5GHz") == []


# ---------------------------------------------------------------------------
# _parse_uptime
# ---------------------------------------------------------------------------


class TestParseUptime:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("1D 15H 31M 10S", 142270),  # fixture value
            ("0D 4H 28M 53S", 16133),
            ("2D 0H 0M 0S", 172800),
            ("0D 0H 0M 1S", 1),
            ("0D 0H 0M 0S", 0),
            ("", 0),
        ],
    )
    def test_parse_uptime(self, raw, expected):
        assert _parse_uptime(raw) == expected

    def test_case_insensitive(self):
        assert _parse_uptime("1d 1h 1m 1s") == 86400 + 3600 + 60 + 1


# ---------------------------------------------------------------------------
# _parse_info
# ---------------------------------------------------------------------------


class TestParseInfo:
    def test_uptime_raw(self, info_html):
        info = _parse_info(info_html)
        assert info.uptime_raw == "1D 15H 31M 10S"

    def test_uptime_seconds(self, info_html):
        info = _parse_info(info_html)
        assert info.uptime_seconds == 142270

    def test_software_version_from_static_row(self, info_html):
        # "Software Version:" is a static <tr> in the fixture — parseable.
        info = _parse_info(info_html)
        assert info.software_version == "Software version"

    def test_wireless_driver_not_available(self, info_html):
        # "Wireless Driver Version:" is rendered by JavaScript; BeautifulSoup
        # cannot execute JS so this field remains empty from server-side HTML.
        info = _parse_info(info_html)
        assert info.wireless_driver == ""

    def test_returns_empty_info_on_empty_string(self):
        info = _parse_info("")
        assert info.uptime_raw == ""
        assert info.uptime_seconds == 0
        assert info.software_version == ""


# ---------------------------------------------------------------------------
# _is_login_page
# ---------------------------------------------------------------------------


class TestIsLoginPage:
    def test_login_page_detected_by_input_name(self, login_html):
        assert _is_login_page(login_html) is True

    def test_dhcp_page_is_not_login(self, dhcp_html):
        assert _is_login_page(dhcp_html) is False

    def test_arp_page_is_not_login(self, arp_html):
        assert _is_login_page(arp_html) is False

    def test_wifi_page_is_not_login(self, wifi_24_html):
        assert _is_login_page(wifi_24_html) is False

    def test_empty_string_is_not_login(self):
        assert _is_login_page("") is False

    def test_minimal_login_indicator(self):
        assert _is_login_page('<input name="loginPassword">') is True
